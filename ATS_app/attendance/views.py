import csv 
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User
from django.http import HttpResponse,Http404,JsonResponse
from .models import Student, Teacher, Course, StudentCourse, TeacherCourse, HourDateCourse, AbsentDetails,Programme,Department
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import transaction
from .forms import (
    StudentForm, TeacherForm, CourseForm, 
    StudentEditForm, TeacherCourseForm, 
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
    students = Student.objects.filter(programme__department=department).order_by('university_register_number')
    
    return render(request, 'attendance/student_list.html', {'students': students, 'department':department})


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
def remove_student(request, id):
    student = get_object_or_404(Student, id=id)
    
    # Optionally check if the user has permissions to delete the student
    student.delete()
    
    return redirect('student_list')

@login_required
def edit_student(request, id):
    student = get_object_or_404(Student, id=id)
    teacher = student.programme.department.teachers.filter(user=request.user).first()  # Use 'teachers' instead of 'teacher_set'
    
    if not teacher:
        return redirect('student_list')  # If the teacher isn't part of the student's department, redirect

    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student, teacher=teacher)
        if form.is_valid():
            form.save()
            return redirect('student_list')  # Redirect to the student list after saving
    else:
        form = StudentForm(instance=student, teacher=teacher)
    
    return render(request, 'attendance/edit_student.html', {'form': form, 'student': student})


@login_required
def teacher_list(request):
    # Get the logged-in teacher's department
    teacher = Teacher.objects.get(user=request.user)
    department = teacher.department
    
    # Filter students based on the department
    teachers = Teacher.objects.filter(department=department)
    
    return render(request, 'attendance/teacher_list.html', {'teachers': teachers, 'department':department})

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


@login_required
def course_list(request):
    teacher = Teacher.objects.get(user=request.user)
    department = teacher.department
    user = request.user
    if user.groups.filter(name='HoD').exists():
            courses = Course.objects.filter(department=teacher.department)
    else:
        teacher_courses = TeacherCourse.objects.filter(teacher=teacher)
        courses = Course.objects.filter(id__in=teacher_courses.values('course'))
    
    teachers = Teacher.objects.filter(department=department)
    
    # List of students for each course (only for HoD)
    if user.groups.filter(name='HoD').exists():
        course_students = {}
        for course in courses:
            students = StudentCourse.objects.filter(course=course).values('student__name')
            course_students[course] = students
    
    return render(request, 'attendance/course_list.html', {
        'teachers': teachers,
        'department': department,
        'courses': courses,
        'course_students': course_students if user.groups.filter(name='HoD').exists() else None,
    })

def get_assigned_students(request, course_id):
    students = StudentCourse.objects.filter(course_id=course_id).select_related('student__programme')
    students_data = [{
        'name': student.student.name,
        'university_register_number': student.student.university_register_number,
        'programme': student.student.programme.name  # Assuming 'name' is the field in Programme
    } for student in students]
    
    return JsonResponse({'students': students_data})

# View for managing Course
def add_course(request):
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('course_form')
    else:
        form = CourseForm()
    return render(request, 'attendance/course_form.html', {'form': form})



@login_required
def teacher_course_assign(request):
    teacher = Teacher.objects.get(user=request.user)
    department = teacher.department
    user = request.user
    courses = Course.objects.filter(department=teacher.department)
    course_teacher_map = {}

    # Ensure the logged-in user is a teacher
    if hasattr(user, 'teacher'):
        teacher = user.teacher

        # Create a map of course to its assigned teachers
        for course in courses:
            assigned_teachers = TeacherCourse.objects.filter(course=course)
            course_teacher_map[course] = [tc.teacher.user.first_name for tc in assigned_teachers]

    # Get all teachers for the dropdown
    teachers = Teacher.objects.filter(department=department)

    return render(request, 'attendance/teacher_course_form.html', {
        'courses': courses,
        'department':department,
        'course_teacher_map': course_teacher_map,
        'teachers': teachers,  # Pass the teachers list to the template
    })

@login_required
def get_assigned_teachers(request, course_id):
    try:
        course = Course.objects.get(id=course_id)
        teacher_courses = TeacherCourse.objects.filter(course=course)
        teachers = [{"id": tc.teacher.id, "first_name": tc.teacher.user.first_name} for tc in teacher_courses]
        return JsonResponse({"teachers": teachers})
    except Course.DoesNotExist:
        return JsonResponse({"error": "Course not found"}, status=404)

