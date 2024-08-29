from datetime import date, timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

from .managers import CustomUserManager


class School(models.Model):
    """
    Represents a school entity.

    Attributes:
        name (str): The name of the school.
        created_date (date): The date when the school record was created.
        updated_date (date): The date when the school record was last updated.
    """
    name = models.CharField(max_length=255, help_text="School Name", blank=True, null=True)
    created_date = models.DateField(_("Created Date"), auto_now_add=True, blank=True)
    updated_date = models.DateField(_("Updated Date"), auto_now=True, blank=True, null=True)

    def __str__(self):
        return str(self.name) + ' #' + str(self.pk)


class CustomUser(AbstractUser):
    """
    Custom user model extending AbstractUser with additional fields.

    Attributes:
        school (School): The school the user belongs to.
        user_type (str): The type of user (e.g., teacher, student, parent, administrator).
        username (str): The unique username of the user.
        email (str): The unique email of the user.
        change_email (str): An email placeholder used during the email change process.
        first_name (str): The first name of the user.
        middle_name (str): The middle name of the user.
        last_name (str): The last name of the user.
        verified (bool): Indicates if the user's email is verified.
        created_date (date): The date when the user record was created.
        updated_date (date): The date when the user record was last updated.
        full_name (str): The full name of the user in the format "last_name, first_name middle_name".
        active (bool): Indicates if the user is active.
        marked_for_deletion (date): A date when the user is marked for deletion.
    """
    USER_TYPE_CHOICES = (
        ('teacher', 'Teacher'),
        ('student', 'Student'),
        ('parent', 'Parent'),
        ('administrator', 'Administrator'),
    )

    school = models.ForeignKey(School, on_delete=models.SET_NULL, null=True, blank=True)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES)
    username = models.CharField(_('Username'), unique=True, max_length=50)
    email = models.EmailField(_('Email'), unique=True)
    change_email = models.EmailField(null=True, blank=True, default=None)
    first_name = models.CharField(_('First Name'), max_length=50, blank=True, null=True)
    middle_name = models.CharField(_('Middle Name'), max_length=50, blank=True, null=True)
    last_name = models.CharField(_('Last Name'), max_length=100, blank=True, null=True)
    verified = models.BooleanField(default=False, blank=True)
    created_date = models.DateField(_("Created Date"), auto_now_add=True, blank=True, null=True)
    updated_date = models.DateField(_("Updated Date"), auto_now=True, blank=True, null=True)
    full_name = models.CharField(_('Full Name'), max_length=210, blank=True, null=True, default=None)
    active = models.BooleanField(_('Active'), blank=True, null=True, default=True)
    marked_for_deletion = models.DateField(null=True,
                                           blank=True)  # added this to allow for a 30 day grace period before deleting the user perminately.

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = [username]

    objects = CustomUserManager()

    def __str__(self):
        return self.username

    def save(self, *args, **kwargs):
        """
        Overrides the save method to update the full name before saving the user.
        """
        self.update_full_name()
        super().save(*args, **kwargs)

    def update_full_name(self):
        """
        Stores the full name as last_name, first_name middle_name.
        """
        if self.first_name and self.last_name:
            text = self.last_name + ', ' + self.first_name
            if self.middle_name:
                text += ' ' + self.middle_name
        else:
            text = ''
        self.full_name = text.upper()


class Classroom(models.Model):
    """
    Represents a classroom entity.

    Attributes:
        name (str): The name of the classroom.
        teacher (CustomUser): The teacher assigned to the classroom.
        students (list[CustomUser]): The students assigned to the classroom.
        created_date (date): The date when the classroom record was created.
        updated_date (date): The date when the classroom record was last updated.
    """
    name = models.CharField(max_length=255, help_text="Classroom Name")
    teacher = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
                                limit_choices_to={'user_type': 'teacher'})
    students = models.ManyToManyField(CustomUser, related_name='classrooms',
                                      limit_choices_to={'user_type': 'student'})
    created_date = models.DateField(_("Created Date"), auto_now_add=True, blank=True)
    updated_date = models.DateField(_("Updated Date"), auto_now=True, blank=True, null=True)

    def __str__(self):
        return self.name


class ReadingGroup(models.Model):
    """
    Represents a reading group entity.

    Attributes:
        name (str): The name of the reading group.
        managers (list[CustomUser]): The managers of the reading group.
        students (list[CustomUser]): The students in the reading group.
        created_date (date): The date when the reading group record was created.
        updated_date (date): The date when the reading group record was last updated.
    """
    name = models.CharField(max_length=255, help_text="Reading Group Name")
    managers = models.ManyToManyField(CustomUser, related_name='managed_reading_groups',
                                      limit_choices_to=models.Q(user_type='teacher') | models.Q(
                                          user_type='administrator'), blank=False)
    students = models.ManyToManyField(CustomUser, related_name='reading_groups',
                                      limit_choices_to={'user_type': 'student'})
    created_date = models.DateField(_("Created Date"), auto_now_add=True, blank=True)
    updated_date = models.DateField(_("Updated Date"), auto_now=True, blank=True, null=True)

    def __str__(self):
        return self.name


class StudentParentRelation(models.Model):
    """
    Represents a relation between a student and a parent.

    Attributes:
        student (CustomUser): The student in the relation.
        parent (CustomUser): The parent in the relation.
        created_date (date): The date when the relation record was created.
        updated_date (date): The date when the relation record was last updated.
    """
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='parents',
                                limit_choices_to={'user_type': 'student'})
    parent = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='children',
                               limit_choices_to={'user_type': 'parent'})
    created_date = models.DateField(_("Created Date"), auto_now_add=True, blank=True)
    updated_date = models.DateField(_("Updated Date"), auto_now=True, blank=True, null=True)

    def __str__(self):
        return f'{self.parent} - {self.student}'
