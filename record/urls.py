# Complete URL patterns
from django.urls import path
from . import views
from .excel import export_report_excel

urlpatterns = [
  #Landing views
  path("",views.landing_view),
    # Main views
    path('home/', views.home_view, name='home'),
    path('home/<str:part>/', views.home_view, name='home-part'),
    
    # List views
    path('records/', views.RecordListView.as_view(), name='record-list'),
    path('students/', views.StudentListView.as_view(), name='student-list'),
    path('classes/', views.ClassListView.as_view(), name='class-list'),
    path('subjects/', views.subject_list_view, name='subject-list'),
    path('topics/', views.topic_list_view, name='topic-list'),
    
    # Detail views
    path('record/<int:id>/', views.record_detail_view, name='get-record'),
    path('student/<int:id>/', views.student_detail_view, name='get-student-detail'),
    path('class/<int:id>/', views.class_detail_view, name='get-class'),
    path('subject/<int:id>/', views.subject_detail_view, name='subject-detail'),
    path('topic/<int:id>/', views.topic_detail_view, name='topic-detail'),
    
    # Class-specific views
    path('class/<int:id>/records/', views.get_class_records_view, name='get-class-record'),
    path('class/<int:id>/students/', views.get_class_students_view, name='get-student'),
    path('class/<int:id>/topics/<str:name>/', views.class_topics_view, name='class-topics'),
    
    # Form views
    path('form/<str:form_type>/', views.form_view, name='form'),
    path('form/<str:form_type>/<int:update_id>/', views.form_view, name='update-form'),
    
    # Specific form actions
    path('add-to-record/<int:id>/', views.add_to_record_view, name='add-to-record'),
    path('add-student/<int:id>/', views.add_student_to_class_view, name='add-student'),
    path('add-topic/<int:id>/', views.add_topic_view, name='add-topic'),
    path('add-record/<int:id>/', views.add_record_to_class_view, name='add-record'),
    path('update-record/<int:id>/', views.update_record_view, name='update-record'),
    
    # Filter and search
    path('search/', views.search_view, name='search'),
    path('filter/records/', views.filter_record_view, name='filterRecord'),
    path('filter/students/', views.filter_student_view, name='filter-students'),
    
    # Reports and analytics
    path('reports/', views.report_view, name='generateReport'),
    path('analytics/', views.analytics_dashboard_view, name='analytics'),
    path("export_excel",export_report_excel,name="export_report_excel"),
    
    # API endpoints
    path('api/student/<int:student_id>/records/', views.api_student_records, name='api-student-records'),
    path('api/class/<int:class_id>/summary/', views.api_class_summary, name='api-class-summary'),
    
    # Utility views
    path('close/', views.close_request_view, name='closeRequest'),
    path('history/', views.history_view, name='historyView'),
    
    # Authentication
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('userdetail',views.user_detail,name="new_user_detail"),
    path('userdetail/<str:form>',views.user_detail,name="user_detail"),
    
]