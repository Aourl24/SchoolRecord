from django.urls import path,include
from .views import recordView, studentView,classView , homeView , getClass, getRecord , getStudent , getClassRecord , getClassStudent,formView, searchView, addToRecord ,filterRecord,filterStudent,closeReq

urlpatterns = [
    path("record", recordView,name="record-list"),
    path('student',studentView,name="student-list"),
    path('class',classView,name="class-list"),
    path('student/<int:id>',getStudent,name='get-student-detail'),
    path('class/<int:id>',getClass,name='get-class'),
    path('record/<int:id>',getRecord,name='get-record'),
    path('',homeView),
    path('getclassrecord/<int:id>',getClassRecord,name="get-class-record"),
    path('getstudent/<int:id>',getClassStudent,name="get-student"),
    path('home/<str:part>',homeView,name='home-part'),
    path('form/<str:get_form>',formView,name="form"),
    path('search',searchView,name='search'),
    path('add-to-record/<int:id>',addToRecord,name='addToRecord'),
    path('filter-students',filterStudent,name="filterStudent"),
    path('filter-record',filterRecord,name="filterRecord"),
    path("close",closeReq,name="closeRequest")
  ]