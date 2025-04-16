from django.urls import path,include
from .views import recordView, studentView,classView , homeView , getClass, getRecord , getStudent

urlpatterns = [
    path("record", recordView,name="record-list"),
    path('student',studentView,name="student-list"),
    path('class',classView,name="class-list"),
    path('student/<int:id>',getStudent,name='get-student'),
    path('class/<int:id>',getClass,name='get-class'),
    path('record/<int:id>',getRecord,name='get-record'),
    path('home',homeView)
  ]