from django.shortcuts import render, reverse, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.hashers import check_password
from django.views.generic import CreateView, UpdateView, ListView, DetailView
from django.utils.decorators import method_decorator
from django.contrib import messages
from .models import *
from .form import *
from .service import *
from .decorator import login_require
from .report import Report 

# Utility Mixins
class UserFilterMixin:
    """Mixin to filter querysets by user"""
    
    def get_queryset(self):
        return super().get_queryset().for_user(self.request.user)

class HistoryMixin:
    """Mixin to log user activity"""
    
    def dispatch(self, request, *args, **kwargs):
        if hasattr(self, 'history_title') and hasattr(self, 'history_url'):
            HistoryService.log_user_activity(
                request.user, 
                self.history_title, 
                self.history_url
            )
        return super().dispatch(request, *args, **kwargs)

#Landimg Views
def landing_view(request):
  return render(request,"landing.html")
  
# Main Views
@login_require
def home_view(request, part=None):
    """Dashboard view with overview data"""
    context = {
        'records': Record.objects.for_user(request.user),
        'students': Student.objects.for_user(request.user),
        'classes': Class.objects.for_user(request.user),
        'subjects': SubjectTeacher.objects.for_user(request.user)
    }
    
    template = "home-partial.html" if part else 'home.html'
    return render(request, template, context)

# Class-Based Views for CRUD operations
@method_decorator(login_require, name='dispatch')
class RecordListView(ListView):
    model = Record
    template_name = 'record.html'
    context_object_name = 'record'
    
    def get_queryset(self):
        return Record.objects.for_user(self.request.user)
    
    def get(self, request, *args, **kwargs):
        HistoryService.log_user_activity(
            request.user, 
            "Record List", 
            reverse('record-list')
        )
        return super().get(request, *args, **kwargs)

@method_decorator(login_require, name='dispatch')
class StudentListView(ListView):
    model = Student
    template_name = 'student.html'
    context_object_name = 'student'
    
    def get_queryset(self):
        return Student.objects.for_user(self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'subjects': Subject.objects.for_user(self.request.user),
            'classes': Class.objects.for_user(self.request.user).values('name').distinct()
        })
        return context
    
    def get(self, request, *args, **kwargs):
        HistoryService.log_user_activity(
            request.user, 
            "Student List", 
            reverse('student-list')
        )
        return super().get(request, *args, **kwargs)

@method_decorator(login_require, name='dispatch')
class ClassListView(ListView):
    model = Class
    template_name = 'class.html'
    context_object_name = 'school_class'
    
    def get_queryset(self):
        return Class.objects.for_user(self.request.user)
    
    def get(self, request, *args, **kwargs):
        HistoryService.log_user_activity(
            request.user, 
            "Class List", 
            reverse('class-list')
        )
        return super().get(request, *args, **kwargs)

# Detail Views
@login_require
def record_detail_view(request, id):
    """Record detail with students"""
    record = get_object_or_404(Record, id=id)
    students = StudentRecord.objects.filter(record=record)
    students_without_record = StudentRecordService.get_students_without_record(record)
    
    HistoryService.log_user_activity(
        request.user, 
        f"{record}", 
        reverse('get-record', args=[id])
    )
    
    context = {
        'record': record,
        'students': students,
        'students_without_record': students_without_record,
        'edit': True,
        'half': record.total_score / 2
    }
    return render(request, 'record-detail.html', context)

@login_require
def student_detail_view(request, id):
    """Student detail with records"""
    student = get_object_or_404(Student, id=id)
    records = StudentRecord.objects.filter(student=student)
    
    HistoryService.log_user_activity(
        request.user, 
        f"{student}", 
        reverse('get-student-detail', args=[id])
    )
    
    context = {
        'student': student,
        'records': records
    }
    return render(request, 'student-detail.html', context)

