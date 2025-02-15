import csv
import re
from django.urls import reverse
from datetime import date
from datetime import datetime
from django.db.models import Min,Count
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.forms import PasswordChangeForm
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.models import User
from django.http import HttpResponse,Http404,JsonResponse, HttpResponseRedirect
from .models import Student, Teacher, Course, StudentCourse, TeacherCourse, HourDateCourse, AbsentDetails,Programme,Department
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import IntegrityError
from django.contrib import messages
from django.db import transaction
from .forms import (
    StudentForm, TeacherForm, CourseForm, 
    UserEditForm,UserForm,CSVUploadForm,
)

def calculate_year(current_date):
    """
    Calculate the academic year based on the date.
    June 1 of a year to May 31 of the next year is considered the same academic year.
    """
    if current_date.month >= 6:  # From June to December
        return current_date.year
    else:  # From January to May
        return current_date.year - 1


def clean_name(name):
    """Standardize the name format: convert to uppercase and replace periods with spaces."""
    return name.strip().replace('.', ' ').upper()

def HoD_group_required(user):
    """Check if the user belongs to the 'HoD' group."""
    return user.groups.filter(name='HoD').exists()

def is_superuser(user):
    return user.is_superuser

@login_required
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
def download_student_template(request):
    # Get the logged-in HoD's department
    teacher = Teacher.objects.get(user=request.user)
    department = teacher.department

    # Create the HTTP response with the appropriate content type for a CSV file
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="student_template.csv"'

    # Write the CSV data
    writer = csv.writer(response)
    writer.writerow(['name', 'programme_name', 'university_register_number', 'admission_number'])  # Header

    # Add example rows
    example_programme = Programme.objects.filter(department=department).first()
    if example_programme:
        writer.writerow(['John Doe', example_programme.name, '1234567890', 'ADM001'])
    else:
        writer.writerow(['John Doe', 'Example Programme', '1234567890', 'ADM001'])

    return response


@login_required
@user_passes_test(HoD_group_required)
def upload_students(request):
    # Get the logged-in HoD's department
    teacher = Teacher.objects.get(user=request.user)
    department = teacher.department

    if request.method == 'POST' and request.FILES['csv_file']:
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = form.cleaned_data['csv_file']
            decoded_file = csv_file.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded_file)

            for row in reader:
                programme_name = row.get('programme_name')  # Programme name from CSV
                student_name = clean_name(row.get('name'))  # Clean and validate the student name
                university_register_number = row.get('university_register_number')
                admission_number = row.get('admission_number')

                # Check for existing students by unique fields
                if Student.objects.filter(university_register_number=university_register_number).exists():
                    messages.warning(
                        request,
                        f"Student with University Register Number '{university_register_number}' already exists. Skipping student '{student_name}'."
                    )
                    continue

                if Student.objects.filter(admission_number=admission_number).exists():
                    messages.warning(
                        request,
                        f"Student with Admission Number '{admission_number}' already exists. Skipping student '{student_name}'."
                    )
                    continue

                # Verify if the programme exists in the HoD's department
                try:
                    programme = Programme.objects.get(name=programme_name, department=department)
                except Programme.DoesNotExist:
                    messages.error(
                        request,
                        f"Programme '{programme_name}' not found in your department. Skipping student '{student_name}'."
                    )
                    continue

                # Create the student if all validations pass
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
@user_passes_test(HoD_group_required)
def remove_student(request, id):
    student = get_object_or_404(Student, id=id)
    
    # Optionally check if the user has permissions to delete the student
    student.delete()
    
    return redirect('student_list')

@login_required
@user_passes_test(HoD_group_required)
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
    # Get the logged-in teacher
    logged_in_teacher = request.user.teacher

    if request.method == 'POST':
        user_form = UserForm(request.POST)
        teacher_form = TeacherForm(request.POST, logged_in_teacher=logged_in_teacher)

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
        teacher_form = TeacherForm(logged_in_teacher=logged_in_teacher)

    return render(request, 'attendance/register_teacher.html', {
        'user_form': user_form,
        'teacher_form': teacher_form,
    })


