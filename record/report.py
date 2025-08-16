from django.db.models import Avg, Max, Min, Q
from .models import Record, StudentRecord, Subject, Class, Student
from collections import defaultdict

class Report:
    """Service for generating various reports"""
    
    @staticmethod
    def generate_student_performance_report(subject_id, class_name, batch, term, sort_order='asc'):
        """Generate comprehensive student performance report"""
        try:
            # Validate inputs
            if subject_id == "all":
                subjects = Subject.objects.all()
                is_all_subjects = True
            else:
                subjects = Subject.objects.filter(id=subject_id)
                is_all_subjects = False
            
            if not subjects.exists():
                raise ValueError("No subjects found")
            
            # Get class
            class_obj = Class.objects.filter(name=class_name, batch=batch).first()
            if not class_obj:
                raise ValueError(f"Class {class_name} batch {batch} not found")
            
            # Build report data
            report_data = []
            terms = []
            
            for subject in subjects:
                records = Record.objects.filter(
                    subject=subject,
                    class_name=class_obj
                )
                
                if term != "all":
                    records = records.filter(record_type=term)
                
                student_records = StudentRecord.objects.filter(
                    record__in=records
                ).select_related('student', 'record')
                
                # Group by student
                student_data = defaultdict(list)
                for sr in student_records:
                    student_data[sr.student].append(sr)
                    if sr.record.record_type not in terms:
                        terms.append(sr.record.record_type)
                
                # Calculate averages and build report
                for student, records_list in student_data.items():
                    avg_score = sum(r.score for r in records_list) / len(records_list)
                    avg_percentage = sum(r.percentage for r in records_list) / len(records_list)
                    
                    report_data.append({
                        'student': student,
                        'subject': subject,
                        'records': records_list,
                        'average_score': round(avg_score, 2),
                        'average_percentage': round(avg_percentage, 2),
                        'total_records': len(records_list)
                    })
            
            # Sort the report
            if sort_order == 'desc':
                report_data.sort(key=lambda x: x['average_percentage'], reverse=True)
            else:
                report_data.sort(key=lambda x: x['average_percentage'])
            
            return {
                'success': True,
                'data': report_data,
                'subject': subjects.first() if not is_all_subjects else None,
                'is_all_subjects': is_all_subjects,
                'terms': terms,
                'class_name': class_name,
                'batch': batch,
                'term': term,
                'sort_order': sort_order
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'data': []
            }
    
    @staticmethod
    def generate_class_summary_report(class_name, batch=None):
        """Generate summary report for a class"""
        try:
            if batch:
                class_obj = Class.objects.get(name=class_name, batch=batch)
            else:
                class_obj = Class.objects.filter(name=class_name).first()
            
            if not class_obj:
                raise ValueError(f"Class {class_name} not found")
            
            students = Student.objects.filter(class_name=class_obj)
            records = Record.objects.filter(class_name=class_obj)
            
            summary = {
                'class': class_obj,
                'total_students': students.count(),
                'total_records': records.count(),
                'subjects': Subject.objects.filter(record__class_name=class_obj).distinct(),
                'recent_records': records.order_by('-date_created')[:5]
            }
            
            # Calculate class averages
            student_records = StudentRecord.objects.filter(
                record__class_name=class_obj
            ).aggregate(
                avg_score=Avg('score'),
                max_score=Max('score'),
                min_score=Min('score')
            )
            
            summary.update(student_records)
            
            return {
                'success': True,
                'data': summary
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    @staticmethod    
    def generate_report(subject_id, class_name, batch, term, sort_order):
        """
        Generate academic report for students in a specific subject and class.
        
        Args:
            subject_id: ID of the subject
            class_name: Name of the class
            batch: Batch name or "All" for all batches
            term: Term name or "All" for all terms
            sort_order: "desc" for descending by score, "asc" for ascending by name
        
        Returns:
            tuple: (total_report, subject_model, is_all, term, terms)
        """
        
        # Get class models with optimization
        class_model = Class.objects.filter(name=class_name)
        if batch != "All":
            class_model = class_model.filter(batch=batch)
            is_all = False
        else:
            is_all = True
    
        # Get subject model with error handling
        try:
            subject_model = Subject.objects.get(id=int(subject_id))
        except (Subject.DoesNotExist, ValueError):
            raise ValueError(f"Subject with id {subject_id} not found")
    
        # Get records with optimized queries
        record_qs = Record.objects.filter(
            class_name__in=class_model, 
            subject=subject_model
        ).select_related('class_name', 'subject')
        
        if term not in ["All", "None", None]:
            record_qs = record_qs.filter(title=term)
        
        # Set term to None if "All" is selected for consistent handling
        term = None if term == "All" else term
    
        # Get student records with optimization
        student_records = StudentRecord.objects.filter(
            record__class_name__in=class_model,
            record__subject=subject_model
        ).select_related('student', 'record', 'record__class_name')
    
        # Group student records by student name
        student_names = set(student_records.values_list('student__name', flat=True))
        student_objects = {name: [] for name in student_names}
    
        for std in student_records:
            student_objects[std.student.name].append(std)
    
        # Initialize data structures
        students_data = []
        term_titles = ["First Term", "Second Term", "Third Term"]
        all_term_records = defaultdict(list)
        
        # Track unique record types per term to avoid duplicates
        term_record_keys = defaultdict(set)
    
        for student_name in sorted(student_objects.keys()):
            try:
                student_model = Student.objects.select_related('class_name').get(name=student_name)
            except Student.DoesNotExist:
                continue  # Skip if student doesn't exist
                
            student_batch = student_model.class_name.batch
            student_records_filtered = record_qs.filter(class_name__batch=student_batch)
    
            # Initialize term data structures
            term_scores = {title: [] for title in term_titles}
            term_test_totals = {title: 0 for title in term_titles}
            term_total_scores = {title: 0 for title in term_titles}
            student_total_score = 0
            student_total_available_score = 0
            
            # Create mapping of record ID to score for this student
            student_scores = {r.record.id: r.score for r in student_objects[student_name]}
    
            for rec in student_records_filtered:
                score = student_scores.get(rec.id, '-')
                term_key = rec.title
                
                rec_data = {
                    'type': rec.record_type,
                    'number': rec.record_number,
                    'score': score,
                }
                term_scores[term_key].append(rec_data)
    
                # Create unique key for record type to avoid duplicates
                record_key = f"{rec.record_type}_{rec.record_number}"
                if record_key not in term_record_keys[rec.title]:
                    term_record_keys[rec.title].add(record_key)
                    all_term_records[rec.title].append({
                        'type': rec.record_type,
                        'number': rec.record_number
                    })
    
                # Calculate totals only for valid numeric scores
                if isinstance(score, (int, float)) and score != '-':
                    student_total_score += score
                    student_total_available_score += rec.total_score
    
                    # Calculate term totals only if not filtering by specific term
                    if not term:
                        if rec.record_type != "Exam":
                            term_test_totals[term_key] += score
                        term_total_scores[term_key] += score
    
            # Calculate percentage with safe division
            percentage = round((student_total_score / student_total_available_score) * 100, 2) if student_total_available_score > 0 else 0
    
            student_data = {
                'id': student_model.id,
                'name': student_name,
                'record_by_term': term_scores,
                'total_score': student_total_score,
                'percentage': percentage,
                'total_available_score': student_total_available_score,
                'class_name': str(student_batch),
            }
            
            # Add term totals only if not filtering by specific term
            if not term:
                student_data['term_totals'] = {
                    title: {
                        'test_total': term_test_totals[title],
                        'total_score': term_total_scores[title]
                    } for title in term_titles
                }
    
            students_data.append(student_data)
    
        # Sort students based on sort_order
        if sort_order == 'desc':
            students_data.sort(key=lambda x: x['total_score'], reverse=True)
        else:
            students_data.sort(key=lambda x: x['name'])
    
        # Create header structure
        header_structure = {
            'header': True,
            'count': 'S/N',
            'name': 'Student',
            'term_headers': {title: all_term_records[title] for title in term_titles},
            'total': 'Total Score',
            'Percentage': '100%',
        }
    
        # Add term totals to header only if not filtering by specific term
        if not term:
            header_structure['term_totals'] = {
                title: {
                    'test_total': f"{title} Test Total",
                    'total_score': f"{title} Total Score"
                } for title in term_titles
            }
    
        # Combine header and student data
        total_report = [header_structure] + students_data
        terms = term_titles
        success = True
        return {
                'success': True,
                'total_report': total_report,
                'subject': subject_model,
                'is_all': is_all,
                'terms': terms or [],
                'class_name': class_name,
                'batch': batch,
                'term': None if term in ("All", "all", None) else term,
                #'sort_order': sort_order
            }