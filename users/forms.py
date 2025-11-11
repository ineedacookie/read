from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AdminPasswordChangeForm, PasswordChangeForm
from django.forms import SelectMultiple, EmailField, ModelForm, BooleanField, CharField, PasswordInput, CheckboxSelectMultiple, ModelMultipleChoiceField, ValidationError, ChoiceField

from .models import CustomUser, School, Classroom, StudentParentRelation, ReadingGroup
from .utils import send_email_with_link
from read.utils.form_helpers import (
    apply_form_control_styling,
    setup_school_filtered_querysets,
    setup_initial_values_for_instance,
    handle_user_type_clean,
    handle_password_validation_for_new_user,
    save_user_with_password,
    update_many_to_many_relationships,
    FormMixin
)


class BaseUserForm(ModelForm):
    """Base form for all user forms - eliminates duplication"""
    
    def __init__(self, *args, **kwargs):
        self.logged_in_user = kwargs.pop('logged_in_user', None)
        super().__init__(*args, **kwargs)
        apply_form_control_styling(self)
        
        # Setup querysets if instance has school (works for both new and existing)
        if self.instance and self.instance.school:
            setup_school_filtered_querysets(self, self.instance.school, self.logged_in_user)
            if self.instance.pk:  # Only setup initial values for existing instances
                setup_initial_values_for_instance(self, self.instance, self.instance.school)


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
        apply_form_control_styling(self)


