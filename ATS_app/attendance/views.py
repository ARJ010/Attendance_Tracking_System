import csv
import re
from collections import defaultdict
from django.urls import reverse
from datetime import date
from datetime import datetime
from django.db.models import Min,Count
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.http import urlencode
from django.template.loader import render_to_string
from django.contrib.auth.forms import PasswordChangeForm
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.models import User
from django.http import HttpResponse,Http404,JsonResponse, HttpResponseRedirect
from .models import Student, Teacher, Course,AbsentDetails,Programme,Department, StudentBatch, Batch, TeacherBatch,HourDateBatch,TC,StudentTransfer,GraceAttendance
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.contrib import messages
from django.db import transaction
from .forms import (
    StudentForm, TeacherForm, CourseForm, 
    UserEditForm,UserForm,CSVUploadForm,BatchForm,TCForm
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


def get_student_batch_stats(student, batch):
    """
    Computes attendance stats for a single student in a single batch.
    """
    sessions = HourDateBatch.objects.filter(batch=batch)
    total_hours = sessions.count()
    
    absences = AbsentDetails.objects.filter(student=student, hour_date_batch__in=sessions, status=False)
    absent_ids = set(absences.values_list('hour_date_batch_id', flat=True))
    
    grace = GraceAttendance.objects.filter(student=student, hour_date_batch__in=sessions)
    grace_ids = set(grace.values_list('hour_date_batch_id', flat=True))
    
    applied_grace_ids = grace_ids.intersection(absent_ids)
    
    grace_hours = len(applied_grace_ids)
    actual_absent = len(absent_ids)
    effective_absent = actual_absent - grace_hours
    
    actual_present = total_hours - actual_absent
    effective_present = total_hours - effective_absent
    
    physical_percentage = round((actual_present / total_hours) * 100, 2) if total_hours > 0 else 0.0
    effective_percentage = round((effective_present / total_hours) * 100, 2) if total_hours > 0 else 0.0
    
    return {
        'total_hours': total_hours,
        'actual_present': actual_present,
        'grace_hours': grace_hours,
        'effective_present': effective_present,
        'physical_percentage': physical_percentage,
        'effective_percentage': effective_percentage,
    }

def HoD_group_required(user):
    """Check if the user belongs to the 'HoD' group."""
    return user.groups.filter(name='HoD').exists()

def is_superuser(user):
    return user.is_superuser

def get_user_teacher(user):
    """
    Safely retrieves the Teacher object associated with the logged-in user.
    If the user is a superuser/admin and does not have a Teacher record,
    it falls back to returning the first Teacher in the database or creates a dummy one,
    preventing crashes.
    """
    try:
        return Teacher.objects.get(user=user)
    except Teacher.DoesNotExist:
        if user.is_superuser:
            first_teacher = Teacher.objects.first()
            if first_teacher:
                return first_teacher
            # If no teachers exist at all (empty DB setup)
            from django.contrib.auth.models import Group
            dept = Department.objects.first()
            if not dept:
                dept = Department.objects.create(name="Default Department")
            # Make sure superuser is in HoD group so they don't get permission errors
            hod_group, _ = Group.objects.get_or_create(name='HoD')
            user.groups.add(hod_group)
            
            teacher = Teacher.objects.create(
                user=user,
                name=user.username,
                department=dept,
                acronym=user.username[:3].upper()
            )
            return teacher
        raise

@login_required
def index(request):
    return render(request, 'attendance/index.html')

@login_required
def student_list(request, sem):
    teacher = get_user_teacher(request.user)
    department = teacher.department

    # Get all semesters available in this department's students
    semesters = Student.objects.filter(programme__department=department).values_list('current_semester', flat=True).distinct().order_by('current_semester')

    # Use the semester from the URL parameter
    selected_semester = sem

    # Filter students by department and selected semester
    students = Student.objects.filter(
        programme__department=department,
        current_semester=selected_semester
    ).order_by('university_register_number')

    tc_forms = {student.id: TCForm() for student in students}

    departments = Department.objects.filter(programmes__isnull=False).distinct()
    

    return render(request, 'attendance/student_list.html', {
        'students': students,
        'tc_forms': tc_forms,
        'department': department,
        'departments': departments,
        'semesters': semesters,
        'selected_semester': selected_semester,
    })

@login_required
def semester_up(request):
    teacher = get_user_teacher(request.user)
    department = teacher.department

    sem = request.POST.get('semester')
    if not sem:
        messages.error(request, "No semester selected.")
        return redirect(reverse('student_list', args=[1]))

    try:
        sem = int(sem)
    except (TypeError, ValueError):
        messages.error(request, "Invalid semester.")
        return redirect(reverse('student_list', args=[1]))

    # Check if next semester already has students
    if sem == 8:
        next_sem = 0
    else:
        next_sem = sem + 1

    if next_sem != 0:
        next_sem_students = Student.objects.filter(
            programme__department=department,
            current_semester=next_sem
        )
        if next_sem_students.exists():
            messages.error(request, f"Cannot move up: Semester {next_sem} already has students.")
            # Redirect to student_list with current semester
            return redirect(reverse('student_list', args=[sem]))

    # Move all students in current semester up by 1 (or to Alumni)
    students_to_update = Student.objects.filter(
        programme__department=department,
        current_semester=sem
    )
    updated_count = students_to_update.update(current_semester=next_sem)
    messages.success(request, f"{updated_count} students moved from semester {sem} to {next_sem if next_sem != 0 else 'Alumni (0)'}.")

    # Redirect to student_list with next semester selected
    return redirect(reverse('student_list', args=[next_sem]))



@login_required
@user_passes_test(HoD_group_required)
def add_student(request):
    teacher = get_user_teacher(request.user)  # Get the teacher associated with the logged-in user

    if request.method == 'POST':
        form = StudentForm(request.POST, teacher=teacher)  # Pass the teacher to the form
        if form.is_valid():
            # Save the student with the department associated with the logged-in teacher
            student = form.save(commit=False)
            student.programme.department = teacher.department  # Assign the department from the teacher
            student.save()
            return redirect(reverse('student_list', args=[student.current_semester]))  # Redirect to the student list after saving
    else:
        form = StudentForm(teacher=teacher)  # Pass the teacher to the form

    return render(request, 'attendance/add_student.html', {'form': form})


@login_required
@user_passes_test(HoD_group_required)
def download_student_template(request):
    # Get the logged-in HoD's department
    teacher = get_user_teacher(request.user)
    department = teacher.department

    # Create the HTTP response with the appropriate content type for a CSV file
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="student_template.csv"'

    # Write the CSV data
    writer = csv.writer(response)
    writer.writerow(['name', 'programme_name', 'year_of_enrolment', 'university_register_number', 'admission_number', 'current_semester'])  # Header

    # Add example rows
    example_programme = Programme.objects.filter(department=department).first()
    if example_programme:
        writer.writerow(['John Doe', example_programme.name, '2024', '1234567890', 'ADM001','1'])
    else:
        writer.writerow(['John Doe', 'Example Programme', '2024', '1234567890', 'ADM001','1'])

    return response


@login_required
@user_passes_test(HoD_group_required)
def upload_students(request):
    # Get the logged-in HoD's department
    teacher = get_user_teacher(request.user)
    department = teacher.department

    if request.method == 'POST' and request.FILES['csv_file']:
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = form.cleaned_data['csv_file']
            decoded_file = csv_file.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded_file)

            current_semester = 1  # Default fallback in case of empty CSV
            for row in reader:
                programme_name = row.get('programme_name')  # Programme name from CSV
                student_name = clean_name(row.get('name'))  # Clean and validate the student name
                university_register_number = row.get('university_register_number')
                year_of_enrolment = row.get('year_of_enrolment')
                admission_number = row.get('admission_number')
                current_semester = row.get('current_semester')

                # Validate university_register_number pattern if provided
                if university_register_number:
                    if not re.match(r'^NA\d{2}[A-Z]{4}\d{3}$', university_register_number):
                        messages.error(
                            request,
                            f"University Register Number '{university_register_number}' does not follow the required pattern (NA + 2-digit year + 4-letter programme code + 3-digit serial). Skipping student '{student_name}'."
                        )
                        continue

                # Check for existing students by unique fields
                if university_register_number and Student.objects.filter(university_register_number=university_register_number).exists():
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
                    year_of_enrolment =year_of_enrolment,
                    university_register_number=university_register_number,
                    admission_number=admission_number,
                    programme=programme,
                    current_semester=current_semester
                )

            messages.success(request, 'Students uploaded successfully!')
            return redirect(reverse('student_list', args=[current_semester]))
    else:
        form = CSVUploadForm()

    return render(request, 'attendance/upload_students.html', {'form': form})


