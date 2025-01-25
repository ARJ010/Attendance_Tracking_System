from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('students/', views.student_list, name='student_list'),
    path('students/add/', views.add_student, name='add_student'),
    path('students/upload/', views.upload_students, name='upload_students'),
    path('edit_student/<int:id>/', views.edit_student, name='edit_student'),
    path('teachers/change_password/<int:teacher_id>/', views.change_password, name='change_password'),
    path('remove_student/<int:id>/', views.remove_student, name='remove_student'),
    path('teachers/', views.teacher_list, name='teacher_list'),
    path('teachers/add/', views.register_teacher, name='register_teacher'),
    path('teachers/upload', views.upload_teachers, name='upload_teachers'),
    path('teachers/edit/<int:teacher_id>/', views.edit_teacher, name='edit_teacher'),
    path('teachers/delete/<int:teacher_id>/', views.delete_teacher, name='delete_teacher'),
    path('course/', views.course_list, name='course_list'),
    path('course/add', views.add_course, name='add_course'),
    path('get_assigned_students/<int:course_id>/', views.get_assigned_students, name='get_assigned_students'),
    path('get_assigned_teachers/<int:course_id>/', views.get_assigned_teachers, name='get_assigned_teachers'),
    path('get_assigned_courses/<int:student_id>/', views.get_assigned_courses, name='get_assigned_courses'),
    path('assign-teachers/', views.assign_teachers, name='assign_teachers'),
    path('remove_courses/', views.remove_courses, name='remove_courses'),
    path('remove-teachers/', views.remove_teachers, name='remove_teachers'),
    path('student-course/', views.student_course_assign, name='student_course_assign'),
    path('teacher-course/', views.teacher_course_assign, name='teacher_course_assign'),
    path('hour-date-course/', views.hour_date_course_form_view, name='hour_date_course_form'),
    path('absent-details/', views.absent_details_form_view, name='absent_details_form'),
]