def assign_teachers(request):
    if request.method == 'POST':
        course_id = request.POST.get('course_id')
        teacher_ids = request.POST.getlist('teachers')  # Get selected teacher IDs

        course = Course.objects.get(id=course_id)
        
        # Create TeacherCourse records for the selected teachers
        for teacher_id in teacher_ids:
            teacher = Teacher.objects.get(id=teacher_id)
            TeacherCourse.objects.create(course=course, teacher=teacher)

        return redirect('teacher_course_assign')  # Redirect to course list after saving

# Remove teachers from a course
def remove_teachers(request):
    if request.method == 'POST':
        course_id = request.POST.get('course_id')
        teacher_ids = request.POST.getlist('teachers_to_remove')

        try:
            # Get the course object
            course = Course.objects.get(id=course_id)

            # Loop through the selected teacher IDs and remove them
            for teacher_id in teacher_ids:
                # Find the TeacherCourse object and remove it
                teacher_course = TeacherCourse.objects.get(course=course, teacher_id=teacher_id)
                teacher_course.delete()

            # Success message
            messages.success(request, "Teachers removed successfully.")

        except Course.DoesNotExist:
            raise Http404("Course not found.")
        except TeacherCourse.DoesNotExist:
            messages.error(request, "Some teachers were not assigned to this course.")
        
        # Redirect to course list or the page where you want
        return redirect('teacher_course_assign')  # Adjust the redirect URL as needed

    # If the request is not POST, redirect to the course list page
    return redirect('teacher_course_assign')


def student_course_assign(request):
    teacher = Teacher.objects.get(user=request.user)
    department = teacher.department
    students = Student.objects.filter(programme__department=department).order_by('university_register_number')

    # Prepare the student_courses_map for all students
    student_courses_map = {}
    for student in students:
        student_courses_map[student] = StudentCourse.objects.filter(student=student)
    
    # If the request method is POST, handle form submission
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        student = Student.objects.get(id=student_id)
        selected_course_ids = request.POST.getlist('courses')

        # Ensure courses are selected
        if selected_course_ids:
            # Assign courses to the selected student
            for course_id in selected_course_ids:
                course = Course.objects.get(id=course_id)
                # Check if the student is already assigned to the course
                if not StudentCourse.objects.filter(student=student, course=course).exists():
                    StudentCourse.objects.create(student=student, course=course)
            messages.success(request, f"Courses successfully assigned to {student.name}.")
        else:
            messages.error(request, "No courses were selected for assignment.")
        
        return redirect('student_course_assign')  # Redirect after saving assignments
    
    all_courses = Course.objects.all()

    # Ensure the selected student is passed to the template
    selected_student = students.first()  # Example: default to the first student, update as per your logic
    selected_student_courses = student_courses_map.get(selected_student, [])

    return render(request, 'attendance/student_course_form.html', {
        'students': students,
        'all_courses': all_courses,
        'student_courses_map': student_courses_map,
        'selected_student_courses': selected_student_courses,  # Pass the courses of the selected student
        'selected_student': selected_student,  # Pass the selected student for further reference
    })


# View to get assigned courses for a student
def get_assigned_courses(request, student_id):
    student = Student.objects.get(id=student_id)
    student_courses = StudentCourse.objects.filter(student=student)
    courses = [student_course.course for student_course in student_courses]
    
    # Prepare the course data to send back
    course_data = [{'id': course.id, 'code': course.code, 'name': course.name} for course in courses]
    
    return JsonResponse({'courses': course_data})




def remove_courses(request):
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        courses_to_remove = request.POST.getlist('courses_to_remove')

        # Debugging: Log the received course IDs and student ID
        print(f"Student ID: {student_id}")
        print(f"Courses to Remove: {courses_to_remove}")

        if student_id and courses_to_remove:
            student = get_object_or_404(Student, id=student_id)

            # Using transaction to ensure the deletion happens
            with transaction.atomic():
                # Delete the selected courses for the student
                StudentCourse.objects.filter(student=student, course_id__in=courses_to_remove).delete()
                messages.success(request, f"Selected courses have been removed from {student.name}.")
        else:
            messages.error(request, "No courses were selected for removal.")

        return redirect('student_course_assign')  # Redirect back to the form page



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


