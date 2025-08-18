# Migration file: 0020_map_subject_to_subjectteacher.py
from django.db import migrations

def map_subject_to_subjectteacher(apps, schema_editor):
    Record = apps.get_model('record', 'Record')
    Subject = apps.get_model('record', 'Subject')
    SubjectTeacher = apps.get_model('record', 'SubjectTeacher')
    
    # Process each record
    for record in Record.objects.all():
        if record.subject:  # If subject_id exists (old Subject ID)
            try:
                # Find SubjectTeacher that matches this subject and class
                subject_teacher = SubjectTeacher.objects.filter(
                    subject_id=record.subject,  # Old subject ID
                    class_name=record.class_name  # Same class
                ).first()
                
                if subject_teacher:
                    # Update to use SubjectTeacher ID
                    record.subject = subject_teacher.id
                    record.save()
                    print(f"Mapped Record {record.id}: Subject {record.subject} -> SubjectTeacher {subject_teacher.id}")
                else:
                    # No matching SubjectTeacher found
                    print(f"Warning: No SubjectTeacher found for Record {record.id} (Subject: {record.subject}, Class: {record.class_name})")
                    
                    # Option A: Set to None
                    record.subject = None
                    record.save()
                    
                    # Option B: Create a SubjectTeacher entry (uncomment if you want this)
                    # if record.class_name:
                    #     subject_obj = Subject.objects.get(id=record.subject)
                    #     new_subject_teacher, created = SubjectTeacher.objects.get_or_create(
                    #         subject=subject_obj,
                    #         class_name=record.class_name,
                    #         defaults={'user': record.user}  # Adjust based on your UserModel
                    #     )
                    #     record.subject = new_subject_teacher.id
                    #     record.save()
                    #     print(f"Created SubjectTeacher {new_subject_teacher.id} for Record {record.id}")
                    
            except Subject.DoesNotExist:
                print(f"Subject {record.subject} does not exist for Record {record.id}")
                record.subject = None
                record.save()
            except Exception as e:
                print(f"Error processing Record {record.id}: {e}")
                record.subject = None
                record.save()

def reverse_map(apps, schema_editor):
    Record = apps.get_model('record', 'Record')
    SubjectTeacher = apps.get_model('record', 'SubjectTeacher')
    
    for record in Record.objects.all():
        if record.subject:
            try:
                subject_teacher = SubjectTeacher.objects.get(id=record.subject)
                if subject_teacher.subject:
                    record.subject = subject_teacher.subject.id
                    record.save()
            except SubjectTeacher.DoesNotExist:
                record.subject = None
                record.save()

class Migration(migrations.Migration):
    dependencies = [
        ('record', '0019_alter_record_subject'),
    ]

    operations = [
        migrations.RunPython(map_subject_to_subjectteacher, reverse_map),
    ]