@login_required
@user_passes_test(HoD_group_required)
def download_teacher_template(request):
    # Get the logged-in HoD's department
    hod = Teacher.objects.get(user=request.user)
    hod_department = hod.department

    # Create the HTTP response with the appropriate content type for a CSV file
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="teacher_template.csv"'

    # Write the CSV data
    writer = csv.writer(response)
    writer.writerow(['name', 'department', 'email', 'mobile_number'])  # Header
    writer.writerow(['John Doe', hod_department.name, 'john.doe@example.com', '9876543210'])  # Example row

    return response


@login_required
@user_passes_test(HoD_group_required)
def upload_teachers(request):
    # Get the logged-in HoD's department
    hod = Teacher.objects.get(user=request.user)
    hod_department = hod.department

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

                # Check if the department matches the HoD's department
                if department_name != hod_department.name:
                    messages.warning(request, f"Teacher '{name}' cannot be added to department '{department_name}' as it does not match your department.")
                    continue

                # Check if the teacher already exists by username or email
                if User.objects.filter(username=username).exists():
                    messages.warning(request, f"User with username '{username}' already exists. Skipping teacher '{name}'.")
                    continue

                if User.objects.filter(email=email).exists():
                    messages.warning(request, f"User with email '{email}' already exists. Skipping teacher '{name}'.")
                    continue

                try:
                    # Create a new user
                    with transaction.atomic():
                        user = User.objects.create_user(username=username, email=email, password=password)
                        user.first_name = name  # Set the teacher's full name
                        user.save()

                        # Create the Teacher instance and associate it with the user and department
                        teacher = Teacher.objects.create(
                            user=user,
                            department=hod_department,  # Assign to HoD's department
                            phone_number=mobile_number,  # Mobile number can be edited later
                        )

                    messages.success(request, f"Teacher '{name}' uploaded successfully!")

                except Exception as e:
                    messages.error(request, f"Error uploading teacher '{name}': {e}")
                    continue

            return redirect('teacher_list')  # Redirect to the teacher list after uploading
    else:
        form = CSVUploadForm()

    return render(request, 'attendance/upload_teachers.html', {'form': form})



@login_required
def edit_teacher(request, teacher_id):
    teacher = get_object_or_404(Teacher, id=teacher_id)  # Get the teacher instance by id
    user = teacher.user  # Get the related User instance

    # Get the logged-in teacher
    logged_in_teacher = request.user.teacher

    if request.method == 'POST':
        user_form = UserEditForm(request.POST, instance=user)
        teacher_form = TeacherForm(request.POST, instance=teacher, logged_in_teacher=logged_in_teacher)

        if user_form.is_valid() and teacher_form.is_valid():
            user_form.save()
            teacher_form.save()
            messages.success(request, "The teacher's profile has been updated successfully.")
            return redirect('teacher_list')

    else:
        user_form = UserEditForm(instance=user)
        teacher_form = TeacherForm(instance=teacher, logged_in_teacher=logged_in_teacher)

    return render(request, 'attendance/edit_teacher.html', {
        'user_form': user_form,
        'teacher_form': teacher_form,
    })

@login_required
@user_passes_test(HoD_group_required)
def reset_password(request, teacher_id):
    try:
        # Get the Teacher instance by ID
        teacher = get_object_or_404(Teacher, id=teacher_id)
        
        # Reset the password for the corresponding User
        user = teacher.user  # Access the related user (one-to-one relationship)
        user.set_password(f"{user.username}@123")
        user.save()
        
        # Display success message
        messages.success(request, f"Password for teacher {teacher.user.username} has been reset.")
        
    except Teacher.DoesNotExist:
        # Handle the case if the teacher doesn't exist
        messages.error(request, "Teacher not found.")
    
    # Redirect back to the admin page or any page you prefer
    return HttpResponseRedirect(reverse('teacher_list'))  # Change to your admin page URL

