from django.contrib import admin
from .models import (
    Department,
    Programme,
    Student,
    Teacher,
    Course,
    StudentCourse,
    TeacherCourse,
    HourDateCourse,
    AbsentDetails,
)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Programme)
class ProgrammeAdmin(admin.ModelAdmin):
    list_display = ('name', 'department')
    list_filter = ('department',)
    search_fields = ('name',)


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('name', 'university_register_number', 'admission_number', 'programme')
    list_filter = ('programme__department',)
    search_fields = ('name', 'university_register_number', 'admission_number')


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('user', 'department', 'phone_number')
    list_filter = ('department',)
    search_fields = ('user__username', 'phone_number')


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'semester', 'credits', 'department')
    list_filter = ('department', 'semester')
    search_fields = ('name', 'code')


@admin.register(StudentCourse)
class StudentCourseAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'year')
    list_filter = ('year', 'course__department', 'course__semester')
    search_fields = ('student__name', 'course__name')
    autocomplete_fields = ('student', 'course')  # For better performance with many rows


@admin.register(TeacherCourse)
class TeacherCourseAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'course', 'year')
    list_filter = ('year', 'course__department', 'course__semester')
    search_fields = ('teacher__user__username', 'course__name')
    autocomplete_fields = ('teacher', 'course')  # For better performance with many rows


@admin.register(HourDateCourse)
class HourDateCourseAdmin(admin.ModelAdmin):
    list_display = ('teacher_course', 'date', 'hour', 'year')
    list_filter = ('year', 'teacher_course__course__department', 'teacher_course__teacher')
    search_fields = ('teacher_course__teacher__user__username', 'teacher_course__course__name')
    autocomplete_fields = ('teacher_course',)


@admin.register(AbsentDetails)
class AbsentDetailsAdmin(admin.ModelAdmin):
    list_display = ('student', 'hour_date_course', 'status')
    list_filter = ('hour_date_course__year', 'hour_date_course__teacher_course__course__department')
    search_fields = ('student__name', 'hour_date_course__teacher_course__course__name')
    autocomplete_fields = ('hour_date_course', 'student')
