from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from .models import Student, Teacher, Course, StudentCourse, TeacherCourse, HourDateCourse, AbsentDetails
from django.contrib.auth.decorators import login_required
from .forms import (
    StudentForm, TeacherForm, CourseForm, 
    StudentCourseForm, TeacherCourseForm, 
    HourDateCourseForm, AbsentDetailsForm,TeacherRegistrationForm
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
<<<<<<< Updated upstream
        form = StudentForm()
    return render(request, 'attendance/student_form.html', {'form': form})
=======
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

>>>>>>> Stashed changes


# View for managing Teacher
def register_teacher(request):
    if request.method == 'POST':
        form = TeacherRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('index')  # Redirect to the home page or any other page
    else:
        form = TeacherRegistrationForm()

    return render(request, 'attendance/register_teacher.html', {'form': form})


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