@login_required
def change_password(request, teacher_id):
    teacher = get_object_or_404(Teacher, id=teacher_id)
    user = teacher.user  # Access the associated user object

    if request.method == 'POST':
        form = PasswordChangeForm(user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Keep the user logged in after password change
            messages.success(request, 'Your password has been successfully updated!')
            return redirect('teacher_list')  # Redirect to teacher list after successful password change
    else:
        form = PasswordChangeForm(user)

    return render(request, 'attendance/change_password.html', {'form': form, 'teacher': teacher})

@login_required
@user_passes_test(HoD_group_required)
def delete_teacher(request, teacher_id):
    # Get the Teacher object
    teacher = get_object_or_404(Teacher, id=teacher_id)

    try:
        with transaction.atomic():
            # Delete the associated user
            user = teacher.user
            user.delete()  # This will delete the user from the User model

            # Delete the Teacher record
            teacher.delete()

        messages.success(request, f"Teacher '{teacher.user.first_name}' and associated user have been deleted successfully.")
    except Exception as e:
        messages.error(request, f"Error deleting teacher '{teacher.user.first_name}': {e}")

    return redirect('teacher_list')

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



@login_required
def get_assigned_students(request, course_id):
    students = StudentCourse.objects.filter(course_id=course_id).select_related('student__programme')
    
    students_data = [{
        'id': student.student.id,  # Include the student's ID
        'c_id': course_id,
        'name': student.student.name,
        'university_register_number': student.student.university_register_number,
        'programme': student.student.programme.name  # Assuming 'name' is the field in Programme
    } for student in students]
    
    return JsonResponse({'students': students_data})

# View for managing Course
@login_required
@user_passes_test(HoD_group_required)
def add_course(request):
    # Get the logged-in teacher
    logged_in_teacher = request.user.teacher

    if request.method == 'POST':
        form = CourseForm(request.POST, logged_in_teacher=logged_in_teacher)
        if form.is_valid():
            form.save()
            return redirect('course_list')
    else:
        form = CourseForm(logged_in_teacher=logged_in_teacher)

    return render(request, 'attendance/course_form.html', {'form': form})

@login_required
def edit_course(request, course_id):
    logged_in_teacher = request.user.teacher
    course = get_object_or_404(Course, id=course_id)
    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course, logged_in_teacher=logged_in_teacher)
        if form.is_valid():
            form.save()
            return redirect('course_list')  # Redirect to course list after saving
    else:
        form = CourseForm(instance=course, logged_in_teacher=logged_in_teacher)
    return render(request, 'attendance/edit_course.html', {'form': form, 'course': course})



@login_required
@user_passes_test(HoD_group_required)
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


@login_required
@user_passes_test(HoD_group_required)
def assign_teachers(request):
    if request.method == 'POST':
        course_id = request.POST.get('course_id')
        teacher_ids = request.POST.getlist('teachers')  # Get selected teacher IDs

        course = get_object_or_404(Course, id=course_id)
        year = calculate_year(date.today())  # Use the calculate_year function

        # Create TeacherCourse records for the selected teachers
        for teacher_id in teacher_ids:
            teacher = get_object_or_404(Teacher, id=teacher_id)

            # Check if the teacher is already assigned to the course for the current year
            if TeacherCourse.objects.filter(course=course, teacher=teacher, year=year).exists():
                # Use teacher.user.get_full_name() or another field for the teacher's name
                messages.warning(request, f"Teacher {teacher.user.get_full_name()} is already assigned to the course {course.name} for the year {year}.")
            else:
                # Create the new TeacherCourse record if no duplicate exists
                TeacherCourse.objects.create(course=course, teacher=teacher, year=year)

        return redirect('teacher_course_assign')  # Redirect to course list after saving

# Remove teachers from a course
@login_required
@user_passes_test(HoD_group_required)
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


