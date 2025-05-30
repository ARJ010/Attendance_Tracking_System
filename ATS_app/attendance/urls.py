from django.urls import path
from . import views
from django.conf.urls.static import static
from django.conf import settings


urlpatterns = [
    path('', views.index, name='index'),
    path('students/', views.student_list, name='student_list'),
    path('students/add/', views.add_student, name='add_student'),
    path('students/upload/', views.upload_students, name='upload_students'),
    path('edit_student/<int:id>/', views.edit_student, name='edit_student'),
    path('remove_student/<int:id>/', views.remove_student, name='remove_student'),
    path('teachers/', views.teacher_list, name='teacher_list'),
    path('teachers/add/', views.register_teacher, name='register_teacher'),
    path('teachers/upload', views.upload_teachers, name='upload_teachers'),
    path('teachers/edit/<int:teacher_id>/', views.edit_teacher, name='edit_teacher'),
    path('teachers/change_password/<int:teacher_id>/', views.change_password, name='change_password'),
    path('reset_password/<int:teacher_id>/', views.reset_password, name='reset_password'),
    path('teachers/delete/<int:teacher_id>/', views.delete_teacher, name='delete_teacher'),
    path('course/', views.course_list, name='course_list'),
    path('course/add', views.add_course, name='add_course'),
    path('course/edit/<int:course_id>/', views.edit_course, name='edit_course'),
    path('get_assigned_students/<int:course_id>/', views.get_assigned_students, name='get_assigned_students'),
    path('get_assigned_teachers/<int:course_id>/', views.get_assigned_teachers, name='get_assigned_teachers'),
    path('get_assigned_courses/<int:student_id>/', views.get_assigned_courses, name='get_assigned_courses'),
    path('assign-teachers/', views.assign_teachers, name='assign_teachers'),
    path('remove_courses/', views.remove_courses, name='remove_courses'),
    path('remove-teachers/', views.remove_teachers, name='remove_teachers'),
    path('student-course/', views.student_course_assign, name='student_course_assign'),
    path('teacher-course/', views.teacher_course_assign, name='teacher_course_assign'),
    path('take_attendance/<int:course_id>/', views.take_attendance, name='take_attendance'),
    path('attendance/report/<int:course_id>/', views.attendance_report, name='attendance_report'),
    path('attendance/compact-report/<int:course_id>/', views.compact_attendance_report, name='compact_attendance_report'),
    path('attendance/download-excel-report/<int:course_id>/', views.download_attendance_excel, name='download_attendance_excel'),

    path('student_report/<int:student_id>/', views.student_individual_report, name='student_report'),
    path('teacher/attendance/', views.teacher_attendance_list, name='teacher_attendance_list'),
    path('teacher/attendance/edit/<int:record_id>/', views.edit_attendance, name='edit_attendance'),
    path('teacher/attendance/remove/<int:record_id>/', views.remove_attendance, name='remove_attendance'),
    path('department/<int:department_id>/', views.department_report, name='department_report'),
    path('download_teacher_template/', views.download_teacher_template, name='download_teacher_template'),
    path('download_student_template/', views.download_student_template, name='download_student_template'),
    path('programme_courses_view/', views.programme_courses_view, name='programme_courses_view'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-department/', views.admin_department_view, name='admin_department_view'),
]

