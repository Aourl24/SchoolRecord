from django.shortcuts import render,reverse,redirect
from .models import Student, Record, Class , Subject , StudentRecord,History , Topic, User
from django.db.models import Q
from .form import RecordForm , StudentForm , ClassForm , SubjectForm , StudentRecordForm , TopicForm
from django.http import HttpResponse
import datetime
from django.contrib.auth.hashers import make_password, check_password
from .decorator import login_require
from uuid import uuid4
from django.core import signing
from .report import generate_report
#from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

#SECRET_KEY = "my_super_secret"
#serializer = URLSafeTimedSerializer(SECRET_KEY)

def save_form(request,form):
    if form.is_valid():
        instance = form.save(commit=False)
        instance.user = request.user
        try:
          instance.save()

          fields = [f.name for f in instance._meta.fields if f.name in form.cleaned_data]
          field_values = [f"{f.capitalize()}: {form.cleaned_data.get(f)}" for f in fields]
          display_data = "<br>".join(field_values)
          return f"<div class='alert alert-primary'>{display_data}<br>Record was created successfully.</div>"
        except:
          error_html = "Data Already exist"
          return f"<div class='alert alert-danger'><strong>Error saving form:</strong>{error_html}</div>"
          

        

    # Return detailed form errors
    error_messages = []
    for field, errors in form.errors.items():
        label = form.fields.get(field).label if field in form.fields else field
        for error in errors:
            error_messages.append(f"<li><strong>{label}:</strong> {error}</li>")
    error_html = "<ul>" + "".join(error_messages) + "</ul>"

    return f"<div class='alert alert-danger'><strong>Error saving form:</strong>{error_html}</div>"

@login_require
def homeView(request,part=None):
    records = Record.objects.for_user(request.user)
    students = Student.objects.for_user(request.user)
    classes = Class.objects.for_user(request.user)
    subject = Subject.objects.for_user(request.user)
    context = dict(records=records,students=students,classes=classes,subject=subject)
    return render(request,"home-partial.html" if part else'home.html',context)
    
@login_require
def recordView(request):
    record = Record.objects.for_user(request.user)
    history = History.objects.get_or_create(user=request.user,title="Record List",url=reverse('record-list'))
    history[0].time=datetime.datetime.now()
    history[0].save()
    context = dict(record=record)
    return render(request, "record.html", context)

@login_require
def studentView(request):
    student = Student.objects.for_user(request.user)
    subjects = Subject.objects.for_user(request.user)
    classes = Class.objects.for_user(request.user).values('name').distinct()
    history = History.objects.get_or_create(user=request.user,title="Student List",url=reverse('student-list'))
    history[0].time=datetime.datetime.now()
    history[0].save()
    context = dict(student=student,subjects=subjects,classes=classes)
    return render(request, "student.html", context)

@login_require
def classView(request):
    school_class = Class.objects.for_user(request.user)
    history = History.objects.get_or_create(user=request.user,title="Class List",url=reverse('class-list'))
    history[0].time=datetime.datetime.now()
    history[0].save()
    context = dict(school_class=school_class)
    return render(request, "class.html", context)
 
@login_require   
def getRecord(request,id):
  record = Record.objects.get(id=id)
  students = StudentRecord.objects.filter(record=record)
  student_not = Student.objects.filter(class_name=record.class_name)
  students_without_record = student_not.exclude(record__in=students).order_by('name')
  
  history = History.objects.get_or_create(user=request.user,title=f"{record}",url=reverse('get-record',args=[id]))
  history[0].time=datetime.datetime.now()
  history[0].save()
  context = dict(record = record,students = students,students_without_record=students_without_record,edit=True,half=record.total_score/2)
  return render(request,'record-detail.html',context)

@login_require
def getStudent(request,id):
  student = Student.objects.get(id=id)
  records = StudentRecord.objects.filter(student=student)
  history = History.objects.get_or_create(user=request.user,title=f"{student}",url=reverse('get-student-detail',args=[id]))
  history[0].time=datetime.datetime.now()
  history[0].save()
  context = dict(student = student,records=records)
  return render(request,'student-detail.html',context)

@login_require 
def getClass(request,id):
  class_name = Class.objects.get(id=id)
  student = Student.objects.filter(class_name=class_name)
  history = History.objects.get_or_create(user=request.user,title=f"{class_name}",url=reverse('get-class',args=[id]))
  history[0].time=datetime.datetime.now()
  history[0].save()
  context = dict(class_name = class_name , student = student)
  return render(request,'class-detail.html',context)

