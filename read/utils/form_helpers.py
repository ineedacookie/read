"""
Form helper functions to reduce code duplication in forms.
Handles common patterns like styling, queryset filtering, and field setup.
"""

from django.forms import ModelMultipleChoiceField, SelectMultiple
from django.contrib.auth import get_user_model


def apply_form_control_styling(form):
    """
    Apply Bootstrap form-control class to all form fields.
    
    Args:
        form: Django form instance
    """
    for field_name in form.fields:
        form.fields[field_name].widget.attrs["class"] = "form-control"


def setup_school_filtered_querysets(form, school, logged_in_user=None):
    """
    Set up querysets filtered by school for common model fields.
    
    Args:
        form: Django form instance
        school: School object to filter by
        logged_in_user: Optional logged-in user for additional filtering
    """
    # Set up students queryset
    if hasattr(form, 'fields') and 'students' in form.fields:
        form.fields['students'].queryset = get_user_model().objects.filter(
            school=school, 
            user_type='student'
        )
    
    # Set up teachers queryset
    if hasattr(form, 'fields') and 'teachers' in form.fields:
        form.fields['teachers'].queryset = get_user_model().objects.filter(
            school=school, 
            user_type='teacher'
        )
    
    # Set up parents queryset
    if hasattr(form, 'fields') and 'parents' in form.fields:
        form.fields['parents'].queryset = get_user_model().objects.filter(
            school=school, 
            user_type='parent'
        )
    
    # Set up classrooms queryset
    if hasattr(form, 'fields') and 'classrooms' in form.fields:
        from users.models import Classroom
        queryset = Classroom.objects.filter(school=school)
        # Filter for teachers to only show their classrooms
        if logged_in_user and logged_in_user.user_type == 'teacher':
            queryset = queryset.filter(teachers=logged_in_user)
        form.fields['classrooms'].queryset = queryset
    
    # Set up reading groups queryset  
    if hasattr(form, 'fields') and 'reading_groups' in form.fields:
        from users.models import ReadingGroup
        queryset = ReadingGroup.objects.filter(school=school)
        # Filter for teachers to only show their reading groups
        if logged_in_user and logged_in_user.user_type == 'teacher':
            queryset = queryset.filter(managers=logged_in_user)
        form.fields['reading_groups'].queryset = queryset
    
    # Set up managers queryset (for reading groups)
    if hasattr(form, 'fields') and 'managers' in form.fields:
        form.fields['managers'].queryset = get_user_model().objects.filter(
            school=school,
            user_type__in=['teacher', 'administrator']
        )


def setup_initial_values_for_instance(form, instance, school):
    """
    Set up initial values for form fields based on the instance.
    
    Args:
        form: Django form instance
        instance: Model instance being edited
        school: School object
    """
    if not instance or not instance.pk:
        return
    
    # Import models lazily to avoid circular imports
    from users.models import Classroom, ReadingGroup
    
    # Set up classroom initial values
    if hasattr(form, 'fields') and 'classrooms' in form.fields:
        if hasattr(instance, 'students_classrooms'):
            # For students - get classrooms they're in
            form.fields['classrooms'].initial = Classroom.objects.filter(
                school=school, 
                students=instance
            )
        elif hasattr(instance, 'teachers_classrooms'):
            # For teachers - get classrooms they teach
            form.fields['classrooms'].initial = Classroom.objects.filter(
                school=school, 
                teachers=instance
            )
    
    # Set up reading group initial values
    if hasattr(form, 'fields') and 'reading_groups' in form.fields:
        if hasattr(instance, 'reading_groups'):
            # For students - get reading groups they're in
            form.fields['reading_groups'].initial = ReadingGroup.objects.filter(
                school=school, 
                students=instance
            )
        elif hasattr(instance, 'managed_reading_groups'):
            # For teachers/managers - get reading groups they manage
            form.fields['reading_groups'].initial = ReadingGroup.objects.filter(
                school=school, 
                managers=instance
            )
    
    # Set up parent initial values for students
    if hasattr(form, 'fields') and 'parents' in form.fields and instance.user_type == 'student':
        form.fields['parents'].initial = get_user_model().objects.filter(
            school=school,
            user_type='parent',
            children_relations__student=instance
        )


def add_many_to_many_field(form, field_name, queryset, required=False, widget=None):
    """
    Add a many-to-many field to a form.
    
    Args:
        form: Django form instance
        field_name: Name of the field to add
        queryset: QuerySet for the field choices
        required: Whether the field is required
        widget: Widget to use (defaults to SelectMultiple)
    """
    if widget is None:
        widget = SelectMultiple
    
    form.fields[field_name] = ModelMultipleChoiceField(
        queryset=queryset,
        widget=widget,
        required=required
    )


def handle_user_type_clean(cleaned_data, user_type):
    """
    Standard clean method pattern for user forms to set user_type.
    
    Args:
        cleaned_data: Form's cleaned_data dictionary
        user_type: User type to set
    
    Returns:
        dict: Updated cleaned_data
    """
    cleaned_data['user_type'] = user_type
    return cleaned_data


def handle_password_validation_for_new_user(form, cleaned_data):
    """
    Handle password validation for new user creation.
    
    Args:
        form: Django form instance
        cleaned_data: Form's cleaned_data dictionary
    
    Returns:
        dict: Updated cleaned_data
    
    Raises:
        ValidationError: If password is required but not provided
    """
    from django.core.exceptions import ValidationError
    
    # Check if this is a new user (no pk) and password is required
    if not form.instance.pk and not cleaned_data.get('password'):
        raise ValidationError('Password is required when creating a new user.')
    
    return cleaned_data


