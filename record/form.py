from .models import Student, Record, Class , Subject , StudentRecord , Topic , User,SubjectTeacher
from django import forms

class BaseForm(forms.ModelForm):
    """Base form class with consistent styling"""
    
    def __init__(self,*args, **kwargs):
        try:
          user = kwargs.pop("user")
        except KeyError:
          pass
        super().__init__(*args, **kwargs)
        self.add_form_styling()
    
    def add_form_styling(self):
      for field_name, field in self.fields.items():
        widget = field.widget
        
        # Check if it's a checkbox or boolean field
        if isinstance(widget, forms.CheckboxInput):
            # Checkboxes need different styling
            widget.attrs.update({
                'class': 'form-p p-2',
                'role': 'switch'  # Optional: makes it a toggle switch in Bootstrap 5
            })
        
        # Check if it's a select/dropdown
        elif isinstance(widget, forms.Select):
            widget.attrs.update({
                'class': 'form-control form-select form-p',
                'placeholder': field.label or ''
            })
        
        # Check if it's a textarea
        elif isinstance(widget, forms.Textarea):
            widget.attrs.update({
                'class': 'form-control form-p',
                'placeholder': field.label or '',
                'rows': widget.attrs.get('rows', 3)  # Default 3 rows
            })
        
        # Check if it's a file input
        elif isinstance(widget, forms.FileInput):
            widget.attrs.update({
                'class': 'form-control form-p',
            })
        
        # Check if it's a multiple choice checkbox
        elif isinstance(widget, forms.CheckboxSelectMultiple):
            widget.attrs.update({
                'class': 'form-check-input'
            })
        
        # Check if it's radio buttons
        elif isinstance(widget, forms.RadioSelect):
            widget.attrs.update({
                'class': 'form-check-input'
            })
        
        # Default for text inputs, number inputs, etc.
        else:
            widget.attrs.update({
                'class': 'form-control form-p',
                'placeholder': field.label or ''
            })
            
class UserForm(BaseForm):
  password = forms.CharField(widget=forms.PasswordInput())
  confirm_password = forms.CharField(widget=forms.PasswordInput())
  class Meta:
    model = User
    exclude = ["secret_key","role","school","email","full_name"]
    
class RecordForm(BaseForm):
	class Meta:
		model = Record 
		exclude = ["user"]
		
	def __init__(self,*args,**kwargs):
	  user = kwargs.pop("user")
	  super().__init__(*args,**kwargs)
	  class_name = Class.objects.for_user(user)
	  subject = SubjectTeacher.objects.for_user(user)
	  self.fields["class_name"].queryset = class_name
	  self.fields["subject"].queryset = subject



class SubjectForm(BaseForm):
	
  class Meta:
	  model = SubjectTeacher
	  exclude = ["user"]

  def __init__(self,*args,**kwargs):
	  user = kwargs.pop("user")
	  super().__init__(*args,**kwargs)
	  class_name = Class.objects.for_user(user)
	  self.fields["class_name"].queryset = class_name
	  
class ClassForm(BaseForm):
	class Meta:
		model = Class
		exclude = ["user","class_teacher"]


class StudentForm(BaseForm):
  class Meta:
    model = Student
    exclude = ["user","school"]
    
  def __init__(self,*args,**kwargs):
	  user = kwargs.pop("user")
	  super().__init__(*args,**kwargs)
	  class_name = Class.objects.for_user(user)
	  self.fields["class_name"].queryset = class_name
	 
	  
	   
	   

class StudentRecordForm(BaseForm):
	class Meta:
		model = StudentRecord
		exclude = ["user"]
		
	def __init__(self,*args,**kwargs):
	  user = kwargs.pop("user")
	  super().__init__(*args,**kwargs)
	  record = Record.objects.for_user(user)
	  student = Student.objects.filter(school=user.school)
	  self.fields["record"].queryset = record
	  self.fields["student"].queryset = student


class TopicForm(BaseForm):
	class Meta:
		model = Topic
		exclude = ["user"]