@login_required
@user_passes_test(HoD_group_required)
def student_course_assign(request):
    teacher = Teacher.objects.get(user=request.user)
    department = teacher.department
    students = Student.objects.filter(programme__department=department).order_by('university_register_number')

    # Prepare the student_courses_map for all students
    student_courses_map = {}
    for student in students:
        student_courses_map[student] = StudentCourse.objects.filter(student=student).order_by('course__code')
    
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
    
    all_courses = Course.objects.all().select_related('department').order_by('department__name', 'name')

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
@login_required
def get_assigned_courses(request, student_id):
    student = Student.objects.get(id=student_id)
    student_courses = StudentCourse.objects.filter(student=student)
    courses = [student_course.course for student_course in student_courses]
    
    # Prepare the course data to send back
    course_data = [{'id': course.id, 'code': course.code, 'name': course.name} for course in courses]
    
    return JsonResponse({'courses': course_data})

@login_required
@user_passes_test(HoD_group_required)
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


@login_required
def take_attendance(request, course_id):
    teacher = request.user.teacher
    course = get_object_or_404(Course, id=course_id)

    if not TeacherCourse.objects.filter(teacher=teacher, course=course).exists():
        messages.error(request, "You are not authorized to take attendance for this course.")
        return redirect('course_list')

    student_courses = StudentCourse.objects.filter(course=course)
    students = [student_course.student for student_course in student_courses]

    # Get sorting option from the request
    sort_by = request.GET.get('sort_by', 'university_register_number')

    # Sort students based on the selected filter
    if sort_by == "roll_no":
        students.sort(key=lambda student: student.roll_no if student.roll_no else "")
    else:
        students.sort(key=lambda student: student.university_register_number)

    if request.method == 'POST':
        attendance_date_str = request.POST.get('date', '')

        if not attendance_date_str:
            messages.warning(request, "Please select a date for taking attendance.")
            return redirect(request.path)

        attendance_date = date.fromisoformat(attendance_date_str)
        selected_hours = request.POST.getlist('hours')

        if not selected_hours:
            messages.warning(request, "Please select at least one hour to record attendance.")
            return redirect(request.path)

        for hour in selected_hours:
            try:
                hour_date_course = HourDateCourse.objects.create(
                    course=course,
                    teacher=teacher,
                    date=attendance_date,
                    hour=int(hour),
                )
                messages.success(request, f"Attendance successfully recorded for Hour {hour}")
            except IntegrityError:
                existing_record = HourDateCourse.objects.get(course=course, date=attendance_date, hour=int(hour))
                teacher_full_name = f"{existing_record.teacher.user.first_name} {existing_record.teacher.user.last_name}"
                teacher_phone = existing_record.teacher.phone_number
                messages.warning(request, f"Attendance already taken by {teacher_full_name} ({teacher_phone}) in Hour {hour} on {attendance_date}")
                continue

            for student in students:
                if f'students_{student.id}' in request.POST:
                    AbsentDetails.objects.update_or_create(
                        hour_date_course=hour_date_course,
                        student=student,
                        defaults={'status': False}
                    )

        return redirect('course_list')

    return render(request, 'attendance/take_attendance.html', {
        'course': course,
        'students': students,
        'today': date.today(),
        'hours': range(1, 6),
        'sort_by': sort_by,  # Pass sorting method to template
    })





@login_required
def teacher_attendance_list(request):
    # Ensure the logged-in user is a teacher
    if not hasattr(request.user, 'teacher'):
        messages.error(request, "You are not authorized to access this page.")
        return redirect('home')

    teacher = request.user.teacher  # Get the Teacher instance linked to the user
    attendance_records = HourDateCourse.objects.filter(teacher=teacher).order_by('-date')

    context = {
        'attendance_records': attendance_records,
    }
    return render(request, 'attendance/teacher_attendance_list.html', context)


