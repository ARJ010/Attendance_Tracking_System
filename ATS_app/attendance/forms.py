from django import forms
from .models import Student, Teacher, Course, StudentCourse, TeacherCourse, HourDateCourse, AbsentDetails
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

class UserForm(UserCreationForm):
    """Form for the User model."""
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']

class TeacherForm(forms.ModelForm):
    """Form for the Teacher model."""
    class Meta:
        model = Teacher
        fields = ['department', 'phone_number']

class TeacherRegistrationForm(forms.Form):
    """Combined form for User and Teacher."""
    user_form = UserForm(prefix='user')
    teacher_form = TeacherForm(prefix='teacher')

    def save(self, commit=True):
        """Save the User and Teacher model instances."""
        user_form = self.user_form
        teacher_form = self.teacher_form

        if user_form.is_valid() and teacher_form.is_valid():
            # Save the User instance
            user = user_form.save(commit=commit)

            # Save the Teacher instance
            teacher = teacher_form.save(commit=False)
            teacher.user = user
            if commit:
                teacher.save()

            return teacher
        return None



# Form for creating/updating a Student
class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['name', 'roll_number', 'university_register_number', 'admission_number', 'department', 'programme']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Enter full name'}),
            'roll_number': forms.TextInput(attrs={'placeholder': 'Enter roll number'}),
            'university_register_number': forms.TextInput(attrs={'placeholder': 'Enter university register number'}),
            'admission_number': forms.TextInput(attrs={'placeholder': 'Enter admission number'}),
            'department': forms.TextInput(attrs={'placeholder': 'Enter department'}),
            'programme': forms.TextInput(attrs={'placeholder': 'Enter programme'}),
        }



# Form for creating/updating a Course
class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['name', 'code', 'credits', 'year_offered']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Enter course name'}),
            'code': forms.TextInput(attrs={'placeholder': 'Enter course code'}),
            'credits': forms.NumberInput(attrs={'placeholder': 'Enter number of credits'}),
            'year_offered': forms.NumberInput(attrs={'placeholder': 'Enter year offered'}),
        }


# Form for assigning a Student to a Course
class StudentCourseForm(forms.ModelForm):
    class Meta:
        model = StudentCourse
        fields = ['student', 'course']
        widgets = {
            'student': forms.Select(attrs={'placeholder': 'Select student'}),
            'course': forms.Select(attrs={'placeholder': 'Select course'}),
        }


# Form for assigning a Teacher to a Course
class TeacherCourseForm(forms.ModelForm):
    class Meta:
        model = TeacherCourse
        fields = ['teacher', 'course']
        widgets = {
            'teacher': forms.Select(attrs={'placeholder': 'Select teacher'}),
            'course': forms.Select(attrs={'placeholder': 'Select course'}),
        }


# Form for managing Hour-Date-Course details
class HourDateCourseForm(forms.ModelForm):
    class Meta:
        model = HourDateCourse
        fields = ['teacher_course', 'date', 'hour']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'hour': forms.TextInput(attrs={'placeholder': 'Enter hour (e.g., 1st Hour, 2nd Hour)'}),
        }


# Form for managing Absent Details
class AbsentDetailsForm(forms.ModelForm):
    class Meta:
        model = AbsentDetails
        fields = ['hour_date_course', 'student', 'status']
        widgets = {
            'hour_date_course': forms.Select(attrs={'placeholder': 'Select Hour-Date-Course'}),
            'student': forms.Select(attrs={'placeholder': 'Select student'}),
            'status': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
