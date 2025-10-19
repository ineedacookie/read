"""
View Mixins for Class-Based Views
Provides reusable functionality for CBVs including:
- School-based filtering
- User type permission checking
- AJAX response handling
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.db.models import Q


class SchoolFilterMixin:
    """
    Automatically filter querysets by the user's school.
    Use with ListView, DetailView, etc.
    """
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by school if user has one
        if hasattr(self.request.user, 'school') and self.request.user.school:
            if hasattr(queryset.model, 'school'):
                queryset = queryset.filter(school=self.request.user.school)
        
        return queryset


class UserTypePermissionMixin:
    """
    Restrict access to views based on user type.
    Set allowed_user_types as a list in your view.
    
    Example:
        class MyView(UserTypePermissionMixin, ListView):
            allowed_user_types = ['teacher', 'administrator']
    """
    allowed_user_types = []
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        if self.allowed_user_types and request.user.user_type not in self.allowed_user_types:
            raise PermissionDenied(
                f"Access denied. This page is only accessible to: {', '.join(self.allowed_user_types)}"
            )
        
        return super().dispatch(request, *args, **kwargs)


class AjaxResponseMixin:
    """
    Mixin for views that need to return JSON responses.
    Automatically detects AJAX requests and returns JSON.
    """
    
    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return self.render_to_json_response(context, **response_kwargs)
        return super().render_to_response(context, **response_kwargs)
    
    def render_to_json_response(self, context, **response_kwargs):
        """
        Returns a JSON response containing the context data.
        Override this method to customize the JSON structure.
        """
        return JsonResponse(self.get_json_data(context), **response_kwargs)
    
    def get_json_data(self, context):
        """
        Returns data to be serialized to JSON.
        Override this method to customize what data is returned.
        """
        return {
            'success': True,
            'data': context
        }


class TeacherAccessMixin:
    """
    Mixin for views that should only show data for students
    assigned to the teacher (via classrooms or reading groups).
    """
    
    def get_teacher_student_ids(self):
        """Get all student IDs assigned to this teacher"""
        if self.request.user.user_type != 'teacher':
            return None
        
        from .models import Classroom, ReadingGroup
        
        student_ids = set()
        
        # Get students from classrooms
        classrooms = Classroom.objects.filter(
            school=self.request.user.school,
            teachers=self.request.user
        )
        for classroom in classrooms:
            student_ids.update(classroom.students.values_list('id', flat=True))
        
        # Get students from reading groups
        reading_groups = ReadingGroup.objects.filter(
            school=self.request.user.school,
            managers=self.request.user
        )
        for group in reading_groups:
            student_ids.update(group.students.values_list('id', flat=True))
        
        return student_ids
    
    def filter_by_teacher_students(self, queryset):
        """Filter a queryset to only include the teacher's students"""
        if self.request.user.user_type == 'administrator':
            return queryset
        
        student_ids = self.get_teacher_student_ids()
        if student_ids is None:
            return queryset.none()
        
        # Check if queryset is for students directly
        if hasattr(queryset.model, 'user_type'):
            return queryset.filter(id__in=student_ids)
        
        # Check if queryset has a 'student' field (like reading logs)
        if hasattr(queryset.model, 'student'):
            return queryset.filter(student_id__in=student_ids)
        
        return queryset


class ParentAccessMixin:
    """
    Mixin for views that should only show data for the parent's children.
    """
    
    def get_parent_child_ids(self):
        """Get all child IDs for this parent"""
        if self.request.user.user_type != 'parent':
            return None
        
        # Get children through StudentParentRelation
        from .models import StudentParentRelation
        
        relations = StudentParentRelation.objects.filter(
            parent=self.request.user,
            school=self.request.user.school
        )
        
        return set(relations.values_list('student_id', flat=True))
    
    def filter_by_parent_children(self, queryset):
        """Filter a queryset to only include the parent's children"""
        child_ids = self.get_parent_child_ids()
        if child_ids is None:
            return queryset.none()
        
        # Check if queryset is for students directly
        if hasattr(queryset.model, 'user_type'):
            return queryset.filter(id__in=child_ids)
        
        # Check if queryset has a 'student' field
        if hasattr(queryset.model, 'student'):
            return queryset.filter(student_id__in=child_ids)
        
        return queryset


class SearchableMixin:
    """
    Mixin to add search functionality to list views.
    Set search_fields as a list of field names to search.
    """
    search_fields = []
    search_param = 'search'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        search_query = self.request.GET.get(self.search_param, '').strip()
        if search_query and self.search_fields:
            # Build Q objects for OR search across all fields
            q_objects = Q()
            for field in self.search_fields:
                q_objects |= Q(**{f"{field}__icontains": search_query})
            
            queryset = queryset.filter(q_objects)
        
        return queryset


class SortableMixin:
    """
    Mixin to add sorting functionality to list views.
    Set sortable_fields as a dict mapping param names to field names.
    """
    sortable_fields = {}
    default_sort = 'id'
    sort_param = 'sort'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        sort_field = self.request.GET.get(self.sort_param, self.default_sort)
        
        # Validate sort field
        if sort_field.lstrip('-') in self.sortable_fields.values():
            queryset = queryset.order_by(sort_field)
        else:
            queryset = queryset.order_by(self.default_sort)
        
        return queryset