@login_require
def class_detail_view(request, id):
    """Class detail with students"""
    class_obj = get_object_or_404(Class, id=id)
    students = Student.objects.filter(class_name=class_obj)
    
    HistoryService.log_user_activity(
        request.user, 
        f"{class_obj}", 
        reverse('get-class', args=[id])
    )
    
    context = {
        'class_name': class_obj,
        'student': students
    }
    return render(request, 'class-detail.html', context)
    
#Form Views
class BaseFormView:
    """Base class for form handling"""
    
    form_classes = {
        'record': RecordForm,
        'subject': SubjectForm,
        'class': ClassForm,
        'student': StudentForm,
        'student-record': StudentRecordForm,
        'topic': TopicForm,
    }
    
    model_classes = {
        'record': Record,
        'subject': Subject,
        'class': Class,
        'student': Student,
        'student-record': StudentRecord,
        'topic': Topic,
    }

@login_require
def form_view(request, form_type, update_id=None):
    """Generic form view for all model forms"""
    base_form = BaseFormView()
    
    if form_type not in base_form.form_classes:
        return HttpResponse("Invalid form type", status=400)
    
    form_class = base_form.form_classes[form_type]
    model_class = base_form.model_classes[form_type]
    
    # Get instance for updates
    instance = None
    if update_id:
        instance = get_object_or_404(model_class, id=update_id)
    
      
    if request.method == 'POST':
        form = form_class(request.POST, instance=instance,user=request.user)
        result = FormService.save_model_form(form, request.user)
        
        HistoryService.log_user_activity(
            request.user,
            f"{'Update' if instance else 'Create'} {form_type}",
            request.path
        )
        
        return HttpResponse(result['message'])
    else:
        form = form_class(instance=instance,user=request.user)
    
    context = {
        'form': form,
        'form_type': form_type,
        'target': 'drop-area',
        'model': instance,
        'update': bool(update_id)
    }
    return render(request, 'record-form.html', context)

# Search and Filter Views
@login_require
def search_view(request):
    """Search across all models"""
    query = request.GET.get('search', '')
    results = SearchService.search_all(query, request.user)
    
    return render(request, 'search.html', results)

def filter_record_view(request):
    """Filter records by various criteria"""
    class_name = request.GET.get('class')
    subject_id = request.GET.get('subject')
    term = request.GET.get('term')
    record_type = request.GET.get('r_type')
    record_number = request.GET.get('number')
    
    subject = get_object_or_404(Subject, id=subject_id)
    records = Record.objects.filter(
        subject=subject,
        record_type=record_type,
        record_number=record_number,
        class_name__name=class_name
    )
    
    students = StudentRecord.objects.filter(record__in=records)
    record_list = [r.id for r in records]
    
    record_data = {
        'class_name': class_name,
        'subject': subject,
        'title': term,
        'record_type': record_type,
        'id': 0,
        'total_score': records.first().total_score if records.exists() else None,
        'half': records.first().total_score / 2 if records.exists() else None
    }
    
    context = {
        'record': record_data,
        'record_list': record_list,
        'students': students,
        'edit': None
    }
    return render(request, 'record-detail.html', context)

def filter_student_view(request):
    """Filter students with advanced criteria"""
    filter_type = request.GET.get("filter")
    operator = request.GET.get("sign")
    score = request.GET.get("score")
    students_list = request.GET.getlist("students")
    record_id = request.GET.get('record')
    edit = request.GET.get("edit")
    record_list = request.GET.getlist("record-list")
    
    # Determine if we're filtering a single record or multiple
    try:
        if record_id:
            record = get_object_or_404(Record, id=record_id)
            students = StudentRecord.objects.filter(
                student__id__in=students_list,
                record=record
            )
        else:
            records = Record.objects.filter(id__in=record_list)
            students = StudentRecord.objects.filter(record__in=record_list)
            record = records.first()
    except (Record.DoesNotExist, ValueError):
        return HttpResponse("Invalid record data", status=400)
    
    # Apply score filtering
    if score and operator:
        score_filter = {'score': score, 'operator': operator}
        students = StudentRecordService.filter_student_records(
            students, 
            score_filter=score_filter
        )
    
    # Apply sorting
    if filter_type:
        students = StudentRecordService.filter_student_records(
            students, 
            sort_filter=filter_type
        )
    
    context = {
        'students': students,
        'edit': edit != "None",
        'record': record,
        'half': record.total_score / 2 if record else None
    }
    return render(request, 'students-table.html', context)

