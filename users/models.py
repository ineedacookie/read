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
        if self.name:
            return str(self.name) + ' #' + str(self.pk)
        else:
            return "#" + str(self.pk)


class CustomUser(AbstractUser):
    """
    Custom user model extending AbstractUser with additional fields.
    """
    USER_TYPE_CHOICES = (
        ('teacher', 'Teacher'),
        ('student', 'Student'),
        ('parent', 'Parent'),
        ('administrator', 'Administrator'),
    )

    school = models.ForeignKey('School', on_delete=models.SET_NULL, null=True, blank=True, db_index=True)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, db_index=True)
    email = models.EmailField(_('Email'), unique=True, db_index=True)
    # REMOVED: students = models.ManyToManyField('CustomUser', blank=True)  # Use StudentParentRelation instead
    change_email = models.EmailField(null=True, blank=True)
    first_name = models.CharField(_('First Name'), max_length=50, blank=True, null=True)
    last_initial = models.CharField(_('Last Initial'), max_length=1, blank=True, null=True)
    verified = models.BooleanField(default=False, blank=True)
    created_date = models.DateField(_("Created Date"), auto_now_add=True, blank=True, null=True)
    updated_date = models.DateField(_("Updated Date"), auto_now=True, blank=True, null=True)
    full_name = models.CharField(_('Full Name'), max_length=210, blank=True, null=True, default=None)
    active = models.BooleanField(_('Active'), blank=True, null=True, default=True)
    marked_for_deletion = models.DateField(null=True, blank=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_initial']

    objects = CustomUserManager()

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        if not self.school:
            self.school = School.objects.create()
        self.update_full_name()
        super().save(*args, **kwargs)

    def update_full_name(self):
        if self.first_name and self.last_initial:
            text = self.first_name + ' ' + self.last_initial + '.'
        else:
            text = ''
        self.full_name = text.upper()

    @classmethod
    def get_by_natural_key(cls, username_or_email):
        return cls.objects.filter(models.Q(username=username_or_email) | models.Q(email=username_or_email)).first()
    
    @property
    def children(self):
        """Get all children for this parent user through StudentParentRelation"""
        if self.user_type != 'parent':
            return CustomUser.objects.none()
        return CustomUser.objects.filter(parent_relations__parent=self).select_related('school')
    
    @property  
    def parents(self):
        """Get all parents for this student user through StudentParentRelation"""
        if self.user_type != 'student':
            return CustomUser.objects.none()
        return CustomUser.objects.filter(children_relations__student=self).select_related('school')


class Classroom(models.Model):
    """
    Represents a classroom entity.

    Attributes:
        name (str): The name of the classroom.
        teachers (list[CustomUser]): The teachers assigned to the classroom.
        students (list[CustomUser]): The students assigned to the classroom.
        created_date (date): The date when the classroom record was created.
        updated_date (date): The date when the classroom record was last updated.
    """
    school = models.ForeignKey('School', on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=255, help_text="Classroom Name")
    teachers = models.ManyToManyField(CustomUser, blank=True, related_name='teachers_classrooms',
                                      limit_choices_to={'user_type': 'teacher'})
    students = models.ManyToManyField(CustomUser, related_name='students_classrooms',
                                      limit_choices_to={'user_type': 'student'})
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
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
    school = models.ForeignKey('School', on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=255, help_text="Reading Group Name")
    managers = models.ManyToManyField(CustomUser, related_name='managed_reading_groups',
                                      limit_choices_to=models.Q(user_type='teacher') | models.Q(
                                          user_type='administrator'), blank=False)
    students = models.ManyToManyField(CustomUser, related_name='reading_groups',
                                      limit_choices_to={'user_type': 'student'})
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    created_date = models.DateField(_("Created Date"), auto_now_add=True, blank=True)
    updated_date = models.DateField(_("Updated Date"), auto_now=True, blank=True, null=True)

    def __str__(self):
        return self.name


class StudentParentRelation(models.Model):
    """
    Represents a relation between a student and a parent.
    
    This is the ONLY way parent-child relationships should be managed.
    Ensures data integrity and proper school-level isolation.

    Attributes:
        student (CustomUser): The student in the relation.
        parent (CustomUser): The parent in the relation.
        school (School): The school context for this relationship.
        created_date (date): The date when the relation record was created.
        updated_date (date): The date when the relation record was last updated.
    """
    school = models.ForeignKey('School', on_delete=models.CASCADE, db_index=True)  # Required, not nullable
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='parent_relations',
                                limit_choices_to={'user_type': 'student'}, db_index=True)
    parent = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='children_relations',
                               limit_choices_to={'user_type': 'parent'}, db_index=True)
    created_date = models.DateField(_("Created Date"), auto_now_add=True, blank=True)
    updated_date = models.DateField(_("Updated Date"), auto_now=True, blank=True, null=True)
    
    class Meta:
        unique_together = [['student', 'parent']]  # Prevent duplicate relationships
        indexes = [
            models.Index(fields=['school', 'parent']),  # For parent dashboard queries
            models.Index(fields=['school', 'student']),  # For student lookup queries
        ]
    
    def clean(self):
        """Validate that parent and student are in the same school"""
        from django.core.exceptions import ValidationError
        if self.student.school != self.parent.school:
            raise ValidationError("Parent and student must be in the same school")
        if self.school != self.student.school:
            raise ValidationError("Relationship school must match student school")
    
    def save(self, *args, **kwargs):
        if not self.school:
            self.school = self.student.school
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.parent} - {self.student}'
    
    @property
    def children(self):
        """Access children through the relation - for backward compatibility"""
        return CustomUser.objects.filter(parent_relations__parent=self.parent)
    
    @property  
    def parents(self):
        """Access parents through the relation - for backward compatibility"""
        return CustomUser.objects.filter(children_relations__student=self.student)
