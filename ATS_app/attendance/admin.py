from django.contrib import admin
from .models import Department, Programme, Student, Teacher, Course, StudentCourse, TeacherCourse, HourDateCourse, AbsentDetails

# Customizing the admin interface for Department model
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

admin.site.register(Department, DepartmentAdmin)

# Customizing the admin interface for Programme model
class ProgrammeAdmin(admin.ModelAdmin):
    list_display = ('name', 'department')
    search_fields = ('name',)
    list_filter = ('department',)

admin.site.register(Programme, ProgrammeAdmin)

# Customizing the admin interface for Student model
class StudentAdmin(admin.ModelAdmin):
    list_display = ('name', 'university_register_number', 'admission_number', 'programme')
    search_fields = ('name', 'university_register_number', 'admission_number')
    list_filter = ('programme',)

admin.site.register(Student, StudentAdmin)

# Customizing the admin interface for Teacher model
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('user', 'department', 'phone_number')
    search_fields = ('user__username', 'phone_number')
    list_filter = ('department',)

admin.site.register(Teacher, TeacherAdmin)

# Customizing the admin interface for Course model
class CourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'semester', 'credits', 'department')
    search_fields = ('name', 'code')
    list_filter = ('semester', 'department')

admin.site.register(Course, CourseAdmin)

# Customizing the admin interface for StudentCourse model
class StudentCourseAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'year')
    search_fields = ('student__name', 'course__name')
    list_filter = ('year', 'course')

admin.site.register(StudentCourse, StudentCourseAdmin)

# Customizing the admin interface for TeacherCourse model
class TeacherCourseAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'course', 'year')
    search_fields = ('teacher__user__username', 'course__name')
    list_filter = ('year', 'course')

admin.site.register(TeacherCourse, TeacherCourseAdmin)

# Customizing the admin interface for HourDateCourse model
class HourDateCourseAdmin(admin.ModelAdmin):
    list_display = ('course', 'teacher', 'date', 'hour', 'year')
    search_fields = ('course__name', 'teacher__user__username', 'date')
    list_filter = ('hour', 'year')

admin.site.register(HourDateCourse, HourDateCourseAdmin)

# Customizing the admin interface for AbsentDetails model
class AbsentDetailsAdmin(admin.ModelAdmin):
    list_display = ('student', 'hour_date_course', 'status')
    search_fields = ('student__name', 'hour_date_course__course__name', 'hour_date_course__teacher__user__username')
    list_filter = ('status',)

admin.site.register(AbsentDetails, AbsentDetailsAdmin)
