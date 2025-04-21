from django.forms import ModelForm
from .models import Student, Record, Class , Subject , StudentRecord

class RecordForm(ModelForm):
	class Meta:
		model = Record 
		fields = "__all__"


class SubjectForm(ModelForm):
	class Meta:
		model = Subject
		fields = "__all__"


class ClassForm(ModelForm):
	class Meta:
		model = Class
		fields = "__all__"


class StudentForm(ModelForm):
	class Meta:
		model = Student
		fields = "__all__"

class StudentRecordForm(ModelForm):
	class Meta:
		model = StudentRecord
		fields = "__all__"