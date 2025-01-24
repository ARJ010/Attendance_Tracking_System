# attendance/context_processors.py

from django.contrib.auth.models import Group

def is_hod(request):
    """Check if the current user belongs to the 'HoD' group."""
    return {'is_hod': request.user.groups.filter(name='HoD').exists()}
