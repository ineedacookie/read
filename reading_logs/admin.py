from django.contrib import admin
from admin_auto_filters.filters import AutocompleteFilter

from .models import Log, DailyGoal, TotalGoal


class SchoolFilter(AutocompleteFilter):
    title = 'School'
    field_name = 'school'


class StudentFilter(AutocompleteFilter):
    title = 'Student'
    field_name = 'student'


@admin.register(Log)
class LogAdmin(admin.ModelAdmin):
    list_display = ('student', 'school', 'date', 'title', 'author', 'pages', 'minutes', 'rating')
    list_filter = ('date', SchoolFilter, 'rating')
    search_fields = ('student__email', 'student__first_name', 'title', 'author')
    autocomplete_fields = ('student', 'school')
    ordering = ('-date', 'student')
    date_hierarchy = 'date'


@admin.register(DailyGoal)
class DailyGoalAdmin(admin.ModelAdmin):
    list_display = ('school', 'student', 'classroom', 'reading_group', 'type', 'value', 'created_at')
    list_filter = ('type', SchoolFilter, 'created_at')
    search_fields = ('student__email', 'student__first_name')
    autocomplete_fields = ('school', 'student', 'classroom', 'reading_group')
    ordering = ('-created_at',)


@admin.register(TotalGoal)
class TotalGoalAdmin(admin.ModelAdmin):
    list_display = ('school', 'student', 'classroom', 'reading_group', 'start', 'end', 'total')
    list_filter = ('start', 'end', SchoolFilter)
    search_fields = ('student__email', 'student__first_name')
    autocomplete_fields = ('school', 'student', 'classroom', 'reading_group')
    ordering = ('-start',)
