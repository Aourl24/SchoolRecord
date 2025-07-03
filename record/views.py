from django.shortcuts import render,reverse
from .models import Student, Record, Class , Subject , StudentRecord,History , Topic
from django.db.models import Q
from .form import RecordForm , StudentForm , ClassForm , SubjectForm , StudentRecordForm , TopicForm
from django.http import HttpResponse
import datetime

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
    context = dict(class_name=class_name,record=record)
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
  record_get = request.GET.get('record')
  edit = request.GET.get("edit")
  #students_list = [int(std) for std in students_list]
  record = Record.objects.get(id=record_get)
  print("record",record)
  students = StudentRecord.objects.filter(student__id__in=students_list,record=record)
  
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
    classes = Class.objects.all()
    subjects = Subject.objects.all()
    context = dict(subjects=subjects, classes=classes)

    if request.method == "POST":
        subject_id = request.POST.get('subject')
        class_id = request.POST.get('class')
        sort_order = request.POST.get('sort', 'asc')  # Default sort ascending

        try:
            class_model = Class.objects.get(id=int(class_id))
            subject_model = Subject.objects.get(id=int(subject_id))
        except (Class.DoesNotExist, Subject.DoesNotExist):
            context['error'] = "Invalid class or subject selected."
            return render(request, 'get_report.html', context)

        record = Record.objects.filter(class_name=class_model, subject=subject_model)
        students = StudentRecord.objects.filter(record__class_name=class_model, record__subject=subject_model)

        context['subject'] = subject_model
        context['class'] = class_model
        context['record'] = record
        context['students'] = students
        context['sort'] = sort_order  # Keep track of current sort order in the template

        # Build student-wise score records
        student_names = set(students.values_list('student__name', flat=True))
        student_objects = {name: [] for name in student_names}

        for std in students:
            student_objects[std.student.name].append(std)

        students_data = []

        for student_name in student_objects.keys():
            rec_list = []
            total_score = 0
            student_scores = {r.record.id: r.score for r in student_objects[student_name]}

            for rec in record:
                score = student_scores.get(rec.id, '-')
                rec_list.append({
                    'title': rec.title,
                    'type': rec.record_type,
                    'score': score
                })
                if isinstance(score, (int, float)):
                    total_score += score

            students_data.append({
                'name': student_name,
                'record': rec_list,
                'total_score': total_score
            })

        # Apply sorting
        if sort_order == 'desc':
            students_data.sort(key=lambda x: x['total_score'], reverse=True)
        else:
            students_data.sort(key=lambda x: x['name'])

        # Add header row
        total_report = [{
            'header': True,
            'count': 'S/N',
            'name': 'Student',
            'record': [{'title': rec.title, 'type': rec.record_type} for rec in record],
            'total': 'Total Score'
        }] + students_data

        context['total_report'] = total_report

        # Return partial if it's an HTMX request
        if request.headers.get('HX-Request'):
            return render(request, 'report-table.html', context)
        else:
            return render(request, 'report.html', context)

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