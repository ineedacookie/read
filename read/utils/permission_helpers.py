"""
Permission and security helper functions to standardize access control.
Reduces code duplication for user type checks, rate limiting, and security logging.
"""

from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.contrib.auth import get_user_model
from functools import wraps
import logging

logger = logging.getLogger('reading_logs.security')


def check_user_type(user, allowed_types):
    """
    Check if user's type is in the list of allowed types.
    
    Args:
        user: Django User object
        allowed_types: List of allowed user types or single user type string
    
    Returns:
        bool: True if user type is allowed
    
    Raises:
        PermissionDenied: If user type is not allowed
    """
    if isinstance(allowed_types, str):
        allowed_types = [allowed_types]
    
    if user.user_type not in allowed_types:
        logger.warning(f"Access denied: User {user.id} (type: {user.user_type}) attempted to access resource requiring {allowed_types}")
        raise PermissionDenied(f"Access denied. Required user type: {' or '.join(allowed_types)}")
    
    return True


def check_rate_limit(user_id, action_type, max_requests=10, window_seconds=60):
    """
    Check if user has exceeded rate limit for a specific action.
    
    Args:
        user_id: User ID to check
        action_type: Type of action being rate limited
        max_requests: Maximum requests allowed in the window
        window_seconds: Time window in seconds
    
    Returns:
        bool: True if within rate limit
    
    Raises:
        PermissionDenied: If rate limit exceeded
    """
    cache_key = f"{action_type}_rate_limit_{user_id}"
    current_requests = cache.get(cache_key, 0)
    
    if current_requests >= max_requests:
        logger.warning(f"Rate limit exceeded: User {user_id} for action {action_type}")
        raise PermissionDenied("Too many requests. Please wait.")
    
    # Increment counter
    cache.set(cache_key, current_requests + 1, window_seconds)
    return True


def verify_school_access(user, resource):
    """
    Verify that user and resource belong to the same school.
    
    Args:
        user: Django User object
        resource: Resource object with school field
    
    Returns:
        bool: True if access is allowed
    
    Raises:
        PermissionDenied: If schools don't match
    """
    if hasattr(resource, 'school') and user.school != resource.school:
        logger.warning(f"Cross-school access attempt: User {user.id} (school {user.school_id}) "
                      f"tried to access resource from school {resource.school_id}")
        raise PermissionDenied("Access denied - resource not in your school")
    
    return True


def verify_parent_child_relationship(parent, child):
    """
    Verify that a parent has access to a specific child.
    
    Args:
        parent: Parent user object
        child: Student user object
    
    Returns:
        bool: True if relationship exists
    
    Raises:
        PermissionDenied: If no relationship exists
    """
    if parent.user_type != 'parent':
        raise PermissionDenied("User is not a parent")
    
    if child not in parent.children.all():
        logger.warning(f"Parent {parent.id} attempted to access non-child user {child.id}")
        raise PermissionDenied("Access denied - not your child")
    
    return True


def verify_teacher_student_access(teacher, student):
    """
    Verify that a teacher has access to a specific student.
    OPTIMIZED: Uses single query instead of looping through classrooms/groups.
    
    Args:
        teacher: Teacher user object
        student: Student user object
    
    Returns:
        bool: True if teacher has access
    
    Raises:
        PermissionDenied: If teacher doesn't have access to student
    """
    if teacher.user_type != 'teacher':
        raise PermissionDenied("User is not a teacher")
    
    # OPTIMIZED: Check if student is in teacher's accessible students with single query
    accessible_students = get_accessible_students(teacher)
    
    if not accessible_students.filter(id=student.id).exists():
        logger.warning(f"Teacher {teacher.id} attempted to access non-assigned student {student.id}")
        raise PermissionDenied("Access denied - student not in your classes")
    
    return True


def get_accessible_students(user):
    """
    Get all students accessible to a user based on their role.
    OPTIMIZED: Eliminates N+1 queries by using values_list directly.
    
    Args:
        user: Django User object
    
    Returns:
        QuerySet: Students accessible to the user
    """
    if user.user_type == 'administrator':
        return get_user_model().objects.filter(
            school=user.school, 
            user_type='student'
        ).select_related('school')
    
    elif user.user_type == 'teacher':
        from users.models import Classroom, ReadingGroup
        from django.db.models import Q
        
        # OPTIMIZED: Single query gets all student IDs from classrooms
        classroom_students = Classroom.objects.filter(
            school=user.school,
            teachers=user
        ).values_list('students', flat=True)
        
        # OPTIMIZED: Single query gets all student IDs from reading groups
        group_students = ReadingGroup.objects.filter(
            school=user.school,
            managers=user
        ).values_list('students', flat=True)
        
        # Combine the two querysets efficiently
        student_ids = set(classroom_students) | set(group_students)
        
        return get_user_model().objects.filter(
            id__in=student_ids,
            user_type='student'
        ).select_related('school')
    
    elif user.user_type == 'parent':
        return user.children.select_related('school')
    
    elif user.user_type == 'student':
        return get_user_model().objects.filter(id=user.id).select_related('school')
    
    else:
        return get_user_model().objects.none()


def get_accessible_reading_logs(user, student=None):
    """
    Get reading logs accessible to a user based on their role.
    
    Args:
        user: Django User object
        student: Optional specific student to filter logs for
    
    Returns:
        QuerySet: Reading logs accessible to the user
    """
    from reading_logs.models import Log
    
    if student:
        # Verify user has access to this specific student
        if user.user_type == 'administrator':
            verify_school_access(user, student)
        elif user.user_type == 'teacher':
            verify_teacher_student_access(user, student)
        elif user.user_type == 'parent':
            verify_parent_child_relationship(user, student)
        elif user.user_type == 'student':
            if user != student:
                raise PermissionDenied("Access denied - can only view your own logs")
        
        return Log.objects.filter(student=student, school=user.school)
    
    else:
        # Return all accessible logs
        accessible_students = get_accessible_students(user)
        return Log.objects.filter(
            student__in=accessible_students,
            school=user.school
        )


# Decorators for common permission checks
def require_user_types(allowed_types):
    """
    Decorator to require specific user types.
    
    Args:
        allowed_types: List of allowed user types or single user type string
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            check_user_type(request.user, allowed_types)
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_same_school(resource_getter):
    """
    Decorator to ensure user and resource are in the same school.
    
    Args:
        resource_getter: Function that returns the resource from request/args
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            resource = resource_getter(request, *args, **kwargs)
            verify_school_access(request.user, resource)
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# Security audit logging functions
def log_successful_action(user_id, action, resource_type=None, resource_id=None):
    """
    Log successful user action for audit trail.
    
    Args:
        user_id: User ID performing the action
        action: Description of the action
        resource_type: Type of resource affected
        resource_id: ID of resource affected
    """
    log_message = f"User {user_id} {action}"
    if resource_type and resource_id:
        log_message += f" {resource_type} {resource_id}"
    
    logger.info(log_message)


def log_security_event(user_id, event_type, details=None):
    """
    Log security-related events.
    
    Args:
        user_id: User ID involved in the event
        event_type: Type of security event
        details: Optional additional details
    """
    log_message = f"Security event - {event_type}: User {user_id}"
    if details:
        log_message += f" - {details}"
    
    logger.warning(log_message)


# Unused helper functions for access patterns have been removed.
# Permission checks are done directly in views for clarity.
