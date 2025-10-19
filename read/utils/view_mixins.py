"""
View mixins and base classes to reduce code duplication across views.
Provides common patterns for permission checking, JSON responses, and form handling.
"""

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
import json
import logging

from .response_helpers import (
    success_response,
    error_response,
    validation_error_response,
    permission_denied_response,
    server_error_response,
    paginated_response
)
from .permission_helpers import (
    check_user_type,
    verify_school_access,
    log_successful_action
)

logger = logging.getLogger('reading_logs.security')


class SchoolFilteredViewMixin:
    """
    Mixin that automatically filters querysets by the user's school.
    """
    
    def get_school_filtered_queryset(self, model_class):
        """Get queryset filtered by user's school"""
        return model_class.objects.filter(school=self.request.user.school)
    
    def get_school_filtered_object(self, model_class, **kwargs):
        """Get single object filtered by user's school"""
        kwargs['school'] = self.request.user.school
        return get_object_or_404(model_class, **kwargs)


class PermissionRequiredMixin:
    """
    Mixin that checks user permissions before allowing access.
    """
    required_user_types = None  # Override in subclasses
    
    def check_permissions(self):
        """Check if user has required permissions"""
        if self.required_user_types:
            check_user_type(self.request.user, self.required_user_types)
    
    def dispatch(self, request, *args, **kwargs):
        """Override dispatch to check permissions"""
        self.check_permissions()
        return super().dispatch(request, *args, **kwargs)


class JSONResponseMixin:
    """
    Mixin that provides standardized JSON responses.
    """
    
    def json_success(self, message="Success", data=None, status=200):
        """Return standardized success JSON response"""
        return success_response(message, data, status)
    
    def json_error(self, message, status=400):
        """Return standardized error JSON response"""
        return error_response(message, status, user_id=self.request.user.id)
    
    def json_permission_denied(self, action_attempted=None):
        """Return standardized permission denied response"""
        return permission_denied_response(self.request.user.id, action_attempted)
    
    def json_server_error(self, error_details=None):
        """Return standardized server error response"""
        return server_error_response(user_id=self.request.user.id, error_details=error_details)


class PaginatedListMixin:
    """
    Mixin that provides paginated list functionality.
    """
    page_size = 10
    
    def get_paginated_queryset(self, queryset, page=None):
        """Get paginated queryset"""
        paginator = Paginator(queryset, self.page_size)
        page_number = page or self.request.GET.get('page', 1)
        return paginator.get_page(page_number)
    
    def get_paginated_json_response(self, queryset, serializer_func=None):
        """Get paginated JSON response"""
        page_obj = self.get_paginated_queryset(queryset)
        
        if serializer_func:
            data = [serializer_func(obj) for obj in page_obj.object_list]
        else:
            data = list(page_obj.object_list.values())
        
        return paginated_response(data, page_obj)


class SearchFilterMixin:
    """
    Mixin that provides search and filter functionality.
    """
    search_fields = []  # Override in subclasses
    filter_fields = []  # Override in subclasses
    
    def apply_search(self, queryset, search_query):
        """Apply search to queryset"""
        if search_query and self.search_fields:
            from django.db.models import Q
            q_objects = Q()
            for field in self.search_fields:
                q_objects |= Q(**{f"{field}__icontains": search_query})
            queryset = queryset.filter(q_objects)
        return queryset
    
    def apply_filters(self, queryset, filters):
        """Apply filters to queryset"""
        for field, value in filters.items():
            if field in self.filter_fields and value:
                queryset = queryset.filter(**{field: value})
        return queryset
    
    def get_filtered_queryset(self, base_queryset):
        """Get queryset with search and filters applied"""
        search_query = self.request.GET.get('search', '')
        
        # Apply search
        queryset = self.apply_search(base_queryset, search_query)
        
        # Apply filters
        filters = {field: self.request.GET.get(field) for field in self.filter_fields}
        queryset = self.apply_filters(queryset, filters)
        
        return queryset


class CRUDViewMixin(
    SchoolFilteredViewMixin,
    JSONResponseMixin,
    PaginatedListMixin,
    SearchFilterMixin
):
    """
    Comprehensive mixin for CRUD operations with common functionality.
    """
    model = None  # Override in subclasses
    form_class = None  # Override in subclasses
    
    def get_object(self, pk):
        """Get object by primary key, filtered by school"""
        return self.get_school_filtered_object(self.model, pk=pk)
    
    def list_objects(self):
        """List objects with pagination, search, and filters"""
        queryset = self.get_school_filtered_queryset(self.model)
        queryset = self.get_filtered_queryset(queryset)
        return self.get_paginated_json_response(queryset)
    
    def create_object(self, data):
        """Create new object"""
        if self.form_class:
            form = self.form_class(data)
            if form.is_valid():
                obj = form.save()
                log_successful_action(
                    self.request.user.id, 
                    f'created {self.model.__name__}', 
                    self.model.__name__, 
                    obj.id
                )
                return self.json_success('Object created successfully', {'id': obj.id})
            else:
                return validation_error_response(form.errors, user_id=self.request.user.id)
        else:
            return self.json_error('Form class not specified')
    
    def update_object(self, pk, data):
        """Update existing object"""
        obj = self.get_object(pk)
        
        if self.form_class:
            form = self.form_class(data, instance=obj)
            if form.is_valid():
                obj = form.save()
                log_successful_action(
                    self.request.user.id, 
                    f'updated {self.model.__name__}', 
                    self.model.__name__, 
                    obj.id
                )
                return self.json_success('Object updated successfully', {'id': obj.id})
            else:
                return validation_error_response(form.errors, user_id=self.request.user.id)
        else:
            return self.json_error('Form class not specified')
    
    def delete_object(self, pk):
        """Delete object"""
        obj = self.get_object(pk)
        obj_name = str(obj)
        obj.delete()
        
        log_successful_action(
            self.request.user.id, 
            f'deleted {self.model.__name__}', 
            self.model.__name__, 
            pk
        )
        
        return self.json_success(f'Deleted {obj_name}')


