from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from users.models import CustomUser, School, ReadingGroup, Classroom
from read.utils.model_mixins import (
    SchoolAndTimestampModelMixin,
    SchoolConsistencyMixin,
    BaseLogModel
)


class Log(SchoolAndTimestampModelMixin, SchoolConsistencyMixin):
    """
    Represents a reading log entry for a student.
    
    Attributes:
        student: The student who created this reading log
        school: The school the student belongs to (from SchoolRelatedModelMixin)
        date: The date the reading was done
        title: Title of the book/material read
        author: Author of the book/material
        pages: Number of pages read
        minutes: Minutes spent reading
        rating: Student's rating of the material (0.00-5.00)
        comments: Additional comments about the reading
        created_date: When the log record was created (from TimestampedModelMixin)
        updated_date: When the log record was last updated (from TimestampedModelMixin)
    """
    # Fields now provided by SchoolAndTimestampModelMixin:
    # school, created_date, updated_date
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, db_index=True)
    date = models.DateField(db_index=True)  # Frequently queried for date ranges
    title = models.CharField(max_length=255, blank=True, null=True, db_index=True)  # For search functionality
    author = models.CharField(max_length=255, blank=True, null=True, db_index=True)  # For search functionality
    pages = models.IntegerField(blank=True, null=True)
    minutes = models.IntegerField(blank=True, null=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, blank=True, null=True, validators=[
        MinValueValidator(0.00),
        MaxValueValidator(5.00)
    ])
    comments = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-date', '-created_date']  # Most recent first
        indexes = [
            models.Index(fields=['school', 'student', 'date']),  # For student progress queries
            models.Index(fields=['school', 'date']),  # For school-wide queries
            models.Index(fields=['student', 'date']),  # For individual student queries
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(pages__gte=0) | models.Q(pages__isnull=True),
                name='pages_non_negative'
            ),
            models.CheckConstraint(
                check=models.Q(minutes__gte=0) | models.Q(minutes__isnull=True),
                name='minutes_non_negative'
            ),
        ]

    def clean(self):
        """Validate log data"""
        super().clean()  # Call SchoolRelatedModelMixin validation
        # Use SchoolConsistencyMixin validation method
        self.validate_school_consistency('student', self.student)
        
        # Custom validation for rating
        from django.core.exceptions import ValidationError
        if self.rating is not None and not (0 <= self.rating <= 5):
            raise ValidationError("Rating must be between 0 and 5")

    def save(self, *args, **kwargs):
        if not self.school_id:  # Check using _id to avoid RelatedObjectDoesNotExist
            self.school = self.student.school
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student} - {self.date}"



class DailyGoal(models.Model):
    """
    Represents a daily reading goal for students.
    Can be set at school, classroom, reading group, or individual student level.
    """
    GOAL_TYPE = [
        ('pages', 'Pages'),
        ('minutes', 'Minutes'),
    ]

    school = models.ForeignKey(School, on_delete=models.CASCADE)
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, null=True, blank=True)
    reading_group = models.ForeignKey(ReadingGroup, on_delete=models.CASCADE, null=True, blank=True)
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    type = models.CharField(
        max_length=10,
        choices=GOAL_TYPE,
        default='pages')
    value = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        target = self.student or self.reading_group or self.classroom or self.school
        return f"{target} - {self.value} {self.type} daily"


class TotalGoal(models.Model):
    """
    Represents a total reading goal over a date range for students.
    Can be set at school, classroom, reading group, or individual student level.
    """
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, null=True, blank=True)
    reading_group = models.ForeignKey(ReadingGroup, on_delete=models.CASCADE, null=True, blank=True)
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    start = models.DateField()
    end = models.DateField()
    total = models.PositiveIntegerField(default=0)

    def __str__(self):
        target = self.student or self.reading_group or self.classroom or self.school
        return f"{target} - {self.total} total ({self.start} to {self.end})"


class ClassroomInsight(SchoolAndTimestampModelMixin):
    """
    Represents a teaching insight shared anonymously by teachers.
    Allows teachers to share effective strategies while protecting student privacy.
    """
    CATEGORY_CHOICES = [
        ('high_engagement', 'High Engagement Strategies'),
        ('goal_achievement', 'Goal Achievement Techniques'),
        ('reading_variety', 'Encouraging Reading Variety'),
        ('student_motivation', 'Student Motivation Methods'),
        ('classroom_management', 'Classroom Management'),
        ('progress_tracking', 'Progress Tracking'),
    ]
    
    METRIC_CHOICES = [
        ('pages_increase', 'Pages read increased'),
        ('engagement_increase', 'Student engagement increased'),
        ('goal_completion', 'Goal completion improved'),
        ('reading_frequency', 'Reading frequency increased'),
        ('book_variety', 'Book variety expanded'),
    ]
    
    # Anonymous sharing - no direct teacher reference
    school = models.ForeignKey(School, on_delete=models.CASCADE, db_index=True)
    teacher_hash = models.CharField(max_length=64, db_index=True)  # Hashed teacher ID for anonymity
    
    # Insight content
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, db_index=True)
    title = models.CharField(max_length=100)
    description = models.TextField(max_length=1000)
    implementation_tips = models.TextField(max_length=500, blank=True, null=True)
    success_metric = models.CharField(max_length=20, choices=METRIC_CHOICES, blank=True, null=True)
    
    # Engagement tracking
    helpful_count = models.PositiveIntegerField(default=0)
    view_count = models.PositiveIntegerField(default=0)
    
    # Contact preferences
    allow_contact = models.BooleanField(default=False)
    
    # Moderation
    is_approved = models.BooleanField(default=True)  # For future moderation system
    is_featured = models.BooleanField(default=False)  # For highlighting great insights
    
    class Meta:
        ordering = ['-created_date']
        indexes = [
            models.Index(fields=['school', 'category', '-created_date']),
            models.Index(fields=['school', '-helpful_count']),
            models.Index(fields=['school', '-created_date']),
        ]
    
    def save(self, *args, **kwargs):
        # Auto-generate teacher hash for anonymity if not set
        if not self.teacher_hash and hasattr(self, '_teacher_user'):
            import hashlib
            self.teacher_hash = hashlib.sha256(
                f"teacher_{self._teacher_user.id}_{self.school.id}".encode()
            ).hexdigest()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.get_category_display()}: {self.title}"


class InsightHelpful(models.Model):
    """
    Track which teachers have marked insights as helpful (prevents duplicate votes).
    """
    insight = models.ForeignKey(ClassroomInsight, on_delete=models.CASCADE, related_name='helpful_votes')
    teacher_hash = models.CharField(max_length=64)  # Same hashing as ClassroomInsight
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['insight', 'teacher_hash']
        indexes = [
            models.Index(fields=['insight', 'teacher_hash']),
        ]
    
    def __str__(self):
        return f"Helpful vote for: {self.insight.title}"