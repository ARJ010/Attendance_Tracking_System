from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('students/', views.student_list, name='student_list'),
    path('students/add/', views.add_student, name='add_student'),
    path('students/upload/', views.upload_students, name='upload_students'),
    path('teachers/', views.teacher_list, name='teacher_list'),
    path('teachers/add/', views.register_teacher, name='register_teacher'),
    path('teachers/upload', views.upload_teachers, name='upload_teachers'),
    path('course/', views.course_list, name='course_list'),
    path('course/add', views.course_form_view, name='add_course'),
    path('get_assigned_teachers/<int:course_id>/', views.get_assigned_teachers, name='get_assigned_teachers'),
    path('get_assigned_students/<int:course_id>/', views.get_assigned_students, name='get_assigned_students'),
    path('assign-teachers/', views.assign_teachers, name='assign_teachers'),
    path('remove-teachers/', views.remove_teachers, name='remove_teachers'),
    path('student-course/', views.student_course_form_view, name='student_course_form'),
    path('teacher-course/', views.teacher_course_form_view, name='teacher_course_form'),
    path('hour-date-course/', views.hour_date_course_form_view, name='hour_date_course_form'),
    path('absent-details/', views.absent_details_form_view, name='absent_details_form'),
]