# Utility Views
@login_require
def add_to_record_view(request, id):
    """Add student to specific record"""
    record = get_object_or_404(Record, id=id)
    form = StudentRecordForm(initial={'record': record},user=request.user)
    
    students_without_record = StudentRecordService.get_students_without_record(record)
    form.fields['student'].queryset = students_without_record
    
    context = {
        'form': form,
        'form_type': 'student-record',
        'target': 'addHere',
        'recordForm': True
    }
    return render(request, 'record-form.html', context)

@login_require
def add_student_to_class_view(request, id):
    """Add student to specific class"""
    class_obj = get_object_or_404(Class, id=id)
    
    if request.method == "POST":
        student_name = request.POST.get("name")
        if student_name:
            Student.objects.create(
                user=request.user,
                name=student_name,
                class_name=class_obj
            )
            return HttpResponse(f"{student_name} added to class {class_obj.name}")
    
    return render(request, "add-student.html", {"class": class_obj})

# Authentication Views

def login(request,username,password,url=None):
  try:
    user = User.objects.get(username=username)
    if check_password(password, user.password):
        token = user.generate_token()
        response = redirect(url)
        response.set_cookie(
            "auth_token", 
            token, 
            max_age=3600, 
            httponly=True,
            samesite="Lax"
        )
        return response
    else:
        return render (request,'login.html',{"error":"Invalid credentials"})
  except User.DoesNotExist:
    messages.error(request, "Invalid credentials")
  
def signup_view(request):
    """User registration"""
    errors = None
    if request.method == "POST":
        form = UserForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            confirm_password = form.cleaned_data["confirm_password"]
            if password == confirm_password:
              
              result = UserService.create_user(username, password)
              if result['success']:
                  messages.success(request, "Account created successfully!")
                  return login(request,username,password,url="new_user_detail")
              else:
                  messages.error(request, result['error'])
            
            else:
              errors = "Password is not the same"
        # else:
        #     form = UserForm(request.POST)
    else:
        form = UserForm()
    
    return render(request, "signup.html", {'form': form,'errors':errors if errors else None })

def login_view(request):
    """User login"""
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        next_url = request.POST.get("next")
        return(login(request,username,password,url= next_url if next_url else "home"))
        
    return render(request, "login.html")
    
# Other Views (subjects, topics, history, reports)
@login_require
def subject_list_view(request):
    """List all subjects"""
    subjects = Subject.objects.for_user(request.user)
    return render(request, 'subject.html', {'subjects': subjects})

@login_require
def history_view(request):
    """User activity history"""
    history = History.objects.for_user(request.user).order_by('-time')
    return render(request, 'history.html', {'history': history})

def close_request_view(request):
    """Utility view for closing modals/requests"""
    return HttpResponse("")
    
    
@login_require
def topic_list_view(request):
    """List all topics"""
    topics = Topic.objects.for_user(request.user).select_related('subject', 'class_name')
    return render(request, 'topic.html', {'topics': topics})

@login_require
def subject_detail_view(request, id):
    """Subject detail with related topics"""
    subject = get_object_or_404(Subject, id=id)
    classes = Class.objects.values('name').distinct()
    
    HistoryService.log_user_activity(
        request.user,
        f"Subject: {subject.name}",
        reverse('subject-detail', args=[id])
    )
    
    context = {
        'subject': subject,
        'classes': classes
    }
    return render(request, 'subject-detail.html', context)

