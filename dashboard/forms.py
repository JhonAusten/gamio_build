from django import forms
from django.contrib.auth.models import User

from .models import GRADE_LEVELS, LEVEL_GROUPS, SchoolClass, Student


class SignUpForm(forms.Form):
    full_name = forms.CharField(label="Full name", max_length=150)
    class_name = forms.CharField(label="Class / Section", max_length=120,
                                  widget=forms.TextInput(attrs={"placeholder": "e.g. Grade 1 - Hope"}))
    username = forms.CharField(label="User name", max_length=150)
    email = forms.EmailField(label="Email address", max_length=254,
                             widget=forms.EmailInput(attrs={"placeholder": "e.g. teacher@gmail.com"}))
    password = forms.CharField(label="Password", widget=forms.PasswordInput,
                                help_text="At least 8 characters")
    confirm_password = forms.CharField(label="Confirm password", widget=forms.PasswordInput)

    def clean_username(self):
        return self.cleaned_data["username"].strip()

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

    def clean_password(self):
        password = self.cleaned_data["password"]
        if len(password) < 8:
            raise forms.ValidationError("Password must be at least 8 characters.")
        return password

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password") and cleaned.get("confirm_password"):
            if cleaned["password"] != cleaned["confirm_password"]:
                raise forms.ValidationError("Passwords don't match.")
        return cleaned


class ClassForm(forms.ModelForm):
    class Meta:
        model = SchoolClass
        fields = ["grade", "section"]
        widgets = {
            "section": forms.TextInput(attrs={"placeholder": "e.g. Hope, Faith, A"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["grade"].choices = [("", "Choose grade")] + GRADE_LEVELS


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ["name", "gender"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. Mariane Vertudes"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["gender"].choices = [("", "Choose one")] + Student.GENDER_CHOICES


class QuizUploadForm(forms.Form):
    source_file = forms.FileField(label="Lesson file")
    level_group = forms.ChoiceField(label="Add this quiz to", choices=LEVEL_GROUPS)
