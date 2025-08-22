"""
Phase 2: Analytics API Views
RESTful endpoints for advanced analytics and reporting
"""

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.core.cache import cache
from django.db import models
from datetime import datetime, date, timedelta
import json
import logging

from .analytics import ReadingAnalytics
from users.models import Classroom, ReadingGroup, CustomUser

logger = logging.getLogger('reading_logs.analytics')


@login_required
@require_http_methods(["GET"])
def school_analytics_api(request):
    """
    School-wide analytics endpoint
    For administrators and district managers
    """
    # Security: Only administrators can access school-wide data
    if request.user.user_type not in ['administrator', 'teacher']:
        logger.warning(f"Unauthorized school analytics access by user {request.user.id}")
        return JsonResponse({'status': 'error', 'message': 'Access denied'}, status=403)
    
    try:
        # Get date range with validation
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        if start_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({'status': 'error', 'message': 'Invalid start_date format'}, status=400)
        
        if end_date:
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({'status': 'error', 'message': 'Invalid end_date format'}, status=400)
        
        # Security: Date range validation
        if start_date and end_date and start_date > end_date:
            return JsonResponse({'status': 'error', 'message': 'Start date must be before end date'}, status=400)
        
        # Performance: Check cache first
        cache_key = f"school_analytics_{request.user.school.id}_{start_date}_{end_date}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return JsonResponse({'status': 'success', 'data': cached_data, 'cached': True})
        
        # Generate analytics
        analytics = ReadingAnalytics(user=request.user)
        data = analytics.get_school_overview(start_date, end_date)
        
        # Cache for 15 minutes
        cache.set(cache_key, data, 900)
        
        logger.info(f"School analytics generated for user {request.user.id}")
        
        return JsonResponse({'status': 'success', 'data': data})
        
    except Exception as e:
        logger.error(f"Error generating school analytics for user {request.user.id}: {str(e)}")
        return JsonResponse({'status': 'error', 'message': 'Unable to generate analytics'}, status=500)


@login_required
@require_http_methods(["GET"])
def classroom_analytics_api(request, classroom_id):
    """
    Classroom-specific analytics endpoint
    For teachers and administrators
    """
    try:
        # Security: Verify access to classroom
        classroom = Classroom.objects.get(id=classroom_id, school=request.user.school)
        
        # Check permissions
        if request.user.user_type == 'teacher':
            if not classroom.teachers.filter(id=request.user.id).exists():
                logger.warning(f"Teacher {request.user.id} attempted to access unauthorized classroom {classroom_id}")
                return JsonResponse({'status': 'error', 'message': 'Access denied'}, status=403)
        elif request.user.user_type not in ['administrator']:
            return JsonResponse({'status': 'error', 'message': 'Access denied'}, status=403)
        
        # Get date range
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # Performance: Check cache
        cache_key = f"classroom_analytics_{classroom_id}_{start_date}_{end_date}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return JsonResponse({'status': 'success', 'data': cached_data, 'cached': True})
        
        # Generate analytics
        analytics = ReadingAnalytics(user=request.user)
        data = analytics.get_classroom_analytics(classroom_id, start_date, end_date)
        
        # Cache for 10 minutes
        cache.set(cache_key, data, 600)
        
        logger.info(f"Classroom analytics generated for classroom {classroom_id} by user {request.user.id}")
        
        return JsonResponse({'status': 'success', 'data': data})
        
    except Classroom.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Classroom not found'}, status=404)
    except ValueError as e:
        return JsonResponse({'status': 'error', 'message': 'Invalid date format'}, status=400)
    except Exception as e:
        logger.error(f"Error generating classroom analytics for user {request.user.id}: {str(e)}")
        return JsonResponse({'status': 'error', 'message': 'Unable to generate analytics'}, status=500)