@login_required
def edit_attendance(request, record_id):
    # Ensure the logged-in user is a teacher
    if not hasattr(request.user, 'teacher'):
        messages.error(request, "You are not authorized to access this page.")
        return redirect('teacher_attendance_list')

    # Get the attendance record (HourDateCourse) by ID
    attendance_record = get_object_or_404(HourDateCourse, id=record_id)

    # Ensure the logged-in teacher is the one who took the attendance
    if attendance_record.teacher != request.user.teacher:
        messages.error(request, "You are not authorized to edit this attendance.")
        return redirect('teacher_attendance_list')

    # Get all students associated with the course in this attendance record
    student_courses = StudentCourse.objects.filter(course=attendance_record.course).select_related('student')
    students = [student_course.student for student_course in student_courses]

    # Sorting logic
    sort_by = request.GET.get('sort', 'register_number')  # Default sorting by University Register No.

    def extract_course_code(register_number):
        """Extract course code from University Register Number (e.g., 'NA24MATR001' -> 'MATR')"""
        match = re.search(r'NA\d{2}([A-Z]+)\d+', register_number)
        return match.group(1) if match else "ZZZ"  # Default to 'ZZZ' if no match (ensures unknown courses go last)

    if sort_by == 'roll_number':
        students.sort(key=lambda student: (extract_course_code(student.university_register_number), student.roll_number or ""))
    else:
        students.sort(key=lambda student: student.university_register_number)

    # Get existing absences for this attendance record
    existing_absences = AbsentDetails.objects.filter(hour_date_course=attendance_record)
    absent_students = {absence.student.id for absence in existing_absences}

    if request.method == 'POST':
        # Update absences based on the submitted form
        selected_absent_ids = {
            int(key.split('_')[1])  # Extract student ID from checkbox name
            for key in request.POST.keys()
            if key.startswith('students_')
        }

        # Update or delete AbsentDetails as needed
        for student in students:
            if student.id in selected_absent_ids:
                AbsentDetails.objects.update_or_create(
                    hour_date_course=attendance_record,
                    student=student,
                    defaults={'status': False}  # Mark as absent
                )
            else:
                AbsentDetails.objects.filter(hour_date_course=attendance_record, student=student).delete()

        messages.success(request, "Attendance updated successfully.")
        return HttpResponseRedirect(reverse('teacher_attendance_list'))

    context = {
        'attendance_record': attendance_record,
        'students': students,
        'absent_students': absent_students,
    }
    return render(request, 'attendance/edit_attendance.html', context)



@login_required
def remove_attendance(request, record_id):
    record = get_object_or_404(HourDateCourse, id=record_id, teacher=request.user.teacher)
    record.delete()
    messages.success(request, "Attendance record removed successfully!")
    return redirect('teacher_attendance_list')




@login_required
def attendance_report(request, course_id):
    course = Course.objects.get(id=course_id)
    total_hours = HourDateCourse.objects.filter(course=course).count()

    # Fetch students from the StudentCourse table, which links students to courses
    student_courses = StudentCourse.objects.filter(course=course)
    students = Student.objects.filter(id__in=student_courses.values_list('student_id', flat=True)).order_by('university_register_number')

    # Fetch attendance records for the course
    attendance_records = AbsentDetails.objects.filter(hour_date_course__course=course)

    # Get the current date and time
    date_time = datetime.now()

    attendance_data = []
    for student in students:
        total_present = 0
        total_absent = 0
        
        # Iterate through each HourDateCourse for the course
        for hour_date_course in HourDateCourse.objects.filter(course=course):
            # Check if there is an attendance record for the student for this hour_date_course
            attendance_record = attendance_records.filter(student=student, hour_date_course=hour_date_course).first()
            
            if attendance_record:  # If there is an attendance record
                if attendance_record.status:  # Mark present if status is True
                    total_present += 1
                else:  # Mark absent if status is False
                    total_absent += 1
            else:  # If no attendance record exists, consider the student as present
                total_present += 1
        
        # Calculate attendance percentage
        attendance_percentage = (total_present / total_hours) * 100 if total_hours else 0

        # Add grace hours logic if applicable
        attendance_with_grace = attendance_percentage  # Adjust this if grace hours apply

        attendance_data.append({
            "student": student,
            "total_present": total_present,
            "total_absent": total_absent,
            "attendance_percentage": round(attendance_percentage, 2),
            "attendance_with_grace": round(attendance_with_grace, 2),
        })

    context = {
        "course": course,
        "total_hours": total_hours,
        "attendance_data": attendance_data,
        "date_time": date_time,  # Pass the current date and time to the template
    }

    return render(request, 'attendance/report.html', context)



