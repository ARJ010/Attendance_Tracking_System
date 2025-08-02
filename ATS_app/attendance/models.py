from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from datetime import date

# Utility function
def calculate_academic_year(given_date: date) -> int:
    return given_date.year if given_date.month >= 6 else given_date.year - 1


# Department Table
class Department(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


# Programme Table
class Programme(models.Model):
    name = models.CharField(max_length=255)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="programmes")

    def __str__(self):
        return f"{self.name} ({self.department.name})"


class Student(models.Model):
    name = models.CharField(max_length=255)
    year_of_enrolment = models.PositiveIntegerField(null=True)
    roll_number = models.CharField(max_length=50, null=True)
    university_register_number = models.CharField(max_length=50, unique=True)
    admission_number = models.CharField(max_length=50, unique=True)
    programme = models.ForeignKey(Programme, on_delete=models.CASCADE, related_name="students")
    
    current_semester = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(8)],
        default=1,
        help_text="Semester 1 to 8. Set to 0 after pass out."
    )


    def __str__(self):
        return self.name


# Teacher Table
class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)  # Link to default User model
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="teachers")
    phone_number = models.CharField(max_length=15, blank=True)

    def __str__(self):
        return self.user.username  # Display the username of the linked user


# Course Table
class Course(models.Model):
    SEMESTER_CHOICES = [
        ('1', 'First Semester'),
        ('2', 'Second Semester'),
        ('3', 'Third Semester'),
        ('4', 'Fourth Semester'),
        ('5', 'Fifth Semester'),
        ('6', 'Sixth Semester'),
        ('7', 'Seventh Semester'),
        ('8', 'Eighth Semester'),
    ]
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    semester = models.CharField(max_length=1, choices=SEMESTER_CHOICES)
    credits = models.IntegerField()
    department = models.ForeignKey(Department, on_delete=models.CASCADE)


    def __str__(self):
        return self.name
    
# Batch Model
class Batch(models.Model):
    PART_CHOICES = [
        ('A', 'Part A'),
        ('B', 'Part B'),
    ]
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="batches")
    academic_year = models.PositiveIntegerField()
    part = models.CharField(max_length=1, choices=PART_CHOICES)
    active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('course', 'academic_year', 'part')

    def __str__(self):
        return f"{self.course.name} - {self.academic_year} - Part {self.part}"
    
# Student-Batch Mapping
class StudentBatch(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('student', 'batch')

    def __str__(self):
        return f"{self.student.name} - {self.batch}"


# Teacher-Batch Mapping
class TeacherBatch(models.Model):
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('teacher', 'batch')

    def __str__(self):
        return f"{self.teacher.user.username} - {self.batch}"


# Hour-Date-Batch Model (Attendance session)
class HourDateBatch(models.Model):
    HOUR_CHOICES = [
        (1, 'Hour 1'),
        (2, 'Hour 2'),
        (3, 'Hour 3'),
        (4, 'Hour 4'),
        (5, 'Hour 5'),
    ]
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE,null=True)
    teacher = models.ForeignKey("Teacher", on_delete=models.CASCADE,null=True)
    date = models.DateField()
    hour = models.PositiveSmallIntegerField(choices=HOUR_CHOICES)
    year = models.PositiveIntegerField(editable=False)

    class Meta:
        unique_together = ('batch', 'date', 'hour')

    def save(self, *args, **kwargs):
        self.year = calculate_academic_year(self.date)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.batch} - {self.date} Hour {self.hour}"
    
class AbsentDetails(models.Model):
    hour_date_batch = models.ForeignKey(HourDateBatch, on_delete=models.CASCADE, related_name="attendance")
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    status = models.BooleanField(default=False)

    class Meta:
        unique_together = ('hour_date_batch', 'student')

    def __str__(self):
        return f"{self.student.name} - {self.hour_date_batch} - {'Present' if self.status else 'Absent'}"

    

class TC(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="tcs")
    reason = models.TextField()
    current_semester = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(8)],
        help_text="The semester in which the student applied for TC."
    )
    year_of_tc = models.PositiveIntegerField(default=date.today().year)

    def __str__(self):
        return f"TC - {self.student.name} - {self.year_of_tc}"





