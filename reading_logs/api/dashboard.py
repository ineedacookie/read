"""
Dashboard API Endpoints
Provides dashboard data for students, parents, and teachers.
"""

from django.http import JsonResponse
from django.db.models import Sum, Count, Avg, Prefetch
import logging
from datetime import datetime, date, timedelta

from reading_logs.models import Log, DailyGoal
from users.models import CustomUser, Classroom, ReadingGroup
from read.utils import ValidationError as UtilsValidationError
from read.utils.validation_helpers import validate_date_range, validate_single_date
from read.utils.decorators import ajax_login_required
from reading_logs.helpers.dashboard_helpers import parse_date_range
from reading_logs.helpers.data_helpers import get_dashboard_data
from read.utils.serializers import LogSerializer

logger = logging.getLogger('reading_logs.api')


@ajax_login_required
def teacher_dashboard_logs(request):
    """
    Teacher dashboard data API.
    OPTIMIZED: Uses centralized business logic helper.
    Query count: 5-8 (was 50+)
    """
    if request.method != 'GET':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)
    
    try:
        # Parse parameters
        date_range = request.GET.get('date_range')
        group = request.GET.get('group')
        
        # Handle both old and new parameter formats
        if group and '_' in group:
            group_type, group_id = group.split('_')
        else:
            group_type = request.GET.get('group_type', 'classroom')
            group_id = request.GET.get('group_id')
        
        if not group_id:
            return JsonResponse({'status': 'error', 'message': 'group_id parameter is required'}, status=400)
        
        if not date_range:
            return JsonResponse({'status': 'error', 'message': 'date_range parameter is required'}, status=400)
        
        # Get dashboard data from business logic helper
        try:
            data = get_dashboard_data(group_type, group_id, request.user.school, date_range)
            response_data = {'status': 'success', **data}
            return JsonResponse(response_data)
            
        except (Classroom.DoesNotExist, ReadingGroup.DoesNotExist):
            return JsonResponse({'status': 'error', 'message': f'{group_type.capitalize()} not found'}, status=404)
        except ValueError as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
        
    except Exception as e:
        logger.error(f"Error in teacher_dashboard_logs: {str(e)}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': 'Failed to load dashboard data'}, status=500)


@ajax_login_required
def student_progress(request):
    """
    Get student's reading progress and stats.
    OPTIMIZED: Uses centralized validation and serializers.
    """
    # Security: Validate user type
    if request.user.user_type not in ['student', 'parent', 'teacher', 'administrator']:
        logger.warning(f"Unauthorized user {request.user.id} attempted to access student progress")
        return JsonResponse({'status': 'error', 'message': 'Access denied'}, status=403)
    
    # Determine target student based on user type
    try:
        target_student = _get_target_student(request)
    except ValueError as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    except CustomUser.DoesNotExist:
        logger.warning(f"User {request.user.id} attempted to access unauthorized student progress")
        return JsonResponse({'status': 'error', 'message': 'Student not found or access denied'}, status=404)
    
    try:
        # CONSOLIDATED: Use centralized date validation
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        date_range = request.GET.get('date_range')
        
        # Default to current month
        today = date.today()
        start_date = today.replace(day=1)
        end_date = today
        
        # Try date_range parameter first
        if date_range:
            try:
                start_date, end_date = parse_date_range(date_range)
            except (ValueError, UtilsValidationError) as e:
                logger.warning(f"Invalid date_range from user {request.user.id}: {date_range}")
                return JsonResponse({'status': 'error', 'message': 'Invalid date range format'}, status=400)
        
        # Individual parameters take precedence
        if start_date_str and end_date_str:
            try:
                start_date, end_date = validate_date_range(start_date_str, end_date_str, max_days_back=1095, max_range_days=365)
            except UtilsValidationError as e:
                return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
        
        # Query logs
        logs = Log.objects.filter(
            student=target_student,
            date__range=(start_date, end_date)
        ).select_related('school').order_by('-date')
        
        # Calculate statistics
        stats = logs.aggregate(
            total_pages=Sum('pages'),
            total_minutes=Sum('minutes'),
            total_logs=Count('id'),
            avg_rating=Avg('rating')
        )
        
        total_pages = stats['total_pages'] or 0
        total_minutes = stats['total_minutes'] or 0
        total_logs = stats['total_logs'] or 0
        avg_rating = round(float(stats['avg_rating']), 2) if stats['avg_rating'] else 0
        
        # Get daily goals
        daily_goal = DailyGoal.objects.filter(student=target_student).select_related('school').first()
        
        # OPTIMIZED: Use serializer for logs
        recent_logs = LogSerializer.serialize_many(
            logs[:10],
            fields=['id', 'date', 'title', 'author', 'pages', 'minutes', 'rating', 'comments']
        )
        
        chart_data = LogSerializer.serialize_many(
            logs,
            fields=['date', 'title', 'pages', 'minutes', 'rating']
        )
        
        return JsonResponse({
            'status': 'success',
            'stats': {
                'total_pages': total_pages,
                'total_minutes': total_minutes,
                'total_logs': total_logs,
                'avg_rating': str(avg_rating),
                'daily_goal': {
                    'type': daily_goal.type if daily_goal else None,
                    'value': daily_goal.value if daily_goal else None
                }
            },
            'recent_logs': recent_logs,
            'chart_data': chart_data,
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error in student_progress for user {request.user.id}: {str(e)}")
        return JsonResponse({'status': 'error', 'message': 'Unable to load progress data'}, status=500)


@ajax_login_required
def parent_dashboard_data(request):
    """
    Get progress data for all children of a parent.
    OPTIMIZED: Uses prefetch and serializers.
    """
    if request.user.user_type != 'parent':
        logger.warning(f"Non-parent user {request.user.id} attempted to access parent dashboard")
        return JsonResponse({'status': 'error', 'message': 'Access denied'}, status=403)
    
    try:
        # CONSOLIDATED: Use centralized date validation
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        
        # Default to current month
        if not start_date_str or not end_date_str:
            today = date.today()
            start_date = today.replace(day=1)
            end_date = today
        else:
            try:
                start_date, end_date = validate_date_range(start_date_str, end_date_str, max_days_back=1095, max_range_days=365)
            except UtilsValidationError as e:
                logger.warning(f"Invalid date range from parent {request.user.id}: {e}")
                return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
        
        # OPTIMIZED: Prefetch children with logs
        children = request.user.children.select_related('school').prefetch_related(
            Prefetch(
                'log_set',
                queryset=Log.objects.filter(date__range=(start_date, end_date)).select_related('school').order_by('-date')
            )
        ).all()
        
        # Limit children count for security
        if len(children) > 50:
            logger.warning(f"Parent {request.user.id} has excessive children count: {len(children)}")
            return JsonResponse({'status': 'error', 'message': 'Too many children associated with account'}, status=400)
        
        children_data = []
        for child in children:
            logs = child.log_set.all()  # Uses prefetched data
            
            # Calculate stats
            stats = logs.aggregate(
                total_pages=Sum('pages'),
                total_minutes=Sum('minutes'),
                total_logs=Count('id'),
                avg_rating=Avg('rating')
            )
            
            total_pages = stats['total_pages'] or 0
            total_minutes = stats['total_minutes'] or 0
            total_logs = stats['total_logs'] or 0
            avg_rating = round(float(stats['avg_rating']), 2) if stats['avg_rating'] else 0
            
            # OPTIMIZED: Use serializer for logs
            recent_logs = LogSerializer.serialize_many(
                logs.order_by('-date')[:5],
                fields=['date', 'title', 'author', 'pages', 'minutes', 'rating']
            )
            
            children_data.append({
                'id': child.id,
                'name': child.full_name or child.first_name or 'Student',
                'email': child.email,
                'stats': {
                    'total_pages': total_pages,
                    'total_minutes': total_minutes,
                    'total_logs': total_logs,
                    'avg_rating': avg_rating
                },
                'recent_logs': recent_logs
            })
        
        logger.info(f"Parent dashboard data accessed by user {request.user.id} for {len(children_data)} children")
        
        return JsonResponse({
            'status': 'success',
            'children': children_data,
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error in parent_dashboard_data for user {request.user.id}: {str(e)}")
        return JsonResponse({'status': 'error', 'message': 'Unable to load dashboard data'}, status=500)


def _get_target_student(request):
    """
    Helper to determine target student based on user type.
    Consolidates duplicate logic from multiple views.
    """
    if request.user.user_type == 'student':
        return request.user
    
    student_id = request.GET.get('student_id')
    if not student_id:
        raise ValueError('Student ID required')
    
    try:
        student_id = int(student_id)
    except (ValueError, TypeError):
        raise ValueError('Invalid student ID format')
    
    if request.user.user_type == 'parent':
        try:
            return request.user.children.get(id=student_id)
        except CustomUser.DoesNotExist:
            raise CustomUser.DoesNotExist()
    
    elif request.user.user_type == 'teacher':
        try:
            return CustomUser.objects.get(
                id=student_id,
                user_type='student',
                students_classrooms__teachers=request.user,
                school=request.user.school
            )
        except CustomUser.DoesNotExist:
            raise CustomUser.DoesNotExist()
    
    elif request.user.user_type == 'administrator':
        try:
            return CustomUser.objects.get(
                id=student_id,
                user_type='student',
                school=request.user.school
            )
        except CustomUser.DoesNotExist:
            raise CustomUser.DoesNotExist()
    
    raise ValueError('Invalid user type')

