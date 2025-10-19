"""
View Helper Functions
Commonly used functions across views to reduce code duplication
"""

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied
from django.db.models import Q
import logging

logger = logging.getLogger(__name__)


def get_user_students(user):
    """
    Get all students accessible to the given user.
    Returns queryset based on user type.
    """
    from users.models import CustomUser, Classroom, ReadingGroup, StudentParentRelation
    
    if user.user_type == 'administrator':
        # Administrators see all students in their school
        return CustomUser.objects.filter(
            school=user.school,
            user_type='student'
        )
    
    elif user.user_type == 'teacher':
        # Teachers see students in their classrooms/groups
        student_ids = set()
        
        classrooms = Classroom.objects.filter(
            school=user.school,
            teachers=user
        )
        for classroom in classrooms:
            student_ids.update(classroom.students.values_list('id', flat=True))
        
        groups = ReadingGroup.objects.filter(
            school=user.school,
            managers=user
        )
        for group in groups:
            student_ids.update(group.students.values_list('id', flat=True))
        
        return CustomUser.objects.filter(id__in=student_ids)
    
    elif user.user_type == 'parent':
        # Parents see their children
        child_ids = StudentParentRelation.objects.filter(
            parent=user,
            school=user.school
        ).values_list('student_id', flat=True)
        
        return CustomUser.objects.filter(id__in=child_ids)
    
    elif user.user_type == 'student':
        # Students see only themselves
        return CustomUser.objects.filter(id=user.id)
    
    return CustomUser.objects.none()


def verify_student_access(user, student_id):
    """
    Verify that the user has permission to access the given student.
    Returns the student object if permitted, raises PermissionDenied otherwise.
    """
    from users.models import CustomUser
    
    accessible_students = get_user_students(user)
    
    try:
        student = accessible_students.get(id=student_id, user_type='student')
        return student
    except CustomUser.DoesNotExist:
        logger.warning(
            f"User {user.id} ({user.user_type}) attempted to access "
            f"student {student_id} without permission"
        )
        raise PermissionDenied("You don't have permission to access this student")


def verify_reading_log_access(user, log_id):
    """
    Verify that the user has permission to access the given reading log.
    Returns the log object if permitted, raises PermissionDenied otherwise.
    """
    from reading_logs.models import Log
    
    try:
        log = Log.objects.select_related('student', 'school').get(id=log_id)
        
        # Check if user can access this log's student
        accessible_students = get_user_students(user)
        
        if log.student not in accessible_students:
            raise PermissionDenied("You don't have permission to access this reading log")
        
        return log
        
    except Log.DoesNotExist:
        raise PermissionDenied("Reading log not found")


def get_date_range_from_request(request, default_days=30):
    """
    Extract and validate date range from request.
    Returns (start_date, end_date) tuple.
    """
    from datetime import datetime, date, timedelta
    
    # Common date range presets
    date_range = request.GET.get('date_range', 'month')
    
    if date_range == 'week':
        start_date = date.today() - timedelta(days=7)
        end_date = date.today()
    elif date_range == 'month':
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()
    elif date_range == 'quarter':
        start_date = date.today() - timedelta(days=90)
        end_date = date.today()
    elif date_range == 'year':
        start_date = date.today() - timedelta(days=365)
        end_date = date.today()
    elif date_range == 'custom':
        # Parse custom dates
        start_str = request.GET.get('start_date')
        end_str = request.GET.get('end_date')
        
        try:
            start_date = datetime.strptime(start_str, '%Y-%m-%d').date() if start_str else date.today() - timedelta(days=default_days)
            end_date = datetime.strptime(end_str, '%Y-%m-%d').date() if end_str else date.today()
        except ValueError:
            # Invalid dates, use default
            start_date = date.today() - timedelta(days=default_days)
            end_date = date.today()
    else:
        # Default
        start_date = date.today() - timedelta(days=default_days)
        end_date = date.today()
    
    return start_date, end_date


