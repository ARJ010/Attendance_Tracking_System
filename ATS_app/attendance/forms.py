from django import forms
from .models import Student, Teacher, Course, StudentCourse, TeacherCourse, HourDateCourse, AbsentDetails,Programme,Department
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

class UserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, required=True)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password']

class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']  # Add other fields as needed
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # You can customize form widgets or validations if needed

class TeacherForm(forms.ModelForm):
    class Meta:
        model = Teacher
        fields = ['department', 'phone_number']

    def __init__(self, *args, **kwargs):
        # Get the logged-in teacher from kwargs
        logged_in_teacher = kwargs.pop('logged_in_teacher', None)
        super().__init__(*args, **kwargs)

        if logged_in_teacher:
            # Restrict the department queryset to the logged-in teacher's department
            self.fields['department'].queryset = Department.objects.filter(id=logged_in_teacher.department.id)



# Form for creating/updating a Student
class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['name', 'university_register_number','roll_number', 'admission_number', 'programme']
    
    def __init__(self, *args, **kwargs):
        # Get the currently logged-in teacher's department
        teacher = kwargs.pop('teacher', None)  # Pass the teacher as an argument to the form
        super().__init__(*args, **kwargs)

        if teacher:
            # Filter programmes based on teacher's department
            self.fields['programme'].queryset = Programme.objects.filter(department=teacher.department)



# Form for creating/updating a Student
class AdminStudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['name', 'university_register_number','roll_number', 'admission_number', 'programme']
    

    

# Form for creating/updating a Course
class CourseForm(forms.ModelForm):
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

    semester = forms.ChoiceField(choices=SEMESTER_CHOICES, widget=forms.Select(attrs={'placeholder': 'Select semester'}))

    class Meta:
        model = Course
        fields = ['name', 'code', 'semester', 'credits', 'department']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Enter course name'}),
            'code': forms.TextInput(attrs={'placeholder': 'Enter course code'}),
            'credits': forms.NumberInput(attrs={'placeholder': 'Enter number of credits'}),
            'department': forms.Select(attrs={'placeholder': 'Select department'}),
        }

    def __init__(self, *args, **kwargs):
        # Get the logged-in teacher from kwargs
        logged_in_teacher = kwargs.pop('logged_in_teacher', None)
        super().__init__(*args, **kwargs)

        if logged_in_teacher:
            # Restrict the department queryset to the logged-in teacher's department
            self.fields['department'].queryset = Department.objects.filter(id=logged_in_teacher.department.id)




# Form for assigning a Student to a Course
class StudentCourseForm(forms.Form):
    student = forms.ModelChoiceField(
        queryset=Student.objects.all(),
        widget=forms.Select(attrs={'placeholder': 'Select student'}),
        label="Select Student"
    )
    courses = forms.ModelMultipleChoiceField(
        queryset=Course.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label="Select Courses"
    )

class CourseSelectionForm(forms.Form):
    courses = forms.ModelMultipleChoiceField(
        queryset=Course.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label="Select Courses"
    )

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
        fields = ['date', 'hour']
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
            'status': forms.Select(choices=[(False, 'Absent'), (True, 'Present')]),
        }


class CSVUploadForm(forms.Form):
    csv_file = forms.FileField()