def save_user_with_password(form, instance, commit=True):
    """
    Save user instance with password handling for new users.
    
    Args:
        form: Django form instance
        instance: User instance to save
        commit: Whether to commit to database
    
    Returns:
        User instance
    """
    # Handle password for new users
    if not instance.pk and form.cleaned_data.get('password'):
        instance.set_password(form.cleaned_data['password'])
        # Teacher/admin sets password, so no need to require change on first login
        instance.password_change_required = False
    
    if commit:
        instance.save()
    
    return instance


def update_many_to_many_relationships(instance, field_name, new_values, school, relation_method='add'):
    """
    Update many-to-many relationships for a model instance.
    
    Args:
        instance: Model instance
        field_name: Name of the M2M field
        new_values: New values for the relationship
        school: School object for filtering
        relation_method: Method to use ('add' or 'set')
    """
    if field_name == 'classrooms':
        update_classroom_relationships(instance, new_values, school)
    elif field_name == 'reading_groups':
        update_reading_group_relationships(instance, new_values, school)
    elif field_name == 'parents':
        update_parent_relationships(instance, new_values, school)


def update_classroom_relationships(instance, new_classrooms, school):
    """
    Update classroom relationships for a user.
    
    Args:
        instance: User instance
        new_classrooms: Set of new classroom objects
        school: School object
    """
    # Import models lazily to avoid circular imports
    from users.models import Classroom
    
    # Get current relationships
    if instance.user_type == 'student':
        current_classrooms = set(Classroom.objects.filter(school=school, students=instance))
    elif instance.user_type == 'teacher':
        current_classrooms = set(Classroom.objects.filter(school=school, teachers=instance))
    else:
        return
    
    new_classrooms_set = set(new_classrooms)
    
    # Add new relationships
    for classroom in new_classrooms_set - current_classrooms:
        if instance.user_type == 'student':
            classroom.students.add(instance)
        elif instance.user_type == 'teacher':
            classroom.teachers.add(instance)
    
    # Remove old relationships
    for classroom in current_classrooms - new_classrooms_set:
        if instance.user_type == 'student':
            classroom.students.remove(instance)
        elif instance.user_type == 'teacher':
            classroom.teachers.remove(instance)


def update_reading_group_relationships(instance, new_groups, school):
    """
    Update reading group relationships for a user.
    
    Args:
        instance: User instance
        new_groups: Set of new reading group objects
        school: School object
    """
    # Import models lazily to avoid circular imports
    from users.models import ReadingGroup
    
    # Get current relationships
    if instance.user_type == 'student':
        current_groups = set(ReadingGroup.objects.filter(school=school, students=instance))
    elif instance.user_type in ['teacher', 'administrator']:
        current_groups = set(ReadingGroup.objects.filter(school=school, managers=instance))
    else:
        return
    
    new_groups_set = set(new_groups)
    
    # Add new relationships
    for group in new_groups_set - current_groups:
        if instance.user_type == 'student':
            group.students.add(instance)
        elif instance.user_type in ['teacher', 'administrator']:
            group.managers.add(instance)
    
    # Remove old relationships
    for group in current_groups - new_groups_set:
        if instance.user_type == 'student':
            group.students.remove(instance)
        elif instance.user_type in ['teacher', 'administrator']:
            group.managers.remove(instance)


def update_parent_relationships(student_instance, new_parents, school):
    """
    Update parent-student relationships.
    
    Args:
        student_instance: Student user instance
        new_parents: Set of new parent objects
        school: School object
    """
    from users.models import StudentParentRelation
    
    # Get current parent relationships
    current_parents = set(get_user_model().objects.filter(
        school=school,
        user_type='parent',
        children_relations__student=student_instance
    ))
    
    new_parents_set = set(new_parents)
    
    # Add new parent-student relationships
    for parent in new_parents_set - current_parents:
        StudentParentRelation.objects.get_or_create(
            school=school,
            student=student_instance,
            parent=parent
        )
    
    # Remove old parent-student relationships
    for parent in current_parents - new_parents_set:
        StudentParentRelation.objects.filter(
            school=school,
            student=student_instance,
            parent=parent
        ).delete()


class FormMixin:
    """
    Mixin class that provides common form functionality.
    Can be used with Django forms to automatically apply common patterns.
    """
    
    def apply_styling(self):
        """Apply Bootstrap styling to all form fields."""
        apply_form_control_styling(self)
    
    def setup_querysets_for_school(self, school, logged_in_user=None):
        """Set up querysets filtered by school."""
        setup_school_filtered_querysets(self, school, logged_in_user)
    
    def setup_initial_values(self, instance, school):
        """Set up initial values based on instance."""
        setup_initial_values_for_instance(self, instance, school)
    
    def __init__(self, *args, **kwargs):
        logged_in_user = kwargs.pop('logged_in_user', None)
        super().__init__(*args, **kwargs)
        
        # Apply common setup
        self.apply_styling()
        
        # Set up querysets if instance has school
        if self.instance and hasattr(self.instance, 'school') and self.instance.school:
            self.setup_querysets_for_school(self.instance.school, logged_in_user)
            self.setup_initial_values(self.instance, self.instance.school)


def create_invite_form_save_method(user_type, send_invitation=True):
    """
    Create a save method for invitation forms.
    
    Args:
        user_type: Type of user being invited
        send_invitation: Whether to send invitation email
    
    Returns:
        Function: Save method for the form
    """
    def save(self, commit=True):
        from users.utils import send_email_with_link
        
        instance = super(self.__class__, self).save(commit=False)
        instance.user_type = user_type
        instance.is_active = False  # Inactive until they complete invitation
        
        if commit:
            instance.save()
            if send_invitation:
                send_email_with_link(instance, type='invitation')
        
        return instance
    
    return save
