from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from users.models import CustomUser, School, ReadingGroup, Classroom


class Log(models.Model):
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


# class LogFormDisplaySettings(models.Model):
#     school = models.ForeignKey(School, on_delete=models.SET_NULL, null=True, blank=True)
#     name = models.CharField(max_length=255)
#     title_display = models.BooleanField(default=True)
#     title_required = models.BooleanField(default=False)
#     author_display = models.BooleanField(default=True)
#     author_required = models.BooleanField(default=False)
#     pages_display = models.BooleanField(default=True)
#     pages_required = models.BooleanField(default=False)
#     minutes_display = models.BooleanField(default=True)
#     minutes_required = models.BooleanField(default=False)
#     rating_display = models.BooleanField(default=True)
#     rating_required = models.BooleanField(default=False)
#     comments_display = models.BooleanField(default=True)
#     comments_required = models.BooleanField(default=False)


class DailyGoal(models.Model):
    GOAL_TYPE = {
        ('pages', 'Pages'),
        ('minutes', 'Minutes'),
    }

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


class TotalGoal(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, null=True, blank=True)
    reading_group = models.ForeignKey(ReadingGroup, on_delete=models.CASCADE, null=True, blank=True)
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    start = models.DateField()
    end = models.DateField()
    total = models.PositiveIntegerField(default=0)