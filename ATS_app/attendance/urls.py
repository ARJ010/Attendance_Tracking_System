from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('student/', views.student_form_view, name='student_form'),
    path('teacher/', views.register_teacher, name='teacher_form'),
    path('course/', views.course_form_view, name='course_form'),
    path('student-course/', views.student_course_form_view, name='student_course_form'),
    path('teacher-course/', views.teacher_course_form_view, name='teacher_course_form'),
    path('hour-date-course/', views.hour_date_course_form_view, name='hour_date_course_form'),
    path('absent-details/', views.absent_details_form_view, name='absent_details_form'),
]
