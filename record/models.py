from django.db import models

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
  
  def __str__(self):
    return self.name
  
    
class Record(models.Model):
  title = models.CharField(max_length=10000,choices=TERM_CHOICES)
  date_created = models.DateTimeField(auto_now_add=True)
  student = models.ForeignKey(Student,related_name="record",on_delete=models.CASCADE)
  score = models.IntegerField()
  type_name = models.CharField(max_length=100000,choices=[("Test","Test"),("Exam","Exam")])
  total = models.IntegerField()
  
  def __str__(self):
    return f"{self.student.name} {self.title} {self.type_name}"
  

#class Evaluation(models.Model):
 # name = models.CharField(max_length=100000)
  
  #def __str__(self):
   # return self.name