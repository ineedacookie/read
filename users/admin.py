from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from admin_auto_filters.filters import AutocompleteFilter

from .forms import CustomUserCreationForm, CustomUserChangeForm
from .models import CustomUser, School, Classroom, ReadingGroup, StudentParentRelation


class SchoolFilter(AutocompleteFilter):
    title = 'School'
    field_name = 'school'


class UserFilter(AutocompleteFilter):
    title = 'User'
    field_name = 'user'


class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser

    list_display = ('username', 'email', 'school', 'is_active', 'created_date')
    list_filter = ('username', SchoolFilter, 'is_active', 'created_date', 'is_staff', 'user_type')
    fieldsets = (
        (None, {'fields': (
            'school', 'user_type', 'email', 'password', 'first_name', 'last_initial', 'change_email',
            'verified')}),
        ('Permissions', {'fields': ('is_active', 'is_staff')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'school', 'user_type', 'email', 'first_name', 'last_initial',
                'verified', 'password1', 'password2', 'is_staff', 'is_active')}
         ),
    )
    search_fields = ('username', 'email',)
    autocomplete_fields = ('school',)
    ordering = ('email',)

    class Media:
        pass


class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_date', 'updated_date')
    search_fields = ('name',)
    ordering = ('name',)


class ClassroomAdmin(admin.ModelAdmin):
    list_display = ('school', 'name', 'created_date', 'updated_date')
    autocomplete_fields = ('school', )
    search_fields = ('name', 'teachers__username')
    ordering = ('name',)


class ReadingGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_date', 'updated_date')
    autocomplete_fields = ('managers', 'students')
    search_fields = ('name', 'managers__username')
    ordering = ('name',)


class StudentParentRelationAdmin(admin.ModelAdmin):
    list_display = ('student', 'parent', 'created_date', 'updated_date')
    autocomplete_fields = ('student', 'parent')
    search_fields = ('student__username', 'parent__username')
    ordering = ('student', 'parent')


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(School, SchoolAdmin)
admin.site.register(Classroom, ClassroomAdmin)
admin.site.register(ReadingGroup, ReadingGroupAdmin)
admin.site.register(StudentParentRelation, StudentParentRelationAdmin)
