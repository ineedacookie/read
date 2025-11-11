"""
Phase 2: Analytics API Views
RESTful endpoints for advanced analytics and reporting
"""

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_http_methods
from datetime import date, timedelta
import json
import logging

from .analytics import ReadingAnalytics
from users.models import Classroom, CustomUser
from read.utils.permission_helpers import check_user_type
from read.utils.response_helpers import (
    error_response,
    permission_denied_response,
    server_error_response,
    success_response,
)
from read.utils.validation_helpers import ValidationError as UtilsValidationError
from read.utils.view_helpers import (
    cached_data,
    get_classroom_or_404,
    get_date_range_from_params,
    resolve_student_access,
    resolve_students_access,
)

logger = logging.getLogger('reading_logs.analytics')


@login_required
@require_http_methods(["GET"])
def school_analytics_api(request):
    """
    School-wide analytics endpoint
    For administrators and district managers
    """
    try:
        check_user_type(request.user, ['administrator', 'teacher'])
    except PermissionDenied:
        logger.warning(f"Unauthorized school analytics access by user {request.user.id}")
        return permission_denied_response(request.user.id, action_attempted='school analytics')
    
    try:
        start_date, end_date, _ = get_date_range_from_params(
            request.GET.get('start_date'),
            request.GET.get('end_date'),
            default_days=30,
            max_days_back=1095,
            max_range_days=365
        )
        
        cache_key = f"school_analytics_{request.user.school.id}_{start_date}_{end_date}"
        data, from_cache = cached_data(
            cache_key,
            900,
            lambda: ReadingAnalytics(user=request.user).get_school_overview(start_date, end_date)
        )
        
        if from_cache:
            return success_response("Analytics retrieved", {'data': data, 'cached': True})
        
        logger.info(f"School analytics generated for user {request.user.id}")
        return success_response("Analytics retrieved", {'data': data})
        
    except UtilsValidationError as e:
        return error_response(str(e), status=400, user_id=request.user.id)
    except Exception as e:
        logger.error(f"Error generating school analytics for user {request.user.id}: {str(e)}")
        return server_error_response(request.user.id, error_details=str(e))


@login_required
@require_http_methods(["GET"])
def classroom_analytics_api(request, classroom_id):
    """
    Classroom-specific analytics endpoint
    For teachers and administrators
    """
    try:
        classroom = get_classroom_or_404(classroom_id, request.user)
        
        start_date, end_date, _ = get_date_range_from_params(
            request.GET.get('start_date'),
            request.GET.get('end_date'),
            default_days=30
        )
        
        cache_key = f"classroom_analytics_{classroom_id}_{start_date}_{end_date}"
        data, from_cache = cached_data(
            cache_key,
            600,
            lambda: ReadingAnalytics(user=request.user).get_classroom_analytics(
                classroom.id, start_date, end_date
            )
        )
        
        if from_cache:
            return success_response("Analytics retrieved", {'data': data, 'cached': True})
        
        logger.info(f"Classroom analytics generated for classroom {classroom_id} by user {request.user.id}")
        return success_response("Analytics retrieved", {'data': data})
    
    except Classroom.DoesNotExist:
        return error_response('Classroom not found', status=404, user_id=request.user.id)
    except UtilsValidationError as e:
        return error_response(str(e), status=400, user_id=request.user.id)
    except PermissionDenied:
        logger.warning(f"Access denied for classroom analytics: user {request.user.id} classroom {classroom_id}")
        return permission_denied_response(request.user.id, action_attempted='classroom analytics')
    except Exception as e:
        logger.error(f"Error generating classroom analytics for user {request.user.id}: {str(e)}")
        return server_error_response(request.user.id, error_details=str(e))


@login_required
@require_http_methods(["GET"])
def student_analytics_api(request, student_id):
    """
    Individual student analytics endpoint
    For teachers, parents, administrators, and the student themselves
    """
    try:
        student = resolve_student_access(request.user, student_id)
        
        start_date, end_date, _ = get_date_range_from_params(
            request.GET.get('start_date'),
            request.GET.get('end_date'),
            default_days=90
        )
        
        cache_key = f"student_analytics_{student_id}_{start_date}_{end_date}"
        data, from_cache = cached_data(
            cache_key,
            300,
            lambda: ReadingAnalytics(user=request.user).get_student_detailed_analytics(
                student.id, start_date, end_date
            )
        )
        
        if from_cache:
            return success_response("Analytics retrieved", {'data': data, 'cached': True})
        
        logger.info(f"Student analytics generated for student {student_id} by user {request.user.id}")
        return success_response("Analytics retrieved", {'data': data})
        
    except CustomUser.DoesNotExist:
        return error_response('Student not found', status=404, user_id=request.user.id)
    except PermissionDenied:
        logger.warning(f"Unauthorized student analytics access: user {request.user.id} to student {student_id}")
        return permission_denied_response(request.user.id, action_attempted='student analytics')
    except UtilsValidationError as e:
        return error_response(str(e), status=400, user_id=request.user.id)
    except Exception as e:
        logger.error(f"Error generating student analytics for user {request.user.id}: {str(e)}")
        return server_error_response(request.user.id, error_details=str(e))


