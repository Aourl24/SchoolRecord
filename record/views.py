from django.shortcuts import render, reverse, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.hashers import check_password
from django.core.exceptions import ValidationError
from django import forms
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

#Landing Views
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
        return Record.objects.for_user(self.request.user).select_related(
            'class_name', 'subject__subject'
        ).order_by(
            'class_name__name', 'class_name__batch',
            'subject__subject__name', 'record_type', 'record_number'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['grouped_records'] = RecordGroupingService.group_by_class_and_subject(
            context['record']
        )
        return context

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
          'subjects': SubjectTeacher.objects.for_user(self.request.user),
          'classes': Class.objects.for_user(self.request.user)
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
    record = get_object_or_404(Record, id=id)
    students = StudentRecord.objects.filter(record=record)
    students_without_record = StudentRecordService.get_students_without_record(record)

    # ---- Statistics ----
    score_list = [sr.score for sr in students]
    total_students = students.count() + students_without_record.count()
    entered = students.count()
    remaining = students_without_record.count()
    avg_score = sum(score_list) / len(score_list) if score_list else None
    max_score = max(score_list) if score_list else None
    min_score = min(score_list) if score_list else None

    # For top performers – sort by score descending, take first 5
    top_performers = students.order_by('-score')[:5] if students else []

    # For "needs attention" – we'll compute in template with filters or simple loops

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
        'half': record.total_score / 2,
        'total_students': total_students,
        'entered': entered,
        'remaining': remaining,
        'avg_score': avg_score,
        'max_score': max_score,
        'min_score': min_score,
        'top_performers': top_performers,
        'score_list': score_list,   # for distribution if needed
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
    class_obj = get_object_or_404(Class, id=id)
    students = Student.objects.filter(class_name=class_obj)
    # Filter history for this class by URL containing the class ID
    history = History.objects.for_user(request.user).filter(
        url__icontains=f'/class/{id}/'
    ).order_by('-time')[:10]

    HistoryService.log_user_activity(
        request.user, 
        f"{class_obj}", 
        reverse('get-class', args=[id])
    )

    context = {
        'class_name': class_obj,
        'student': students,
        'history': history,  # <-- add this
    }
    return render(request, 'class-detail.html', context)


from django.db.models import Avg  # at top of file

@login_require
def class_report_view(request, id):
    """Class‑specific report:
       - GET without subject_id → list of subjects with records.
       - GET with subject_id → full report for that subject.
    """
    class_obj = get_object_or_404(Class, id=id, user=request.user)
    term = request.user.active_term or "First Term"
    subject_id = request.GET.get('subject_id')
    sort_order = request.GET.get('sort', 'asc')

    if subject_id:
        # Generate report for a specific subject – NO user argument
        report_result = ReportService.generate_report(
            subject_id=subject_id,
            class_name=class_obj.name,
            batch=class_obj.batch,
            term=term,
            sort_order=sort_order,
        )

        context = {
            'class_obj': class_obj,
            'total_report': report_result.get('total_report'),
            'subject': report_result.get('subject'),
            'is_all_subjects': report_result.get('is_all_subjects', False),
            'terms': report_result.get('terms', []),
            'batch': class_obj.batch,
            'class': class_obj.name,
            'term': term,
            'sort': sort_order,
            'error': report_result.get('error'),
        }
        return render(request, 'class-report-partial.html', context)

    else:
        # List mode: show all subjects with records for this class
        subject_teachers = SubjectTeacher.objects.filter(
            class_name=class_obj,
            user=request.user,
            record__isnull=False
        ).distinct().select_related('subject')

        subjects_data = []
        for st in subject_teachers:
            records = Record.objects.filter(subject=st, class_name=class_obj)
            student_records = StudentRecord.objects.filter(record__in=records)
            avg_score = student_records.aggregate(Avg('score'))['score__avg']
            subjects_data.append({
                'subject_teacher': st,
                'subject': st.subject,
                'record_count': records.count(),
                'avg_score': avg_score or 0,
            })

        context = {
            'class_obj': class_obj,
            'subjects_data': subjects_data,
            'term': term,
        }
        return render(request, 'class-report-list.html', context)
        
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
        'term-report': TermReportForm,
    }

    model_classes = {
        'record': Record,
        'subject': SubjectTeacher,
        'class': Class,
        'student': Student,
        'student-record': StudentRecord,
        'topic': Topic,
        'term-report': TermReport,
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
        form = form_class(request.POST, instance=instance, user=request.user)
        result = FormService.save_model_form(form, request.user)

        HistoryService.log_user_activity(
            request.user,
            f"{'Update' if instance else 'Create'} {form_type}",
            request.path
        )

        return HttpResponse(result['message'])
    else:
        initial = {}
        if form_type == 'record' and not update_id:
            initial['title'] = getattr(request.user, 'active_term', None)
        form = form_class(instance=instance, user=request.user, initial=initial or None)

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
    result = SearchService.search_all(query, request.user)
    context = dict(record=result['records'], student=result["students"], school_class=result["classes"])
    return render(request, 'search.html', context)

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
    form = StudentRecordForm(initial={'record': record}, user=request.user)

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
def bulk_score_entry_view(request, id):
    """
    Bulk score entry/edit for every student in a record's class.

    GET  -> render a table with one row per student, score input pre-filled
            with their existing StudentRecord.score if one exists.
    POST -> for each non-empty score_<student_id> field, create a new
            StudentRecord or update the existing one. Blank fields are
            skipped (lets a teacher save a partial pass without wiping
            scores for students they haven't gotten to yet).
    """
    record = get_object_or_404(Record, id=id)
    students = Student.objects.filter(class_name=record.class_name).order_by('name')

    if request.method == "POST":
        existing = {sr.student_id: sr for sr in StudentRecord.objects.filter(record=record)}
        created, updated, errors = 0, 0, []

        for student in students:
            raw_score = request.POST.get(f"score_{student.id}", "").strip()
            if raw_score == "":
                continue

            try:
                score = int(raw_score)
            except ValueError:
                errors.append(f"{student.name}: '{raw_score}' is not a whole number")
                continue

            student_record = existing.get(student.id)
            try:
                if student_record:
                    student_record.score = score
                    student_record.save()
                    updated += 1
                else:
                    StudentRecord.objects.create(
                        user=request.user,
                        student=student,
                        record=record,
                        score=score
                    )
                    created += 1
            except ValidationError as e:
                errors.append(f"{student.name}: {'; '.join(e.messages) if hasattr(e, 'messages') else str(e)}")

        HistoryService.log_user_activity(
            request.user,
            f"Bulk scores — {record}",
            request.path
        )

        context = {
            'record': record,
            'created': created,
            'updated': updated,
            'errors': errors,
        }
        return render(request, 'bulk-score-result.html', context)

    # GET: build rows, pre-filling any score the student already has
    existing_scores = {
        sr.student_id: sr.score
        for sr in StudentRecord.objects.filter(record=record)
    }
    student_rows = [
        {'student': s, 'score': existing_scores.get(s.id, '')}
        for s in students
    ]

    context = {
        'record': record,
        'student_rows': student_rows,
    }
    return render(request, 'bulk-score-form.html', context)

@login_require
def add_student_to_class_view(request, id):
    """Add student to specific class"""
    class_obj = get_object_or_404(Class, id=id)

    if request.method == "POST":
        student_name = request.POST.get("name")
        if student_name:
            Student.objects.create_for_user(
                user=request.user,
                name=student_name,
                class_name=class_obj
            )
            return HttpResponse(f"{student_name} added to class {class_obj.name}")

    return render(request, "add-student.html", {"class": class_obj})

# Authentication Views

def login(request, username, password, url=None):
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
        return render(request, 'login.html', {"error": "Invalid credentials"})
  except User.DoesNotExist:
    return render(request, 'login.html', {"error": "User doesn't exist"})
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
                  return login(request, username, password, url="new_user_detail")
              else:
                  messages.error(request, result['error'])

            else:
              errors = "Password is not the same"
        # else:
        #     form = UserForm(request.POST)
    else:
        form = UserForm()

    return render(request, "signup.html", {'form': form, 'errors': errors if errors else None})

def login_view(request):
    """User login"""
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        next_url = request.POST.get("next")
        url = "home" if not next_url or next_url == "/" else next_url
        return login(request, username, password, url=url)

    return render(request, "login.html")

# Other Views (subjects, topics, history, reports)
@login_require
def subject_list_view(request):
    """List all subjects (shared across every teacher — not per-user)"""
    subjects = Subject.objects.filter(subjectTeacher__user=request.user).order_by('name').distinct()
    return render(request, 'subject.html', {'subjects': subjects})

@login_require
def history_view(request):
    """User activity history – latest 10 entries"""
    history = History.objects.for_user(request.user).order_by('-time')[:10]
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
    """Subject detail — classes, students, and topics scoped via SubjectTeacher."""
    subject = get_object_or_404(Subject, id=id)

    # Only classes where THIS teacher has assigned this subject (via SubjectTeacher)
    # This replaces Class.objects.for_user().values('name').distinct() which
    # returned all the teacher's classes regardless of whether they teach this subject.
    subject_teachers = (
        SubjectTeacher.objects
        .filter(subject=subject, user=request.user)
        .select_related('class_name')
        .order_by('class_name__name', 'class_name__batch')
    )

    classes = [st.class_name for st in subject_teachers]

    # Students enrolled in those classes, scoped to this teacher
    students = (
        Student.objects
        .filter(class_name__in=classes, user=request.user)
        .select_related('class_name')
        .order_by('class_name__name', 'name')
    )

    # Records created for this subject by this teacher
    records_count = (
        Record.objects
        .filter(subject__in=subject_teachers, user=request.user)
        .count()
    )

    HistoryService.log_user_activity(
        request.user,
        f"Subject: {subject.name}",
        reverse('subject-detail', args=[id])
    )

    context = {
        'subject': subject,
        'subject_teachers': subject_teachers,   # full objects with class_name
        'classes': classes,                      # Class instances (not dicts)
        'students': students,
        'records_count': records_count,
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
def promote_class_view(request, id):
    """
    Bulk-promote selected students from this class into the next class in
    the progression (e.g. JSS1 -> JSS2), creating that target Class for the
    chosen session if it doesn't already exist. Historical Records and
    StudentRecords stay attached to THIS class, so past report data is
    untouched — only each promoted student's current class_name changes.
    """
    source_class = get_object_or_404(Class, id=id, user=request.user)
    next_name = PromotionService.next_class_name(source_class.name)
    students = Student.objects.filter(class_name=source_class).order_by('name')

    if request.method == "POST":
        if not next_name:
            return render(request, 'promote-class-result.html', {
                'error': f"{source_class.name} is the final class — there's no next class to promote into."
            })

        target_batch = request.POST.get('target_batch', source_class.batch)
        target_session = request.POST.get('target_session') or PromotionService.next_session(source_class.session)
        selected_ids = request.POST.getlist('students')

        if not selected_ids:
            return render(request, 'promote-class-result.html', {
                'error': "Select at least one student to promote."
            })

        target_class, moved_count = PromotionService.promote_students(
            source_class, selected_ids, target_batch, target_session, request.user
        )

        HistoryService.log_user_activity(
            request.user,
            f"Promoted {moved_count} students: {source_class} -> {target_class}",
            request.path
        )

        context = {
            'source_class': source_class,
            'target_class': target_class,
            'moved_count': moved_count,
        }
        return render(request, 'promote-class-result.html', context)

    context = {
        'source_class': source_class,
        'next_name': next_name,
        'suggested_batch': source_class.batch,
        'suggested_session': PromotionService.next_session(source_class.session) if next_name else None,
        'students': students,
        'final_class': not bool(next_name),
    }
    return render(request, 'promote-class.html', context)

@login_require
def add_record_to_class_view(request, id):
    """Add record to specific class"""
    class_obj = get_object_or_404(Class, id=id)
    form = RecordForm(
        initial={
            'class_name': class_obj,
            'title': getattr(request.user, 'active_term', None),
        },
        user=request.user
    )

    context = {
        'class': class_obj,
        'form': form,
        'form_type': "record",
        'recordForm': True
    }
    return render(request, "record-form.html", context)

@login_require
def get_class_records_view(request, id):
    """Get all records for a specific class, grouped by subject"""
    class_obj = get_object_or_404(Class, id=id)
    records = Record.objects.filter(class_name=class_obj).select_related(
        'subject__subject'
    ).order_by('subject__subject__name', 'record_type', 'record_number')

    HistoryService.log_user_activity(
        request.user,
        f"{class_obj} records",
        reverse('get-class-record', args=[id])
    )

    context = {
        'class_name': class_obj,
        'record': records,
        'grouped_records': RecordGroupingService.group_by_subject(records),
        'partial': True
    }
    return render(request, 'record-list-by-subject.html', context)

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
    """Report generation — only shows subject+class combos the teacher has records for."""

    # ── GET context ──────────────────────────────────────────────────────────
    # SubjectTeacher rows where at least one Record exists for this user.
    # This replaces Subject.objects.all() + the batch-A-only class filter.
    subject_teachers = (
    SubjectTeacher.objects
    .for_user(request.user)
    .filter(record__isnull=False)
    .select_related('subject', 'class_name')
    .prefetch_related('record')
    .distinct()
    .order_by('class_name__name', 'class_name__batch', 'subject__name')
)

    # Distinct classes — all batches, not just A
    classes = (
        Class.objects
        .for_user(request.user)
        .filter(subjectTeacher__record__isnull=False)
        .distinct()
        .order_by('name', 'batch')
    )

    context = {
        'subject_teachers': subject_teachers,
        'classes': classes,
        'error': None,
    }

    # ── POST ─────────────────────────────────────────────────────────────────
    if request.method == "POST":
        subject_id  = request.POST.get('subject')
        class_name  = request.POST.get('class')
        batch       = request.POST.get("batch", "A")
        term        = request.POST.get("term", "all")
        sort_order  = request.POST.get('sort', 'asc')

        if not all([subject_id, class_name, batch, term, sort_order]):
            context['error'] = "Invalid Parameters"
            return render(request, 'get_report.html', context)

        report_result = Report.generate_report(
            subject_id=subject_id, 
            class_name=class_name,
            batch=batch, 
            term=term, 
            sort_order=sort_order,
            user=request.user
        )
        if report_result['success']:
            context.update({
                'total_report': report_result.get('total_report') or report_result.get('data'),
                'subject':      report_result.get('subject'),
                'term':         report_result.get('term'),
                'batch':        report_result.get('batch'),
                'sort':         report_result.get('sort_order'),
                'class':        report_result.get('class_name'),
                'All':          report_result.get('is_all_subjects'),
                'terms':        report_result.get('terms'),
                'report_data':  report_result.get('data'),
            })
            template = 'report-table.html' if request.headers.get('HX-Request') else 'report.html'
            return render(request, template, context)
        else:
            context['error'] = report_result.get('error', 'Unknown error')
            return render(request, 'get_report.html', context)

    return render(request, 'get_report.html', context)


def logout_view(request):
    """User logout"""
    response = redirect('login')
    response.delete_cookie('auth_token')
    messages.success(request, "You have been logged out successfully.")
    return response

@login_require
def user_detail(request, form="role"):
  schools = None   
  if request.method == "POST":
    user = request.user
    skip = request.POST.get("action") == "skip"

    if form == "role":
      if not skip:
        role = request.POST.get("role")
        if role:
          user.role = role
          user.save()
      form = "term"
    elif form == "term":
      term = request.POST.get("term")
      if term in ["First Term", "Second Term", "Third Term"]:
        user.active_term = term
        user.save()
      form = "full_name"
    elif form == "school":
      if not skip:
        new_school = request.POST.get("new_school", "").strip()
        school = new_school or request.POST.get("school")
        if school:
          check_school = School.objects.get_or_create(name=school)
          user.school = check_school[0]
          user.save()
      return redirect("onboarding-classes")
    elif form == "full_name":
      if not skip:
        full_name = request.POST.get("full_name")
        if full_name:
          user.full_name = full_name
          user.save()
      form = "email"
    elif form == "email":
      if not skip:
        email = request.POST.get("email")
        if email:
          user.email = email
          user.save()
      form = "school"
      schools = School.objects.all()

  context = {"form": form, "schools": schools}
  return render(request, "details.html", context)


def _classes_needing_records(request):
    """
    Classes that have at least one matched subject but still have zero
    records, minus any the teacher explicitly skipped this session
    (tracked in the session so 'skip' doesn't just re-show the same class).
    """
    skipped = request.session.get('onboarding_skipped_classes', [])
    return Class.objects.for_user(request.user).filter(
        subjectTeacher__isnull=False
    ).exclude(
        record__isnull=False
    ).exclude(
        id__in=skipped
    ).distinct().order_by('id')


@login_require
def onboarding_classes_view(request):
    """Onboarding step: tick every class+batch combo the teacher teaches (no free text — can't be typo'd)."""
    context = {
        'current_session': current_academic_session(),
        'class_names': [c[0] for c in CLASSES],
    }

    if request.method == "POST":
        if request.POST.get("action") == "skip":
            return redirect('onboarding-subjects')

        created = 0
        for value in request.POST.getlist('classes'):
            try:
                name, batch = value.split('|')
            except ValueError:
                continue
            _, was_created = Class.objects.get_or_create(
                user=request.user, name=name, batch=batch, session=current_academic_session()
            )
            if was_created:
                created += 1

        if created:
            return redirect('onboarding-subjects')

        context['error'] = "Tick at least one class, or skip this step."

    return render(request, 'onboarding-classes.html', context)


@login_require
def onboarding_subjects_view(request):
    """
    Onboarding step: pick which existing subjects the teacher teaches, with
    a quick 'Add Subject' for anything missing from the shared list. The
    chosen subject ids are stashed in session so the next step (matching
    them to classes) only shows what's relevant to this teacher instead of
    every subject in the database.
    """
    if request.method == "POST":
        if request.POST.get("action") == "skip":
            return redirect('home')

        selected_ids = request.POST.getlist('subjects')
        subjects = list(Subject.objects.filter(id__in=selected_ids))

        if Class.objects.for_user(request.user).exists() and subjects:
            request.session['onboarding_selected_subjects'] = [s.id for s in subjects]
            return redirect('onboarding-subject-match')
        return redirect('home')

    subjects = Subject.objects.all().order_by('name')
    return render(request, 'onboarding-subjects.html', {'subjects': subjects})


@login_require
def onboarding_subject_match_view(request):
    """Onboarding step: tick which (teacher-picked) subjects apply to which class — creates SubjectTeacher rows."""
    classes = Class.objects.for_user(request.user).order_by('name', 'batch')

    selected_subject_ids = request.session.get('onboarding_selected_subjects')
    if selected_subject_ids:
        subjects = Subject.objects.filter(id__in=selected_subject_ids).order_by('name')
    else:
        subjects = Subject.objects.all().order_by('name')

    if not classes.exists() or not subjects.exists():
        request.session.pop('onboarding_selected_subjects', None)
        return redirect('home')

    if request.method == "POST":
        request.session.pop('onboarding_selected_subjects', None)
        if request.POST.get("action") == "skip":
            return redirect('home')

        OnboardingService.save_subject_class_matches(request.POST, request.user)
        return redirect('onboarding-records')

    context = {'classes': classes, 'subjects': subjects}
    return render(request, 'onboarding-subject-match.html', context)


@login_require
def create_subject_ajax_view(request):
    """
    Quick-create (or reuse) a Subject inline, without leaving the form
    that needed it. Used from:
      - the regular Subject form's dropdown (mode='select', default) —
        returns a freshly rendered <select id="id_subject"> with the new
        subject selected, swapped in via outerHTML.
      - the onboarding subjects checklist (mode='checklist-item') —
        returns one new checked checkbox row to append.
    """
    name = request.POST.get('name', '').strip()
    mode = request.POST.get('mode', 'select')

    subject = None
    if name:
        subject, _ = Subject.objects.get_or_create(name=name.strip().title())

    if mode == 'checklist-item':
        return render(request, 'subject-checklist-item.html', {'subject': subject})

    subjects = Subject.objects.all().order_by('name')
    context = {'subjects': subjects, 'selected_id': subject.id if subject else None}
    return render(request, 'subject-select.html', context)


@login_require
def onboarding_records_view(request):
    """
    Onboarding step: create one starter Record per class that has a
    matched subject. Auto-advances to the next class needing a record
    after each save or skip; redirects home once none remain.
    """
    if request.method == "POST":
        action = request.POST.get("action")
        class_id = request.POST.get("class_id")

        if action == "skip_all":
            request.session.pop('onboarding_skipped_classes', None)
            return redirect('home')

        if action == "skip_class" and class_id:
            skipped = request.session.get('onboarding_skipped_classes', [])
            skipped.append(int(class_id))
            request.session['onboarding_skipped_classes'] = skipped
            return redirect('onboarding-records')

        # action == "save"
        class_obj = get_object_or_404(Class, id=class_id, user=request.user)
        form = RecordForm(request.POST, user=request.user)
        form.fields['class_name'].widget = forms.HiddenInput()
        form.fields['subject'].queryset = SubjectTeacher.objects.filter(
            user=request.user, class_name=class_obj
        )

        if form.is_valid():
            record = form.save(commit=False)
            record.user = request.user
            record.class_name = class_obj
            record.save()
            return redirect('onboarding-records')

        remaining = _classes_needing_records(request).count()
        context = {'form': form, 'class_obj': class_obj, 'remaining': remaining}
        return render(request, 'onboarding-records.html', context)

    next_class = _classes_needing_records(request).first()
    if not next_class:
        request.session.pop('onboarding_skipped_classes', None)
        return redirect('home')

    form = RecordForm(initial={'class_name': next_class}, user=request.user)
    form.fields['class_name'].widget = forms.HiddenInput()
    form.fields['subject'].queryset = SubjectTeacher.objects.filter(
        user=request.user, class_name=next_class
    )

    remaining = _classes_needing_records(request).count()
    context = {'form': form, 'class_obj': next_class, 'remaining': remaining}
    return render(request, 'onboarding-records.html', context)

@login_require
def bulk_create_student(request, id):
  class_name = Class.objects.get(id=id)
  body = request.POST.get("body")
  if body:
    seperate_body = body.split("\n")
    for std in seperate_body:
      Student.objects.create_for_user(request.user, name=std, class_name=class_name)
    return HttpResponse(f"{len(seperate_body)} students have been added to {class_name.name}")
  else:
    return HttpResponse("Body is empty")

@login_require
def set_active_term_view(request):
    """
    HTMX view — updates the user's active term and returns the refreshed
    term-indicator partial so the sidebar/top-bar badge updates in place.
    """
    if request.method == "POST":
        term = request.POST.get("term")
        valid_terms = ["First Term", "Second Term", "Third Term"]
        if term in valid_terms:
            request.user.active_term = term
            request.user.save()
    # Always return the updated indicator partial
    return render(request, "term-indicator.html", {"user": request.user})


@login_require
def quick_setup_view(request, class_id):
    """
    Quick-setup: creates Exam (70) + Test (30) records for a class in one shot.
    Expects POST with:
      - subject_id  (SubjectTeacher id)
      - record_number (default 1)
    Uses request.user.active_term as the term.
    """
    from django.db import IntegrityError

    class_obj = get_object_or_404(Class, id=class_id)

    if request.method == "GET":
        # Return the quick-setup modal
        subjects = SubjectTeacher.objects.for_user(request.user).filter(
            class_name=class_obj
        )
        return render(request, "quick-setup-modal.html", {
            "class": class_obj,
            "subjects": subjects,
            "active_term": request.user.active_term,
        })

    # POST — create the two records
    subject_id   = request.POST.get("subject_id")
    record_number = int(request.POST.get("record_number", 1))
    active_term  = request.user.active_term or "First Term"

    subject_obj = get_object_or_404(SubjectTeacher, id=subject_id)

    created = []
    errors  = []

    specs = [
        {"record_type": "Exam", "total_score": 70},
        {"record_type": "Test", "total_score": 30},
    ]

    for spec in specs:
        try:
            rec, was_created = Record.objects.get_or_create(
                title=active_term,
                subject=subject_obj,
                class_name=class_obj,
                record_type=spec["record_type"],
                record_number=record_number,
                defaults={
                    "user": request.user,
                    "total_score": spec["total_score"],
                },
            )
            if was_created:
                created.append(f"{spec['record_type']} ({spec['total_score']})")
            else:
                errors.append(
                    f"{spec['record_type']} #{record_number} already exists for {active_term}"
                )
        except IntegrityError:
            errors.append(
                f"{spec['record_type']} #{record_number} already exists for {active_term}"
            )

    if created and not errors:
        msg = (
            f"<div class='quick-setup-success'>"
            f"<i class='fas fa-circle-check'></i> "
            f"Created {' + '.join(created)} for {subject_obj} · {active_term}"
            f"</div>"
        )
    elif created and errors:
        msg = (
            f"<div class='quick-setup-partial'>"
            f"<i class='fas fa-triangle-exclamation'></i> "
            f"Created: {', '.join(created)}. Skipped: {', '.join(errors)}"
            f"</div>"
        )
    else:
        msg = (
            f"<div class='quick-setup-error'>"
            f"<i class='fas fa-circle-xmark'></i> "
            f"{' '.join(errors)}"
            f"</div>"
        )

    return HttpResponse(msg)


# ═══════════════════════════════════════════════════════════════
# NEW: Report Card view
# ═══════════════════════════════════════════════════════════════

@login_require
def report_card_view(request, student_id=None):
    # ----- No student or class specified – show class selection -----
    if student_id is None and 'class_id' not in request.GET:
        all_classes = Class.objects.for_user(request.user).order_by('name', 'batch')
        return render(request, 'report-card-select.html', {'all_classes': all_classes})

    # ----- If class_id is provided, redirect to the first student in that class -----
    class_id = request.GET.get('class_id')
    if class_id and student_id is None:
        class_obj = get_object_or_404(Class, id=class_id, user=request.user)
        first_student = Student.objects.filter(class_name=class_obj, user=request.user).order_by('name').first()
        if first_student:
            term = request.GET.get('term', request.user.active_term or "First Term")
            session = request.GET.get('session', class_obj.session)
            return redirect(f"{reverse('report-card', args=[first_student.id])}?term={term}&session={session}")
        else:
            messages.warning(request, "No students found in this class.")
            return redirect('class-list')

    # ----- Existing student report logic (same as before) -----

    # Otherwise, get the student by ID
    student = get_object_or_404(Student, id=student_id, user=request.user)
    class_obj = student.class_name

    term = request.GET.get('term', request.user.active_term or "First Term")
    session = request.GET.get('session', class_obj.session)

    # Build report context
    context = ReportCardService.build_report_card_context(student, term, session)
    context['school'] = request.user.school
    context['term'] = term
    context['session'] = session
    context['student'] = student
    context['class_obj'] = class_obj

    # ---- Navigation: all students in the same class ----
    all_students = Student.objects.filter(class_name=class_obj, user=request.user).order_by('name')
    student_ids = list(all_students.values_list('id', flat=True))
    current_index = student_ids.index(student.id) if student.id in student_ids else -1

    prev_id = student_ids[current_index - 1] if current_index > 0 else None
    next_id = student_ids[current_index + 1] if current_index < len(student_ids) - 1 else None

    # ---- All classes taught by this teacher ----
    all_classes = Class.objects.for_user(request.user).order_by('name', 'batch')

    context.update({
        'all_students': all_students,
        'prev_id': prev_id,
        'next_id': next_id,
        'current_index': current_index + 1,
        'total_students': len(student_ids),
        'all_classes': all_classes,
    })

    HistoryService.log_user_activity(
        request.user,
        f"Report Card: {student.name} ({term} {session})",
        reverse('report-card', args=[student_id])
    )
    return render(request, 'report-card.html', context)



@login_require
def class_report_view(request, id):
    """Class‑specific report:
       - GET without subject_id → list of subjects with records.
       - GET with subject_id → full report for that subject.
    """
    class_obj = get_object_or_404(Class, id=id, user=request.user)
    term = request.user.active_term or "First Term"
    subject_id = request.GET.get('subject_id')
    sort_order = request.GET.get('sort', 'asc')

    if subject_id:
        # Generate report for a specific subject – NO user argument
        report_result = ReportService.generate_report(
            subject_id=subject_id,
            class_name=class_obj.name,
            batch=class_obj.batch,
            term=term,
            sort_order=sort_order,
        )

        context = {
            'class_obj': class_obj,
            'total_report': report_result.get('total_report'),
            'subject': report_result.get('subject'),
            'is_all_subjects': report_result.get('is_all_subjects', False),
            'terms': report_result.get('terms', []),
            'batch': class_obj.batch,
            'class': class_obj.name,
            'term': term,
            'sort': sort_order,
            'error': report_result.get('error'),
        }
        return render(request, 'class-report-partial.html', context)

    else:
        # List mode: show all subjects with records for this class
        subject_teachers = SubjectTeacher.objects.filter(
            class_name=class_obj,
            user=request.user,
            record__isnull=False
        ).distinct().select_related('subject')

        subjects_data = []
        for st in subject_teachers:
            records = Record.objects.filter(subject=st, class_name=class_obj)
            student_records = StudentRecord.objects.filter(record__in=records)
            avg_score = student_records.aggregate(Avg('score'))['score__avg']
            subjects_data.append({
                'subject_teacher': st,
                'subject': st.subject,
                'record_count': records.count(),
                'avg_score': avg_score or 0,
            })

        context = {
            'class_obj': class_obj,
            'subjects_data': subjects_data,
            'term': term,
        }
        return render(request, 'class-report-list.html', context)
        
@login_require
def bulk_record_create_view(request, st_id):
    subject_teacher = get_object_or_404(SubjectTeacher, id=st_id, user=request.user)
    class_obj = subject_teacher.class_name
    term = request.user.active_term or "First Term"
    record_type_choices = ['Test', 'Exam', 'Assignment', 'Notes']

    if request.method == "POST":
        record_types = request.POST.getlist('record_type')
        total_scores = request.POST.getlist('total_score')
        created = []
        errors = []
        # Find the next available record number for this subject+class+term (we'll auto-number)
        # We'll use the existing `_next_record_number` logic, but we need to call it per record.
        # To avoid conflicts, we'll create records sequentially without a starting number.
        # The model's save() will auto-assign the next number within its scope.

        for rt, ts in zip(record_types, total_scores):
            try:
                ts_int = int(ts)
                if ts_int <= 0:
                    raise ValueError("Score must be positive")
            except ValueError:
                errors.append(f"Invalid total score for {rt}: {ts}")
                continue

            # Create record without record_number – it will be auto-assigned in save()
            rec = Record(
                user=request.user,
                title=term,
                subject=subject_teacher,
                class_name=class_obj,
                record_type=rt,
                total_score=ts_int,
                # record_number is left None – save() will assign it
            )
            try:
                rec.save()  # This will call _next_record_number()
                created.append(f"{rt} #{rec.record_number}")
            except Exception as e:
                errors.append(f"{rt}: {str(e)}")

        # Return the result partial
        context = {
            'created': created,
            'errors': errors,
            'subject_teacher': subject_teacher,
        }
        return render(request, 'bulk-record-result.html', context)

    # GET: render the full modal
    context = {
        'subject_teacher': subject_teacher,
        'class_obj': class_obj,
        'term': term,
        'record_type_choices': record_type_choices,
    }
    return render(request, 'bulk-record-form.html', context)
    
@login_require
def bulk_multi_record_score_view(request, st_id):
    subject_teacher = get_object_or_404(SubjectTeacher, id=st_id, user=request.user)
    class_obj = subject_teacher.class_name
    term = request.user.active_term or "First Term"
    mode = request.GET.get('mode', 'table')  # 'table' or 'single'

    # Get all manual records for this subject, class, and term
    records = Record.objects.filter(
        subject=subject_teacher,
        class_name=class_obj,
        title=term,
        logic__isnull=True
    ).order_by('record_number')

    students = Student.objects.filter(class_name=class_obj).order_by('name')

    if request.method == "POST":
        # Save scores (same as before)
        for student in students:
            for rec in records:
                key = f"score_{student.id}_{rec.id}"
                raw = request.POST.get(key, '').strip()
                if raw == '':
                    continue
                try:
                    score = int(raw)
                    if score < 0 or score > rec.total_score:
                        raise ValueError(f"Score must be between 0 and {rec.total_score}")
                    sr, created = StudentRecord.objects.get_or_create(
                        student=student,
                        record=rec,
                        defaults={'score': score}
                    )
                    if not created:
                        sr.score = score
                        sr.save()
                except ValueError:
                    pass
        return HttpResponse("Scores saved successfully.")

    # Build existing scores map
    existing = {}
    for sr in StudentRecord.objects.filter(record__in=records):
        existing[(sr.student.id, sr.record.id)] = sr.score

    # Build grid rows (for table mode)
    grid_rows = []
    for student in students:
        cells = []
        for rec in records:
            cells.append({
                'record': rec,
                'score': existing.get((student.id, rec.id), ''),
            })
        grid_rows.append({
            'student': student,
            'cells': cells,
        })

    context = {
        'subject_teacher': subject_teacher,
        'class_obj': class_obj,
        'term': term,
        'records': records,
        'grid_rows': grid_rows,
        'students': students,
        'existing_scores': existing,
        'mode': mode,
        'total_students': students.count(),
    }

    if mode == 'single':
        # Get the current index from GET, default to 0
        try:
            current_index = int(request.GET.get('index', 0))
        except ValueError:
            current_index = 0

        # Clamp index
        if current_index >= students.count():
            current_index = students.count() - 1
        if current_index < 0:
            current_index = 0

        student = students[current_index] if students else None
        prev_index = current_index - 1 if current_index > 0 else None
        next_index = current_index + 1 if current_index < students.count() - 1 else None

        # Build records for this student
        student_records = []
        for rec in records:
            score = existing.get((student.id, rec.id), '') if student else ''
            student_records.append({
                'record': rec,
                'score': score,
            })

        context.update({
            'current_student': student,
            'current_index': current_index + 1,
            'prev_index': prev_index,
            'next_index': next_index,
            'student_records': student_records,
        })
        return render(request, 'bulk-multi-score-single.html', context)

    # Default: render table mode
    return render(request, 'bulk-multi-score-form.html', context)