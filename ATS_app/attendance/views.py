import csv 
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from .models import Student, Teacher, Course, StudentCourse, TeacherCourse, HourDateCourse, AbsentDetails,Programme
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from .forms import (
    StudentForm, TeacherForm, CourseForm, 
    StudentCourseForm, TeacherCourseForm, 
    HourDateCourseForm, AbsentDetailsForm,
    UserForm,CSVUploadForm
)

def clean_name(name):
    """Standardize the name format: convert to uppercase and replace periods with spaces."""
    return name.strip().replace('.', ' ').upper()


@login_required()
def index(request):
    return render(request, 'attendance/index.html')

@login_required
def student_list(request):
    # Get the logged-in teacher's department
    teacher = Teacher.objects.get(user=request.user)
    department = teacher.department
    
    # Filter students based on the department
    students = Student.objects.filter(programme__department=department)
    
    return render(request, 'attendance/student_list.html', {'students': students})


@login_required()
def add_student(request):
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            # Save the student
            form.save()
            return redirect('student_list')  # Redirect to the student list after saving
    else:
        form = StudentForm()

    return render(request, 'attendance/add_student.html', {'form': form})


def upload_students(request):
    if request.method == 'POST' and request.FILES['csv_file']:
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = form.cleaned_data['csv_file']
            decoded_file = csv_file.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded_file)

            for row in reader:
                programme_name = row.get('programme_name')  # Adjusted to match the CSV column name
                student_name = clean_name(row.get('name'))  # Clean the student name
                university_register_number = row.get('university_register_number')
                admission_number = row.get('admission_number')

                # Check if the student already exists by unique fields (e.g., university_register_number or admission_number)
                if Student.objects.filter(university_register_number=university_register_number).exists():
                    messages.warning(request, f"Student with University Register Number '{university_register_number}' already exists. Skipping student '{student_name}'.")
                    continue  # Skip this student and move to the next one

                if Student.objects.filter(admission_number=admission_number).exists():
                    messages.warning(request, f"Student with Admission Number '{admission_number}' already exists. Skipping student '{student_name}'.")
                    continue  # Skip this student and move to the next one

                # Try to get the Programme, handle the case when it doesn't exist
                try:
                    programme = Programme.objects.get(name=programme_name)
                except Programme.DoesNotExist:
                    messages.error(request, f"Programme '{programme_name}' not found. Skipping student '{student_name}'.")
                    continue  # Skip this student and move to the next one

                # Create a new student record if programme exists
                Student.objects.create(
                    name=student_name,
                    university_register_number=university_register_number,
                    admission_number=admission_number,
                    programme=programme
                )

            messages.success(request, 'Students uploaded successfully!')
            return redirect('student_list')
    else:
        form = CSVUploadForm()
    
    return render(request, 'attendance/upload_students.html', {'form': form})




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


