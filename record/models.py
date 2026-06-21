from django.db import models
from django.shortcuts import reverse
import secrets
import hashlib
from django.db import models
from itsdangerous import TimestampSigner, BadSignature
from django.contrib.auth.hashers import make_password, check_password
from uuid import uuid4
from django.core.exceptions import ValidationError
from django.utils import timezone


def current_academic_session():
    """
    Best-guess default for a new Class's session, based on today's date.
    Most school years run roughly September-July, so September onward
    counts as the start of a new session (e.g. "2026/2027").
    Purely a default — teachers can override it on the class form.
    """
    today = timezone.now()
    if today.month >= 9:
        return f"{today.year}/{today.year + 1}"
    return f"{today.year - 1}/{today.year}"

class UserQuerySet(models.QuerySet):
    def for_user(self, user):
        return self.filter(user)
    
class StudentRecordQuerySet(UserQuerySet):
    def by_score_range(self, min_score, max_score):
        return self.filter(score__gte=min_score, score__lte=max_score)
    
    def passed(self, passing_score=50):
        return self.filter(score__gte=passing_score)
    
    def failed(self, passing_score=50):
        return self.filter(score__lt=passing_score)
        

class UserManager(models.Manager):
    def get_queryset(self):
        return UserQuerySet(self.model, using=self._db)

    def for_user(self, user):
        return self.get_queryset().filter(user=user)

    def create_for_user(self, user, **kwargs):
        return self.model.objects.create(user=user, **kwargs)

class School(models.Model):
  name = models.CharField(max_length=10000)
  
  def __str__(self):
    return self.name
    
class User(models.Model):
    full_name = models.CharField(max_length=500, blank=True,null=True)
    username = models.CharField(max_length=255, unique=True)
    email = models.EmailField(max_length=500,blank=True,null=True)
    password = models.CharField(max_length=255)
    school = models.ForeignKey(School,related_name="user",null=True,blank=True,on_delete=models.CASCADE)
    role = models.CharField(choices=[("Teacher","Teacher"),("School Administration","School Administration"),("Student","Student")],default="Teacher",max_length=255)
    secret_key = models.CharField(max_length=255, blank=True, null=True)

    def set_password(self, raw_password):
        self.password = make_password(raw_password)
        self.save()

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def ensure_secret(self):
        if not self.secret_key:
            self.secret_key = secrets.token_urlsafe(32)
            self.save()

    def generate_token(self):
        self.ensure_secret()
        signer = TimestampSigner(self.secret_key)
        token = signer.sign(f"{self.id}:{uuid4()}").decode()
        return token
        
    def verify_token(self, token, max_age=60*60*24):
          signer = TimestampSigner(self.secret_key)
          try:
              unsigned = signer.unsign(token, max_age=max_age).decode()
              user_id, _ = unsigned.split(":")  # Grab the ID part
              return str(self.id) == user_id
          except BadSignature:
              return False
    
 