@login_required
@user_passes_test(HoD_group_required)
def remove_student(request, id):
    if request.method == 'POST':
        student = get_object_or_404(Student, id=id)
        sem = student.current_semester
        student.delete()
        messages.success(request, f"Student '{student.name}' removed successfully.")
        return redirect(reverse('student_list', args=[sem]))
    else:
        messages.error(request, "Invalid request method. Deletion must be done via POST.")
        return redirect(reverse('student_list', args=[1]))

@login_required
@user_passes_test(HoD_group_required)
def edit_student(request, id):
    student = get_object_or_404(Student, id=id)
    teacher = student.programme.department.teachers.filter(user=request.user).first()  # Use 'teachers' instead of 'teacher_set'
    
    if not teacher:
        return redirect(reverse('student_list', args=[student.current_semester]))  # If the teacher isn't part of the student's department, redirect

    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student, teacher=teacher)
        if form.is_valid():
            form.save()
            return redirect(reverse('student_list', args=[student.current_semester])) # Redirect to the student list after saving
    else:
        form = StudentForm(instance=student, teacher=teacher)
    
    return render(request, 'attendance/edit_student.html', {'form': form, 'student': student})


@login_required
def teacher_list(request):
    # Get the logged-in teacher's department
    teacher = get_user_teacher(request.user)
    department = teacher.department
    
    # Filter teachers based on the department and activity status
    active_teachers = Teacher.objects.filter(department=department, user__is_active=True)
    inactive_teachers = Teacher.objects.filter(department=department, user__is_active=False)
    
    return render(request, 'attendance/teacher_list.html', {
        'active_teachers': active_teachers,
        'inactive_teachers': inactive_teachers,
        'department': department
    })

@login_required
@user_passes_test(HoD_group_required)
def toggle_teacher_active(request, teacher_id):
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('teacher_list')

    teacher = get_object_or_404(Teacher, id=teacher_id)
    if teacher.user == request.user:
        messages.error(request, "You cannot deactivate your own account.")
    else:
        teacher.user.is_active = not teacher.user.is_active
        teacher.user.save()
        status = "activated" if teacher.user.is_active else "deactivated"
        messages.success(request, f"Teacher {teacher.user.get_full_name() or teacher.user.username} has been {status}.")
    
    return redirect('teacher_list')

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
    hod = get_user_teacher(request.user)
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
    hod = get_user_teacher(request.user)
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
                
                # Generate unique username
                base_username = first_name.lower()
                username = base_username
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}{counter}"
                    counter += 1

                password = f'{first_name.lower()}@123'  # Default password format: firstname@123
                mobile_number = row.get('mobile_number') or '1234567890'  # Default mobile number if missing

                # Check if the department matches the HoD's department
                if department_name != hod_department.name:
                    messages.warning(request, f"Teacher '{name}' cannot be added to department '{department_name}' as it does not match your department.")
                    continue

                # Check if the teacher already exists by email
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
    if request.method == 'POST':
        # Get the Teacher object
        teacher = get_object_or_404(Teacher, id=teacher_id)
        teacher_name = teacher.user.first_name

        try:
            with transaction.atomic():
                # Delete the associated user
                user = teacher.user
                user.delete()  # This will delete the user from the User model

            messages.success(request, f"Teacher '{teacher_name}' and associated user have been deleted successfully.")
        except Exception as e:
            messages.error(request, f"Error deleting teacher '{teacher_name}': {e}")
    else:
        messages.error(request, "Invalid request method. Deletion must be done via POST.")

    return redirect('teacher_list')


@login_required
def course_list(request, sem):
    teacher = get_user_teacher(request.user)
    department = teacher.department
    user = request.user

    # Filter courses by department and semester
    if user.groups.filter(name='HoD').exists():
        courses = Course.objects.filter(department=department, semester=sem)
    else:
        # Get batches where this teacher is assigned for this semester
        teacher_batches = TeacherBatch.objects.filter(teacher=teacher, batch__course__semester=sem)
        courses = Course.objects.filter(
            id__in=teacher_batches.values_list('batch__course', flat=True),
            semester=sem
        ).distinct()

    teachers = Teacher.objects.filter(department=department, user__is_active=True)

    # List of students for each course (only for HoD)
    course_students = None
    if user.groups.filter(name='HoD').exists():
        course_students = {}
        for course in courses:
            # Get all batches for this course and semester
            batches = Batch.objects.filter(course=course, course__semester=sem)
            # Get all students in these batches
            students = Student.objects.filter(
                id__in=StudentBatch.objects.filter(batch__in=batches).values_list('student', flat=True)
            ).distinct()
            course_students[course] = students

    return render(request, 'attendance/course_list.html', {
        'teachers': teachers,
        'department': department,
        'courses': courses,
        'course_students': course_students,
        'selected_semester': sem,
    })

@login_required
def get_assigned_batch_students(request, batch_id):
    students = StudentBatch.objects.filter(batch_id=batch_id).select_related('student__programme')

    students_data = [{
        'id': sb.student.id,
        'b_id': batch_id,
        'name': sb.student.name,
        'university_register_number': sb.student.university_register_number,
        'programme': sb.student.programme.name
    } for sb in students]

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
            saved_course = form.save()
            # Redirect to the course list of the saved course's semester
            return redirect('course_list', saved_course.semester)
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
            saved_course = form.save()
            # Redirect to the course list of the saved course's semester
            return redirect('course_list', saved_course.semester)
    else:
        form = CourseForm(instance=course, logged_in_teacher=logged_in_teacher)
    return render(request, 'attendance/edit_course.html', {'form': form, 'course': course})