@login_required
@require_http_methods(["GET"])
def student_analytics_api(request, student_id):
    """
    Individual student analytics endpoint
    For teachers, parents, administrators, and the student themselves
    """
    try:
        # Security: Verify access to student data
        student = CustomUser.objects.get(
            id=student_id, 
            school=request.user.school,
            user_type='student'
        )
        
        # Check permissions
        has_access = False
        
        if request.user.user_type == 'student' and request.user.id == student_id:
            has_access = True
        elif request.user.user_type == 'parent':
            # Check if this parent has access to this student
            from users.models import StudentParentRelation
            has_access = StudentParentRelation.objects.filter(
                parent=request.user,
                student=student
            ).exists()
        elif request.user.user_type == 'teacher':
            # Check if teacher has access through classroom or reading group
            has_access = (
                Classroom.objects.filter(
                    teachers=request.user,
                    students=student
                ).exists() or
                ReadingGroup.objects.filter(
                    managers=request.user,
                    students=student
                ).exists()
            )
        elif request.user.user_type == 'administrator':
            has_access = True
        
        if not has_access:
            logger.warning(f"Unauthorized student analytics access: user {request.user.id} to student {student_id}")
            return JsonResponse({'status': 'error', 'message': 'Access denied'}, status=403)
        
        # Get date range
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # Performance: Check cache
        cache_key = f"student_analytics_{student_id}_{start_date}_{end_date}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return JsonResponse({'status': 'success', 'data': cached_data, 'cached': True})
        
        # Generate analytics
        analytics = ReadingAnalytics(user=request.user)
        data = analytics.get_student_detailed_analytics(student_id, start_date, end_date)
        
        # Cache for 5 minutes
        cache.set(cache_key, data, 300)
        
        logger.info(f"Student analytics generated for student {student_id} by user {request.user.id}")
        
        return JsonResponse({'status': 'success', 'data': data})
        
    except CustomUser.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Student not found'}, status=404)
    except ValueError as e:
        return JsonResponse({'status': 'error', 'message': 'Invalid date format'}, status=400)
    except Exception as e:
        logger.error(f"Error generating student analytics for user {request.user.id}: {str(e)}")
        return JsonResponse({'status': 'error', 'message': 'Unable to generate analytics'}, status=500)


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
        
        # Security: Validate student IDs list
        if not isinstance(student_ids, list) or len(student_ids) < 2:
            return JsonResponse({'status': 'error', 'message': 'At least 2 student IDs required'}, status=400)
        
        if len(student_ids) > 10:  # Prevent abuse
            return JsonResponse({'status': 'error', 'message': 'Maximum 10 students for comparison'}, status=400)
        
        # Verify access to all students
        accessible_students = []
        
        for student_id in student_ids:
            try:
                student = CustomUser.objects.get(
                    id=student_id,
                    school=request.user.school,
                    user_type='student'
                )
                
                # Check access permissions (similar to student_analytics_api)
                has_access = False
                
                if request.user.user_type == 'parent':
                    from users.models import StudentParentRelation
                    has_access = StudentParentRelation.objects.filter(
                        parent=request.user,
                        student=student
                    ).exists()
                elif request.user.user_type == 'teacher':
                    has_access = (
                        Classroom.objects.filter(
                            teachers=request.user,
                            students=student
                        ).exists() or
                        ReadingGroup.objects.filter(
                            managers=request.user,
                            students=student
                        ).exists()
                    )
                elif request.user.user_type == 'administrator':
                    has_access = True
                
                if has_access:
                    accessible_students.append(student_id)
                    
            except CustomUser.DoesNotExist:
                continue
        
        if len(accessible_students) < 2:
            return JsonResponse({'status': 'error', 'message': 'Insufficient accessible students for comparison'}, status=403)
        
        # Get date range
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # Generate comparison report
        analytics = ReadingAnalytics(user=request.user)
        comparison_data = analytics.generate_comparison_report(
            accessible_students, start_date, end_date
        )
        
        logger.info(f"Comparison report generated by user {request.user.id} for {len(accessible_students)} students")
        
        return JsonResponse({'status': 'success', 'data': comparison_data})
        
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'}, status=400)
    except ValueError as e:
        return JsonResponse({'status': 'error', 'message': 'Invalid date format'}, status=400)
    except Exception as e:
        logger.error(f"Error generating comparison report for user {request.user.id}: {str(e)}")
        return JsonResponse({'status': 'error', 'message': 'Unable to generate comparison report'}, status=500)


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
            return JsonResponse({'status': 'error', 'message': 'Access denied'}, status=403)
        
        if scope == 'classroom':
            if not scope_id:
                return JsonResponse({'status': 'error', 'message': 'Classroom ID required'}, status=400)
            
            try:
                classroom = Classroom.objects.get(id=scope_id, school=request.user.school)
                if request.user.user_type == 'teacher':
                    if not classroom.teachers.filter(id=request.user.id).exists():
                        return JsonResponse({'status': 'error', 'message': 'Access denied'}, status=403)
            except Classroom.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Classroom not found'}, status=404)
        
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
        
        # Performance: Check cache
        cache_key = f"trends_{scope}_{scope_id}_{days}_{request.user.id}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return JsonResponse({'status': 'success', 'data': cached_data, 'cached': True})
        
        # Generate trends based on scope
        analytics = ReadingAnalytics(user=request.user)
        
        if scope == 'personal' and request.user.user_type == 'student':
            data = analytics.get_student_detailed_analytics(
                request.user.id, start_date, end_date
            )
            trends = data.get('progression', [])
        elif scope == 'classroom':
            data = analytics.get_classroom_analytics(scope_id, start_date, end_date)
            trends = data.get('daily_activity', [])
        elif scope == 'school':
            data = analytics.get_school_overview(start_date, end_date)
            trends = data.get('trends', [])
        else:
            trends = []
        
        # Cache for 5 minutes
        cache.set(cache_key, trends, 300)
        
        return JsonResponse({'status': 'success', 'data': trends})
        
    except Exception as e:
        logger.error(f"Error generating trends for user {request.user.id}: {str(e)}")
        return JsonResponse({'status': 'error', 'message': 'Unable to generate trends'}, status=500)
