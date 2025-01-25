import csv 
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User
from django.http import HttpResponse
from .models import Student, Teacher, Course, StudentCourse, TeacherCourse, HourDateCourse, AbsentDetails,Programme,Department
from django.contrib.auth.decorators import login_required, user_passes_test
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

def HoD_group_required(user):
    """Check if the user belongs to the 'HoD' group."""
    return user.groups.filter(name='HoD').exists()

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


@login_required
@user_passes_test(HoD_group_required)
def add_student(request):
    teacher = Teacher.objects.get(user=request.user)  # Get the teacher associated with the logged-in user

    if request.method == 'POST':
        form = StudentForm(request.POST, teacher=teacher)  # Pass the teacher to the form
        if form.is_valid():
            # Save the student with the department associated with the logged-in teacher
            student = form.save(commit=False)
            student.programme.department = teacher.department  # Assign the department from the teacher
            student.save()
            return redirect('student_list')  # Redirect to the student list after saving
    else:
        form = StudentForm(teacher=teacher)  # Pass the teacher to the form

    return render(request, 'attendance/add_student.html', {'form': form})


@login_required
@user_passes_test(HoD_group_required)
def upload_students(request):
    teacher = Teacher.objects.get(user=request.user)
    department = teacher.department

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
                    programme = Programme.objects.get(name=programme_name, department=department)
                except Programme.DoesNotExist:
                    messages.error(request, f"Programme '{programme_name}' not found in your department. Skipping student '{student_name}'.")
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


@login_required
def teacher_list(request):
    # Get the logged-in teacher's department
    teacher = Teacher.objects.get(user=request.user)
    department = teacher.department
    
    # Filter students based on the department
    teachers = Teacher.objects.filter(department=department)
    
    return render(request, 'attendance/teacher_list.html', {'teachers': teachers})


@login_required
@user_passes_test(HoD_group_required)
def upload_teachers(request):
    if request.method == 'POST' and request.FILES['csv_file']:
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = form.cleaned_data['csv_file']
            decoded_file = csv_file.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded_file)

            for row in reader:
                name = row.get('name')
                department_name = row.get('department')  # Department from CSV
                first_name = name.split()[0]  # Get the first part of the name for the username
                email = row.get('email') or f'{first_name.lower()}@example.com'  # Default email if missing
                username = first_name.lower()  # Username is the first name in lowercase
                password = f'{first_name.lower()}@123'  # Default password format: firstname@123
                mobile_number = row.get('mobile_number') or '1234567890'  # Default mobile number if missing

                # Check if the teacher already exists by username or email
                if User.objects.filter(username=username).exists():
                    messages.warning(request, f"User with username '{username}' already exists. Skipping teacher '{name}'.")
                    continue

                if User.objects.filter(email=email).exists():
                    messages.warning(request, f"User with email '{email}' already exists. Skipping teacher '{name}'.")
                    continue

                try:

                    # Create or get the department
                    department, created = Department.objects.get_or_create(name=department_name)

                    # Create a new user
                    with transaction.atomic():
                        user = User.objects.create_user(username=username, email=email, password=password)
                        user.first_name = name  # Set the teacher's full name
                        user.save()

                        # Create the Teacher instance and associate it with the user and department
                        teacher = Teacher.objects.create(
                            user=user,
                            department=department,
                            phone_number=mobile_number,  # Mobile number can be edited later
                        )

                    if created:
                        messages.success(request, f"Department '{department_name}' created and teacher '{name}' uploaded successfully!")
                    else:
                        messages.success(request, f"Teacher '{name}' uploaded successfully!")

                except Exception as e:
                    messages.error(request, f"Error uploading teacher '{name}': {e}")
                    continue

            return redirect('teacher_list')  # Redirect to the teacher list after uploading
    else:
        form = CSVUploadForm()

    return render(request, 'attendance/upload_teachers.html', {'form': form})



# View for managing Teacher
@login_required
@user_passes_test(HoD_group_required)
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


