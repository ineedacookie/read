from datetime import date, timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

from .managers import CustomUserManager
from read.utils.model_mixins import (
    TimestampedModelMixin,
    SchoolAndTimestampModelMixin,
    NamedModelMixin,
    FullNameMixin,
    VerifiedModelMixin,
    ActiveModelMixin,
    SoftDeleteModelMixin,
    BaseNamedContentModel,
    SchoolConsistencyMixin
)


class School(TimestampedModelMixin):
    """
    Represents a school entity.

    Attributes:
        name (str): The name of the school.
        created_date (date): The date when the school record was created (from TimestampedModelMixin).
        updated_date (date): The date when the school record was last updated (from TimestampedModelMixin).
    """
    name = models.CharField(max_length=255, help_text="School Name", blank=True, null=True)

    def __str__(self):
        if self.name:
            return str(self.name) + ' #' + str(self.pk)
        else:
            return "#" + str(self.pk)


class CustomUser(FullNameMixin, VerifiedModelMixin, ActiveModelMixin, SoftDeleteModelMixin, TimestampedModelMixin, AbstractUser):
    """
    Custom user model extending AbstractUser with additional mixins for common functionality.
    Uses FullNameMixin, VerifiedModelMixin, ActiveModelMixin, SoftDeleteModelMixin, and TimestampedModelMixin.
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
    # Fields now provided by mixins:
    # first_name, last_initial, full_name - from FullNameMixin
    # verified - from VerifiedModelMixin
    # created_date, updated_date - from TimestampedModelMixin
    # active - from ActiveModelMixin
    # marked_for_deletion - from SoftDeleteModelMixin
    password_change_required = models.BooleanField(_('Password Change Required'), default=False, help_text='User must change password on next login')
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_initial']

    objects = CustomUserManager()

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        if not self.school:
            self.school = School.objects.create()
        # update_full_name is now handled by FullNameMixin
        super().save(*args, **kwargs)

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


class Classroom(BaseNamedContentModel):
    """
    Represents a classroom entity.

    Attributes:
        name (str): The name of the classroom (from NamedModelMixin).
        teachers (list[CustomUser]): The teachers assigned to the classroom.
        students (list[CustomUser]): The students assigned to the classroom.
        school (School): The school this classroom belongs to (from SchoolRelatedModelMixin).
        created_by (CustomUser): User who created this classroom (from UserRelatedModelMixin).
        created_date (date): The date when the classroom record was created (from TimestampedModelMixin).
        updated_date (date): The date when the classroom record was last updated (from TimestampedModelMixin).
        active (bool): Whether the classroom is active (from ActiveModelMixin).
    """
    # Fields now provided by BaseNamedContentModel:
    # school, name, created_by, created_date, updated_date, active
    teachers = models.ManyToManyField(CustomUser, blank=True, related_name='teachers_classrooms',
                                      limit_choices_to={'user_type': 'teacher'})
    students = models.ManyToManyField(CustomUser, related_name='students_classrooms',
                                      limit_choices_to={'user_type': 'student'})
    # __str__ method now provided by NamedModelMixin


class ReadingGroup(BaseNamedContentModel):
    """
    Represents a reading group entity.

    Attributes:
        name (str): The name of the reading group (from NamedModelMixin).
        managers (list[CustomUser]): The managers of the reading group.
        students (list[CustomUser]): The students in the reading group.
        school (School): The school this reading group belongs to (from SchoolRelatedModelMixin).
        created_by (CustomUser): User who created this reading group (from UserRelatedModelMixin).
        created_date (date): The date when the reading group record was created (from TimestampedModelMixin).
        updated_date (date): The date when the reading group record was last updated (from TimestampedModelMixin).
        active (bool): Whether the reading group is active (from ActiveModelMixin).
    """
    # Fields now provided by BaseNamedContentModel:
    # school, name, created_by, created_date, updated_date, active
    managers = models.ManyToManyField(CustomUser, related_name='managed_reading_groups',
                                      limit_choices_to=models.Q(user_type='teacher') | models.Q(
                                          user_type='administrator'), blank=False)
    students = models.ManyToManyField(CustomUser, related_name='reading_groups',
                                      limit_choices_to={'user_type': 'student'})
    # __str__ method now provided by NamedModelMixin


class StudentParentRelation(SchoolAndTimestampModelMixin, SchoolConsistencyMixin):
    """
    Represents a relation between a student and a parent.
    
    This is the ONLY way parent-child relationships should be managed.
    Ensures data integrity and proper school-level isolation.

    Attributes:
        student (CustomUser): The student in the relation.
        parent (CustomUser): The parent in the relation.
        school (School): The school context for this relationship (from SchoolRelatedModelMixin).
        created_date (date): The date when the relation record was created (from TimestampedModelMixin).
        updated_date (date): The date when the relation record was last updated (from TimestampedModelMixin).
    """
    # Fields now provided by SchoolAndTimestampModelMixin:
    # school, created_date, updated_date
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='parent_relations',
                                limit_choices_to={'user_type': 'student'}, db_index=True)
    parent = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='children_relations',
                               limit_choices_to={'user_type': 'parent'}, db_index=True)
    
    class Meta:
        unique_together = [['student', 'parent']]  # Prevent duplicate relationships
        indexes = [
            models.Index(fields=['school', 'parent']),  # For parent dashboard queries
            models.Index(fields=['school', 'student']),  # For student lookup queries
        ]
    
    def clean(self):
        """Validate that parent and student are in the same school"""
        super().clean()  # Call SchoolRelatedModelMixin validation
        # Use SchoolConsistencyMixin validation methods
        self.validate_school_consistency('student', self.student)
        self.validate_school_consistency('parent', self.parent)
    
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
