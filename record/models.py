from django.db import models
from django.shortcuts import reverse
import secrets
import hashlib
from django.db import models
from itsdangerous import TimestampSigner, BadSignature
from django.contrib.auth.hashers import make_password, check_password
from uuid import uuid4

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
    role = models.CharField(choices=[("Teacher","Teacher"),("School Administration","School Administration"),("Student","Student")],default="Teacher")
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
  class_teacher = models.ForeignKey(User,related_name="class_name",on_delete=models.CASCADE,null=True,blank=True)
  
  class Meta:
    unique_together = ("user","name","batch")
  
  def __str__(self):
    return f"{self.name} {self.batch}"

class Student(UserModel):
  name = models.CharField(max_length=100000)
  class_name = models.ForeignKey(Class, related_name="student",on_delete=models.CASCADE)
  gender = models.CharField(choices=[("Male","Male"),("Female","Female")],null=True,blank=True)
  admission_number = models.IntegerField(null=True,blank=True)
  contact_info = models.CharField(max_length=9000000,null=True,blank=True)
  date_of_birth = models.CharField(max_length=1000000,null=True,blank=True)
  school = models.ForeignKey(School,related_name="Student",on_delete=models.CASCADE,null=True,blank=True)
  #profile_photo = models.ImageField(null=True,blank=True)

  class Meta:
    unique_together = ("name","class_name")
  
  def __str__(self):
    return self.name
    
  def save(self):
    self.school = self.user.school
    super().save()

class Subject(UserModel):
  name = models.CharField(max_length=1000000,unique=True)

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
    return self.subject.name

class Record(UserModel):
  title = models.CharField(max_length=10000,choices=TERM_CHOICES)
  subject = models.ForeignKey(SubjectTeacher,related_name='record',on_delete=models.CASCADE,null=True,blank=True)
  date_created = models.DateTimeField(auto_now_add=True)
  record_type = models.CharField(choices=[('Test','Test'),('Exam','Exam'),("Assignment","Assignment"),("Notes","Notes")],max_length=1000000)
  total_score = models.IntegerField()
  class_name = models.ForeignKey(Class,on_delete=models.CASCADE,related_name="record",null=True,blank=True)
  record_number = models.IntegerField()

  class Meta: 
    unique_together = ("title","subject","class_name","record_type","record_number")

  def __str__(self):
    return f"{self.title} {self.subject} {self.record_type} {self.class_name} ({self.record_number})"

   
class StudentRecord(UserModel):
  student = models.ForeignKey(Student,related_name="record",on_delete=models.CASCADE)
  record =  models.ForeignKey(Record,related_name='evaluation',on_delete=models.CASCADE)
  score = models.IntegerField()
  
  class Meta:
    unique_together = ("student","record")
  
  def __str__(self):
    return f"{self.student.name} {self.record.title} {self.record.subject}"
    
  
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
