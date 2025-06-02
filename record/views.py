from django.shortcuts import render
from .models import Student, Record, Class , Subject , StudentRecord
from django.db.models import Q
from .form import RecordForm , StudentForm , ClassForm , SubjectForm , StudentRecordForm
from django.http import HttpResponse


def homeView(request,part=None):
    records = Record.objects.all()
    students = Student.objects.all()
    classes = Class.objects.all()
    subject = Subject.objects.all()
    context = dict(records=records,students=students,classes=classes,subject=subject)
    return render(request,"home-partial.html" if part else'home.html',context)
    

def recordView(request):
    record = Record.objects.all()
    context = dict(record=record)
    return render(request, "record.html", context)

def studentView(request):
    student = Student.objects.all()
    subjects = Subject.objects.all()
    classes = Class.objects.values('name').distinct()
    context = dict(student=student,subjects=subjects,classes=classes)
    return render(request, "student.html", context)

def classView(request):
    school_class = Class.objects.all()
    context = dict(school_class=school_class)
    return render(request, "class.html", context)
    
def getRecord(request,id):
  record = Record.objects.get(id=id)
  students = StudentRecord.objects.filter(record=record)
  context = dict(record = record,students = students,edit=True)
  return render(request,'record-detail.html',context)
  
def getStudent(request,id):
  student = Student.objects.get(id=id)
  records = StudentRecord.objects.filter(student=student)
  context = dict(student = student,records=records)
  return render(request,'student-detail.html',context)
  
def getClass(request,id):
  class_name = Class.objects.get(id=id)
  student = Student.objects.filter(class_name=class_name)
  context = dict(class_name = class_name , student = student)
  return render(request,'class-detail.html',context)

def getClassRecord(request,id):
    class_name = Class.objects.get(id=id)
    record = Record.objects.filter(class_name=class_name)
    context = dict(class_name=class_name,record=record)
    return render(request,'record.html',context)

def getClassStudent(request,id):
    class_name = Class.objects.get(id=id)
    student = Student.objects.filter(class_name=class_name)
    context = dict(student=student)
    return render(request,'student.html',context)

def formView(request,get_form):
    match get_form:
        case 'record':
            form_class = RecordForm
        case 'subject':
            form_class = SubjectForm
        case 'class':
            form_class = ClassForm
        case 'student':
            form_class = StudentForm
        case 'student-record':
            form_class = StudentRecordForm
        case _:
            form = RecordForm
    

    if request.method == 'POST':
        form = form_class(request.POST)
        saved=save_form(form)
        return HttpResponse(saved)
    else:
        form = form_class()
        saved = ""
    
    for field in form.fields.values():
        field.widget.attrs.update({'class':'form-control p-3'})
    context = dict(form=form,saved=saved ,form_type=get_form,target="drop-area")
    return render(request,'record-form.html',context)


def save_form(form):
    if form.is_valid():
        instance = form.save()

        # Dynamically fetch all cleaned data except hidden fields
        fields = [f.name for f in instance._meta.fields if f.name in form.cleaned_data]
        field_values = [f"{f.capitalize()}: {form.cleaned_data.get(f)}" for f in fields]
        display_data = "<br>".join(field_values)

        return f"<div class='alert alert-primary'>{display_data}<br>Record was created successfully.</div>"

    # Return detailed form errors
    error_messages = []
    for field, errors in form.errors.items():
        label = form.fields.get(field).label if field in form.fields else field
        for error in errors:
            error_messages.append(f"<li><strong>{label}:</strong> {error}</li>")
    error_html = "<ul>" + "".join(error_messages) + "</ul>"

    return f"<div class='alert alert-danger'><strong>Error saving form:</strong>{error_html}</div>"

def searchView(request):
  data = request.GET.get('search')
  record = Record.objects.filter(title__icontains=data)
  student = Student.objects.filter(name__icontains=data)
  school_class = Class.objects.filter(name__icontains=data)
  context=dict(record=record,student=student,school_class=school_class)
  return render(request,'search.html',context)

def addToRecord(request, id):
    record = Record.objects.get(id=id)
    form = StudentRecordForm(initial={'record': record})
    form.fields['student'].queryset = Student.objects.filter(class_name=record.class_name) 
    for field in form.fields.values():
        field.widget.attrs.update({'class':'form-control p-3'})
    #form.fields['record'].widget = forms.HiddenInput()

    return render(request, 'record-form.html', {'form': form,'saved':'','form_type':'student-record','target':'addHere','recordForm':True})

def filterRecord(request):
  class_name = request.GET.get('class')
  sbj_id = request.GET.get('subject')
  #if sbj_id == "All Subject":
  subject = Subject.objects.get(id=sbj_id)
  term = request.GET.get('term')
  record_type = request.GET.get('r_type')
  records = Record.objects.filter(subject=subject,record_type=record_type,class_name__name=class_name)
  students = StudentRecord.objects.filter(record__in=records)
  record = dict(class_name=class_name,subject=subject,title=term,record_type=record_type,id=0,total_score= records.first().total_score if records else None)
  context = dict(record=record, students=students,edit=None)
  return render(request,'record-detail.html',context)
  
  
def filterStudent(request):
  #students = StudentRecord.objects.filter(record=record)
  filter = request.GET.get("filter")
  sign = request.GET.get("sign")
  score = request.GET.get("score")
  students_list = request.GET.getlist("students")
  edit = request.GET.get("edit")
  #students_list = [int(std) for std in students_list]
  students = StudentRecord.objects.filter(student__id__in=students_list)
  
  if edit == "None":
    edit = False
  
  match sign:
    case "=":
      students = students.filter(score=score)
    case ">":
      students = students.filter(score__gt=score)
    case "<" :
      students = students.filter(score__lt=score)
    case _:
      pass
  
  match filter:
    case "alpha":
      students = students.order_by("student__name")
    case "score":
      students = students.order_by("-score")
    case _:
      pass
      
  return render(request,'students-table.html',dict(students=students,edit=edit))
  

def closeReq(request):
  return HttpResponse("")
  