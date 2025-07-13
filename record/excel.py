from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from django.http import HttpResponse
from .models import Subject, Class, Record, StudentRecord, Student

def export_report_excel(request):
    subject_id = request.GET.get('subject')
    class_name = request.GET.get('class')
    batch = request.GET.get("batch")
    term = request.GET.get("term")
    sort_order = request.GET.get('sort', 'asc')

    # Validate input
    try:
        class_model = Class.objects.filter(name=class_name)
        if batch != "All":
            class_model = class_model.filter(batch=batch)
        subject_model = Subject.objects.get(id=int(subject_id))
    except (Class.DoesNotExist, Subject.DoesNotExist):
        return HttpResponse("Invalid class or subject", status=400)

    record_qs = Record.objects.filter(class_name__in=class_model, subject=subject_model)
    if term not in ["All", "None", None]:
        record_qs = record_qs.filter(title=term)
    student_records = StudentRecord.objects.filter(record__class_name__in=class_model, record__subject=subject_model)

    term = None if term == "All" else term
    student_names = set(student_records.values_list('student__name', flat=True))
    student_objects = {name: [] for name in student_names}

    for std in student_records:
        student_objects[std.student.name].append(std)

    record_to_render = []
    students_data = []
    total_available_score = 0

    for student_name in sorted(student_objects.keys()):
        student_model = Student.objects.get(name=student_name)
        student_batch = student_model.class_name.batch
        student_records_filtered = record_qs.filter(class_name__batch=student_batch)

        rec_list = []
        total_score = 0
        first_term_total_score = 0
        second_term_total_score = 0
        third_term_total_score = 0
        first_term_test_total = 0
        second_term_test_total = 0
        third_term_test_total = 0
        student_total_available_score = 0
        percentage = 0
        student_scores = {r.record.id: r.score for r in student_objects[student_name]}

        for rec in student_records_filtered:
            score = student_scores.get(rec.id, '-')
            rec_list.append({
                'title': rec.title,
                'type': rec.record_type,
                'number': rec.record_number,
                'score': score,
            })

            record_id_str = f"{rec.title} {rec.record_type} {rec.record_number}"
            if record_id_str not in record_to_render:
                record_to_render.append(record_id_str)

            if isinstance(score, (int, float)):
                total_score += score
                student_total_available_score += rec.total_score
                if not term:
                    if rec.title == "First Term":
                        if rec.record_type != "Exam":
                            first_term_test_total += score
                        first_term_total_score += score
                    elif rec.title == "Second Term":
                        if rec.record_type != "Exam":
                            second_term_test_total += score
                        second_term_total_score += score
                    elif rec.title == "Third Term":
                        if rec.record_type != "Exam":
                            third_term_test_total += score
                        third_term_total_score += score

        if student_total_available_score > total_available_score:
            total_available_score = student_total_available_score
        if total_available_score != 0:
            percentage = round((total_score / total_available_score) * 100, 2)

        data = {
            'id': student_model.id,
            'name': student_name,
            'record': rec_list,
            'total_score': total_score,
            'class_name': f"{student_batch}",
            'percentage': percentage,
            'total_available_score': total_available_score
        }
        if not term:
            data.update({
                'first_term_total_score': first_term_total_score,
                'second_term_total_score': second_term_total_score,
                'third_term_total_score': third_term_total_score,
                'first_term_test_total': first_term_test_total,
                'second_term_test_total': second_term_test_total,
                'third_term_test_total': third_term_test_total,
            })

        students_data.append(data)

    if sort_order == 'desc':
        students_data.sort(key=lambda x: x['total_score'], reverse=True)
    else:
        students_data.sort(key=lambda x: x['name'])

    # === Generate Excel ===
    wb = Workbook()
    ws = wb.active
    ws.title = "Student Report"
# Make header row bold and wrap text
    from openpyxl.styles import Font, Alignment
    bold_font = Font(bold=True)
    wrap_text = Alignment(wrap_text=True)

    for cell in ws[1]:
      cell.font = bold_font
      cell.alignment = wrap_text

# Set width for the first 50 columns (adjust if you have more)
    for col in range(1, 51):
      col_letter = get_column_letter(col)
      ws.column_dimensions[col_letter].width = 20  # You can increase this to 25 or reduce to 15 if needed

    row = 1
    col = 1

    # Header
    ws.cell(row=row, column=col, value="S/N"); col += 1
    ws.cell(row=row, column=col, value="Student"); col += 1

    for rec in record_to_render:
        ws.cell(row=row, column=col, value=rec)
        col += 1

    if not term:
        ws.cell(row=row, column=col, value="First Term Test Total"); col += 1
        ws.cell(row=row, column=col, value="First Term Total Score"); col += 1
        ws.cell(row=row, column=col, value="Second Term Test Total"); col += 1
        ws.cell(row=row, column=col, value="Second Term Total Score"); col += 1
        ws.cell(row=row, column=col, value="Third Term Test Total"); col += 1
        ws.cell(row=row, column=col, value="Third Term Total Score"); col += 1

    ws.cell(row=row, column=col, value="Total Score"); col += 1
    ws.cell(row=row, column=col, value="Total Available Score"); col += 1
    ws.cell(row=row, column=col, value="Percentage")

    # Student Rows
    for idx, student in enumerate(students_data, start=1):
        row += 1
        col = 1
        ws.cell(row=row, column=col, value=idx); col += 1
        ws.cell(row=row, column=col, value=f"{student['name']} ({student['class_name']})"); col += 1

        for rec in student['record']:
            ws.cell(row=row, column=col, value=rec['score'] if rec['score'] != '-' else None)
            col += 1

        if not term:
            ws.cell(row=row, column=col, value=student.get('first_term_test_total')); col += 1
            ws.cell(row=row, column=col, value=student.get('first_term_total_score')); col += 1
            ws.cell(row=row, column=col, value=student.get('second_term_test_total')); col += 1
            ws.cell(row=row, column=col, value=student.get('second_term_total_score')); col += 1
            ws.cell(row=row, column=col, value=student.get('third_term_test_total')); col += 1
            ws.cell(row=row, column=col, value=student.get('third_term_total_score')); col += 1

        ws.cell(row=row, column=col, value=student.get('total_score')); col += 1
        ws.cell(row=row, column=col, value=student.get('total_available_score')); col += 1
        ws.cell(row=row, column=col, value=student.get('percentage'))

    # === Send Response ===
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename=f"{class_name} {batch} Report.xlsx"'
    wb.save(response)
    return response