class CustomUserChangeForm(UserChangeForm):
    """This form is used for recovering a lost password"""
    email = EmailField(max_length=200, help_text='Required')

    class Meta:
        model = CustomUser
        fields = ('email',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_form_control_styling(self)


class OverriddenAdminPasswordChangeForm(AdminPasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super(OverriddenAdminPasswordChangeForm, self).__init__(*args, **kwargs)
        if 'usable_password' in self.fields:
            self.fields.pop('usable_password')
        apply_form_control_styling(self)

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data['usable_password'] = True
        return cleaned_data


class OverriddenPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super(OverriddenPasswordChangeForm, self).__init__(*args, **kwargs)
        apply_form_control_styling(self)


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
        apply_form_control_styling(self)


class RegisterUserForm(ModelForm):
    agree_to_terms_and_conditions = BooleanField(required=True)
    
    class Meta:
        model = CustomUser
        fields = (
            'first_name',
            'last_initial',
            'email'
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_form_control_styling(self)
        
        # Add helpful labels
        self.fields['first_name'].help_text = 'Your first name'
        self.fields['last_initial'].help_text = 'First letter of your last name (e.g., "S" for Smith)'
        self.fields['email'].help_text = 'Your email address (used for login)'
    
    def save(self, commit=True):
        # All new registrations default to administrator
        instance = super().save(commit=False)
        instance.user_type = 'administrator'
        
        # Auto-generate username from email (required by Django for admin)
        if not instance.username:
            instance.username = instance.email
        
        if commit:
            instance.save()
        
        return instance


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
        apply_form_control_styling(self)

    def save(self, commit=True):
        # Create user without password - they'll set it during activation
        instance = super().save(commit=False)
        
        # Accounts start as inactive until they complete invitation process
        instance.is_active = False
        
        if commit:
            instance.save()
            # Send invitation email after saving the user
            send_email_with_link(instance, type='invitation')

        return instance


class InviteParentForm(ModelForm):
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

    # Note: Child assignment will be handled separately through StudentParentRelation
    # This simplifies the invite process and allows for proper relationship management

    def __init__(self, *args, **kwargs):
        logged_in_user = kwargs.pop('logged_in_user', None)
        super().__init__(*args, **kwargs)
        apply_form_control_styling(self)

    def clean(self):
        cleaned_data = super().clean()
        return handle_user_type_clean(cleaned_data, 'parent')

    def save(self, commit=True):
        # Create parent user without password - they'll set it during activation
        instance = super().save(commit=False)
        
        # Parent accounts start as inactive until they complete invitation process
        instance.is_active = False
        
        if commit:
            instance.save()
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
        apply_form_control_styling(self)

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data = handle_user_type_clean(cleaned_data, 'student')
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

        # Apply styling to password fields
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


class CustomStudentForm(BaseUserForm):
    password = CharField(widget=PasswordInput, required=False, help_text='Set password for new students. Leave blank when editing existing students.')
    
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

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data = handle_user_type_clean(cleaned_data, 'student')
        cleaned_data = handle_password_validation_for_new_user(self, cleaned_data)
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Handle password using helper
        instance = save_user_with_password(self, instance, commit=False)

        if commit:
            instance.save()
            self.save_m2m()

            school = instance.school

            # Update many-to-many relationships using helpers
            update_many_to_many_relationships(instance, 'classrooms', self.cleaned_data['classrooms'], school)
            update_many_to_many_relationships(instance, 'reading_groups', self.cleaned_data['reading_groups'], school)
            update_many_to_many_relationships(instance, 'parents', self.cleaned_data['parents'], school)

        return instance


class CustomTeacherForm(BaseUserForm):
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

    def clean(self):
        cleaned_data = super().clean()
        return handle_user_type_clean(cleaned_data, 'teacher')

    def save(self, commit=True):
        instance = super().save(commit=False)

        if commit:
            instance.save()
            self.save_m2m()

            school = instance.school

            # Update many-to-many relationships using helpers
            update_many_to_many_relationships(instance, 'classrooms', self.cleaned_data['classrooms'], school)
            update_many_to_many_relationships(instance, 'reading_groups', self.cleaned_data['reading_groups'], school)

        return instance


class CustomAdministratorForm(BaseUserForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'last_initial', 'email']

    reading_groups = ModelMultipleChoiceField(
        queryset=ReadingGroup.objects.none(),
        widget=SelectMultiple,
        required=False
    )

    def clean(self):
        cleaned_data = super().clean()
        return handle_user_type_clean(cleaned_data, 'administrator')

    def save(self, commit=True):
        instance = super().save(commit=False)

        if commit:
            instance.save()
            self.save_m2m()

            school = instance.school

            # Update many-to-many relationships using helpers
            update_many_to_many_relationships(instance, 'reading_groups', self.cleaned_data['reading_groups'], school)

        return instance


class CustomParentForm(BaseUserForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'last_initial', 'email']

    # Children are now managed through StudentParentRelation
    # This form will need to be updated in Phase 2 to handle child assignment

    def clean(self):
        cleaned_data = super().clean()
        return handle_user_type_clean(cleaned_data, 'parent')

    def save(self, commit=True):
        instance = super().save(commit=False)

        if commit:
            instance.save()

        return instance


class CustomClassroomForm(ModelForm):
    class Meta:
        model = Classroom
        fields = ['name', 'teachers', 'students']

    students = ModelMultipleChoiceField(
        queryset=CustomUser.objects.none(),
        widget=SelectMultiple,
        required=False
    )

    teachers = ModelMultipleChoiceField(
        queryset=CustomUser.objects.none(),
        widget=SelectMultiple,
        required=False
    )

    def __init__(self, *args, **kwargs):
        logged_in_user = kwargs.pop('logged_in_user', None)
        super().__init__(*args, **kwargs)

        # Apply common form styling
        apply_form_control_styling(self)

        # Set up querysets and initial values if instance has school
        if self.instance and self.instance.school:
            setup_school_filtered_querysets(self, self.instance.school, logged_in_user)
            setup_initial_values_for_instance(self, self.instance, self.instance.school)

    def save(self, commit=True):
        instance = super().save(commit=False)

        if commit:
            instance.save()
            self.save_m2m()

        return instance


class CustomReadingGroupForm(ModelForm):
    class Meta:
        model = ReadingGroup
        fields = ['name', 'managers', 'students']

    students = ModelMultipleChoiceField(
        queryset=CustomUser.objects.none(),
        widget=SelectMultiple,
        required=False
    )

    managers = ModelMultipleChoiceField(
        queryset=CustomUser.objects.none(),
        widget=SelectMultiple,
        required=False
    )

    def __init__(self, *args, **kwargs):
        logged_in_user = kwargs.pop('logged_in_user', None)
        super().__init__(*args, **kwargs)

        # Apply common form styling
        apply_form_control_styling(self)

        # Set up querysets and initial values if instance has school
        if self.instance and self.instance.school:
            setup_school_filtered_querysets(self, self.instance.school, logged_in_user)
            setup_initial_values_for_instance(self, self.instance, self.instance.school)

    def save(self, commit=True):
        instance = super().save(commit=False)

        if commit:
            instance.save()
            self.save_m2m()

        return instance