class BulkOperationMixin:
    """
    Mixin that provides bulk operation functionality.
    """
    
    def bulk_delete(self, ids):
        """Delete multiple objects by IDs"""
        if not isinstance(ids, list):
            return self.json_error('Invalid data format. Expected a list of IDs.')
        
        queryset = self.get_school_filtered_queryset(self.model)
        deleted_count = queryset.filter(id__in=ids).count()
        queryset.filter(id__in=ids).delete()
        
        log_successful_action(
            self.request.user.id, 
            f'bulk deleted {deleted_count} {self.model.__name__} objects'
        )
        
        return self.json_success(f'Deleted {deleted_count} objects')
    
    def bulk_update(self, updates):
        """Update multiple objects"""
        updated_count = 0
        
        for update_data in updates:
            obj_id = update_data.get('id')
            if obj_id:
                try:
                    obj = self.get_object(obj_id)
                    for field, value in update_data.items():
                        if field != 'id' and hasattr(obj, field):
                            setattr(obj, field, value)
                    obj.save()
                    updated_count += 1
                except Exception as e:
                    logger.warning(f"Failed to update object {obj_id}: {str(e)}")
        
        log_successful_action(
            self.request.user.id, 
            f'bulk updated {updated_count} {self.model.__name__} objects'
        )
        
        return self.json_success(f'Updated {updated_count} objects')


class FormHandlingMixin:
    """
    Mixin that provides common form handling patterns.
    """
    
    def parse_request_data(self, request):
        """Parse JSON or form data from request"""
        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body)
                if not isinstance(data, dict):
                    raise ValueError("Invalid data format")
                return data
            else:
                # Handle form data
                data = dict(request.POST)
                # Convert single-item lists to strings
                return {k: v[0] if isinstance(v, list) and len(v) == 1 else v 
                       for k, v in data.items()}
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Invalid data from user {request.user.id}: {str(e)}")
            raise ValueError("Invalid data format")
    
    def handle_form_errors(self, form):
        """Handle form validation errors"""
        errors = {}
        for field, field_errors in form.errors.items():
            errors[field] = list(field_errors)
        return validation_error_response(errors, user_id=self.request.user.id)


class AuditLogMixin:
    """
    Mixin that provides audit logging functionality.
    """
    
    def log_action(self, action, resource_type=None, resource_id=None, details=None):
        """Log user action for audit trail"""
        log_successful_action(
            self.request.user.id, 
            action, 
            resource_type, 
            resource_id
        )
        
        if details:
            logger.info(f"User {self.request.user.id} {action} - {details}")


# Function-based view decorators and helpers
def ajax_required(view_func):
    """Decorator that requires AJAX requests"""
    def wrapper(request, *args, **kwargs):
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return error_response('This endpoint requires AJAX')
        return view_func(request, *args, **kwargs)
    return wrapper


def school_filtered_view(model_class):
    """Decorator that adds school filtering to view functions"""
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            # Add school-filtered queryset to request
            request.school_queryset = model_class.objects.filter(school=request.user.school)
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def permission_required_view(required_user_types):
    """Decorator that checks user permissions for view functions"""
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            try:
                check_user_type(request.user, required_user_types)
                return view_func(request, *args, **kwargs)
            except PermissionDenied:
                return permission_denied_response(request.user.id)
        return wrapper
    return decorator


def transaction_required(view_func):
    """Decorator that wraps view in database transaction"""
    def wrapper(request, *args, **kwargs):
        with transaction.atomic():
            return view_func(request, *args, **kwargs)
    return wrapper


# Common view patterns
class BaseAPIView(
    PermissionRequiredMixin,
    CRUDViewMixin,
    BulkOperationMixin,
    FormHandlingMixin,
    AuditLogMixin
):
    """
    Base class for API views with common functionality.
    """
    
    def dispatch(self, request, *args, **kwargs):
        """Override dispatch for common setup"""
        try:
            # Check permissions
            if hasattr(self, 'check_permissions'):
                self.check_permissions()
            
            # Set up request attributes
            self.request = request
            self.args = args
            self.kwargs = kwargs
            
            return super().dispatch(request, *args, **kwargs)
            
        except PermissionDenied:
            return self.json_permission_denied()
        except Exception as e:
            logger.error(f"Unexpected error in {self.__class__.__name__}: {str(e)}")
            return self.json_server_error(str(e))
    
    def get(self, request, *args, **kwargs):
        """Handle GET requests - list objects"""
        return self.list_objects()
    
    def post(self, request, *args, **kwargs):
        """Handle POST requests - create object"""
        try:
            data = self.parse_request_data(request)
            return self.create_object(data)
        except ValueError as e:
            return self.json_error(str(e))
    
    def put(self, request, pk, *args, **kwargs):
        """Handle PUT requests - update object"""
        try:
            data = self.parse_request_data(request)
            return self.update_object(pk, data)
        except ValueError as e:
            return self.json_error(str(e))
    
    def delete(self, request, pk=None, *args, **kwargs):
        """Handle DELETE requests - delete object(s)"""
        if pk:
            return self.delete_object(pk)
        else:
            # Bulk delete
            try:
                data = self.parse_request_data(request)
                ids = data.get('ids', [])
                return self.bulk_delete(ids)
            except ValueError as e:
                return self.json_error(str(e))