@login_required
@user_passes_test(HoD_group_required)
def student_individual_report(request, student_id):
    # Fetch the student and their enrolled courses
    student = Student.objects.get(id=student_id)
    student_courses = StudentCourse.objects.filter(student=student)
    
    # List of courses the student is enrolled in
    courses = [sc.course for sc in student_courses]

    courses.sort(key=lambda course: course.code)
    
    # Get attendance records for the student
    attendance_data = []
    total_hours = 0
    total_present = 0
    total_absent = 0
    total_course_hours = 0  # Total hours across all courses
    total_attended_hours = 0  # Total hours the student was present across all courses

    # Iterate over each course the student is enrolled in
    for course in courses:
        course_data = {
            'course': course,
            'attendance_per_day': [],
            'total_hours': 0,
            'total_present': 0,
            'total_absent': 0,
            'attendance_percentage': 0,
        }

        # Fetch the class sessions for the course, ordered by date
        sessions = HourDateCourse.objects.filter(course=course).order_by('date')

        for session in sessions:
            # Check if there is an attendance record for this student for this session
            attendance_record = AbsentDetails.objects.filter(student=student, hour_date_course=session).first()
            
            # Calculate attendance status
            if attendance_record:
                status = 'Present' if attendance_record.status else 'Absent'
                if attendance_record.status:
                    course_data['total_present'] += 1
                    total_attended_hours += 1  # Increase the attended hours for the student
                else:
                    course_data['total_absent'] += 1
            else:
                status = 'Present'  # Assume present if no record exists
                course_data['total_present'] += 1
                total_attended_hours += 1  # Assume student is present if no record exists

            course_data['attendance_per_day'].append({
                'date': session.date,
                'status': status,
                'hour': session.hour,
            })
            course_data['total_hours'] += 1
        
        # Calculate attendance percentage for the course
        if course_data['total_hours'] > 0:
            course_data['attendance_percentage'] = round((course_data['total_present'] / course_data['total_hours']) * 100,2)
        
        # Add the course data to the attendance data
        attendance_data.append(course_data)

        # Accumulate total course hours and total attended hours for the entire student
        total_course_hours += course_data['total_hours']
        total_present += course_data['total_present']
        total_absent += course_data['total_absent']

    # Calculate overall attendance percentage for the student
    if total_course_hours > 0:
        overall_attendance_percentage = (total_attended_hours / total_course_hours) * 100
    else:
        overall_attendance_percentage = 0

    context = {
        'student': student,
        'attendance_data': attendance_data,
        'total_hours': total_course_hours,
        'total_present': total_present,
        'total_absent': total_absent,
        'overall_attendance_percentage': round(overall_attendance_percentage, 2),
    }

    return render(request, 'attendance/student_report.html', context)



