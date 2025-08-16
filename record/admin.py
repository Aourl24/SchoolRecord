from django.contrib import admin
from .models import Student, Record, Class, Subject, StudentRecord, History, Topic, User, School

admin.site.register(School)
#admin.site.unregister(User)

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email']
    list_filter = ['role', 'school']
    search_fields = ['username', 'email']

@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ['name', 'batch', 'user']
    list_filter = ['batch', 'user']
    search_fields = ['name']

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'user']
    list_filter = ['user']
    search_fields = ['name']

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['name', 'class_name', 'admission_number', 'user']
    list_filter = ['class_name', 'user']
    search_fields = ['name', 'student_id']

@admin.register(Record)
class RecordAdmin(admin.ModelAdmin):
    list_display = ['title', 'subject', 'class_name', 'record_type', 'total_score', 'date_created']
    list_filter = ['record_type', 'subject', 'class_name', 'date_created']
    search_fields = ['title']

@admin.register(StudentRecord)
class StudentRecordAdmin(admin.ModelAdmin):
    list_display = ['student', 'record', 'score', 'percentage']
    list_filter = ['record__record_type']
    search_fields = ['student__name', 'record__title']
    
    def percentage(self, obj):
        return f"{obj.percentage:.1f}%"

@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ['title', 'subject', 'class_name', 'user']
    list_filter = ['subject', 'class_name']
    search_fields = ['title']

@admin.register(History)
class HistoryAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'time']
    list_filter = ['user', 'time']
    search_fields = ['title']
    readonly_fields = ['time']
    
