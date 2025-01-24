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
        form = StudentForm()
    return render(request, 'attendance/student_form.html', {'form': form})


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
