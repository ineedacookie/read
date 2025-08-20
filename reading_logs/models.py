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
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    school = models.ForeignKey(School, on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateField()
    title = models.CharField(max_length=255, blank=True, null=True)
    author = models.CharField(max_length=255, blank=True, null=True)
    pages = models.IntegerField(blank=True, null=True)
    minutes = models.IntegerField(blank=True, null=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, blank=True, null=True, validators=[
        MinValueValidator(0.00),
        MaxValueValidator(5.00)
    ])
    comments = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.school:
            self.school = self.student.school
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