@login_required
@user_passes_test(HoD_group_required)
def department_report(request, department_id):
    # Fetch the department
    department = Department.objects.get(id=department_id)
    
    # Get all students in the department, ordered by their university register number
    students = Student.objects.filter(programme__department=department).order_by('university_register_number')
    
    # Calculate total hours taken for the department (sum of all hours in all courses)
    total_hours_taken = HourDateCourse.objects.filter(course__studentcourse__student__programme__department=department).count()

    # Prepare the data for each student
    student_data = []

    # Iterate over each student in the department
    for student in students:
        total_present = 0
        total_hours = 0  # Total hours the student could attend (across all their courses)
        total_absent = 0
        total_attended_hours = 0  # Total hours the student was present across all courses
        
        # Fetch the courses assigned to this student
        courses = student.studentcourse_set.values_list('course', flat=True)

        # Loop through the courses the student is enrolled in
        for course_id in courses:
            # Calculate the total number of hours for this course
            course_hours = HourDateCourse.objects.filter(course_id=course_id).count()
            total_hours += course_hours  # Accumulate the total hours for this student
            
            # Fetch all the sessions for this course
            sessions = HourDateCourse.objects.filter(course_id=course_id).order_by('date')
            
            # Loop through each session and calculate present/absent status
            for session in sessions:
                # Check if there is an attendance record for this student for this session
                attendance_record = AbsentDetails.objects.filter(student=student, hour_date_course=session).first()
                
                if attendance_record:
                    if attendance_record.status:
                        total_present += 1
                        total_attended_hours += 1
                    else:
                        total_absent += 1
                else:
                    # If no record exists, assume the student is present
                    total_present += 1
                    total_attended_hours += 1

        # Calculate attendance percentage for this student
        attendance_percentage = (total_attended_hours / total_hours * 100) if total_hours > 0 else 0

        # Append the student's data to the list
        student_data.append({
            'student': student,
            'total_present': total_present,
            'attendance_percentage': round(attendance_percentage, 2),
            'total_hours_taken': total_hours,  # Total hours across all courses
        })
    
    # Prepare context for rendering
    context = {
        'department': department,
        'students': student_data,
        'total_hours_taken': total_hours_taken,
        'is_hod': request.user.groups.filter(name='HOD').exists()  # Check if the user is HOD
    }

    return render(request, 'attendance/department.html', context)


@login_required
@user_passes_test(is_superuser)
@user_passes_test(HoD_group_required)
def programme_courses_view(request):
    programmes = Programme.objects.all()
    programme_data = []

    for programme in programmes:
        students = Student.objects.filter(programme=programme)
        total_students = students.count()
        total_courses_required = total_students * 6 if total_students else 0

        # Get unique courses per student by course code
        student_course_counts = StudentCourse.objects.filter(student__programme=programme) \
            .values('student', 'course__code') \
            .distinct() \
            .values('student') \
            .annotate(unique_courses=Count('course__code', distinct=True))

        # Sum unique courses across all students
        current_courses_count = sum(entry['unique_courses'] for entry in student_course_counts)

        # Get distinct courses (by picking only one per unique code)
        unique_courses = Course.objects.filter(studentcourse__student__programme=programme) \
            .values('code') \
            .annotate(id=Min('id'))  # Pick one course per unique code

        courses = Course.objects.filter(id__in=[entry['id'] for entry in unique_courses]).order_by('code')

        # Calculate the difference
        difference = total_courses_required - current_courses_count

        programme_data.append({
            'programme': programme,
            'courses': courses,
            'total_students': total_students,
            'total_courses_required': total_courses_required,
            'current_courses_count': current_courses_count,
            'difference': difference,
        })

    return render(request, 'attendance/programme_courses.html', {'programme_data': programme_data})


@login_required
@user_passes_test(is_superuser)
def admin_dashboard(request):
    return render(request, 'attendance/admin_page.html')


@login_required
@user_passes_test(is_superuser)
def admin_department_view(request):
    departments = Department.objects.all()
    selected_department = None
    students, teachers, courses = [], [], []

    if request.GET.get('department_id'):
        department_id = request.GET.get('department_id')
        selected_department = Department.objects.get(id=department_id)
        students = Student.objects.filter(programme__department=selected_department).order_by('university_register_number')
        teachers = Teacher.objects.filter(department=selected_department)
        courses = Course.objects.filter(department=selected_department)
        
        # Get students assigned to each course
        course_students = {}
        for course in courses:
            assigned_students = StudentCourse.objects.filter(course=course).values('student__name')
            course_students[course] = assigned_students
    else:
        course_students = None

    return render(request, 'attendance/admin_department_view.html', {
        'departments': departments,
        'selected_department': selected_department,
        'students': students,
        'teachers': teachers,
        'courses': courses,
        'course_students': course_students,
    })
