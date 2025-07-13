from collections import defaultdict
from django.shortcuts import get_object_or_404
from .models import Class, Subject, Record, StudentRecord, Student

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
    
    return total_report, subject_model, is_all, term, terms