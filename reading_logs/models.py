from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from users.models import CustomUser, School


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