@login_require
def getClassRecord(request,id):
    class_name = Class.objects.get(id=id)
    record = Record.objects.filter(class_name=class_name)
    history = History.objects.get_or_create(user=request.user,title=f"{class_name} records",url=reverse('get-class-record',args=[id]))
    history[0].time=datetime.datetime.now()
    history[0].save()
    context = dict(class_name=class_name,record=record,partial=True)
    return render(request,'record-list.html',context)

@login_require
def getClassStudent(request,id):
    class_name = Class.objects.get(id=id)
    student = Student.objects.filter(class_name=class_name).order_by("name")
    history = History.objects.get_or_create(user=request.user,title=f"{class_name} students",url=reverse('get-student',args=[id]))
    history[0].time=datetime.datetime.now()
    history[0].save()
    context = dict(student=student)
    return render(request,'student-list.html',context)

@login_require
def formView(request,get_form,update=False):
    model = None
    match get_form:
        case 'record':
            form_class = RecordForm
            if update:
              model = Record.objects.get(id=update)
        case 'subject':
            form_class = SubjectForm
            if update:
              model = Subject.objects.get(id=update)
        case 'class':
            form_class = ClassForm
            if update:
              model = Class.objects.get(id=update)
        case 'student':
            form_class = StudentForm
            if update:
              model = Student.objects.get(id=update)
        case 'student-record':
            form_class = StudentRecordForm
            if update:
              model = StudentRecord.objects.get(id=update)
        case 'topic':
            form_class = TopicForm
            if update:
              model = Topic.objects.get(id=update)
        case _:
            form = RecordForm
    

    if request.method == 'POST':
        if not model:
          form = form_class(request.POST)
        else:
          form = form_class(request.POST,instance=model)
        saved=save_form(request,form)
        history = History.objects.get_or_create(title=f"Create new {get_form}")
        history[0].time=datetime.datetime.now()
        history[0].save()
        return HttpResponse(saved)
    else:
        form = form_class(instance=model)
        saved = ""
    
    for field in form.fields.values():
        field.widget.attrs.update({'class':'form-control p-3'})
    context = dict(form=form,saved=saved ,form_type=get_form,target="drop-area",model=model,update=update)
    return render(request,'record-form.html',context)

@login_require
def searchView(request):
  data = request.GET.get('search')
  # record = Record.objects.for_user(request.user).filter(title__icontains=data)
  # student = Student.objects.for_user(request.user).filter(name__icontains=data)
  # school_class = Class.objects.for_user(request.user).filter(name__icontains=data)
  record = Record.objects.filter(title__icontains=data)
  student = Student.objects.filter(name__icontains=data)
  school_class = Class.objects.filter(name__icontains=data)
  context=dict(record=record,student=student,school_class=school_class)
  return render(request,'search.html',context)

def addToRecord(request, id):
    record = Record.objects.get(id=id)
    form = StudentRecordForm(initial={'record': record})
    students = StudentRecord.objects.filter(record=record)
    student_not = Student.objects.filter(class_name=record.class_name)
    students_without_record = student_not.exclude(record__in=students).order_by('name')
    form.fields['student'].queryset = students_without_record
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
  record_number = request.GET.get('number')
  records = Record.objects.filter(subject=subject,record_type=record_type,record_number=record_number,class_name__name=class_name)
  students = StudentRecord.objects.filter(record__in=records)
  record_list = [r.id for r in records]
  record = dict(class_name=class_name,subject=subject,title=term,record_type=record_type,id=0,total_score= records.first().total_score if records else None,half=records.first().total_score/2 if records else None )
  context = dict(record=record, record_list=record_list , students=students,edit=None)
  return render(request,'record-detail.html',context)
  
  
def filterStudent(request):
  #students = StudentRecord.objects.filter(record=record)
  filter = request.GET.get("filter")
  sign = request.GET.get("sign")
  score = request.GET.get("score")
  students_list = request.GET.getlist("students")
  record_get = request.GET.get('record')
  edit = request.GET.get("edit")
  record_list = request.GET.getlist("record-list")
  half = None
  #students_list = [int(std) for std in students_list]
  try:
    record = Record.objects.get(id=record_get)
    half = record.total_score/2
    students = StudentRecord.objects.filter(student__id__in=students_list,record=record)
  except Record.DoesNotExist:
    records = Record.objects.filter(id__in=record_list)
    students = StudentRecord.objects.filter(record__in=record_list)
    record = records.first()
    half = record.total_score/2
  
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
      
  return render(request,'students-table.html',dict(students=students,edit=edit,record=record,half=half))
  

def closeReq(request):
  return HttpResponse("")
  
