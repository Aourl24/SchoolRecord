from django.shortcuts import render
from .models import Student, Record, Class

def homeView(request):
    return render(request,"home.html")
    
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
  context = dict(record = record)
  return render(request,'record-detail.html',context)
  
def getStudent(request,id):
  student = Student.objects.get(id=id)
  context = dict(student = student)
  return render(request,'student-detail.html',context)
  
def getClass(request,id):
  class_name = Class.objects.get(id=id)
  context = dict(class_name = class_name)
  return render(request,'class-detail.html',context)