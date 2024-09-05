from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AdminPasswordChangeForm, PasswordChangeForm
from django.forms import EmailField, ModelForm, BooleanField, CharField, PasswordInput

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
        fields = ['name', 'teacher', 'students']

class ReadingGroupForm(ModelForm):
    class Meta:
        model = ReadingGroup
        fields = ['name', 'managers', 'students']

class StudentParentRelationForm(ModelForm):
    class Meta:
        model = StudentParentRelation
        fields = ['student', 'parent']