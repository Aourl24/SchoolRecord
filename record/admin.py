from django.contrib import admin
from .models import Class,Record,Student,Subject,StudentRecord
# Register your models here.

admin.site.register([Class,Record,Student,Subject,StudentRecord])