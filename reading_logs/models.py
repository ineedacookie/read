from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from users.models import CustomUser, School, ReadingGroup, Classroom


class Log(models.Model):
    """
    Represents a reading log entry for a student.
    
    Attributes:
        student: The student who created this reading log
        school: The school the student belongs to  
        date: The date the reading was done
        title: Title of the book/material read
        author: Author of the book/material
        pages: Number of pages read
        minutes: Minutes spent reading
        rating: Student's rating of the material (0.00-5.00)
        comments: Additional comments about the reading
    """
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, db_index=True)
    school = models.ForeignKey(School, on_delete=models.CASCADE, db_index=True)  # Required for data integrity
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
    created_at = models.DateTimeField(auto_now_add=True, null=True)  # Track when log was created
    updated_at = models.DateTimeField(auto_now=True, null=True)  # Track when log was last modified

    class Meta:
        ordering = ['-date', '-created_at']  # Most recent first
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
        from django.core.exceptions import ValidationError
        if self.student.school != self.school:
            raise ValidationError("Log school must match student school")
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