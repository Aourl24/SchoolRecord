from django.contrib import admin
from .models import Class,Record,Student,Subject,StudentRecord,History,Topic
# Register your models here.

admin.site.register([Class,Record,Student,Subject,StudentRecord,History,Topic])