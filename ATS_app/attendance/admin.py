from django.contrib import admin
from .models import (
    Student, 
    Teacher, 
    Course, 
    StudentCourse, 
    TeacherCourse, 
    HourDateCourse, 
    AbsentDetails
)

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'roll_number', 'university_register_number', 'admission_number', 'programme')
    search_fields = ('name', 'roll_number', 'university_register_number', 'admission_number')
    list_filter = ('programme',)

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'department', 'phone_number')
    search_fields = ('user__username', 'user__email', 'department')
    list_filter = ('department',)

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'code', 'credits', 'year_offered')
    search_fields = ('name', 'code')
    list_filter = ('year_offered',)

@admin.register(StudentCourse)
class StudentCourseAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'course')
    search_fields = ('student__name', 'course__name')
    list_filter = ('course',)

@admin.register(TeacherCourse)
class TeacherCourseAdmin(admin.ModelAdmin):
    list_display = ('id', 'teacher', 'course')
    search_fields = ('teacher__user__username', 'course__name')
    list_filter = ('course',)

@admin.register(HourDateCourse)
class HourDateCourseAdmin(admin.ModelAdmin):
    list_display = ('id', 'teacher_course', 'date', 'hour')
    search_fields = ('teacher_course__teacher__user__username', 'teacher_course__course__name')
    list_filter = ('date', 'hour')

@admin.register(AbsentDetails)
class AbsentDetailsAdmin(admin.ModelAdmin):
    list_display = ('id', 'hour_date_course', 'student', 'status')
    search_fields = ('hour_date_course__teacher_course__teacher__user__username', 'student__name')
    list_filter = ('status',)