@login_require
def topic_detail_view(request, id):
    """Topic detail view"""
    topic = get_object_or_404(Topic, id=id)
    
    HistoryService.log_user_activity(
        request.user,
        f"Topic: {topic.title}",
        reverse('topic-detail', args=[id])
    )
    
    return render(request, 'topic-detail.html', {'topic': topic})

def class_topics_view(request, id, name):
    """Get topics for specific class and subject"""
    subject = get_object_or_404(Subject, id=id)
    class_obj = Class.objects.filter(name=name).first()
    
    if not class_obj:
        return HttpResponse("Class not found", status=404)
    
    topics = subject.topic.filter(class_name=class_obj)
    return render(request, 'topic-list.html', {'topics': topics})

def add_topic_view(request, id):
    """Add topic to specific subject"""
    subject = get_object_or_404(Subject, id=id)
    form = TopicForm(initial={'subject': subject})
    form.fields['class_name'].queryset = Class.objects.values('name').distinct()
    
    context = {
        'form': form,
        'form_type': "topic",
        'target': "topic",
        'recordForm': True
    }
    return render(request, 'record-form.html', context)

def update_record_view(request, id):
    """Update student record"""
    student_record = get_object_or_404(StudentRecord, id=id)
    form = StudentRecordForm(instance=student_record)
    
    context = {
        'form': form,
        'form_type': "student-record",
        'target': "addHere",
        'recordForm': True,
        'update': True,
        'model': student_record
    }
    return render(request, "record-form.html", context)

@login_require
def add_record_to_class_view(request, id):
    """Add record to specific class"""
    class_obj = get_object_or_404(Class, id=id)
    form = RecordForm(initial={'class_name': class_obj},user=request.user)
    
    context = {
        'class': class_obj,
        'form': form,
        'form_type': "record",
        'recordForm': True
    }
    return render(request, "record-form.html", context)

@login_require
def get_class_records_view(request, id):
    """Get all records for a specific class"""
    class_obj = get_object_or_404(Class, id=id)
    records = Record.objects.filter(class_name=class_obj).select_related('subject')
    
    HistoryService.log_user_activity(
        request.user,
        f"{class_obj} records",
        reverse('get-class-record', args=[id])
    )
    
    context = {
        'class_name': class_obj,
        'record': records,
        'partial': True
    }
    return render(request, 'record-list.html', context)

@login_require
def get_class_students_view(request, id):
    """Get all students for a specific class"""
    class_obj = get_object_or_404(Class, id=id)
    students = Student.objects.filter(class_name=class_obj).order_by("name")
    
    HistoryService.log_user_activity(
        request.user,
        f"{class_obj} students",
        reverse('get-student', args=[id])
    )
    
    return render(request, 'student-list.html', {'student': students})

# Advanced filtering and analytics views
@login_require
def analytics_dashboard_view(request):
    """Analytics dashboard with charts and statistics"""
    user_records = Record.objects.for_user(request.user)
    user_students = Student.objects.for_user(request.user)
    
    # Calculate basic statistics
    stats = {
        'total_records': user_records.count(),
        'total_students': user_students.count(),
        'total_classes': Class.objects.for_user(request.user).count(),
        'total_subjects': Subject.objects.for_user(request.user).count(),
    }
    
    # Get recent activity
    recent_records = user_records.order_by('-date_created')[:5]
    
    # Performance statistics
    student_records = StudentRecord.objects.for_user(request.user)
    if student_records.exists():
        performance_stats = student_records.aggregate(
            avg_score=Avg('score'),
            max_score=Max('score'),
            min_score=Min('score'),
            total_records=Count('id')
        )
        stats.update(performance_stats)
    
    context = {
        'stats': stats,
        'recent_records': recent_records,
    }
    
    return render(request, 'analytics.html', context)

