from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('student/checkin/', views.student_checkin, name='student_checkin'),
    path('student/history/', views.student_history, name='student_history'),
    path('teacher/dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('teacher/results/', views.teacher_results, name='teacher_results'),
    path('teacher/students/', views.teacher_students, name='teacher_students'),
    path('teacher/settings/', views.teacher_settings, name='teacher_settings'),
    path('teacher/download-csv/', views.download_csv, name='download_csv'),
]