@login_required
@require_http_methods(["POST"])
def comparison_report_api(request):
    """
    Generate comparison reports for multiple students
    For teachers and parents with multiple children
    """
    try:
        data = json.loads(request.body)
        student_ids = data.get('student_ids', [])
        
        if not isinstance(student_ids, list) or len(student_ids) < 2:
            return error_response('At least 2 student IDs required', status=400, user_id=request.user.id)
        
        if len(student_ids) > 10:
            return error_response('Maximum 10 students for comparison', status=400, user_id=request.user.id)
        
        accessible_students = list(
            resolve_students_access(request.user, student_ids).values_list('id', flat=True)
        )
        
        if len(accessible_students) < 2:
            return permission_denied_response(
                request.user.id,
                action_attempted='comparison report - insufficient students'
            )
        
        start_date, end_date, _ = get_date_range_from_params(
            data.get('start_date'),
            data.get('end_date'),
            default_days=30
        )
        
        analytics = ReadingAnalytics(user=request.user)
        comparison_data = analytics.generate_comparison_report(
            accessible_students, start_date, end_date
        )
        
        logger.info(f"Comparison report generated by user {request.user.id} for {len(accessible_students)} students")
        return success_response("Comparison generated", {'data': comparison_data})
        
    except json.JSONDecodeError:
        return error_response('Invalid JSON data', status=400, user_id=request.user.id)
    except UtilsValidationError as e:
        return error_response(str(e), status=400, user_id=request.user.id)
    except Exception as e:
        logger.error(f"Error generating comparison report for user {request.user.id}: {str(e)}")
        return server_error_response(request.user.id, error_details=str(e))


@login_required
@require_http_methods(["GET"])
def reading_trends_api(request):
    """
    Get reading trends for charts and visualizations
    Optimized for dashboard widgets
    """
    try:
        # Get scope parameter
        scope = request.GET.get('scope', 'personal')  # personal, classroom, school
        scope_id = request.GET.get('scope_id')  # classroom_id if scope=classroom
        
        # Security and permission checking
        if scope == 'school' and request.user.user_type not in ['administrator']:
            return permission_denied_response(request.user.id, action_attempted='school trends')
        
        if scope == 'classroom':
            if not scope_id:
                return error_response('Classroom ID required', status=400, user_id=request.user.id)
            
            try:
                classroom = Classroom.objects.get(id=scope_id, school=request.user.school)
                if request.user.user_type == 'teacher':
                    if not classroom.teachers.filter(id=request.user.id).exists():
                        return permission_denied_response(
                            request.user.id,
                            action_attempted=f'classroom trends {scope_id}'
                        )
            except Classroom.DoesNotExist:
                return error_response('Classroom not found', status=404, user_id=request.user.id)
        
        # Get time period
        period = request.GET.get('period', '30')  # days
        try:
            days = int(period)
            if days > 365:  # Limit to 1 year
                days = 365
        except ValueError:
            days = 30
        
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        def _generate_trends():
            analytics = ReadingAnalytics(user=request.user)
            
            if scope == 'personal' and request.user.user_type == 'student':
                data = analytics.get_student_detailed_analytics(
                    request.user.id, start_date, end_date
                )
                return data.get('progression', [])
            if scope == 'classroom':
                data = analytics.get_classroom_analytics(scope_id, start_date, end_date)
                return data.get('daily_activity', [])
            if scope == 'school':
                data = analytics.get_school_overview(start_date, end_date)
                return data.get('trends', [])
            return []
        
        cache_key = f"trends_{scope}_{scope_id}_{days}_{request.user.id}"
        trends, from_cache = cached_data(cache_key, 300, _generate_trends)
        
        if from_cache:
            return success_response("Trends retrieved", {'data': trends, 'cached': True})
        
        return success_response("Trends retrieved", {'data': trends})
        
    except Exception as e:
        logger.error(f"Error generating trends for user {request.user.id}: {str(e)}")
        return server_error_response(request.user.id, error_details=str(e))