# API-style views for AJAX requests
def api_student_records(request, student_id):
    """API endpoint to get student records as JSON"""
    from django.http import JsonResponse
    
    try:
        student = get_object_or_404(Student, id=student_id)
        records = StudentRecord.objects.filter(student=student).select_related('record')
        
        data = [
            {
                'id': sr.id,
                'record_title': sr.record.title,
                'subject': sr.record.subject.name,
                'score': float(sr.score),
                'total_score': float(sr.record.total_score),
                'percentage': sr.percentage,
                'date': sr.date_recorded.isoformat(),
                'is_passed': sr.is_passed
            }
            for sr in records
        ]
        
        return JsonResponse({'success': True, 'data': data})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

def api_class_summary(request, class_id):
    """API endpoint to get class summary as JSON"""
    from django.http import JsonResponse
    
    try:
        class_obj = get_object_or_404(Class, id=class_id)
        summary_result = ReportService.generate_class_summary_report(
            class_obj.name, 
            class_obj.batch
        )
        
        if summary_result['success']:
            # Convert model instances to serializable data
            data = summary_result['data']
            serialized_data = {
                'class_name': str(data['class']),
                'total_students': data['total_students'],
                'total_records': data['total_records'],
                'avg_score': float(data['avg_score'] or 0),
                'max_score': float(data['max_score'] or 0),
                'min_score': float(data['min_score'] or 0),
            }
            
            return JsonResponse({'success': True, 'data': serialized_data})
        else:
            return JsonResponse({'success': False, 'error': summary_result['error']})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_require
def report_view(request):
    """Enhanced report generation view"""
    classes_obj = Class.objects.for_user(request.user)
    classes = [c for c in classes_obj if c.batch == "A"]
    subjects = Subject.objects.for_user(request.user)

    context = {
        'subjects': subjects,
        'classes': classes,
        'error': None
    }

    if request.method == "POST":
        subject_id = request.POST.get('subject')
        class_name = request.POST.get('class')
        batch = request.POST.get("batch", "A")
        term = request.POST.get("term", "all")
        sort_order = request.POST.get('sort', 'asc')

        if not all([subject_id,class_name,batch,term,sort_order]):
            context['error'] = "Invalid Parameters"
            return render(request,'get_report.html' ,context)

        report_result = Report.generate_report(
            subject_id=subject_id,
            class_name=class_name,
            batch=batch,
            term=term,
            sort_order=sort_order
        )

        if report_result['success']:
            context.update({
                'total_report': report_result.get('total_report') or report_result.get('data'),
                'subject': report_result.get('subject'),
                'term': report_result.get('term'),
                'batch': report_result.get('batch'),
                'sort': report_result.get('sort_order'),
                'class': report_result.get('class_name'),
                'All': report_result.get('is_all_subjects'),
                'terms': report_result.get('terms'),
                # also keep raw data if needed in the template
                'report_data': report_result.get('data')
            })

            template = 'report-table.html' if request.headers.get('HX-Request') else 'report.html'
            return render(request, template, context)
        else:
            context['error'] = report_result.get('error', 'Unknown error')
            return render(request, 'report.html', context)

    return render(request, 'get_report.html', context)



def logout_view(request):
    """User logout"""
    response = redirect('login')
    response.delete_cookie('auth_token')
    messages.success(request, "You have been logged out successfully.")
    return response

@login_require
def user_detail(request,form="role"):
  schools = None   
  if request.method == "POST":
    user = request.user
    if form == "role":
      role = request.POST.get("role")
      user.role = role
      user.save()
      form = "full_name"
    elif form == "school":
      school = request.POST.get("school")
      check_school = School.objects.get(id=school)
      user.school = check_school
      user.save()
      return redirect("home")
    elif form == "full_name":
      full_name = request.POST.get("full_name")
      user.full_name = full_name
      user.save()
      form = "email"
    elif form == "email":
      email = request.POST.get("email")
      user.email = email
      user.save()
      form = "school"
      schools = School.objects.all()
      
  context = {"form":form,"schools":schools}
  return render(request,"details.html",context)