from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font, Alignment, Border, Side
from django.http import HttpResponse
from .models import Subject, Class, Record, StudentRecord, Student
from .report import generate_report

def export_report_excel(request):
    subject_id = request.GET.get('subject')
    class_name = request.GET.get('class')
    batch = request.GET.get("batch")
    term = request.GET.get("term")
    sort_order = request.GET.get('sort', 'asc')
    
    try:
        # Get report data
        total_report, subject_model, is_all, term, terms = generate_report(
            subject_id, class_name, batch, term, sort_order
        )
        
        # Validate that we have data
        if not total_report or len(total_report) < 2:
            raise ValueError("No data available for export")
        
        # Extract header and student data
        header_data = total_report[0]
        students_data = total_report[1:]  # All items except the header
        
        # === Generate Excel ===
        wb = Workbook()
        ws = wb.active
        ws.title = "Student Report"
        
        # Style configuration
        bold_font = Font(bold=True)
        center_alignment = Alignment(horizontal='center', vertical='center')
        wrap_alignment = Alignment(wrap_text=True, horizontal='center', vertical='center')
        border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # === CALCULATE COLUMN STRUCTURE ===
        col_position = 1
        
        # Basic columns
        basic_cols = 2  # S/N and Student
        col_position += basic_cols
        
        # Calculate columns for each term
        term_columns = {}
        for term_name in terms:
            term_records = header_data.get('term_headers', {}).get(term_name, [])
            record_count = len(term_records)
            totals_count = 2 if header_data.get('term_totals') else 0  # Test Total + Term Total
            
            term_columns[term_name] = {
                'start_col': col_position,
                'record_count': record_count,
                'totals_count': totals_count,
                'total_cols': record_count + totals_count
            }
            col_position += record_count + totals_count
        
        # Final columns
        final_cols = 2  # Total Score + Percentage
        total_columns = col_position + final_cols - 1
        
        # === CREATE FIRST HEADER ROW (Term Headers) ===
        row = 1
        col = 1
        
        # S/N and Student (rowspan=2)
        ws.cell(row=row, column=col, value="S/N")
        ws.merge_cells(start_row=row, start_column=col, end_row=row+1, end_column=col)
        col += 1
        
        ws.cell(row=row, column=col, value="Student")
        ws.merge_cells(start_row=row, start_column=col, end_row=row+1, end_column=col)
        col += 1
        
        # Term headers with colspan
        for term_name in terms:
            term_info = term_columns[term_name]
            if term_info['total_cols'] > 0:
                ws.cell(row=row, column=col, value=term_name)
                if term_info['total_cols'] > 1:
                    ws.merge_cells(start_row=row, start_column=col, end_row=row, end_column=col + term_info['total_cols'] - 1)
                col += term_info['total_cols']
            
            # Add term totals header if exists
            if header_data.get('term_totals'):
                ws.cell(row=row, column=col, value=f"{term_name} Totals")
                if term_info['totals_count'] > 1:
                    ws.merge_cells(start_row=row, start_column=col, end_row=row, end_column=col + term_info['totals_count'] - 1)
                col += term_info['totals_count']
        
        # Total Score and Percentage (rowspan=2)
        ws.cell(row=row, column=col, value="Total Score")
        ws.merge_cells(start_row=row, start_column=col, end_row=row+1, end_column=col)
        col += 1
        
        ws.cell(row=row, column=col, value="Percentage")
        ws.merge_cells(start_row=row, start_column=col, end_row=row+1, end_column=col)
        
        # === CREATE SECOND HEADER ROW (Assessment Headers) ===
        row = 2
        col = 3  # Skip S/N and Student columns
        
        # Assessment headers for each term
        for term_name in terms:
            term_records = header_data.get('term_headers', {}).get(term_name, [])
            
            # Individual assessment headers
            for rec in term_records:
                ws.cell(row=row, column=col, value=f"{rec['type']} {rec['number']}")
                col += 1
            
            # Term totals headers if exists
            if header_data.get('term_totals'):
                ws.cell(row=row, column=col, value="Test Total")
                col += 1
                ws.cell(row=row, column=col, value="Term Total")
                col += 1
        
        # === APPLY HEADER STYLING ===
        for row_num in [1, 2]:
            for col_num in range(1, total_columns + 1):
                cell = ws.cell(row=row_num, column=col_num)
                cell.font = bold_font
                cell.alignment = wrap_alignment
                cell.border = border
        
        # === CREATE DATA ROWS ===
        for idx, student in enumerate(students_data, start=1):
            row += 1
            col = 1
            
            # Basic student info
            ws.cell(row=row, column=col, value=idx)
            ws.cell(row=row, column=col).alignment = center_alignment
            ws.cell(row=row, column=col).border = border
            col += 1
            
            ws.cell(row=row, column=col, value=f"{student['name']} ({student['class_name']})")
            ws.cell(row=row, column=col).border = border
            col += 1
            
            # Add scores for each term
            for term_name in terms:
                term_records = student.get('record_by_term', {}).get(term_name, [])
                
                # Individual assessment scores
                for rec in term_records:
                    score_value = rec['score'] if rec['score'] != '-' else None
                    cell = ws.cell(row=row, column=col, value=score_value)
                    cell.alignment = center_alignment
                    cell.border = border
                    col += 1
                
                # Term totals if exists
                if header_data.get('term_totals') and 'term_totals' in student:
                    term_data = student['term_totals'].get(term_name, {})
                    
                    # Test Total
                    cell = ws.cell(row=row, column=col, value=term_data.get('test_total', 0))
                    cell.alignment = center_alignment
                    cell.border = border
                    col += 1
                    
                    # Term Total
                    cell = ws.cell(row=row, column=col, value=term_data.get('total_score', 0))
                    cell.alignment = center_alignment
                    cell.border = border
                    col += 1
            
            # Final totals
            cell = ws.cell(row=row, column=col, value=student.get('total_score', 0))
            cell.alignment = center_alignment
            cell.border = border
            col += 1
            
            cell = ws.cell(row=row, column=col, value=f"{student.get('percentage', 0)}%")
            cell.alignment = center_alignment
            cell.border = border
        
        # === SET COLUMN WIDTHS ===
        # Set appropriate widths for different column types
        ws.column_dimensions['A'].width = 8   # S/N
        ws.column_dimensions['B'].width = 25  # Student names
        
        # Assessment columns
        for col_num in range(3, total_columns - 1):
            col_letter = get_column_letter(col_num)
            ws.column_dimensions[col_letter].width = 12
        
        # Final columns
        final_col_letters = [get_column_letter(total_columns - 1), get_column_letter(total_columns)]
        for col_letter in final_col_letters:
            ws.column_dimensions[col_letter].width = 15
        
        # === FREEZE PANES ===
        ws.freeze_panes = 'C3'  # Freeze first 2 columns and first 2 rows
        
        # === Send Response ===
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
        # Create filename
        batch_text = batch if batch != "All" else "All_Batches"
        term_text = term if term else "All_Terms"
        filename = f"{class_name}_{batch_text}_{subject_model.name}_{term_text}_Report.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        wb.save(response)
        return response
        
    except Exception as e:
        # Return error response
        response = HttpResponse(f"Error generating Excel report: {str(e)}", status=500)
        return response