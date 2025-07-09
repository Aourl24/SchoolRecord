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
#from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

#SECRET_KEY = "my_super_secret"
#serializer = URLSafeTimedSerializer(SECRET_KEY)

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

@login_require
def homeView(request,part=None):
    records = Record.objects.all()
    students = Student.objects.all()
    classes = Class.objects.all()
    subject = Subject.objects.all()
    context = dict(records=records,students=students,classes=classes,subject=subject)
    return render(request,"home-partial.html" if part else'home.html',context)
    

def recordView(request):
    record = Record.objects.all()
    history = History.objects.get_or_create(title="Record List",url=reverse('record-list'))
    history[0].time=datetime.datetime.now()
    history[0].save()
    context = dict(record=record)
    return render(request, "record.html", context)

def studentView(request):
    student = Student.objects.all()
    subjects = Subject.objects.all()
    classes = Class.objects.values('name').distinct()
    history = History.objects.get_or_create(title="Student List",url=reverse('student-list'))
    history[0].time=datetime.datetime.now()
    history[0].save()
    context = dict(student=student,subjects=subjects,classes=classes)
    return render(request, "student.html", context)

def classView(request):
    school_class = Class.objects.all()
    history = History.objects.get_or_create(title="Class List",url=reverse('class-list'))
    history[0].time=datetime.datetime.now()
    history[0].save()
    context = dict(school_class=school_class)
    return render(request, "class.html", context)
    
def getRecord(request,id):
  record = Record.objects.get(id=id)
  students = StudentRecord.objects.filter(record=record)
  history = History.objects.get_or_create(title=f"{record}",url=reverse('get-record',args=[id]))
  history[0].time=datetime.datetime.now()
  history[0].save()
  context = dict(record = record,students = students,edit=True)
  return render(request,'record-detail.html',context)
  
def getStudent(request,id):
  student = Student.objects.get(id=id)
  records = StudentRecord.objects.filter(student=student)
  history = History.objects.get_or_create(title=f"{student}",url=reverse('get-student-detail',args=[id]))
  history[0].time=datetime.datetime.now()
  history[0].save()
  context = dict(student = student,records=records)
  return render(request,'student-detail.html',context)
  
def getClass(request,id):
  class_name = Class.objects.get(id=id)
  student = Student.objects.filter(class_name=class_name)
  history = History.objects.get_or_create(title=f"{class_name}",url=reverse('get-class',args=[id]))
  history[0].time=datetime.datetime.now()
  history[0].save()
  context = dict(class_name = class_name , student = student)
  return render(request,'class-detail.html',context)

def getClassRecord(request,id):
    class_name = Class.objects.get(id=id)
    record = Record.objects.filter(class_name=class_name)
    context = dict(class_name=class_name,record=record,partial=True)
    return render(request,'record-list.html',context)

def getClassStudent(request,id):
    class_name = Class.objects.get(id=id)
    student = Student.objects.filter(class_name=class_name)
    context = dict(student=student)
    return render(request,'student-list.html',context)

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
        case 'topic':
            form_class = TopicForm
        case _:
            form = RecordForm
    

    if request.method == 'POST':
        form = form_class(request.POST)
        saved=save_form(form)
        history = History.objects.get_or_create(title=f"Create new {get_form}")
        history[0].time=datetime.datetime.now()
        history[0].save()
        return HttpResponse(saved)
    else:
        form = form_class()
        saved = ""
    
    for field in form.fields.values():
        field.widget.attrs.update({'class':'form-control p-3'})
    context = dict(form=form,saved=saved ,form_type=get_form,target="drop-area")
    return render(request,'record-form.html',context)


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
    form.fields['student'].queryset = Student.objects.filter(class_name=record.class_name).order_by('name')
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
  record = dict(class_name=class_name,subject=subject,title=term,record_type=record_type,id=0,total_score= records.first().total_score if records else None)
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
  #students_list = [int(std) for std in students_list]
  try:
    record = Record.objects.get(id=record_get)
    students = StudentRecord.objects.filter(student__id__in=students_list,record=record)
  except Record.DoesNotExist:
    records = Record.objects.filter(id__in=record_list)
    students = StudentRecord.objects.filter(record__in=record_list)
    record = records.first()
  
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
      
  return render(request,'students-table.html',dict(students=students,edit=edit,record=record))
  

def closeReq(request):
  return HttpResponse("")
  
def generateReport(request):
    from django.db.models import Q

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
            # Filter classes by name and batch
            class_model = Class.objects.filter(name=class_name)
            if batch != "All":
                class_model = class_model.filter(batch=batch)
                context["All"] = False
            else:
                context["All"] = True

            subject_model = Subject.objects.get(id=int(subject_id))
        except (Class.DoesNotExist, Subject.DoesNotExist):
            context['error'] = "Invalid class or subject selected."
            return render(request, 'get_report.html', context)

        # Fetch records and student records
        record_qs = Record.objects.filter(class_name__in=class_model, subject=subject_model)
        if term not in ["All", "None", None]:
            record_qs = record_qs.filter(title=term)

        student_records = StudentRecord.objects.filter(
            record__class_name__in=class_model,
            record__subject=subject_model
        )

        context.update({
            'subject': subject_model,
            'class': class_name,
            'batch': batch,
            'record': record_qs,
            'students': student_records,
            'sort': sort_order,
            'term': None if term == "All" else term
        })

        # Prepare student data
        student_names = set(student_records.values_list('student__name', flat=True))
        student_objects = {name: [] for name in student_names}

        for std in student_records:
            student_objects[std.student.name].append(std)

        record_to_render = []
        students_data = []

        for student_name in sorted(student_objects.keys()):
            # Get the student's batch
            student_model = Student.objects.get(name=student_name)
            student_batch = student_model.class_name.batch
            student_records_filtered = record_qs.filter(class_name__batch=student_batch)

            rec_list = []
            total_score = 0
            student_scores = {r.record.id: r.score for r in student_objects[student_name]}

            for rec in student_records_filtered:
                score = student_scores.get(rec.id, '-')
                rec_list.append({
                    'title': rec.title,
                    'type': rec.record_type,
                    'number': rec.record_number,
                    'score': score,
                    'class': rec.class_name.batch
                })

                record_id_str = f"{rec.title} {rec.record_type} {rec.record_number}"
                if record_id_str not in record_to_render:
                    record_to_render.append(record_id_str)

                if isinstance(score, (int, float)):
                    total_score += score

            students_data.append({
                'id' : student_model.id,
                'name': student_name,
                'record': rec_list,
                'total_score': total_score,
                'class_name' : f"{student_batch}"
            })

        # Sort the final student data
        if sort_order == 'desc':
            students_data.sort(key=lambda x: x['total_score'], reverse=True)
        else:
            students_data.sort(key=lambda x: x['name'])

        # Build report
        total_report = [{
            'header': True,
            'count': 'S/N',
            'name': 'Student',
            'record': [{'title': rec} for rec in record_to_render],
            'total': 'Total Score'
        }] + students_data

        context['total_report'] = total_report

        # HTMX or full render
        template = 'report-table.html' if request.headers.get('HX-Request') else 'report.html'
        return render(request, template, context)

    return render(request, 'get_report.html', context)
          


def historyView(request):
    history = History.objects.all().order_by('-time')
    return render(request,'history.html',dict(history=history))


def subjectView(request):
    subjects = Subject.objects.all()
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
    