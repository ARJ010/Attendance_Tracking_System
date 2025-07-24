# attendance/context_processors.py

from django.contrib.auth.models import Group

def is_hod(request):
    """Check if the current user belongs to the 'HoD' group."""
    return {'is_hod': request.user.groups.filter(name='HoD').exists()}

from attendance.models import Student,Course, Teacher  # or wherever Student model is
from django.db.models import Count

def semesters_with_students(request):
    # Default: empty list
    semesters = []
    if request.user.is_authenticated and hasattr(request.user, 'teacher'):
        department = request.user.teacher.department
        active_semesters = (
            Student.objects
            .filter(
                programme__department=department,
                current_semester__in=range(1, 9)
            )
            .values('current_semester')
            .annotate(count=Count('id'))
            .order_by('current_semester')
        )
        semesters = [entry['current_semester'] for entry in active_semesters if entry['count'] > 0]
    return {'semesters': semesters}

def semesters_with_courses(request):
    # Default: empty list
    course_semesters = []
    if request.user.is_authenticated and hasattr(request.user, 'teacher'):
        department = request.user.teacher.department
        active_semesters = (
            Course.objects
            .filter(
                department=department,
                semester__in=range(1, 9)
            )
            .values('semester')
            .annotate(count=Count('id'))
            .order_by('semester')
        )
        course_semesters = [entry['semester'] for entry in active_semesters if entry['count'] > 0]
    return {'course_semesters': course_semesters}


from attendance.models import StudentBatch

def get_student_semester_history(student_id):
    semesters = (
        StudentBatch.objects
        .filter(student_id=student_id)
        .values_list('batch__course__semester', flat=True)
        .distinct()
        .order_by('batch__course__semester')
    )
    # Convert to string if needed
    return [str(s) for s in semesters]