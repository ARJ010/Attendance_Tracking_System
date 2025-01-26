from django.contrib.auth.models import User
from django.db import models
from datetime import date

def calculate_year(current_date):
    """
    Calculate the academic year based on the date.
    June 1 of a year to May 31 of the next year is considered the same academic year.
    """
    if current_date.month >= 6:  # From June to December
        return current_date.year
    else:  # From January to May
        return current_date.year - 1


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


# Student Table
class Student(models.Model):
    name = models.CharField(max_length=255)
    university_register_number = models.CharField(max_length=50, unique=True)
    admission_number = models.CharField(max_length=50, unique=True)
    programme = models.ForeignKey(Programme, on_delete=models.CASCADE, related_name="students")

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


# Student-Course Table
class StudentCourse(models.Model):
    student = models.ForeignKey("Student", on_delete=models.CASCADE)
    course = models.ForeignKey("Course", on_delete=models.CASCADE)
    year = models.PositiveIntegerField(editable=False)  # Year is non-editable

    class Meta:
        unique_together = ('student', 'course', 'year')

    def save(self, *args, **kwargs):
        # Calculate and set the year dynamically
        self.year = calculate_year(date.today())
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student.name} - {self.course.name} - {self.year}"


# Teacher-Course Table
class TeacherCourse(models.Model):
    teacher = models.ForeignKey("Teacher", on_delete=models.CASCADE)
    course = models.ForeignKey("Course", on_delete=models.CASCADE)
    year = models.PositiveIntegerField(editable=False)  # Year is non-editable

    class Meta:
        unique_together = ('teacher', 'course', 'year')

    def save(self, *args, **kwargs):
        # Calculate and set the year dynamically
        self.year = calculate_year(date.today())
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.teacher.user.username} - {self.course.name} - {self.year}"


class HourDateCourse(models.Model):
    HOUR_CHOICES = [
        (1, 'Hour 1'),
        (2, 'Hour 2'),
        (3, 'Hour 3'),
        (4, 'Hour 4'),
        (5, 'Hour 5'),
    ]
    course = models.ForeignKey("Course", on_delete=models.CASCADE)
    teacher = models.ForeignKey("Teacher", on_delete=models.CASCADE)
    date = models.DateField()
    hour = models.PositiveSmallIntegerField(choices=HOUR_CHOICES)  # Restrict to valid choices
    year = models.PositiveIntegerField(editable=False)  # Year is non-editable

    class Meta:
        unique_together = ('course', 'date', 'hour')  # Ensure only one teacher can mark attendance

    def save(self, *args, **kwargs):
        # Calculate the year based on the date field
        self.year = calculate_year(self.date)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.teacher.user.first_name} {self.teacher.user.last_name} - {self.course.name} - {self.date} Hour {self.hour} - Year {self.year}"





# Absent Details Table
class AbsentDetails(models.Model):
    hour_date_course = models.ForeignKey(HourDateCourse, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    status = models.BooleanField(default=False)  # False for absent, True for present

    class Meta:
        unique_together = ('student', 'hour_date_course')

    def __str__(self):
        return f"{self.student.name} - {self.hour_date_course} - {'Present' if self.status else 'Absent'}"