@login_required
def create_batch(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if request.method == 'POST':
        form = BatchForm(request.POST)
        if form.is_valid():
            batch = form.save(commit=False)
            batch.course = course
            # Set academic_year automatically
            batch.academic_year = calculate_year(date.today())
            batch.save()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
            return redirect('course_list', course.semester)
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                html = render_to_string('attendance/partial_create_batch_form.html', {'form': form, 'course': course}, request)
                return JsonResponse({'success': False, 'form_html': html})
    else:
        form = BatchForm()
    return render(request, 'attendance/create_batch.html', {'form': form, 'course': course})

@login_required
def create_batch_form(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    form = BatchForm()
    html = render_to_string('attendance/partial_create_batch_form.html', {'form': form, 'course': course}, request)
    return HttpResponse(html)

@login_required
@user_passes_test(HoD_group_required)
def toggle_batch_active(request, batch_id):
    batch = get_object_or_404(Batch, id=batch_id)
    batch.active = not batch.active
    batch.save()
    status = "activated" if batch.active else "deactivated"
    messages.success(request, f"Batch {batch} has been {status}.")
    # Redirect back to the course list or wherever you want
    return redirect(request.META.get('HTTP_REFERER', reverse('course_list', args=[batch.course.semester])))


@login_required
@user_passes_test(HoD_group_required)
def teacher_batch_assign(request, sem):
    teacher = get_user_teacher(request.user)
    department = teacher.department

    # Get all active batches under the department's courses for the given semester
    batches = Batch.objects.filter(
        course__department=department,
        course__semester=sem,
        active=True
    ).select_related('course')

    # Prefetch and group assigned teachers per batch in one query
    teacher_batches = TeacherBatch.objects.filter(batch__in=batches).select_related('teacher__user')
    teachers_by_batch = defaultdict(list)
    for tb in teacher_batches:
        teachers_by_batch[tb.batch_id].append(tb.teacher.user.first_name)

    # Map each batch to its assigned teachers
    batch_teacher_map = {}
    for batch in batches:
        batch_teacher_map[batch] = teachers_by_batch[batch.id]

    # Get all teachers in the department for dropdown
    teachers = Teacher.objects.filter(department=department, user__is_active=True)

    return render(request, 'attendance/teacher_batch_form.html', {
        'batches': batches,
        'department': department,
        'batch_teacher_map': batch_teacher_map,
        'teachers': teachers,
        'selected_semester': sem,
    })


@login_required
def get_assigned_teachers_for_batch(request, batch_id):
    try:
        batch = Batch.objects.get(id=batch_id)
        teacher_batches = TeacherBatch.objects.filter(batch=batch)
        teachers = [{"id": tb.teacher.id, "first_name": tb.teacher.user.first_name} for tb in teacher_batches]
        return JsonResponse({"teachers": teachers})
    except Batch.DoesNotExist:
        return JsonResponse({"error": "Batch not found"}, status=404)


@login_required
@user_passes_test(HoD_group_required)
def assign_teachers_to_batch(request):
    if request.method == 'POST':
        batch_id = request.POST.get('batch_id')
        teacher_ids = request.POST.getlist('teachers')  # List of selected teacher IDs

        batch = get_object_or_404(Batch, id=batch_id)

        for teacher_id in teacher_ids:
            teacher = get_object_or_404(Teacher, id=teacher_id)

            # Check for existing assignment
            if TeacherBatch.objects.filter(batch=batch, teacher=teacher).exists():
                messages.warning(request, f"Teacher {teacher.user.get_full_name()} is already assigned to batch {batch.academic_year}-{batch.part}.")
            else:
                TeacherBatch.objects.create(batch=batch, teacher=teacher)

        return redirect(reverse('teacher_batch_assign', args=[batch.course.semester])) # Redirect to the batch-assignment page


@login_required
@user_passes_test(HoD_group_required)
def remove_teachers_from_batch(request):
    if request.method == 'POST':
        batch_id = request.POST.get('batch_id')
        teacher_ids = request.POST.getlist('teachers_to_remove')

        try:
            batch = Batch.objects.get(id=batch_id)
            for teacher_id in teacher_ids:
                try:
                    teacher_batch = TeacherBatch.objects.get(batch=batch, teacher_id=teacher_id)
                    teacher_batch.delete()
                except TeacherBatch.DoesNotExist:
                    messages.warning(request, f"Teacher ID {teacher_id} not assigned to batch {batch.academic_year}-{batch.part}.")

            messages.success(request, "Teachers removed successfully.")

        except Batch.DoesNotExist:
            raise Http404("Batch not found.")


        return redirect(reverse('teacher_batch_assign', args=[batch.course.semester]))


    return redirect(reverse('teacher_batch_assign', args=[batch.course.semester]))


@login_required
@user_passes_test(HoD_group_required)
def student_batch_assign(request, sem):
    teacher = get_user_teacher(request.user)
    department = teacher.department

    students = Student.objects.filter(
        programme__department=department, 
        current_semester=sem
    ).order_by('university_register_number')

    batch_query = Batch.objects.filter(
        active=True, 
        course__semester=sem
    ).select_related('course')
    all_batches = batch_query.order_by('course__department__name', 'course__code')

    student_batches = StudentBatch.objects.select_related('batch__course', 'student').filter(student__in=students)
    student_batches_map = {}
    for sb in student_batches:
        student_batches_map.setdefault(sb.student.id, []).append(sb)

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'bulk_assign':
            student_ids = request.POST.getlist('selected_students')
            batch_id = request.POST.get('bulk_batch')
            if not student_ids:
                messages.warning(request, "No students selected for bulk assignment.")
            elif not batch_id:
                messages.warning(request, "No course batch selected for bulk assignment.")
            else:
                batch = get_object_or_404(Batch, id=batch_id)
                if str(batch.course.semester) != str(sem):
                    messages.error(request, "Selected batch does not belong to this semester.")
                else:
                    assigned_count = 0
                    for s_id in student_ids:
                        _, created = StudentBatch.objects.get_or_create(student_id=s_id, batch=batch)
                        if created:
                            assigned_count += 1
                    messages.success(request, f"Bulk assigned {batch.course.name} to {assigned_count} students.")
            return redirect('student_batch_assign', sem=sem)

        elif action == 'bulk_remove':
            student_ids = request.POST.getlist('selected_students')
            batch_id = request.POST.get('bulk_batch')
            if not student_ids:
                messages.warning(request, "No students selected for bulk removal.")
            elif not batch_id:
                messages.warning(request, "No course batch selected for bulk removal.")
            else:
                batch = get_object_or_404(Batch, id=batch_id)
                deleted_count, _ = StudentBatch.objects.filter(student_id__in=student_ids, batch=batch).delete()
                messages.success(request, f"Bulk removed {batch.course.name} from {deleted_count} students.")
            return redirect('student_batch_assign', sem=sem)

        elif action == 'assign':
            student_id = request.POST.get('student_id')
            student = get_object_or_404(Student, id=student_id)

            # Ensure student semester matches the parameter
            if str(student.current_semester) != str(sem):
                messages.error(request, "Student semester mismatch.")
                return redirect('student_batch_assign', sem=sem)

            selected_batch_ids = request.POST.getlist('batches')

            if selected_batch_ids:
                # Prefetch all selected batches at once to avoid query in loop
                batches = Batch.objects.filter(id__in=selected_batch_ids).select_related('course')
                batch_map = {str(b.id): b for b in batches}
                
                assigned = False
                for batch_id in selected_batch_ids:
                    batch = batch_map.get(str(batch_id))
                    if not batch:
                        continue
                    # Ensure batch's course semester matches the parameter
                    if str(batch.course.semester) != str(sem):
                        messages.warning(request, f"Batch {batch} does not belong to semester {sem}. Skipped.")
                        continue
                    StudentBatch.objects.get_or_create(student=student, batch=batch)
                    assigned = True
                if assigned:
                    messages.success(request, f"Batches assigned to {student.name}.")
                else:
                    messages.warning(request, "No valid batches assigned.")
            else:
                messages.warning(request, "No batches selected.")
            return redirect(reverse('student_batch_assign', args=[sem]) + f"#student-row-{student_id}")

    return render(request, 'attendance/student_batch_form.html', {
        'students': students,
        'all_batches': all_batches,
        'student_batches_map': student_batches_map,
        'selected_semester': sem,
    })


@login_required
def get_assigned_batches(request, student_id):
    try:
        student = Student.objects.get(id=student_id)
    except Student.DoesNotExist:
        raise Http404("Student not found")
    # THIS LINE IS CRUCIAL:
    student_batches = StudentBatch.objects.filter(
        student=student,
        batch__course__semester=student.current_semester
    ).select_related('batch__course')
    batch_data = []
    for sb in student_batches:
        batch = sb.batch
        course = batch.course
        batch_data.append({
            'id': batch.id,
            'code': course.code,
            'course_name': course.name,
            'academic_year': batch.academic_year,
            'part': batch.part,
        })
    return JsonResponse({'batches': batch_data})

@login_required
@user_passes_test(HoD_group_required)
def remove_student_batches(request):
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        batch_ids = request.POST.getlist('batches_to_remove')

        student = get_object_or_404(Student, id=student_id)
        removed_count, _ = StudentBatch.objects.filter(student=student, batch__id__in=batch_ids).delete()

        messages.success(request, f"Removed {removed_count} batches from {student.name}.")
        return redirect(reverse('student_batch_assign', args=[student.current_semester]) + f"#student-row-{student_id}")

    messages.error(request, "Invalid request.")
    return redirect('student_batch_assign', sem=1)



@login_required
def take_attendance(request, batch_id):
    teacher = request.user.teacher
    batch = get_object_or_404(Batch, id=batch_id)
    course = batch.course

    # Authorization: check if teacher is assigned to this course
    if not TeacherBatch.objects.filter(teacher=teacher, batch=batch).exists():
        messages.error(request, "You are not authorized to take attendance for this course.")
        return redirect('course_list', sem=course.semester)  # or your course list URL

    # Get students assigned to this batch
    student_batches = StudentBatch.objects.filter(batch=batch)
    students = [sb.student for sb in student_batches]

    # Sorting
    sort_by = request.GET.get('sort_by', 'university_register_number')

    if sort_by == "roll_no":
        def get_roll_key(student):
            roll = student.roll_number
            if not roll:
                return float('inf')
            try:
                return int(roll)
            except ValueError:
                import re
                digits = re.findall(r'\d+', roll)
                return int(digits[0]) if digits else float('inf')

        def get_group_key(student):
            reg = student.university_register_number
            if not reg:
                return "ZZZ"
            import re
            match = re.match(r'^NA\d{2}([A-Z]+)\d+$', reg)
            return match.group(1) if match else "ZZZ"

        students.sort(key=lambda s: (get_group_key(s), get_roll_key(s), s.university_register_number or "ZZZ"))
    else:
        students.sort(key=lambda s: s.university_register_number or "ZZZ")

    # Get all unique programmes of the students in the batch
    programmes = sorted(list(set(student.programme for student in students)), key=lambda p: p.name)

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
                hour_date_batch = HourDateBatch.objects.create(
                    batch=batch,
                    teacher=teacher,
                    date=attendance_date,
                    hour=int(hour),
                )
                messages.success(request, f"Attendance successfully recorded for Hour {hour}")
            except IntegrityError:
                existing_record = HourDateBatch.objects.get(batch=batch, date=attendance_date, hour=int(hour))
                teacher_full_name = f"{existing_record.teacher.user.first_name} {existing_record.teacher.user.last_name}"
                teacher_phone = existing_record.teacher.phone_number
                messages.warning(request, f"Attendance already taken by {teacher_full_name} ({teacher_phone}) in Hour {hour} on {attendance_date}")
                continue

            for student in students:
                if f'students_{student.id}' in request.POST:
                    AbsentDetails.objects.update_or_create(
                        hour_date_batch=hour_date_batch,
                        student=student,
                        defaults={'status': False}
                    )

        return redirect('course_list', sem=course.semester)

    return render(request, 'attendance/take_attendance.html', {
        'course': course,
        'batch': batch,
        'students': students,
        'today': date.today(),
        'hours': range(1, 6),
        'sort_by': sort_by,
        'programmes': programmes,
    })





@login_required
def teacher_attendance_list(request):
    # Ensure the logged-in user is a teacher
    if not hasattr(request.user, 'teacher'):
        messages.error(request, "You are not authorized to access this page.")
        return redirect('home')

    teacher = request.user.teacher  # Get the Teacher instance linked to the user
    attendance_records = HourDateBatch.objects.filter(teacher=teacher).order_by('-date')

    context = {
        'attendance_records': attendance_records,
    }
    return render(request, 'attendance/teacher_attendance_list.html', context)

@login_required
def teacher_attendance_list(request, sem):
    # Ensure the logged-in user is a teacher
    if not hasattr(request.user, 'teacher'):
        messages.error(request, "You are not authorized to access this page.")
        return redirect('home')

    teacher = request.user.teacher

    # Get all active batches for this teacher in the selected semester
    batches = Batch.objects.filter(
        course__semester=sem,
        teacherbatch__teacher=teacher,
        active=True
    ).distinct()

    # Get all attendance records for these batches
    attendance_records = HourDateBatch.objects.filter(
        teacher=teacher,
        batch__in=batches
    ).order_by('-date')

    context = {
        'attendance_records': attendance_records,
        'batches': batches,
        'selected_semester': sem,
    }
    return render(request, 'attendance/teacher_attendance_list.html', context)


@login_required
def edit_attendance(request, record_id):
    # Ensure the logged-in user is a teacher
    if not hasattr(request.user, 'teacher'):
        messages.error(request, "You are not authorized to access this page.")
        return redirect('teacher_attendance_list', sem=1)  # or your default semester

    # Get the attendance record (HourDateBatch) by ID
    attendance_record = get_object_or_404(HourDateBatch, id=record_id)

    # Ensure the logged-in teacher is the one who took the attendance
    if attendance_record.teacher != request.user.teacher:
        messages.error(request, "You are not authorized to edit this attendance.")
        return redirect('teacher_attendance_list', sem=attendance_record.batch.course.semester)

    # Get all students assigned to this batch
    student_batches = StudentBatch.objects.filter(batch=attendance_record.batch).select_related('student')
    students = [sb.student for sb in student_batches]

    # Sorting logic (optional, you can keep or remove)
    sort_by = request.GET.get('sort_by', 'university_register_number')

    if sort_by == "roll_no":
        students.sort(key=lambda student: student.roll_number or "")  # fixed field name
    else:
        students.sort(key=lambda student: student.university_register_number or "")

    # Get existing absences for this attendance record
    existing_absences = AbsentDetails.objects.filter(hour_date_batch=attendance_record)
    absent_students = {absence.student.id for absence in existing_absences if not absence.status}

    if request.method == 'POST':
        # Update absences based on the submitted form
        selected_absent_ids = {
            int(key.split('_')[1])
            for key in request.POST.keys()
            if key.startswith('students_')
        }

        # Update or delete AbsentDetails as needed
        for student in students:
            if student.id in selected_absent_ids:
                AbsentDetails.objects.update_or_create(
                    hour_date_batch=attendance_record,
                    student=student,
                    defaults={'status': False}  # Mark as absent
                )
            else:
                # Mark as present (status=True) or delete absent record
                AbsentDetails.objects.update_or_create(
                    hour_date_batch=attendance_record,
                    student=student,
                    defaults={'status': True}  # Mark as present
                )
                GraceAttendance.objects.filter(student=student, hour_date_batch=attendance_record).delete()

        messages.success(request, "Attendance updated successfully.")
        return HttpResponseRedirect(reverse('teacher_attendance_list', args=[attendance_record.batch.course.semester]))

    context = {
        'attendance_record': attendance_record,
        'students': students,
        'absent_students': absent_students,
    }
    return render(request, 'attendance/edit_attendance.html', context)

@login_required
def remove_attendance(request, record_id):
    if request.method == 'POST':
        # Get the attendance record for this teacher
        record = get_object_or_404(HourDateBatch, id=record_id, teacher=request.user.teacher)
        # Store the semester for redirect
        sem = record.batch.course.semester
        record.delete()
        messages.success(request, "Attendance record removed successfully!")
        return redirect('teacher_attendance_list', sem=sem)
    else:
        messages.error(request, "Invalid request method. Deletion must be done via POST.")
        return redirect('teacher_attendance_list', sem=1)






@login_required
def attendance_report(request, batch_id):
    batch = get_object_or_404(Batch, id=batch_id)
    date_time = datetime.now()

    # All HourDateBatch entries for this batch
    hour_date_batches = HourDateBatch.objects.filter(batch=batch)
    total_hours = hour_date_batches.count()

    # Students assigned to this batch
    student_ids = StudentBatch.objects.filter(batch=batch).values_list('student_id', flat=True)
    students = Student.objects.filter(id__in=student_ids).order_by('university_register_number')

    # All AbsentDetails related to this batch
    attendance_records = AbsentDetails.objects.filter(hour_date_batch__in=hour_date_batches)
    attendance_lookup = {(record.student_id, record.hour_date_batch_id): record.status for record in attendance_records}

    # Fetch all GraceAttendance records for this batch
    grace_records = GraceAttendance.objects.filter(hour_date_batch__in=hour_date_batches)
    grace_lookup = defaultdict(set)
    for record in grace_records:
        grace_lookup[record.student_id].add(record.hour_date_batch_id)

    attendance_data = []

    for student in students:
        total_present = 0
        grace_hours = 0
        student_grace_ids = grace_lookup.get(student.id, set())

        for hour in hour_date_batches:
            status = attendance_lookup.get((student.id, hour.id), True)  # Default to present (True)
            if status:
                total_present += 1
            elif hour.id in student_grace_ids:
                grace_hours += 1

        total_absent = total_hours - total_present - grace_hours
        effective_present = total_present + grace_hours
        attendance_percentage = (total_present / total_hours) * 100 if total_hours else 0
        attendance_with_grace = (effective_present / total_hours) * 100 if total_hours else 0

        attendance_data.append({
            "student": student,
            "total_present": total_present,
            "grace_hours": grace_hours,
            "total_absent": total_absent,
            "attendance_percentage": round(attendance_percentage, 2),
            "attendance_with_grace": round(attendance_with_grace, 2),
        })

    context = {
        "batch": batch,
        "total_hours": total_hours,
        "attendance_data": attendance_data,
        "date_time": date_time,
    }

    return render(request, 'attendance/report.html', context)


def extract_admission_year(reg_no):
    try:
        year_suffix = reg_no[2:4]
        year = int(year_suffix)
        if year < 30:  # Assuming you're only dealing with 2000s admissions
            return 2000 + year
        else:
            return 1900 + year  # Just in case you have very old data
    except (ValueError, TypeError, IndexError):
        return date.today().year - 3  # Safe fallback estimate


@login_required
def compact_attendance_report(request, batch_id):
    batch = get_object_or_404(Batch, id=batch_id)
    course = batch.course
    semester = course.semester
    department = course.department

    # Fetch all students for the batch
    students = Student.objects.filter(
        id__in=StudentBatch.objects.filter(batch=batch).values_list('student_id', flat=True)
    ).order_by('university_register_number')

    reg_no = students.first().university_register_number if students else ""
    admission_year = extract_admission_year(reg_no) if reg_no else ""

    # Get all HourDateBatch entries for this batch
    hour_slots = HourDateBatch.objects.filter(batch=batch).order_by('date', 'hour')

    # Build dictionary of all teachers for entire batch (all sessions)
    all_teachers = {}
    for hdb in hour_slots:
        if hdb.teacher:
            acronym = hdb.teacher.acronym
            fullname = hdb.teacher.user.get_full_name() or hdb.teacher.user.username
            all_teachers[acronym] = fullname

    # Preprocess HourDateBatch to detect date changes & include teacher acronym for header
    header_order = []
    last_date = None
    for hdb in hour_slots:
        date_str = hdb.date.strftime("%d-%m-%Y")
        is_new_date = date_str != last_date
        teacher_acronym = hdb.teacher.acronym if hdb.teacher else ""
        header_order.append((date_str, hdb.hour, hdb.id, is_new_date, teacher_acronym))
        last_date = date_str

    # Paginate header_order (6 columns per page)
    paginator = Paginator(header_order, 6)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    # Pad columns BEFORE passing to template to always show 6 columns
    required_columns = 6
    current_columns = len(page_obj.object_list)
    visible_columns = list(page_obj.object_list)  # Make a copy
    if current_columns < required_columns:
        visible_columns += [(None, None, None, False, "")] * (required_columns - current_columns)

    # Fetch only attendance for visible columns
    visible_hdb_ids = [hdb_id for _, _, hdb_id, _, _ in visible_columns if hdb_id]
    attendance_lookup = AbsentDetails.objects.filter(
        hour_date_batch_id__in=visible_hdb_ids
    ).values_list('student_id', 'hour_date_batch_id', 'status')

    # Fetch GraceAttendance records for visible columns
    grace_lookup = GraceAttendance.objects.filter(
        hour_date_batch_id__in=visible_hdb_ids
    ).values_list('student_id', 'hour_date_batch_id', 'reason')
    grace_map = {(student_id, hdb_id): reason for student_id, hdb_id, reason in grace_lookup}

    # Build attendance map: True/Present ("X"), False/Absent ("A"), or Grace (reason string)
    attendance_map = defaultdict(lambda: "X")  # Default to Present ("X")
    for student_id, hdb_id, status in attendance_lookup:
        if not status:
            grace_reason = grace_map.get((student_id, hdb_id))
            if grace_reason:
                attendance_map[(student_id, hdb_id)] = grace_reason
            else:
                attendance_map[(student_id, hdb_id)] = "A"
        else:
            attendance_map[(student_id, hdb_id)] = "X"


    # Build report data rows
    report_data = []
    for idx, student in enumerate(students, 1):
        row = {
            "sl_no": idx,
            "reg_no": student.university_register_number,
            "roll_no": student.roll_number,
            "name": student.name,
            "attendance": []
        }
        for date_str, hour, hdb_id, is_new_date, _ in visible_columns:
            if hdb_id is not None:
                mark = attendance_map[(student.id, hdb_id)]
            else:
                mark = ""
            row["attendance"].append((mark, is_new_date))
        report_data.append(row)

    # Prepare list of teachers info with full name and acronym for entire batch
    teachers_info = [f"{fullname} ({acronym})" for acronym, fullname in all_teachers.items()]

    context = {
        "batch": batch,
        "course": course,
        "page_obj": page_obj,
        "visible_columns": visible_columns,  # padded columns with teacher acronym
        "report_data": report_data,
        "total_hours": hour_slots.count(),
        "date_time": datetime.now(),
        "department": department,
        "semester": semester,
        "admission_year": admission_year,
        "teachers_info": teachers_info,
    }

    return render(request, "attendance/compact_report.html", context)




from django.http import HttpResponse

@login_required





@login_required
@user_passes_test(HoD_group_required)
def student_individual_report(request, student_id):
    # 1. Get student or 404
    student = get_object_or_404(Student, id=student_id)

    # 2. Get all semesters attended by the student
    semesters = (
        StudentBatch.objects
        .filter(student=student)
        .values_list('batch__course__semester', flat=True)
        .distinct()
        .order_by('batch__course__semester')
    )
    semesters = [str(s) for s in semesters]

    # 3. Get selected semester from GET, default to current semester
    selected_semester = request.GET.get('semester', str(student.current_semester))
    if selected_semester not in semesters:
        selected_semester = semesters[-1] if semesters else str(student.current_semester)

    # 4. Get all batches for the selected semester
    student_batches = (
        StudentBatch.objects
        .filter(student=student, batch__course__semester=selected_semester)
        .select_related('batch__course')
    )
    batches = [sb.batch for sb in student_batches]
    batches.sort(key=lambda batch: (batch.course.code, batch.academic_year, batch.part))

    # 5. Prepare attendance data
    attendance_data = []
    total_hours = total_present = total_absent = total_grace = 0

    for batch in batches:
        batch_sessions = (
            HourDateBatch.objects
            .filter(batch=batch)
            .order_by('date', 'hour')
        )
        batch_total_hours = batch_total_present = batch_total_absent = batch_total_grace = 0
        attendance_per_day = []

        # Optimize: fetch all AbsentDetails for this student and these sessions in one query
        absent_records = AbsentDetails.objects.filter(
            student=student,
            hour_date_batch__in=batch_sessions
        )
        attendance_lookup = {record.hour_date_batch_id: record.status for record in absent_records}

        # Fetch GraceAttendance records for this student and these sessions
        grace_records = GraceAttendance.objects.filter(
            student=student,
            hour_date_batch__in=batch_sessions
        )
        grace_lookup = {record.hour_date_batch_id: record.reason for record in grace_records}

        for session in batch_sessions:
            status_bool = attendance_lookup.get(session.id, True)  # Default to present (True)
            status = 'Present' if status_bool else 'Absent'

            grace_reason = grace_lookup.get(session.id)
            is_grace = (status == 'Absent' and grace_reason is not None)

            if status == 'Present':
                batch_total_present += 1
            elif is_grace:
                batch_total_grace += 1
            else:
                batch_total_absent += 1

            attendance_per_day.append({
                'date': session.date,
                'hour': session.hour,
                'status': 'Grace' if is_grace else status,
                'grace_reason': grace_reason if is_grace else None,
            })
            batch_total_hours += 1

        batch_effective_present = batch_total_present + batch_total_grace
        physical_percentage = (
            round((batch_total_present / batch_total_hours) * 100, 2)
            if batch_total_hours > 0 else 0
        )
        effective_percentage = (
            round((batch_effective_present / batch_total_hours) * 100, 2)
            if batch_total_hours > 0 else 0
        )

        attendance_data.append({
            'batch': batch,
            'course': batch.course,
            'attendance_per_day': attendance_per_day,
            'total_hours': batch_total_hours,
            'total_present': batch_total_present,
            'total_grace': batch_total_grace,
            'total_absent': batch_total_absent,
            'physical_percentage': physical_percentage,
            'effective_percentage': effective_percentage,
        })

        total_hours += batch_total_hours
        total_present += batch_total_present
        total_grace += batch_total_grace
        total_absent += batch_total_absent

    total_effective_present = total_present + total_grace
    total_effective_absent = total_hours - total_effective_present

    overall_physical_percentage = (
        round((total_present / total_hours) * 100, 2) if total_hours > 0 else 0
    )
    overall_effective_percentage = (
        round((total_effective_present / total_hours) * 100, 2) if total_hours > 0 else 0
    )

    is_hod = request.user.groups.filter(name='HoD').exists() or request.user.is_superuser

    context = {
        'student': student,
        'attendance_data': attendance_data,
        'total_hours': total_hours,
        'total_present': total_present,
        'total_grace': total_grace,
        'total_absent': total_absent,
        'total_effective_present': total_effective_present,
        'total_effective_absent': total_effective_absent,
        'overall_physical_percentage': overall_physical_percentage,
        'overall_effective_percentage': overall_effective_percentage,
        'semesters_history': semesters,
        'selected_semester': selected_semester,
        'is_hod': is_hod,
    }
    return render(request, 'attendance/student_report.html', context)


@login_required
@user_passes_test(HoD_group_required)
def manage_grace_attendance(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    
    # Get semester from query params (default to student's current semester)
    selected_semester = request.GET.get('semester', str(student.current_semester))
    
    # Gather semesters history
    student_batches_history = StudentBatch.objects.filter(student=student).select_related('batch__course')
    semesters = sorted(list(set(str(sb.batch.course.semester) for sb in student_batches_history)))
    if selected_semester not in semesters:
        selected_semester = semesters[-1] if semesters else str(student.current_semester)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        hour_date_batch_id = request.POST.get('hour_date_batch_id')
        hour_date_batch = get_object_or_404(HourDateBatch, id=hour_date_batch_id)
        
        if action == 'grant':
            reason = request.POST.get('reason', '').strip()
            if not reason:
                messages.error(request, "A reason must be provided to grant grace attendance.")
            else:
                # Ensure the student was actually marked absent
                is_absent = AbsentDetails.objects.filter(student=student, hour_date_batch=hour_date_batch, status=False).exists()
                if not is_absent:
                    messages.error(request, "Grace can only be granted for hours where the student was marked absent.")
                else:
                    GraceAttendance.objects.update_or_create(
                        student=student,
                        hour_date_batch=hour_date_batch,
                        defaults={'reason': reason}
                    )
                    messages.success(request, f"Grace attendance granted for {hour_date_batch.date} H{hour_date_batch.hour} ({reason}).")
        
        elif action == 'revoke':
            deleted_count, _ = GraceAttendance.objects.filter(student=student, hour_date_batch=hour_date_batch).delete()
            if deleted_count > 0:
                messages.success(request, f"Grace attendance revoked for {hour_date_batch.date} H{hour_date_batch.hour}.")
        
        return redirect(reverse('manage_grace_attendance', args=[student_id]) + f"?semester={selected_semester}")
        
    # GET request: load absences and grace
    # Fetch all absences for this student in the selected semester
    absent_records = AbsentDetails.objects.filter(
        student=student,
        status=False,
        hour_date_batch__batch__course__semester=selected_semester
    ).select_related('hour_date_batch__batch__course', 'hour_date_batch__teacher__user').order_by('hour_date_batch__date', 'hour_date_batch__hour')
    
    # Prefetch existing grace records
    grace_records = GraceAttendance.objects.filter(
        student=student,
        hour_date_batch__batch__course__semester=selected_semester
    )
    grace_map = {gr.hour_date_batch_id: gr.reason for gr in grace_records}
    
    absences_list = []
    for record in absent_records:
        hdb = record.hour_date_batch
        grace_reason = grace_map.get(hdb.id)
        absences_list.append({
            'hour_date_batch': hdb,
            'course': hdb.batch.course,
            'teacher': hdb.teacher,
            'is_grace': grace_reason is not None,
            'grace_reason': grace_reason,
        })
        
    context = {
        'student': student,
        'absences': absences_list,
        'selected_semester': selected_semester,
        'semesters_history': semesters,
    }
    return render(request, 'attendance/grace_assignment.html', context)


@login_required
@user_passes_test(HoD_group_required)
def department_report(request, department_id):
    # Fetch the department
    department = get_object_or_404(Department, id=department_id)
    
    # Get all active semesters for this department's students to find a default
    active_semesters = (
        Student.objects
        .filter(programme__department=department, current_semester__in=range(1, 9))
        .values_list('current_semester', flat=True)
        .distinct()
        .order_by('current_semester')
    )
    
    # Get selected semester from query params
    selected_sem_str = request.GET.get('semester')
    if selected_sem_str is not None:
        try:
            selected_semester = int(selected_sem_str)
        except ValueError:
            selected_semester = active_semesters[0] if active_semesters else 1
    else:
        selected_semester = active_semesters[0] if active_semesters else 1

    # Get students of the selected semester in the department, ordered by register number
    students = Student.objects.filter(
        programme__department=department,
        current_semester=selected_semester
    ).order_by('university_register_number')
    
    # Calculate total hours taken for the department for the selected semester
    total_hours_taken = HourDateBatch.objects.filter(
        batch__course__department=department,
        batch__course__semester=str(selected_semester)
    ).count()

    # 1. Fetch batches for the department courses of the selected semester
    batches = Batch.objects.filter(
        course__department=department,
        course__semester=str(selected_semester)
    )
    
    # 2. Fetch all HourDateBatch sessions for these batches
    sessions = HourDateBatch.objects.filter(batch__in=batches).order_by('date')
    
    # Group sessions by batch_id
    sessions_by_batch = defaultdict(list)
    for session in sessions:
        sessions_by_batch[session.batch_id].append(session)
        
    # 3. Fetch all StudentBatch mappings for these students
    student_batches = StudentBatch.objects.filter(student__in=students)
    batches_by_student = defaultdict(list)
    for sb in student_batches:
        batches_by_student[sb.student_id].append(sb.batch_id)
        
    # 4. Fetch all AbsentDetails for these sessions and students
    attendance_records = AbsentDetails.objects.filter(
        student__in=students,
        hour_date_batch__in=sessions
    )
    # Lookup dictionary: (student_id, session_id) -> status
    attendance_lookup = {
        (record.student_id, record.hour_date_batch_id): record.status 
        for record in attendance_records
    }

    # 5. Fetch all GraceAttendance records for these sessions and students in bulk
    grace_records = GraceAttendance.objects.filter(
        student__in=students,
        hour_date_batch__in=sessions
    )
    grace_lookup = {
        (record.student_id, record.hour_date_batch_id)
        for record in grace_records
    }

    # Prepare the data for each student
    student_data = []

    # Iterate over each student in the department
    for student in students:
        total_present = 0
        total_hours = 0
        total_absent = 0
        total_grace = 0

        # Get batch ids for this student
        student_batch_ids = batches_by_student[student.id]
        
        # Collect sessions for all batches the student is enrolled in
        student_sessions = []
        for b_id in student_batch_ids:
            student_sessions.extend(sessions_by_batch[b_id])
            
        total_hours = len(student_sessions)

        # For all those sessions, check attendance
        for session in student_sessions:
            status = attendance_lookup.get((student.id, session.id), True) # Default to present (True)
            if status:
                total_present += 1
            elif (student.id, session.id) in grace_lookup:
                total_grace += 1
            else:
                total_absent += 1

        effective_present = total_present + total_grace
        # Calculate attendance percentage for this student
        attendance_percentage = (effective_present / total_hours * 100) if total_hours > 0 else 0

        # Append the student's data to the list
        student_data.append({
            'student': student,
            'total_present': total_present,
            'total_grace': total_grace,
            'total_absent': total_absent,
            'attendance_percentage': round(attendance_percentage, 2),
            'total_hours_taken': total_hours,
        })
    
    # Prepare context for rendering
    has_alumni = Student.objects.filter(programme__department=department, current_semester=0).exists()
    context = {
        'department': department,
        'students': student_data,
        'total_hours_taken': total_hours_taken,
        'selected_semester': selected_semester,
        'available_semesters': list(active_semesters),
        'has_alumni': has_alumni,
        'is_hod': request.user.groups.filter(name='HoD').exists()
    }

    return render(request, 'attendance/department.html', context)


from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Min
from django.shortcuts import render

@login_required
@user_passes_test(lambda u: u.is_superuser or u.groups.filter(name='HoD').exists())
def programme_courses_view(request):
    semester = request.GET.get("semester")  # e.g., ?semester=3

    programmes = Programme.objects.all()
    programme_data = []

    for programme in programmes:
        # 🔹 Only students in this programme (and semester if provided)
        students = Student.objects.filter(programme=programme)
        if semester:
            students = students.filter(current_semester=semester)

        total_students = students.count()
        student_ids = students.values_list('id', flat=True)

        # 🔹 Get batches linked to these students
        batches = Batch.objects.filter(
            id__in=StudentBatch.objects.filter(
                student__in=student_ids
            ).values_list('batch', flat=True)
        )

        if semester:
            batches = batches.filter(course__semester=semester)

        # 🔹 Get distinct courses (deduplicate by code)
        unique_courses = (
            Course.objects
            .filter(batches__in=batches)
            .values('code')
            .annotate(id=Min('id'))
        )
        courses = Course.objects.filter(
            id__in=[entry['id'] for entry in unique_courses]
        ).order_by('code')

        if semester:
            courses = courses.filter(semester=semester)

        total_courses_required = total_students * 6 if total_students else 0

        # 🔹 For each student, count unique courses by code
        student_course_counts = (
            StudentBatch.objects
            .filter(student__in=student_ids, batch__in=batches)
            .values('student', 'batch__course__code')
            .distinct()
            .values('student')
            .annotate(unique_courses=Count('batch__course__code', distinct=True))
        )
        current_courses_count = sum(
            entry['unique_courses'] for entry in student_course_counts
        )

        difference = total_courses_required - current_courses_count

        programme_data.append({
            'programme': programme,
            'courses': courses,
            'total_students': total_students,
            'total_courses_required': total_courses_required,
            'current_courses_count': current_courses_count,
            'difference': difference,
        })

    active_semesters = (
        Student.objects
        .filter(current_semester__in=range(1, 9))
        .values_list('current_semester', flat=True)
        .distinct()
        .order_by('current_semester')
    )
    active_semesters = [str(sem) for sem in active_semesters]

    return render(request, 'attendance/programme_courses.html', {
        'programme_data': programme_data,
        'semester': semester,  # Pass selected semester to template
        'active_semesters': active_semesters,
    })


@login_required
@user_passes_test(is_superuser)
def admin_dashboard(request):
    return render(request, 'attendance/admin_page.html')

@login_required
@user_passes_test(is_superuser)
def admin_toggle_hod(request, teacher_id):
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect(request.META.get('HTTP_REFERER', 'admin_department_view'))

    teacher = get_object_or_404(Teacher, id=teacher_id)
    from django.contrib.auth.models import Group
    hod_group, created = Group.objects.get_or_create(name='HoD')
    
    if teacher.user.groups.filter(name='HoD').exists():
        teacher.user.groups.remove(hod_group)
        messages.success(request, f"Teacher {teacher.user.get_full_name() or teacher.user.username} has been removed from HOD group.")
    else:
        teacher.user.groups.add(hod_group)
        messages.success(request, f"Teacher {teacher.user.get_full_name() or teacher.user.username} has been promoted to HOD group.")
        
    return redirect(request.META.get('HTTP_REFERER', 'admin_department_view'))


@login_required
@user_passes_test(is_superuser)
def admin_bulk_deactivate_batches(request):
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('admin_dashboard')

    semester = request.POST.get('semester')
    if not semester:
        messages.error(request, "Please select a valid semester.")
        return redirect('admin_dashboard')

    # Deactivate batches for all courses of this semester college-wide
    batches_updated = Batch.objects.filter(
        course__semester=semester,
        active=True
    ).update(active=False)

    messages.success(request, f"Successfully deactivated {batches_updated} active course batches for Semester {semester} college-wide (across all departments).")
    return redirect('admin_dashboard')


@login_required
@user_passes_test(is_superuser)
def admin_department_view(request):
    departments = Department.objects.all()
    selected_department = None
    selected_semester = None
    students, teachers, courses = [], [], []
    course_batches = None

    if request.GET.get('department_id'):
        department_id = request.GET.get('department_id')
        selected_department = get_object_or_404(Department, id=department_id)
        
        sem_str = request.GET.get('semester')
        if sem_str and sem_str.isdigit():
            selected_semester = int(sem_str)

        students_query = Student.objects.filter(programme__department=selected_department)
        if selected_semester:
            students_query = students_query.filter(current_semester=selected_semester)
        students = students_query.order_by('university_register_number')

        teachers = Teacher.objects.filter(department=selected_department, user__is_active=True)

        courses_query = Course.objects.filter(department=selected_department)
        if selected_semester:
            courses_query = courses_query.filter(semester=selected_semester)
        courses = courses_query.order_by('code')

        course_batches = {}
        for course in courses:
            batches = Batch.objects.filter(course=course).order_by('academic_year', 'part')
            batches_list = []
            for batch in batches:
                batch_students = Student.objects.filter(
                    id__in=StudentBatch.objects.filter(batch=batch).values_list('student_id', flat=True)
                ).order_by('university_register_number')
                batches_list.append({
                    'batch': batch,
                    'students': batch_students
                })
            course_batches[course] = batches_list

    return render(request, 'attendance/admin_department_view.html', {
        'departments': departments,
        'selected_department': selected_department,
        'selected_semester': selected_semester,
        'students': students,
        'teachers': teachers,
        'courses': courses,
        'course_batches': course_batches,
    })


@login_required
@user_passes_test(HoD_group_required)
def create_tc(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    sem = student.current_semester

    if request.method == 'POST':
        form = TCForm(request.POST)
        if form.is_valid():
            tc = form.save(commit=False)
            tc.student = student
            tc.year_of_tc = date.today().year
            tc.save()

            # Set student semester to 0 after issuing TC
            student.current_semester = 0
            student.save()

            return redirect(reverse('student_list', args=[sem])) # Redirect to the student list after saving
    else:
        form = TCForm()

    return redirect(reverse('student_list', args=[sem]))


@login_required
@user_passes_test(HoD_group_required)
def get_tc_details(request, student_id):
    try:
        tc = TC.objects.filter(student_id=student_id).latest('year_of_tc')
        data = {
            'student': tc.student.name,
            'reason': tc.reason,
            'leaving_semester': tc.leaving_semester,
            'year_of_tc': tc.year_of_tc,
        }
        return JsonResponse({'status': 'success', 'data': data})
    except TC.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'No TC found for this student.'})




def create_transfer(request, student_id):
    student = get_object_or_404(Student, id=student_id)

    if request.method == "POST":
        dept_to = get_object_or_404(
            Department, id=request.POST["department_to"])
        prog_to = get_object_or_404(Programme, id=request.POST["programme_to"])
        semester_completed = int(request.POST["semester_completed"])
        remarks = request.POST.get("remarks", "")

        StudentTransfer.objects.create(
            student=student,
            department_from=student.programme.department,
            department_to=dept_to,
            semester_completed=semester_completed,
            remarks=remarks,
        )

        # Update student's current programme
        student.programme = prog_to
        student.save()

        messages.success(
            request, f"{student.name} transferred to {dept_to.name} - {prog_to.name}.")
        return redirect(reverse('student_list', args=[student.current_semester]))


def get_programmes_by_department(request, dept_id):
    programmes = Programme.objects.filter(
        department_id=dept_id).values("id", "name")
    return JsonResponse({"programmes": list(programmes)})