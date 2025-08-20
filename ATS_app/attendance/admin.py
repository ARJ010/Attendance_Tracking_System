from django.contrib import admin
from .models import Department, Programme, Student, Teacher, Course

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
    list_display = ('name', 'roll_number','university_register_number', 'admission_number', 'programme')
    search_fields = ('name', 'university_register_number', 'admission_number')
    list_filter = ('programme',)

admin.site.register(Student, StudentAdmin)

# Customizing the admin interface for Teacher model
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('user','acronym', 'department', 'phone_number')
    search_fields = ('user__username', 'phone_number')
    list_filter = ('department',)

admin.site.register(Teacher, TeacherAdmin)

# Customizing the admin interface for Course model
class CourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'semester', 'credits', 'department')
    search_fields = ('name', 'code')
    list_filter = ('semester', 'department')

admin.site.register(Course, CourseAdmin)


from django.contrib import admin
from .models import (
    Department, Programme, Student, Teacher, Course,
    StudentBatch, TeacherBatch, Batch, HourDateBatch, AbsentDetails
)



# Batch Admin
@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ('course', 'academic_year', 'part', 'active')
    list_filter = ('academic_year', 'part', 'active')
    search_fields = ('course__name', 'course__code')

# StudentBatch Admin
@admin.register(StudentBatch)
class StudentBatchAdmin(admin.ModelAdmin):
    list_display = ('student', 'batch')
    search_fields = ('student__name', 'batch__course__name')
    list_filter = ('batch__academic_year', 'batch__course')

# TeacherBatch Admin
@admin.register(TeacherBatch)
class TeacherBatchAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'batch')
    search_fields = ('teacher__name', 'batch__course__name')
    list_filter = ('batch__academic_year', 'batch__course')

# HourDateBatch Admin
@admin.register(HourDateBatch)
class HourDateBatchAdmin(admin.ModelAdmin):
    list_display = ('batch', 'teacher', 'date', 'hour')
    search_fields = ('batch__course__name', 'teacher__user__username', 'date')
    list_filter = ('date', 'hour')

# AbsentDetails Admin
@admin.register(AbsentDetails)
class AbsentDetailsAdmin(admin.ModelAdmin):
    list_display = ('student', 'hour_date_batch', 'status')
    search_fields = ('student__name', 'hour_date_batch__teacher_batch__teacher__name')
    list_filter = ('status',)

from .models import TC

@admin.register(TC)
class TCAdmin(admin.ModelAdmin):
    list_display = ('student', 'current_semester', 'year_of_tc', 'reason_short')
    search_fields = ('student__name', 'student__university_register_number', 'reason')
    list_filter = ('year_of_tc', 'current_semester')

    def reason_short(self, obj):
        return (obj.reason[:50] + '...') if len(obj.reason) > 50 else obj.reason

    reason_short.short_description = 'Reason'