def Report(request):
    classes_obj = Class.objects.all()
    classes = [c for c in classes_obj if c.batch == "A"]
    subjects = Subject.objects.all()
    context = dict(subjects=subjects, classes=classes)
    
    if request.method == "POST":
        subject_id = request.POST.get('subject')
        class_name = request.POST.get('class')
        batch = request.POST.get("batch")
        term = request.POST.get("term")
        sort_order = request.POST.get('sort', 'asc')
        
        try:
            total_report, subject_model, is_all, term, terms = generate_report(
                subject_id, class_name, batch, term, sort_order
            )
            context.update({
                'total_report': total_report,
                'subject': subject_model,
                'term': term,
                'batch': batch,
                'sort': sort_order,
                'class': class_name,
                'All': is_all,
                'terms': terms
            })
            
            # Remove duplicate assignment - it's already in context.update()
            # context['total_report'] = total_report  # REMOVED THIS LINE
            
            # HTMX or full render
            template = 'report-table.html' if request.headers.get('HX-Request') else 'report.html'
            return render(request, template, context)
            
        except Exception as e:
            # Add error handling
            context['error'] = f"Error generating report: {str(e)}"
            return render(request, 'get_report.html', context)

    return render(request, 'get_report.html', context)


          


def historyView(request):
    history = History.objects.all().order_by('-time')
    return render(request,'history.html',dict(history=history))

@login_require
def subjectView(request):
    subjects = Subject.objects.for_user(request.user)
    return render(request,'subject.html',dict(subjects=subjects))


def topicView(request):
    topics = Topic.objects.all()
    return render(request,'topic.html',dict(topics=topics))


def subjectDetail(request,id):
    subject = Subject.objects.get(id=id)
    classes = Class.objects.values('name').distinct()
    context = dict(subject=subject,classes=classes)
    return render(request,'subject-detail.html',context)

def topicDetail(request,id):
    topic = Topic.objects.get(id=id)
    return render(request,'topic-detail.html',dict(topic=topic))

def classTopic(request,id,name):
    subject = Subject.objects.get(id=id)
    class_name = Class.objects.filter(name=name).first()
    topics = subject.topic.filter(class_name=class_name)
    context = dict(topics=topics)
    return render(request,'topic-list.html',context)

def addTopic(request,id):
    subject = Subject.objects.get(id=id)
    form = TopicForm(initial=dict(subject=subject))
    form.fields['class_name'].queryset = Class.objects.values('name').distinct() 
    for field in form.fields.values():
        field.widget.attrs.update({'class':'form-control p-3'})

    context = dict(form=form,form_type="topic",target="topic",recordForm=True)
    return render(request,'record-form.html',context)

def signUp(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        if not username or not password:
            return HttpResponse("Missing credentials", status=400)

        hashed_password = make_password(password)
        user = User.objects.create(username=username, password=hashed_password)
        user.ensure_secret()  # Make sure secret is generated
        return redirect("login")  # Redirect after signup
    return render(request, "signup.html")


def login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return HttpResponse("Invalid username or password", status=401)

        if not check_password(password, user.password):
            return HttpResponse("Invalid username or password", status=401)

        token = user.generate_token()
        response = redirect("home") 
         # "1234:uuid:signature"
        response.set_cookie("auth_token", token, max_age=3600, httponly=True)
        response.set_cookie("auth_token", token, httponly=True, samesite="Lax")
        return response

    return render(request, "login.html")
    

def updateRecord(request,id):
  #student = Student.objects.get(id=id)
  model = StudentRecord.objects.get(id=id)
  #form = StudentRecordForm(initial=dict(student=student_records.student,record=student_records.record))
  form = StudentRecordForm(instance=model)
  #if request.method == "POST":
    #save_form(form)
    
  for field in form.fields.values():
        field.widget.attrs.update({'class':'form-control p-3'})

  context = dict(form=form,form_type="student-record",target="addHere",recordForm=True,update=True,model=model)
  return render(request,"record-form.html",context)
    
@login_require   
def addStudent(request,id):
  class_model = Class.objects.get(id=id)
  if request.method == "POST":
    student = request.POST.get("name")
    student_model = Student.objects.create(user=request.user,name=student,class_name=class_model)
    
    return HttpResponse(f"{student} is added to class {class_model.name}")
  return render(request,"add-student.html",{"class":class_model})
  
@login_require   
def addRecord(request,id):
  class_model = Class.objects.get(id=id)
  form = RecordForm(initial=dict(class_name=class_model))
  for field in form.fields.values():
     field.widget.attrs.update({"class" :'form-control'})
  return render(request,"record-form.html",{"class":class_model,"form":form,"form_type":"record","recordForm":True})
    
    