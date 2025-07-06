from django.db import models
from django.shortcuts import reverse

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

class Class(models.Model):
  name = models.CharField(max_length=100000,choices=CLASSES)
  batch = models.CharField(max_length=100000,choices=[("A","A"),("B","B"),("C","C"),("D","D")])
  
  class Meta:
    unique_together = ("name","batch")
  
  def __str__(self):
    return f"{self.name} {self.batch}"

class Student(models.Model):
  name = models.CharField(max_length=100000)
  class_name = models.ForeignKey(Class, related_name="student",on_delete=models.CASCADE)

  class Meta:
    unique_together = ("name","class_name")
  
  def __str__(self):
    return self.name

class Subject(models.Model):
  name = models.CharField(max_length=1000000,unique=True)

  def __str__(self):
    return self.name

  def get_absolute_url(self):
    return reverse('subject-detail',args=[self.id])

class Record(models.Model):
  title = models.CharField(max_length=10000,choices=TERM_CHOICES)
  subject = models.ForeignKey(Subject,related_name='record',on_delete=models.CASCADE)
  date_created = models.DateTimeField(auto_now_add=True)
  record_type = models.CharField(choices=[('Test','Test'),('Exam','Exam')],max_length=1000000)
  total_score = models.IntegerField()
  class_name = models.ForeignKey(Class,on_delete=models.CASCADE,related_name="record",null=True,blank=True)
  record_number = models.IntegerField()

  class Meta: 
    unique_together = ("title","subject","class_name","record_type","record_number")

  def __str__(self):
    return f"{self.title} {self.subject} {self.record_type} {self.class_name} ({self.record_number})"

   
class StudentRecord(models.Model):
  student = models.ForeignKey(Student,related_name="record",on_delete=models.CASCADE)
  record =  models.ForeignKey(Record,related_name='evaluation',on_delete=models.CASCADE)
  score = models.IntegerField()
  
  class Meta:
    unique_together = ("student","record")
  
  def __str__(self):
    return f"{self.student.name} {self.record.title} {self.record.subject}"
    
  
class History(models.Model):
  title = models.CharField(max_length=1000000,null=True,blank=True)
  url = models.URLField(null=True,blank=True)
  time = models.DateTimeField(auto_now_add=True,null=True,blank=True)

  def __str__(self):
    return self.title


class Topic(models.Model):
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
