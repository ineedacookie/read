from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AdminPasswordChangeForm, PasswordChangeForm
from django.forms import SelectMultiple, EmailField, ModelForm, BooleanField, CharField, PasswordInput, CheckboxSelectMultiple, ModelMultipleChoiceField

from .models import CustomUser, School, Classroom, StudentParentRelation, ReadingGroup
from .utils import send_email_with_link


class SchoolForm(ModelForm):
    class Meta:
        model = School
        fields = ['name']


class CustomUserCreationForm(UserCreationForm):
    """This form is used for creating a user in django admin mode"""
    email = EmailField(max_length=200, help_text='Required')

    class Meta(UserCreationForm):
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_initial', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name in self.fields:
            self.fields[name].widget.attrs["class"] = "form-control"


class CustomUserChangeForm(UserChangeForm):
    """This form is used for recovering a lost password"""
    email = EmailField(max_length=200, help_text='Required')

    class Meta:
        model = CustomUser
        fields = ('email',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name in self.fields:
            self.fields[name].widget.attrs["class"] = "form-control"


class OverriddenAdminPasswordChangeForm(AdminPasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super(OverriddenAdminPasswordChangeForm, self).__init__(*args, **kwargs)

        for name in ["password1", "password2"]:
            self.fields[name].widget.attrs["class"] = "form-control"


class OverriddenPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super(OverriddenPasswordChangeForm, self).__init__(*args, **kwargs)

        for name in ["old_password", "new_password1", "new_password2"]:
            self.fields[name].widget.attrs["class"] = "form-control"


class UserForm(ModelForm):
    class Meta:
        model = CustomUser
        fields = (
            'first_name',
            'last_initial',
            'username',
            'email',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name in self.fields:
            self.fields[name].widget.attrs["class"] = "form-control"


class RegisterUserForm(ModelForm):
    agree_to_terms_and_conditions = BooleanField(required=True)
    class Meta:
        model = CustomUser
        fields = (
            'first_name',
            'last_initial',
            'username',
            'email'
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name in self.fields:
            self.fields[name].widget.attrs["class"] = "form-control"


class InviteUsersForm(ModelForm):
    class Meta:
        model = CustomUser
        fields = (
            'first_name',
            'last_initial',
            'username',
            'email',
            'user_type',
            'school'
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name in self.fields:
            self.fields[name].widget.attrs["class"] = "form-control"

    def save(self, commit=False):
        instance = super().save(commit=True)

        if not commit:
            # Send invitation email after saving the user
            send_email_with_link(instance, type='invitation')

        return instance


class InviteStudentsForm(ModelForm):
    password = CharField(widget=PasswordInput, required=True)

    class Meta:
        model = CustomUser
        fields = (
            'first_name',
            'last_initial',
            'user_type',
            'username',
            'email',
            'school',
            'password')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name in self.fields:
            self.fields[name].widget.attrs["class"] = "form-control"

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data['user_type'] = 'student'
        cleaned_data['verified'] = True
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.set_password(self.cleaned_data["password"])

        if commit:
            instance.save()

        return instance


class InviteCombinedForm(ModelForm, AdminPasswordChangeForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'first_name', 'last_initial')

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        AdminPasswordChangeForm.__init__(self, user, *args, **kwargs)
        ModelForm.__init__(self, *args, **kwargs)
        # Add the fields from AdminPasswordChangeForm to this form
        self.fields.update(AdminPasswordChangeForm.base_fields)
        self.initial.update(AdminPasswordChangeForm(user).initial)

        for name in ["password1", "password2"]:
            self.fields[name].widget.attrs["class"] = "form-control"

    def clean(self):
        cleaned_data = super().clean()
        AdminPasswordChangeForm.clean_password2(self)
        return cleaned_data

    def save(self, commit=True):
        # Save the initial info fields
        instance = super().save(commit=False)
        instance.set_password(self.cleaned_data["password1"])

        if commit:
            instance.save()

class ClassroomForm(ModelForm):
    class Meta:
        model = Classroom
        fields = ['school', 'name', 'teachers', 'students']
        widgets = {
            'teachers': CheckboxSelectMultiple,
            'students': CheckboxSelectMultiple,
        }

class ReadingGroupForm(ModelForm):
    class Meta:
        model = ReadingGroup
        fields = ['school', 'name', 'managers', 'students']
        widgets = {
            'managers': CheckboxSelectMultiple,
            'students': CheckboxSelectMultiple,
        }

class StudentParentRelationForm(ModelForm):
    class Meta:
        model = StudentParentRelation
        fields = ['school', 'student', 'parent']


class CustomStudentForm(ModelForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'last_initial', 'email']

    classrooms = ModelMultipleChoiceField(
        queryset=Classroom.objects.none(),
        widget=SelectMultiple,
        required=False
    )

    reading_groups = ModelMultipleChoiceField(
        queryset=ReadingGroup.objects.none(),
        widget=SelectMultiple,
        required=False
    )

    parents = ModelMultipleChoiceField(
        queryset=CustomUser.objects.none(),
        widget=SelectMultiple,
        required=False
    )

    def __init__(self, *args, **kwargs):
        logged_in_user = kwargs.pop('logged_in_user', None)
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.school:
            school = self.instance.school

            self.fields['classrooms'].queryset = Classroom.objects.filter(school=school)
            self.fields['reading_groups'].queryset = ReadingGroup.objects.filter(school=school)
            self.fields['parents'].queryset = CustomUser.objects.filter(school=school, user_type='parent')


            if self.instance and self.instance.pk:
                self.fields['classrooms'].initial = Classroom.objects.filter(school=school, students=self.instance)
                self.fields['reading_groups'].initial = ReadingGroup.objects.filter(school=school, students=self.instance)
                self.fields['parents'].initial = CustomUser.objects.filter(school=school, students=self.instance)

            if logged_in_user and logged_in_user.user_type == 'teacher':
                self.fields['classrooms'].queryset = self.fields['classrooms'].queryset.filter(teachers=logged_in_user)
                self.fields['reading_groups'].queryset = self.fields['reading_groups'].queryset.filter(
                    managers=logged_in_user)

        for name in self.fields:
            self.fields[name].widget.attrs["class"] = "form-control"

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data['user_type'] = 'student'
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        if commit:

            instance.save()
            self.save_m2m()

            school = instance.school

            # Update Classroom's students field
            current_classrooms = set(self.cleaned_data['classrooms'])
            original_classrooms = set(Classroom.objects.filter(school=school, students=self.instance))
            for classroom in current_classrooms - original_classrooms:
                classroom.students.add(instance)
            for classroom in original_classrooms - current_classrooms:
                classroom.students.remove(instance)

            # Update ReadingGroup's students field
            current_reading_groups = set(self.cleaned_data['reading_groups'])
            original_reading_groups = set(ReadingGroup.objects.filter(school=school, students=self.instance))
            for reading_group in current_reading_groups - original_reading_groups:
                reading_group.students.add(instance)
            for reading_group in original_reading_groups - current_reading_groups:
                reading_group.students.remove(instance)

            # Update Parent's students field
            current_parents = set(self.cleaned_data['parents'])
            original_parents = set(CustomUser.objects.filter(school=school, students=self.instance))
            for parent in current_parents - original_parents:
                parent.students.add(instance)
            for parent in original_parents - current_parents:
                parent.students.remove(instance)

        return instance
