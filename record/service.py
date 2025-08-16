# services.py - Business logic separated from views
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from django.shortcuts import get_object_or_404
from .models import *

class HistoryService:
    """Handle user history logging"""
    
    @staticmethod
    def log_user_activity(user, title, url):
        """Log user activity to history"""
        history, created = History.objects.get_or_create(
            user=user, 
            title=title, 
            url=url,
            defaults={'time': timezone.now()}
        )
        if not created:
            history.time = timezone.now()
            history.save()
        return history

class FormService:
    """Handle form processing and validation"""
    
    @staticmethod
    def save_model_form(form, user):
        """Save form with proper error handling"""

        if not form.is_valid():
            return FormService._format_form_errors(form)
        
        try:
            instance = form.save(commit=False)
            instance.user = user
            instance.save()
            
            success_message = FormService._format_success_message(form, instance)
            return {
                'success': True,
                'message': success_message,
                'instance': instance
            }
            
        except ValidationError as e:
            return {
                'success': False,
                'message': f"Validation error: {str(e)}"
            }
        except Exception as e:
            return {
                'success': False,
                'message': f"Error saving record: {str(e)}"
            }
    
    @staticmethod
    def _format_success_message(form, instance):
        """Format success message with field values"""
        fields = [f.name for f in instance._meta.fields if f.name in form.cleaned_data]
        field_values = [
            f"{f.replace('_', ' ').title()}: {form.cleaned_data.get(f)}" 
            for f in fields
        ]
        print("success")
        display_data = "<br>".join(field_values)
        return f"<div class='alert alert-primary'>{display_data}<br>Record created successfully.</div>"
    
    @staticmethod
    def _format_form_errors(form):
        """Format form errors for display"""
        error_messages = []
        print("failed")
        for field, errors in form.errors.items():
            label = form.fields.get(field).label if field in form.fields else field.replace('_', ' ').title()
            for error in errors:
                error_messages.append(f"<li><strong>{label}:</strong> {error}</li>")
        
        error_html = "<ul>" + "".join(error_messages) + "</ul>"
        return {
            'success': False,
            'message': f"<div class='alert alert-danger'><strong>Form Errors:</strong>{error_html}</div>"
        }

class StudentRecordService:
    """Handle student record operations"""
    
    @staticmethod
    def get_students_without_record(record):
        """Get students in class who don't have this record"""
        students_with_record = StudentRecord.objects.filter(record=record)
        return Student.objects.filter(class_name=record.class_name).exclude(
            record__in=students_with_record
        ).order_by('name')
    
    @staticmethod
    def filter_student_records(students_queryset, score_filter=None, sort_filter=None):
        """Filter and sort student records"""
        if score_filter:
            score = score_filter.get('score')
            operator = score_filter.get('operator')
            
            if operator == "=":
                students_queryset = students_queryset.filter(score=score)
            elif operator == ">":
                students_queryset = students_queryset.filter(score__gt=score)
            elif operator == "<":
                students_queryset = students_queryset.filter(score__lt=score)
        
        if sort_filter == "alpha":
            students_queryset = students_queryset.order_by("student__name")
        elif sort_filter == "score":
            students_queryset = students_queryset.order_by("-score")
        
        return students_queryset

class SearchService:
    """Handle search operations"""
    
    @staticmethod
    def search_all(query, user):
        """Search across all models"""
        return {
            'records': Record.objects.for_user(user).filter(title__icontains=query),
            'students': Student.objects.for_user(user).filter(name__icontains=query),
            'classes': Class.objects.for_user(user).filter(name__icontains=query)
        }

class UserService:
    """Handle user operations"""
    
    @staticmethod
    def create_user(username, password):
        """Create new user with hashed password"""
        try:
            hashed_password = make_password(password)
            user = User.objects.create(username=username, password=hashed_password)
            return {'success': True, 'user': user}
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
from collections import defaultdict
from django.db.models import Avg, Max, Min, Q
from .models import Record, StudentRecord, Subject, Class, Student

