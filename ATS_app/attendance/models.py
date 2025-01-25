from django.contrib.auth.models import User
from django.db import models

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
    year_offered = models.IntegerField()
    department = models.ForeignKey(Department, on_delete=models.CASCADE)


    def __str__(self):
        return self.name


# Student-Course Table
class StudentCourse(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('student', 'course')

    def __str__(self):
        return f"{self.student.name} - {self.course.name}"


# Teacher-Course Table
class TeacherCourse(models.Model):
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('teacher', 'course')

    def __str__(self):
        return f"{self.teacher.user.username} - {self.course.name}"


# Hour-Date-Course Table
class HourDateCourse(models.Model):
    teacher_course = models.ForeignKey(TeacherCourse, on_delete=models.CASCADE)
    date = models.DateField()
    hour = models.PositiveSmallIntegerField()  # Hour (1-5)
    year = models.IntegerField()  # Year of the course (e.g., 2025)

    def __str__(self):
        return f"{self.teacher_course} - {self.date} Hour {self.hour} - Year {self.year}"



# Absent Details Table
class AbsentDetails(models.Model):
    hour_date_course = models.ForeignKey(HourDateCourse, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    status = models.BooleanField(default=False)  # False for absent, True for present

    class Meta:
        unique_together = ('hour_date_course', 'student')

    def __str__(self):
        return f"{self.student.name} - {self.hour_date_course} - {'Present' if self.status else 'Absent'}"