def build_search_query(queryset, search_term, search_fields):
    """
    Build a search query across multiple fields.
    
    Args:
        queryset: Base queryset to filter
        search_term: Search string
        search_fields: List of field names to search
    
    Returns:
        Filtered queryset
    """
    if not search_term or not search_fields:
        return queryset
    
    q_objects = Q()
    for field in search_fields:
        q_objects |= Q(**{f"{field}__icontains": search_term})
    
    return queryset.filter(q_objects)


def paginate_queryset(queryset, request, per_page=10):
    """
    Paginate a queryset based on request parameters.
    
    Returns:
        Paginated page object
    """
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    
    page_number = request.GET.get('page', 1)
    paginator = Paginator(queryset, per_page)
    
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    return page_obj


def json_success(message="Success", data=None, status=200):
    """
    Return a standardized success JSON response.
    """
    response_data = {
        'success': True,
        'message': message
    }
    
    if data is not None:
        response_data['data'] = data
    
    return JsonResponse(response_data, status=status)


def json_error(message="An error occurred", errors=None, status=400):
    """
    Return a standardized error JSON response.
    """
    response_data = {
        'success': False,
        'message': message
    }
    
    if errors is not None:
        response_data['errors'] = errors
    
    return JsonResponse(response_data, status=status)


def get_classroom_or_404(classroom_id, user):
    """
    Get classroom ensuring user has access.
    Raises PermissionDenied if user cannot access.
    """
    from users.models import Classroom
    
    if user.user_type == 'administrator':
        return get_object_or_404(
            Classroom,
            id=classroom_id,
            school=user.school
        )
    elif user.user_type == 'teacher':
        return get_object_or_404(
            Classroom,
            id=classroom_id,
            school=user.school,
            teachers=user
        )
    else:
        raise PermissionDenied("You don't have permission to access classrooms")


def get_reading_group_or_404(group_id, user):
    """
    Get reading group ensuring user has access.
    Raises PermissionDenied if user cannot access.
    """
    from users.models import ReadingGroup
    
    if user.user_type == 'administrator':
        return get_object_or_404(
            ReadingGroup,
            id=group_id,
            school=user.school
        )
    elif user.user_type == 'teacher':
        return get_object_or_404(
            ReadingGroup,
            id=group_id,
            school=user.school,
            managers=user
        )
    else:
        raise PermissionDenied("You don't have permission to access reading groups")


def calculate_reading_stats(logs):
    """
    Calculate aggregate reading statistics from a queryset of logs.
    
    Args:
        logs: Queryset of Log objects
    
    Returns:
        dict with total_pages, total_minutes, total_books, avg_rating
    """
    from django.db.models import Sum, Count, Avg
    
    stats = logs.aggregate(
        total_pages=Sum('pages_read'),
        total_minutes=Sum('reading_time_minutes'),
        total_books=Count('id', distinct=True),
        avg_rating=Avg('rating')
    )
    
    return {
        'total_pages': stats['total_pages'] or 0,
        'total_minutes': stats['total_minutes'] or 0,
        'total_books': stats['total_books'] or 0,
        'avg_rating': round(stats['avg_rating'], 2) if stats['avg_rating'] else 0
    }


def format_duration(minutes):
    """
    Format minutes into a human-readable duration.
    
    Examples:
        45 → "45m"
        90 → "1h 30m"
        125 → "2h 5m"
    """
    if not minutes:
        return "0m"
    
    hours = minutes // 60
    mins = minutes % 60
    
    if hours > 0:
        if mins > 0:
            return f"{hours}h {mins}m"
        return f"{hours}h"
    
    return f"{mins}m"


def sanitize_user_data(user, fields=None):
    """
    Return sanitized user data safe for JSON responses.
    Only returns non-sensitive fields.
    """
    if fields is None:
        fields = ['id', 'first_name', 'last_name', 'email', 'user_type']
    
    return {
        field: getattr(user, field, None)
        for field in fields
        if hasattr(user, field)
    }

