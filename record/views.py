from django.shortcuts import render
from .models import Student, Record, Class , Subject , StudentRecord
from django.db.models import Q
from .form import RecordForm , StudentForm , ClassForm , SubjectForm , StudentRecordForm

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
    context = dict(student=student)
    return render(request, "student.html", context)

def classView(request):
    school_class = Class.objects.all()
    context = dict(school_class=school_class)
    return render(request, "class.html", context)
    
def getRecord(request,id):
  record = Record.objects.get(id=id)
  students = StudentRecord.objects.filter(record=record)
  # records = Record.objects.filter(title=record.title)
  context = dict(record = record,students = students)
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
    else:
        form = form_class()
        saved = ""
    for field in form.fields.values():
        field.widget.attrs.update({'class':'form-control'})
    context = dict(form=form,saved=saved ,form_type=get_form)
    return render(request,'record-form.html',context)


def save_form(form):
    if form.is_valid():
        form.save()
        return "Record is created successfully"
    return "Error saving form"
