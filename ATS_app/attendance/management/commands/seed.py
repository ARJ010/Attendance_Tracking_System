from django.core.management.base import BaseCommand
from attendance.models import Teacher

class Command(BaseCommand):
    help = "Assign dummy email and phone number to all teachers."

    def handle(self, *args, **kwargs):
        teachers = Teacher.objects.all()
        for i, teacher in enumerate(teachers, start=1):
            user = teacher.user
            user.email = f"teacher{i}@example.com"
            user.save()
            teacher.phone_number = f"+100000000{i:03d}"  # example phone pattern
            teacher.save()
            self.stdout.write(f"Updated {user.username}: email={user.email}, phone={teacher.phone_number}")

        self.stdout.write(self.style.SUCCESS("✅ All teachers updated with dummy emails and phone numbers."))
