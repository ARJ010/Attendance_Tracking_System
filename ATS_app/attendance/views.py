from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from .models import Student, Teacher, Course, StudentCourse, TeacherCourse, HourDateCourse, AbsentDetails,Programme
from django.contrib.auth.decorators import login_required
from django.db import transaction
from .forms import (
    StudentForm, TeacherForm, CourseForm, 
    StudentCourseForm, TeacherCourseForm, 
    HourDateCourseForm, AbsentDetailsForm,UserForm
)

@login_required()
def index(request):
    return render(request, 'attendance/index.html')

# View for managing Student
def student_form_view(request):
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('student_list')
    else:
        form = StudentForm()
    return render(request, 'attendance/student_form.html', {'form': form})

def student_list(request):
    # Retrieve all students
    students = Student.objects.all()

    return render(request, 'attendance/student_list.html', {'students': students})


# View for managing Teacher
def register_teacher(request):
    if request.method == 'POST':
        user_form = UserForm(request.POST)
        teacher_form = TeacherForm(request.POST)

        if user_form.is_valid() and teacher_form.is_valid():
            try:
                with transaction.atomic():
                    # Save the User instance
                    user = user_form.save(commit=False)
                    user.set_password(user_form.cleaned_data['password'])
                    user.save()

                    # Save the Teacher instance
                    teacher = teacher_form.save(commit=False)
                    teacher.user = user
                    teacher.save()

                return redirect('index')  # Replace with your success URL
            except Exception as e:
                print(e)
                # Handle the exception or show an error message
    else:
        user_form = UserForm()
        teacher_form = TeacherForm()

    return render(request, 'attendance/register_teacher.html', {
        'user_form': user_form,
        'teacher_form': teacher_form,
    })


# View for managing Course
def course_form_view(request):
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('course_list')
    else:
        form = CourseForm()
    return render(request, 'attendance/course_form.html', {'form': form})


# View for assigning Student to Course
def student_course_form_view(request):
    if request.method == 'POST':
        form = StudentCourseForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('student_course_list')
    else:
        form = StudentCourseForm()
    return render(request, 'attendance/student_course_form.html', {'form': form})


# View for assigning Teacher to Course
def teacher_course_form_view(request):
    if request.method == 'POST':
        form = TeacherCourseForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('teacher_course_list')
    else:
        form = TeacherCourseForm()
    return render(request, 'attendance/teacher_course_form.html', {'form': form})


# View for Hour-Date-Course
def hour_date_course_form_view(request):
    if request.method == 'POST':
        form = HourDateCourseForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('hour_date_course_list')
    else:
        form = HourDateCourseForm()
    return render(request, 'attendance/hour_date_course_form.html', {'form': form})


# View for Absent Details
def absent_details_form_view(request):
    if request.method == 'POST':
        form = AbsentDetailsForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('absent_details_list')
    else:
        form = AbsentDetailsForm()
    return render(request, 'attendance/absent_details_form.html', {'form': form})



import csv
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Import students from a CSV file where the programme name is provided"

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the CSV file')

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        try:
            with open(csv_file, mode='r') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    # Get or create the programme by name
                    programme, created = Programme.objects.get_or_create(name=row['programme_name'])

                    # Create the student
                    Student.objects.create(
                        name=row['name'],
                        university_register_number=row['university_register_number'],
                        admission_number=row['admission_number'],
                        programme=programme
                    )
                    self.stdout.write(
                        self.style.SUCCESS(f"Added {row['name']} to programme {programme.name}")
                    )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {e}"))