class UserModel(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    objects = UserManager()
    
    class Meta:
        abstract = True
        
    
CLASSES = [
    ("JSS1", "JSS1"),
    ("JSS2", "JSS2"),
    ("JSS3", "JSS3"),
    ("SS1", "SS1"),
    ("SS2", "SS2"),
    ("SS3", "SS3"),
]

TERM_CHOICES = [
    ('First Term', 'First Term'),
    ('Second Term', 'Second Term'),
    ('Third Term', 'Third Term'),
]

#class User(models.Model):
 # username = models.CharField(max_lemght)

class Class(UserModel):
  name = models.CharField(max_length=100000,choices=CLASSES)
  batch = models.CharField(max_length=100000,choices=[("A","A"),("B","B"),("C","C"),("D","D")])
  session = models.CharField(max_length=20, default=current_academic_session, help_text="Academic session, e.g. 2025/2026")
  class_teacher = models.ForeignKey(User,related_name="class_name",on_delete=models.CASCADE,null=True,blank=True)
  
  class Meta:
    unique_together = ("user","name","batch","session")
  
  def __str__(self):
    return f"{self.name} {self.batch} ({self.session})"

class Student(UserModel):
  name = models.CharField(max_length=100000)
  class_name = models.ForeignKey(Class, related_name="student",on_delete=models.CASCADE)
  gender = models.CharField(choices=[("Male","Male"),("Female","Female")],null=True,blank=True,max_length=255)
  admission_number = models.IntegerField(null=True,blank=True)
  contact_info = models.CharField(max_length=9000000,null=True,blank=True)
  date_of_birth = models.CharField(max_length=1000000,null=True,blank=True)
  school = models.ForeignKey(School,related_name="Student",on_delete=models.CASCADE,null=True,blank=True)
  #profile_photo = models.ImageField(null=True,blank=True)

  class Meta:
    unique_together = ("name","class_name")
  
  def __str__(self):
    return self.name
    
  def save(self,**kwargs):
    self.school = self.user.school
    super().save(**kwargs)


class Subject(models.Model):
  """
  Subjects are a SHARED list across every teacher — "Mathematics" is the
  same row no matter who teaches it. This used to inherit UserModel and be
  filtered with .for_user(), which meant each teacher silently got their
  own private, isolated copy of every subject name (and a unique=True
  constraint that fought that at the same time). Per-teacher assignment of
  a subject to a class now lives entirely on SubjectTeacher, which still
  has its own `user` field.

  NOTE: if you already have duplicate Subject rows per teacher in your
  database (e.g. several "Mathematics" rows owned by different users),
  merge them — repoint any SubjectTeacher.subject FKs to one canonical
  Subject row and delete the rest — BEFORE running migrations, or the new
  unique constraint will fail to apply cleanly.
  """
  name = models.CharField(max_length=255, unique=True)

  def save(self, *args, **kwargs):
    # Normalize so "math", "Math", "MATH" all collapse to one row instead
    # of slipping past the unique constraint as separate subjects.
    self.name = self.name.strip().title()
    super().save(*args, **kwargs)

  def __str__(self):
    return self.name

  def get_absolute_url(self):
    return reverse('subject-detail',args=[self.id])
    
class SubjectTeacher(UserModel):
  subject = models.ForeignKey(Subject,related_name="subjectTeacher",null=True,blank=True,on_delete=models.CASCADE)
  class_name = models.ForeignKey(Class,related_name="subjectTeacher",null=True,blank=True,on_delete=models.CASCADE)
  
  class Meta: 
    unique_together = ("subject","class_name")

  def __str__(self):
    return self.subject.name if self.subject else "Unassigned Subject"

import re
from django.core.exceptions import ValidationError
from django.db import transaction

class Record(UserModel):
    title = models.CharField(max_length=10000, choices=TERM_CHOICES)
    subject = models.ForeignKey(SubjectTeacher, related_name='record', on_delete=models.CASCADE, null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    record_type = models.CharField(
        choices=[('Test','Test'), ('Exam','Exam'), ("Assignment","Assignment"), ("Notes","Notes")],
        max_length=1000
    )
    total_score = models.IntegerField()
    class_name = models.ForeignKey(Class, on_delete=models.CASCADE, related_name="record", null=True, blank=True)
    record_number = models.IntegerField(null=True, blank=True)
    logic = models.CharField(max_length=10000, null=True, blank=True)
    auto_create_records = models.BooleanField(default=True, help_text="Automatically create student records when logic is present")
    show_in_report = models.BooleanField(default=True,help_text="Indicate whether to include record in report ")

    class Meta:
        unique_together = ("title", "subject", "class_name", "record_type", "record_number")

    def __str__(self):
        return f"{self.title} {self.subject} {self.record_type} {self.class_name} ({self.record_number})"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Auto-create StudentRecords if enabled and logic exists
        if is_new and self.logic and self.auto_create_records:
            self.create_student_records_with_logic()
    
    @transaction.atomic
    def create_student_records_with_logic(self):
        """
        Create StudentRecords for all students in this class.
        Only creates records that don't already exist.
        """
        students = Student.objects.filter(class_name=self.class_name)
        
        created_count = 0
        failed_students = []
        
        for student in students:
            # Skip if StudentRecord already exists
            if StudentRecord.objects.filter(student=student, record=self).exists():
                continue
            
            try:
                # Create the StudentRecord - it will auto-calculate via save()
                StudentRecord.objects.create(
                    student=student,
                    record=self,
                    score=0  # Will be overwritten by process_logic in save()
                )
                created_count += 1
            except Exception as e:
                failed_students.append({
                    'student': student.name,
                    'error': str(e)
                })
        
        return {
            'created': created_count,
            'failed': failed_students
        }
    
    def recalculate_all_student_scores(self):
        """
        Recalculate scores for all existing StudentRecords.
        Useful when logic is updated or dependent records change.
        """
        student_records = StudentRecord.objects.filter(record=self)
        updated_count = 0
        
        for sr in student_records:
            try:
                if self.logic:
                    sr.score = sr.process_logic()
                    sr.save()
                    updated_count += 1
            except Exception as e:
                print(f"Failed to recalculate for {sr.student.name}: {e}")
        
        return updated_count


class StudentRecord(UserModel):
    student = models.ForeignKey(Student, related_name="record", on_delete=models.CASCADE)
    record = models.ForeignKey(Record, related_name='evaluation', on_delete=models.CASCADE)
    score = models.IntegerField()

    class Meta:
        unique_together = ("student", "record")

    def __str__(self):
        return f"{self.student.name} {self.record.title} {self.record.subject}"

    def _get_referenced_record_score(self, ref_pattern):
        """
        Parse reference patterns and return the score from another record.
        Supported formats:
        - @record_number -> same subject, class, title, type
        - @record_type:record_number -> same subject, class, title
        - @title:record_type:record_number -> same subject, class
        - @title:subject:record_type:record_number -> specific record
        """
        parts = ref_pattern.strip('@').split(':')
        
        filters = {
            'evaluation__student': self.student,
        }
        
        if len(parts) == 1:
            filters.update({
                'title': self.record.title,
                'subject': self.record.subject,
                'class_name': self.record.class_name,
                'record_type': self.record.record_type,
                'record_number': int(parts[0])
            })
        elif len(parts) == 2:
            filters.update({
                'title': self.record.title,
                'subject': self.record.subject,
                'class_name': self.record.class_name,
                'record_type': parts[0],
                'record_number': int(parts[1])
            })
        elif len(parts) == 3:
            filters.update({
                'title': parts[0],
                'subject': self.record.subject,
                'class_name': self.record.class_name,
                'record_type': parts[1],
                'record_number': int(parts[2])
            })
        elif len(parts) == 4:
            subject = SubjectTeacher.objects.filter(
                subject__name=parts[1],
                teacher=self.record.subject.teacher
            ).first()
            filters.update({
                'title': parts[0],
                'subject': subject,
                'class_name': self.record.class_name,
                'record_type': parts[2],
                'record_number': int(parts[3])
            })
        
        try:
            referenced_record = Record.objects.get(**filters)
            student_record = StudentRecord.objects.get(
                student=self.student,
                record=referenced_record
            )
            return student_record.score
        except (Record.DoesNotExist, StudentRecord.DoesNotExist):
            raise ValidationError(f"Referenced record not found: {ref_pattern}")

    def process_logic(self):
        """
        Process the logic string and calculate the score.
        
        Supported syntax:
        - Arithmetic: +, -, *, /, //, %, **
        - References: @record_number, @record_type:number, etc.
        - Numbers: integers and floats
        - Parentheses for grouping
        - Functions: avg(), min(), max(), sum()
        
        Examples:
        - "@1 + @2" -> sum of record 1 and 2
        - "@1 * 0.5 + @2 * 0.5" -> weighted average
        - "avg(@1, @2, @3)" -> average of three records
        - "(@Test:1 + @Test:2) / 2" -> average of two tests
        """
        if not self.record.logic:
            return self.score
        
        logic = self.record.logic.strip()
        
        # Handle function calls (avg, min, max, sum)
        func_pattern = r'(avg|min|max|sum)\((.*?)\)'
        
        def replace_function(match):
            func_name = match.group(1)
            args = match.group(2)
            
            arg_list = [arg.strip() for arg in args.split(',')]
            values = []
            
            for arg in arg_list:
                if arg.startswith('@'):
                    values.append(self._get_referenced_record_score(arg))
                else:
                    values.append(eval(arg))
            
            operations = {
                'avg': lambda x: sum(x) / len(x),
                'min': min,
                'max': max,
                'sum': sum
            }
            
            return str(operations[func_name](values))
        
        # Replace functions first
        while re.search(func_pattern, logic):
            logic = re.sub(func_pattern, replace_function, logic)
        
        # Replace @ references with actual scores
        ref_pattern = r'@[\w:]+'
        
        def replace_reference(match):
            ref = match.group(0)
            return str(self._get_referenced_record_score(ref))
        
        logic = re.sub(ref_pattern, replace_reference, logic)
        
        # Safely evaluate the expression
        try:
            allowed_names = {"__builtins__": {}}
            calculated_score = eval(logic, allowed_names)
            return int(round(calculated_score))
        except Exception as e:
            raise ValidationError(f"Invalid logic expression: {logic}. Error: {str(e)}")

    def save(self, *args, **kwargs):
        # Process logic before saving
        if self.record.logic:
            try:
                self.score = self.process_logic()
            except ValidationError as e:
                # If logic fails, keep manual score but log the error
                print(f"Logic calculation failed for {self}: {e}")
        
        # Validate score
        if self.score > self.record.total_score:
            raise ValidationError(f"Score ({self.score}) can't be greater than Total Score ({self.record.total_score})")
        
        if self.score < 0:
            raise ValidationError("Score can't be negative")
        
        super().save(*args, **kwargs)


# MANAGEMENT COMMAND OR ADMIN ACTION
# Use this to manually trigger student record creation if needed

def bulk_create_student_records_for_record(record_id):
    """
    Utility function to create StudentRecords for a specific Record.
    Can be called from admin action or management command.
    """
    try:
        record = Record.objects.get(id=record_id)
        result = record.create_student_records_with_logic()
        return {
            'success': True,
            'message': f"Created {result['created']} student records",
            'failed': result['failed']
        }
    except Record.DoesNotExist:
        return {
            'success': False,
            'error': 'Record not found'
        }


class History(UserModel):
  title = models.CharField(max_length=1000000,null=True,blank=True)
  url = models.URLField(null=True,blank=True)
  time = models.DateTimeField(auto_now_add=True,null=True,blank=True)

  def __str__(self):
    return self.title


class Topic(UserModel):
  subject = models.ForeignKey(Subject,related_name='topic',on_delete=models.CASCADE)
  class_name = models.ForeignKey(Class,related_name="topic",on_delete=models.CASCADE,null=True,blank=True)
  title = models.CharField(max_length=10000)
  content = models.TextField(null=True,blank=True)
  order = models.IntegerField(null=True,blank=True)
  done = models.BooleanField(default=False)

  def __str__(self):
    return self.title


  def get_absolute_url(self):
    return reverse('topic-detail',args=[self.id])    
