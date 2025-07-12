from django.forms import ModelForm
from .models import Student, Record, Class , Subject , StudentRecord , Topic 

class RecordForm(ModelForm):
	class Meta:
		model = Record 
		exclude = ["user"]


class SubjectForm(ModelForm):
	class Meta:
		model = Subject
		exclude = ["user"]


class ClassForm(ModelForm):
	class Meta:
		model = Class
		exclude = ["user"]


class StudentForm(ModelForm):
	class Meta:
		model = Student
		exclude = ["user"]

class StudentRecordForm(ModelForm):
	class Meta:
		model = StudentRecord
		exclude = ["user"]


class TopicForm(ModelForm):
	class Meta:
		model = Topic
		exclude = ["user"]