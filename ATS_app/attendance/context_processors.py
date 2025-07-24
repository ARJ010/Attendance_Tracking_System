# attendance/context_processors.py

from django.contrib.auth.models import Group

def is_hod(request):
    """Check if the current user belongs to the 'HoD' group."""
    return {'is_hod': request.user.groups.filter(name='HoD').exists()}

from attendance.models import Student,Course  # or wherever Student model is
from django.db.models import Count

def semesters_with_students(request):
    # Only include semesters between 1 and 8 that have students
    active_semesters = (
        Student.objects
        .filter(current_semester__in=range(1, 9))
        .values('current_semester')
        .annotate(count=Count('id'))
        .order_by('current_semester')
    )

    semesters = [entry['current_semester'] for entry in active_semesters]
    return {'semesters': semesters}

def semesters_with_courses(request):
    # Only include semesters between 1 and 8 that have courses
    active_semesters = (
        Course.objects
        .filter(semester__in=range(1, 9))
        .values('semester')
        .annotate(count=Count('id'))
        .order_by('semester')
    )

    semesters = [entry['semester'] for entry in active_semesters]
    return {'course_semesters': semesters}