class ReportService:
    """Unified report service combining student performance and class-summary style output."""

    @staticmethod
    def generate_report(subject_id, class_name, batch="All", term="All", sort_order="asc"):
        """
        Unified report builder.

        Returns a dict with:
          - success (bool)
          - data: list of per-student-per-subject summary items (avg score / percentage)
          - total_report: header + student rows (only built when a single subject is requested)
          - subject: Subject model or None
          - is_all_subjects: bool
          - terms: list of detected term names
          - class_name, batch, term, sort_order (echoed)
          - error (if success is False)
        """
        try:
            # --- Resolve class queryset and batch handling ---
            class_qs = Class.objects.filter(name=class_name)
            if batch and batch != "All":
                class_qs = class_qs.filter(batch=batch)
                is_all_batches = False
            else:
                is_all_batches = True

            if not class_qs.exists():
                raise ValueError(f"Class {class_name} (batch={batch}) not found")

            # --- Resolve subject(s) ---
            if subject_id in ("all", "All", None):
                subjects = Subject.objects.all()
                is_all_subjects = True
                subject_model = None
            else:
                try:
                    subject_model = Subject.objects.get(id=int(subject_id))
                except (Subject.DoesNotExist, ValueError):
                    raise ValueError(f"Subject with id {subject_id} not found")
                subjects = Subject.objects.filter(id=subject_model.id)
                is_all_subjects = False

            # --- Build base Record queryset ---
            record_qs = Record.objects.filter(
                class_name__in=class_qs,
                subject__in=subjects
            ).select_related('class_name', 'subject')

            # term filtering — accept either record_type or title
            if term not in ("All", "all", None):
                record_qs = record_qs.filter(Q(record_type=term) | Q(title=term))
                term_filtering = True
            else:
                term_filtering = False

            # --- StudentRecord queryset (optimized) ---
            student_record_qs = StudentRecord.objects.filter(
                record__in=record_qs
            ).select_related('student', 'record', 'record__class_name')

            # --- Build per-subject per-student summary (data) ---
            data = []
            detected_terms = []
            for subject in subjects:
                s_records = student_record_qs.filter(record__subject=subject)
                # group by student
                by_student = defaultdict(list)
                for sr in s_records:
                    by_student[sr.student].append(sr)
                    if sr.record.record_type not in detected_terms:
                        detected_terms.append(sr.record.record_type)

                for student_obj, recs in by_student.items():
                    avg_score = sum(r.score for r in recs if isinstance(r.score, (int, float))) / (
                        sum(1 for r in recs if isinstance(r.score, (int, float))) or 1
                    )
                    avg_percentage = sum(r.percentage for r in recs if isinstance(r.percentage, (int, float))) / (
                        sum(1 for r in recs if isinstance(r.percentage, (int, float))) or 1
                    )

                    data.append({
                        'student': student_obj,
                        'subject': subject,
                        'records': recs,
                        'average_score': round(avg_score, 2),
                        'average_percentage': round(avg_percentage, 2),
                        'total_records': len(recs)
                    })

            # sort `data` by average_percentage or student name as requested
            if sort_order == 'desc':
                data.sort(key=lambda x: x['average_percentage'], reverse=True)
            else:
                data.sort(key=lambda x: getattr(x['student'], 'name', '') or '')

            # --- Build detailed `total_report` (header + student rows) when a single subject requested ---
            total_report = None
            if not is_all_subjects and subjects.exists():
                subject_for_report = subjects.first()

                # We'll build a header describing terms and the records for each term
                term_titles = ["First Term", "Second Term", "Third Term"]
                # collect all records grouped by term title to use as column headers
                all_term_records = defaultdict(list)
                term_record_keys = defaultdict(set)

                # prepare mapping of student name -> list of StudentRecord
                student_objects = defaultdict(list)
                for sr in student_record_qs.filter(record__subject=subject_for_report):
                    student_objects[sr.student.name].append(sr)

                # Build students_data rows
                students_data = []
                for student_name in sorted(student_objects.keys()):
                    try:
                        student_model = Student.objects.select_related('class_name').get(name=student_name)
                    except Student.DoesNotExist:
                        continue

                    student_batch = student_model.class_name.batch
                    # filter records to the class & batch of the student
                    records_for_class_and_subject = record_qs.filter(class_name__batch=student_batch, subject=subject_for_report)

                    # term structures
                    term_scores_by_title = {t: [] for t in term_titles}
                    term_test_totals = {t: 0 for t in term_titles}
                    term_total_scores = {t: 0 for t in term_titles}
                    student_total_score = 0
                    student_total_available_score = 0

                    # map record.id -> score for this student
                    student_scores_map = {r.record.id: r.score for r in student_objects[student_name]}

                    for rec in records_for_class_and_subject:
                        score = student_scores_map.get(rec.id, '-')
                        term_key = rec.title if rec.title else rec.record_type or "Unknown"

                        rec_data = {
                            'type': rec.record_type,
                            'number': getattr(rec, 'record_number', None),
                            'score': score,
                            'total_score': getattr(rec, 'total_score', None)
                        }
                        # append to term list
                        if term_key not in term_scores_by_title:
                            # ensure we have a slot if custom terms exist
                            term_scores_by_title.setdefault(term_key, [])
                        term_scores_by_title[term_key].append(rec_data)

                        # build unique key for header record list
                        record_key = f"{rec.record_type}_{getattr(rec, 'record_number', '')}"
                        if record_key not in term_record_keys[term_key]:
                            term_record_keys[term_key].add(record_key)
                            all_term_records[term_key].append({
                                'type': rec.record_type,
                                'number': getattr(rec, 'record_number', None)
                            })

                        # totals (only if numeric)
                        if isinstance(score, (int, float)):
                            student_total_score += score
                            if getattr(rec, 'total_score', None):
                                student_total_available_score += rec.total_score

                            if not term_filtering:
                                if rec.record_type != "Exam":
                                    term_test_totals[term_key] = term_test_totals.get(term_key, 0) + score
                                term_total_scores[term_key] = term_total_scores.get(term_key, 0) + score

                    percentage = round(
                        (student_total_score / student_total_available_score) * 100, 2
                    ) if student_total_available_score > 0 else 0

                    student_row = {
                        'id': student_model.id,
                        'name': student_name,
                        'record_by_term': term_scores_by_title,
                        'total_score': student_total_score,
                        'percentage': percentage,
                        'total_available_score': student_total_available_score,
                        'class_name': str(student_batch),
                    }

                    if not term_filtering:
                        student_row['term_totals'] = {
                            title: {
                                'test_total': term_test_totals.get(title, 0),
                                'total_score': term_total_scores.get(title, 0)
                            } for title in term_titles
                        }

                    students_data.append(student_row)

                # Sorting students_data
                if sort_order == 'desc':
                    students_data.sort(key=lambda x: x['total_score'], reverse=True)
                else:
                    students_data.sort(key=lambda x: x['name'])

                # header
                header_structure = {
                    'header': True,
                    'count': 'S/N',
                    'name': 'Student',
                    'term_headers': {title: all_term_records.get(title, []) for title in term_titles},
                    'total': 'Total Score',
                    'Percentage': '100%',
                }
                if not term_filtering:
                    header_structure['term_totals'] = {
                        title: {
                            'test_total': f"{title} Test Total",
                            'total_score': f"{title} Total Score"
                        } for title in term_titles
                    }

                total_report = [header_structure] + students_data

            # --- assemble final response ---
            return {
                'success': True,
                'data': data,
                'total_report': total_report,
                'subject': subject_model,
                'is_all_subjects': is_all_subjects,
                'terms': detected_terms or [],
                'class_name': class_name,
                'batch': batch,
                'term': None if term in ("All", "all", None) else term,
                'sort_order': sort_order
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'data': [],
                'total_report': None
            }
