"""
Model mixins and base classes to reduce code duplication across models.
Provides common patterns for timestamps, school relationships, and validation.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError


class TimestampedModelMixin(models.Model):
    """
    Abstract base class that provides automatic created and updated timestamps.
    """
    created_date = models.DateField(_("Created Date"), auto_now_add=True, blank=True, null=True)
    updated_date = models.DateField(_("Updated Date"), auto_now=True, blank=True, null=True)

    class Meta:
        abstract = True


class SchoolRelatedModelMixin(models.Model):
    """
    Abstract base class for models that belong to a school.
    Provides school foreign key and related validation.
    """
    school = models.ForeignKey(
        'users.School', 
        on_delete=models.CASCADE, 
        db_index=True,
        help_text="The school this record belongs to"
    )

    class Meta:
        abstract = True

    def clean(self):
        """Validate that the school is set"""
        super().clean()
        if not self.school_id:
            raise ValidationError("School is required")


class SchoolAndTimestampModelMixin(SchoolRelatedModelMixin, TimestampedModelMixin):
    """
    Abstract base class that combines school relationship and timestamps.
    Most commonly used base class for school-related models.
    """
    class Meta:
        abstract = True


class NamedModelMixin(models.Model):
    """
    Abstract base class for models that have a name field.
    """
    name = models.CharField(
        max_length=255, 
        help_text="Name of the record",
        db_index=True
    )

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class UserRelatedModelMixin(models.Model):
    """
    Abstract base class for models that are related to a user (creator, owner, etc).
    """
    created_by = models.ForeignKey(
        'users.CustomUser', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='%(class)s_created',
        help_text="User who created this record"
    )

    class Meta:
        abstract = True


class ActiveModelMixin(models.Model):
    """
    Abstract base class for models that can be active/inactive.
    """
    active = models.BooleanField(
        _('Active'), 
        default=True, 
        help_text="Whether this record is active"
    )

    class Meta:
        abstract = True

    @property
    def is_active(self):
        """Convenience property for checking if the model is active"""
        return self.active


class SoftDeleteModelMixin(models.Model):
    """
    Abstract base class for models that support soft deletion.
    """
    marked_for_deletion = models.DateField(
        null=True, 
        blank=True,
        help_text="Date when this record was marked for deletion"
    )

    class Meta:
        abstract = True

    @property
    def is_deleted(self):
        """Check if the model is marked for deletion"""
        return self.marked_for_deletion is not None

    def soft_delete(self):
        """Mark the model for deletion"""
        from datetime import date
        self.marked_for_deletion = date.today()
        self.save(update_fields=['marked_for_deletion'])

    def restore(self):
        """Restore the model from soft deletion"""
        self.marked_for_deletion = None
        self.save(update_fields=['marked_for_deletion'])


class FullNameMixin(models.Model):
    """
    Abstract base class for models that have first_name and last_initial.
    Automatically manages the full_name field.
    """
    first_name = models.CharField(
        _('First Name'), 
        max_length=50, 
        blank=True, 
        null=True
    )
    last_initial = models.CharField(
        _('Last Initial'), 
        max_length=1, 
        blank=True, 
        null=True
    )
    full_name = models.CharField(
        _('Full Name'), 
        max_length=210, 
        blank=True, 
        null=True, 
        default=None,
        help_text="Automatically generated from first name and last initial"
    )

    class Meta:
        abstract = True

    def update_full_name(self):
        """Update the full_name field based on first_name and last_initial"""
        if self.first_name and self.last_initial:
            text = f"{self.first_name} {self.last_initial}."
        else:
            text = ''
        self.full_name = text.upper()

    def save(self, *args, **kwargs):
        """Override save to automatically update full_name"""
        self.update_full_name()
        super().save(*args, **kwargs)


class VerifiedModelMixin(models.Model):
    """
    Abstract base class for models that can be verified (like users).
    """
    verified = models.BooleanField(
        default=False, 
        blank=True,
        help_text="Whether this record has been verified"
    )

    class Meta:
        abstract = True

    @property
    def is_verified(self):
        """Convenience property for checking verification status"""
        return self.verified


class OrderedModelMixin(models.Model):
    """
    Abstract base class for models that have an ordering field.
    """
    order = models.PositiveIntegerField(
        default=0,
        help_text="Order for sorting"
    )

    class Meta:
        abstract = True
        ordering = ['order']


class DescriptionModelMixin(models.Model):
    """
    Abstract base class for models that have a description field.
    """
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Optional description"
    )

    class Meta:
        abstract = True


# Common combinations for specific use cases
class BaseUserModel(
    SchoolAndTimestampModelMixin, 
    FullNameMixin, 
    VerifiedModelMixin, 
    ActiveModelMixin,
    SoftDeleteModelMixin
):
    """
    Base class for user-like models with common fields.
    """
    class Meta:
        abstract = True


class BaseContentModel(
    SchoolAndTimestampModelMixin,
    UserRelatedModelMixin,
    ActiveModelMixin
):
    """
    Base class for content models like classrooms, groups, etc.
    """
    class Meta:
        abstract = True


class BaseNamedContentModel(
    BaseContentModel,
    NamedModelMixin,
    DescriptionModelMixin
):
    """
    Base class for named content models with descriptions.
    """
    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class BaseLogModel(SchoolAndTimestampModelMixin):
    """
    Base class for log-type models with timestamps and school relationship.
    """
    class Meta:
        abstract = True
        ordering = ['-created_date', '-id']


# Validation mixins
class SchoolConsistencyMixin:
    """
    Mixin that provides validation for ensuring related objects are in the same school.
    """
    
    def validate_school_consistency(self, field_name, related_object):
        """
        Validate that a related object belongs to the same school.
        
        Args:
            field_name: Name of the field being validated
            related_object: The related object to check
        """
        if hasattr(self, 'school') and hasattr(related_object, 'school'):
            if self.school != related_object.school:
                raise ValidationError(f"{field_name} must be from the same school")

    def validate_multiple_school_consistency(self, field_name, related_objects):
        """
        Validate that multiple related objects belong to the same school.
        
        Args:
            field_name: Name of the field being validated
            related_objects: QuerySet or list of related objects to check
        """
        if hasattr(self, 'school'):
            for obj in related_objects:
                if hasattr(obj, 'school') and obj.school != self.school:
                    raise ValidationError(f"All {field_name} must be from the same school")


# Common model managers
class ActiveManager(models.Manager):
    """Manager that only returns active records by default"""
    
    def get_queryset(self):
        return super().get_queryset().filter(active=True)


class SchoolFilteredManager(models.Manager):
    """Manager that provides school-filtered querysets"""
    
    def for_school(self, school):
        """Get records for a specific school"""
        return self.filter(school=school)
    
    def active_for_school(self, school):
        """Get active records for a specific school"""
        return self.filter(school=school, active=True)


class VerifiedManager(models.Manager):
    """Manager that only returns verified records by default"""
    
    def get_queryset(self):
        return super().get_queryset().filter(verified=True)


# Common model properties and methods
class MetricsMixin:
    """
    Mixin that provides common metric calculations for models.
    """
    
    def get_related_count(self, field_name):
        """Get count of related objects"""
        if hasattr(self, field_name):
            related_manager = getattr(self, field_name)
            if hasattr(related_manager, 'count'):
                return related_manager.count()
        return 0
    
    def get_active_related_count(self, field_name):
        """Get count of active related objects"""
        if hasattr(self, field_name):
            related_manager = getattr(self, field_name)
            if hasattr(related_manager, 'filter'):
                return related_manager.filter(active=True).count()
        return 0


# Combined base model classes
class BaseNamedContentModel(
    SchoolRelatedModelMixin, 
    NamedModelMixin, 
    UserRelatedModelMixin, 
    ActiveModelMixin, 
    TimestampedModelMixin
):
    """
    Base model that combines all common functionality for content models like Classroom and ReadingGroup.
    
    Provides:
    - school: ForeignKey to School (from SchoolRelatedModelMixin)
    - name: CharField for the model name (from NamedModelMixin)
    - created_by: ForeignKey to user who created it (from UserRelatedModelMixin)
    - active: BooleanField for active/inactive status (from ActiveModelMixin)
    - created_date, updated_date: DateFields for timestamps (from TimestampedModelMixin)
    """
    
    class Meta:
        abstract = True
        ordering = ['name']
        
    def save(self, *args, **kwargs):
        """Override save to ensure proper validation"""
        self.clean()
        super().save(*args, **kwargs)
