from django.shortcuts import render
from .forms import LogForm
from .models import Log, DailyGoal, TotalGoal

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from django.core.cache import cache
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils.html import escape
import logging
from datetime import datetime, date, timedelta
import json

# Set up logging for security events
logger = logging.getLogger('reading_logs.security')

from users.models import CustomUser, Classroom, ReadingGroup
from read.utils import (
    validate_date_range,
    validate_reading_log_data,
    success_response,
    error_response,
    validation_error_response,
    permission_denied_response,
    rate_limit_response,
    server_error_response,
    reading_log_created_response,
    reading_log_updated_response,
    student_progress_response,
    teacher_dashboard_response,
    parent_dashboard_response,
    check_user_type,
    check_rate_limit,
    verify_school_access,
    verify_parent_child_relationship,
    get_accessible_reading_logs,
    log_successful_action,
    ValidationError as UtilsValidationError
)


@login_required
def get_logs_by_date_range(request):
    try:
        # Validate date range
        start_date, end_date = validate_date_range(
            request.GET.get('start'), 
            request.GET.get('end')
        )
    except UtilsValidationError as e:
        return error_response(str(e), user_id=request.user.id)

    obj_id = request.GET.get('id')
    form_name = request.GET.get('form_name')

    if not obj_id or not form_name:
        return error_response('Missing required parameters: id and form_name')

    try:
        if form_name == 'Student':
            # Validate user
            try:
                user = CustomUser.objects.get(id=obj_id, user_type="student", school=request.user.school)
            except CustomUser.DoesNotExist:
                return error_response('Student not found', status=404, user_id=request.user.id)
        
            # Fetch logs within the date range for the specified user
            logs = Log.objects.filter(school=request.user.school, student=user, date__range=(start_date, end_date))
            num_students = 1
            
            # Serialize logs
            logs_data = [{
                'id': log.id, 
                'date': log.date, 
                'title': log.title, 
                'author': log.author, 
                'pages': log.pages, 
                'minutes': log.minutes, 
                'rating': log.rating, 
                'comments': log.comments
            } for log in logs]
            
        elif form_name in ['Classrooms', 'Groups']:
            if form_name == 'Classrooms':
                try:
                    temp_obj = Classroom.objects.get(school=request.user.school, id=obj_id)
                except Classroom.DoesNotExist:
                    return error_response('Classroom not found', status=404, user_id=request.user.id)
            else:
                try:
                    temp_obj = ReadingGroup.objects.get(school=request.user.school, id=obj_id)
                except ReadingGroup.DoesNotExist:
                    return error_response('Reading Group not found', status=404, user_id=request.user.id)
            
            logs = Log.objects.filter(
                school=request.user.school, 
                student__in=temp_obj.students.all(),
                date__range=(start_date, end_date)
            ).values('id', 'date', 'pages', 'minutes')
            
            num_students = temp_obj.students.count()
            logs_data = [{
                'id': log['id'], 
                'date': log['date'], 
                'pages': log['pages'], 
                'minutes': log['minutes']
            } for log in logs]
        else:
            return error_response('Invalid form_name. Must be Student, Classrooms, or Groups')

        return success_response(data={
            'logs': logs_data or [],
            'num_students': num_students
        })
        
    except Exception as e:
        return server_error_response(user_id=request.user.id, error_details=str(e))


@login_required
def teacher_dashboard_logs(request):
    if request.method == 'GET':
        date_range = request.GET.get('date_range')
        group = request.GET.get('group')
        
        # Handle both old and new parameter formats
        if group and '_' in group:
            group_type, group_id = group.split('_')
        else:
            # Try new format with separate parameters
            group_type = request.GET.get('group_type', 'classroom')
            group_id = request.GET.get('group_id')
            
        if not group_id:
            return JsonResponse({
                'status': 'error',
                'message': 'group_id parameter is required'
            }, status=400)
        if group_type == 'class':
            group_obj = Classroom.objects.get(id=group_id, school=request.user.school)
        elif group_type == 'group':
            group_obj = ReadingGroup.objects.get(id=group_id, school=request.user.school)
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid group type'})

        if date_range:
            try:
                if ' to ' in date_range:
                    start_date_str, end_date_str = date_range.split(' to ')
                    start_date = datetime.strptime(start_date_str, '%b %d, %Y').date()
                    end_date = datetime.strptime(end_date_str, '%b %d, %Y').date()
                else:
                    start_date = datetime.strptime(date_range, '%b %d, %Y').date()
                    end_date = start_date
            except ValueError:
                return JsonResponse({'status': 'error', 'message': 'Invalid date format'})
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid date range'})

        students = group_obj.students.all()
        num_days = (end_date - start_date).days + 1

        # Enhanced student data with goals and progress
        student_data = []
        group_totals = {'pages': 0, 'minutes': 0, 'students_with_goals': 0, 'struggling_students': 0}
        
        for student in students:
            # Get student's reading logs for the period
            logs = Log.objects.filter(
                student=student, 
                date__range=(start_date, end_date)
            ).values('pages', 'minutes')
            
            total_pages = sum(log['pages'] or 0 for log in logs)
            total_minutes = sum(log['minutes'] or 0 for log in logs)
            
            # Get student's goals
            daily_goal = DailyGoal.objects.filter(student=student).first()
            total_goal = TotalGoal.objects.filter(student=student).first()
            
            # Calculate goal progress
            goal_progress = None
            goal_status = 'no_goal'
            daily_avg_pages = total_pages / num_days if num_days > 0 else 0
            daily_avg_minutes = total_minutes / num_days if num_days > 0 else 0
            
            if daily_goal:
                group_totals['students_with_goals'] += 1
                if daily_goal.type == 'pages' and daily_goal.value > 0:
                    goal_progress = (daily_avg_pages / daily_goal.value) * 100
                    if goal_progress < 50:
                        goal_status = 'struggling'
                        group_totals['struggling_students'] += 1
                    elif goal_progress < 80:
                        goal_status = 'behind'
                    elif goal_progress >= 100:
                        goal_status = 'exceeding'
                    else:
                        goal_status = 'on_track'
                        
                elif daily_goal.type == 'minutes' and daily_goal.value > 0:
                    goal_progress = (daily_avg_minutes / daily_goal.value) * 100
                    if goal_progress < 50:
                        goal_status = 'struggling'
                        group_totals['struggling_students'] += 1
                    elif goal_progress < 80:
                        goal_status = 'behind'
                    elif goal_progress >= 100:
                        goal_status = 'exceeding'
                    else:
                        goal_status = 'on_track'
            
            student_info = {
                'id': student.id,
                'name': student.full_name,
                'pages': total_pages,
                'minutes': total_minutes,
                'daily_avg_pages': round(daily_avg_pages, 1),
                'daily_avg_minutes': round(daily_avg_minutes, 1),
                'goal_progress': round(goal_progress, 1) if goal_progress is not None else None,
                'goal_status': goal_status,
                'goal_type': daily_goal.type if daily_goal else None,
                'goal_value': daily_goal.value if daily_goal else None,
                'has_total_goal': total_goal is not None,
                'logs_count': len(logs)
            }
            
            student_data.append(student_info)
            group_totals['pages'] += total_pages
            group_totals['minutes'] += total_minutes

        # Calculate group-level metrics
        group_totals['students_count'] = len(students)
        group_totals['avg_pages_per_student'] = round(group_totals['pages'] / len(students) if students else 0, 1)
        group_totals['avg_minutes_per_student'] = round(group_totals['minutes'] / len(students) if students else 0, 1)
        group_totals['daily_avg_pages'] = round(group_totals['pages'] / (num_days * len(students)) if students and num_days > 0 else 0, 1)
        group_totals['daily_avg_minutes'] = round(group_totals['minutes'] / (num_days * len(students)) if students and num_days > 0 else 0, 1)
        
        # Calculate group goal progress
        if group_totals['students_with_goals'] > 0:
            students_on_track = sum(1 for s in student_data if s['goal_status'] in ['on_track', 'exceeding'])
            group_totals['goal_achievement_rate'] = round((students_on_track / group_totals['students_with_goals']) * 100, 1)
        else:
            group_totals['goal_achievement_rate'] = None

        # Sort students by goal status (struggling first) and then by name
        status_priority = {'struggling': 1, 'behind': 2, 'on_track': 3, 'exceeding': 4, 'no_goal': 5}
        student_data.sort(key=lambda x: (status_priority.get(x['goal_status'], 6), x['name']))

        response_data = {
            'status': 'success',
            'group_totals': group_totals,
            'students': student_data,
            'date_range': {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d'),
                'days': num_days
            },
            'group_info': {
                'name': group_obj.name,
                'type': group_type,
                'id': group_id
            },
            # Legacy fields for backward compatibility
            'logs': student_data,
            'pages': group_totals['pages'],
            'minutes': group_totals['minutes']
        }

        return JsonResponse(response_data)
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'})


@login_required
def manage_log(request):
    if request.method == 'POST':
        delete = request.POST.get('del', False)
        if delete:
            try:
                log_id = request.POST.get('id')
                log = Log.objects.get(id=log_id)
                log.delete()
                return JsonResponse({'status': 'success', 'message': 'Log deleted'})
            except Log.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Log not found'})
        else:
            # Create a new log entry
            form = LogForm(request.POST)
            if form.is_valid():
                log = form.save()
                return JsonResponse({'status': 'success', 'message': 'Log created', 'log_id': log.id})
            else:
                return JsonResponse({'status': 'error', 'errors': form.errors})

    elif request.method == 'PUT':
        # Update an existing log entry
        try:
            log_id = request.PUT.get('id')
            log = Log.objects.get(id=log_id)
            form = LogForm(request.PUT, instance=log)
            if form.is_valid():
                log = form.save()
                return JsonResponse({'status': 'success', 'message': 'Log updated', 'log_id': log.id})
            else:
                return JsonResponse({'status': 'error', 'errors': form.errors})
        except Log.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Log not found'})
    
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'})


@login_required
@require_http_methods(["POST"])
@transaction.atomic
def student_quick_log(request):
    """
    Quick log entry API for students - Enterprise-grade security and validation
    """
    try:
        # Check user type permission
        check_user_type(request.user, 'student')
        
        # Check rate limiting
        check_rate_limit(request.user.id, 'student_log')
        
        # Security: Check request size (prevent DoS)
        content_length = len(request.body) if hasattr(request, 'body') else 0
        if content_length > 10240:  # 10KB limit
            logger.warning(f"Oversized request from user {request.user.id}: {content_length} bytes")
            return error_response('Request too large', status=413, user_id=request.user.id)
        
        # Parse request data
        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body)
                if not isinstance(data, dict):
                    raise ValueError("Invalid data format")
            else:
                # Handle form data (application/x-www-form-urlencoded)
                data = dict(request.POST)
                # Convert single-item lists to strings (Django form parsing)
                data = {k: v[0] if isinstance(v, list) and len(v) == 1 else v for k, v in data.items()}
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Invalid JSON from user {request.user.id}: {str(e)}")
            return error_response('Invalid data format', status=400, user_id=request.user.id)
        
        # Validate reading log data using helper
        try:
            validated_data = validate_reading_log_data(data)
        except UtilsValidationError as e:
            return error_response(str(e), status=400, user_id=request.user.id)
        
        # Set default date if not provided
        log_date = validated_data.get('date', date.today())
        
        # Create log entry within transaction
        log = Log.objects.create(
            student=request.user,
            school=request.user.school,
            date=log_date,
            **{k: v for k, v in validated_data.items() if k != 'date'}
        )
        
        # Process gamification achievements
        try:
            from .gamification import GamificationEngine
            gamification_engine = GamificationEngine()
            gamification_engine.process_reading_log(log)
        except Exception as gamification_error:
            # Don't fail the log creation if gamification fails
            logger.warning(f"Gamification processing failed for log {log.id}: {str(gamification_error)}")
        
        # Log successful creation for audit trail
        log_successful_action(request.user.id, 'created reading log', 'Log', log.id)
        
        return reading_log_created_response(log.id)
        
    except ValidationError as e:
        return validation_error_response(str(e), user_id=request.user.id)
    except Exception as e:
        # Security: Never expose internal errors to users
        return server_error_response(user_id=request.user.id, error_details=str(e))


@login_required
def student_progress(request):
    """Get student's reading progress and stats - Enterprise security"""
    # Security: Validate user type
    if request.user.user_type not in ['student', 'parent']:
        logger.warning(f"Non-student/parent user {request.user.id} attempted to access student progress")
        return JsonResponse({'status': 'error', 'message': 'Access denied'}, status=403)
    
    # Determine which student's progress to show
    target_student = None
    if request.user.user_type == 'student':
        target_student = request.user
    elif request.user.user_type == 'parent':
        # Parent requesting child's progress
        student_id = request.GET.get('student_id')
        if not student_id:
            return JsonResponse({'status': 'error', 'message': 'Student ID required for parent requests'}, status=400)
        
        try:
            student_id = int(student_id)
            target_student = request.user.children.get(id=student_id)
        except (ValueError, TypeError):
            return JsonResponse({'status': 'error', 'message': 'Invalid student ID format'}, status=400)
        except CustomUser.DoesNotExist:
            logger.warning(f"Parent {request.user.id} attempted to access non-child progress: {student_id}")
            return JsonResponse({'status': 'error', 'message': 'Student not found or access denied'}, status=404)
    
    try:
        # Get date range with proper validation (default to current month)
        today = date.today()
        start_date = today.replace(day=1)  # First day of current month
        end_date = today
        
        # Security: Validate date parameters
        if request.GET.get('start_date'):
            try:
                start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d').date()
                # Security: Prevent unreasonable date ranges
                if start_date < date.today() - timedelta(days=1095):  # Max 3 years back
                    return JsonResponse({'status': 'error', 'message': 'Start date too far in the past'}, status=400)
            except ValueError:
                logger.warning(f"Invalid start_date from user {request.user.id}: {request.GET.get('start_date')}")
                return JsonResponse({'status': 'error', 'message': 'Invalid start date format'}, status=400)
        
        if request.GET.get('end_date'):
            try:
                end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d').date()
                # Security: Prevent future dates
                if end_date > date.today():
                    return JsonResponse({'status': 'error', 'message': 'End date cannot be in the future'}, status=400)
            except ValueError:
                logger.warning(f"Invalid end_date from user {request.user.id}: {request.GET.get('end_date')}")
                return JsonResponse({'status': 'error', 'message': 'Invalid end date format'}, status=400)
        
        # Security: Validate date range logic
        if start_date > end_date:
            return JsonResponse({'status': 'error', 'message': 'Start date must be before end date'}, status=400)
        
        # Security: Limit date range to prevent excessive queries
        if (end_date - start_date).days > 365:
            return JsonResponse({'status': 'error', 'message': 'Date range cannot exceed 1 year'}, status=400)
        
        # Performance: Optimized query with select_related
        logs = Log.objects.filter(
            student=target_student, 
            date__range=(start_date, end_date)
        ).select_related('school').order_by('-date')
        
        # Calculate statistics with database aggregation
        stats = logs.aggregate(
            total_pages=Sum('pages'),
            total_minutes=Sum('minutes'),
            total_logs=Count('id'),
            avg_rating=Avg('rating')
        )
        
        # Security: Sanitize aggregated data
        total_pages = stats['total_pages'] or 0
        total_minutes = stats['total_minutes'] or 0
        total_logs = stats['total_logs'] or 0
        avg_rating = round(float(stats['avg_rating']), 2) if stats['avg_rating'] else 0
        
        # Get daily goals if any (optimized query)
        daily_goal = DailyGoal.objects.filter(
            student=target_student
        ).select_related('school').first()
        
        # Recent logs for display (limit and sanitize)
        recent_logs = []
        for log in logs[:10]:  # Limit to 10 recent logs
            recent_logs.append({
                'id': log.id,
                'date': log.date.isoformat(),
                'title': log.title or '',
                'author': log.author or '',
                'pages': log.pages or 0,
                'minutes': log.minutes or 0,
                'rating': float(log.rating) if log.rating else None,
                'comments': log.comments or ''
            })
        
        # Prepare chart data for progress visualization
        chart_data = []
        for log in logs:
            chart_data.append({
                'date': log.date.isoformat(),
                'title': log.title or 'Untitled',
                'pages': log.pages or 0,
                'minutes': log.minutes or 0,
                'rating': float(log.rating) if log.rating else None
            })
        
        # Security: Log successful data access
        user_type = request.user.user_type
        if user_type == 'parent':
            logger.info(f"Student progress data accessed by parent {request.user.id} for child {target_student.id}")
        else:
            logger.info(f"Student progress data accessed by user {request.user.id}")
        
        return JsonResponse({
            'status': 'success',
            'stats': {
                'total_pages': total_pages,
                'total_minutes': total_minutes,
                'total_logs': total_logs,
                'avg_rating': str(avg_rating),  # String to prevent precision issues
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
        # Security: Never expose internal errors
        logger.error(f"Error in student_progress for user {request.user.id}: {str(e)}")
        return JsonResponse({'status': 'error', 'message': 'Unable to load progress data'}, status=500)


@login_required
def parent_dashboard_data(request):
    """Get progress data for all children of a parent - Enterprise security"""
    # Security: Validate user type
    if request.user.user_type != 'parent':
        logger.warning(f"Non-parent user {request.user.id} attempted to access parent dashboard")
        return JsonResponse({'status': 'error', 'message': 'Access denied'}, status=403)
    
    try:
        # Get date range with comprehensive validation (default to current month)
        today = date.today()
        start_date = today.replace(day=1)
        end_date = today
        
        # Security: Validate date parameters with proper error handling
        if request.GET.get('start_date'):
            try:
                start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d').date()
                # Security: Prevent unreasonable date ranges
                if start_date < date.today() - timedelta(days=1095):  # Max 3 years back
                    return JsonResponse({'status': 'error', 'message': 'Start date too far in the past'}, status=400)
            except ValueError:
                logger.warning(f"Invalid start_date from parent {request.user.id}: {request.GET.get('start_date')}")
                return JsonResponse({'status': 'error', 'message': 'Invalid start date format. Use YYYY-MM-DD'}, status=400)
        
        if request.GET.get('end_date'):
            try:
                end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d').date()
                # Security: Prevent future dates
                if end_date > date.today():
                    return JsonResponse({'status': 'error', 'message': 'End date cannot be in the future'}, status=400)
            except ValueError:
                logger.warning(f"Invalid end_date from parent {request.user.id}: {request.GET.get('end_date')}")
                return JsonResponse({'status': 'error', 'message': 'Invalid end date format. Use YYYY-MM-DD'}, status=400)
        
        # Security: Validate date range logic
        if start_date > end_date:
            return JsonResponse({'status': 'error', 'message': 'Start date must be before end date'}, status=400)
        
        # Security: Limit date range to prevent excessive queries
        if (end_date - start_date).days > 365:
            return JsonResponse({'status': 'error', 'message': 'Date range cannot exceed 1 year'}, status=400)
        
        # Performance: Get all children with optimized query
        children = request.user.children.select_related('school').all()
        
        # Security: Limit number of children to prevent abuse
        if children.count() > 50:  # Reasonable family size limit
            logger.warning(f"Parent {request.user.id} has excessive children count: {children.count()}")
            return JsonResponse({'status': 'error', 'message': 'Too many children associated with account'}, status=400)
        
        children_data = []
        for child in children:
            # Performance: Optimized query with select_related
            logs = Log.objects.filter(
                student=child,
                date__range=(start_date, end_date)
            ).select_related('school')
            
            # Calculate stats with database aggregation
            stats = logs.aggregate(
                total_pages=Sum('pages'),
                total_minutes=Sum('minutes'),
                total_logs=Count('id'),
                avg_rating=Avg('rating')
            )
            
            # Security: Sanitize and validate stats
            total_pages = stats['total_pages'] or 0
            total_minutes = stats['total_minutes'] or 0
            total_logs = stats['total_logs'] or 0
            avg_rating = round(float(stats['avg_rating']), 2) if stats['avg_rating'] else 0
            
            # Get recent logs with limit and sanitization
            recent_logs = []
            for log in logs.order_by('-date')[:5]:  # Limit to 5 recent logs
                recent_logs.append({
                    'date': log.date.isoformat(),
                    'title': log.title or '',
                    'author': log.author or '',
                    'pages': log.pages or 0,
                    'minutes': log.minutes or 0,
                    'rating': float(log.rating) if log.rating else None
                })
            
            # Security: Sanitize child data
            children_data.append({
                'id': child.id,
                'name': child.full_name or child.first_name or 'Student',
                'email': child.email,  # Only show email to parent
                'stats': {
                    'total_pages': total_pages,
                    'total_minutes': total_minutes,
                    'total_logs': total_logs,
                    'avg_rating': avg_rating
                },
                'recent_logs': recent_logs
            })
        
        # Security: Log successful data access
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
        # Security: Never expose internal errors
        logger.error(f"Error in parent_dashboard_data for user {request.user.id}: {str(e)}")
        return JsonResponse({'status': 'error', 'message': 'Unable to load dashboard data'}, status=500)


@login_required
@require_http_methods(["POST"])
@transaction.atomic
def parent_add_log(request):
    """Allow parents to add reading logs for their children - Enterprise security"""
    # Security: Validate user type
    if request.user.user_type != 'parent':
        logger.warning(f"Non-parent user {request.user.id} attempted to add child reading log")
        return JsonResponse({'status': 'error', 'message': 'Access denied'}, status=403)
    
    try:
        # Parse JSON data
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'}, status=400)
        
        # Security: Validate child_id
        child_id = data.get('child_id')
        if not child_id:
            return JsonResponse({'status': 'error', 'message': 'Child ID is required'}, status=400)
        
        try:
            child_id = int(child_id)
        except (ValueError, TypeError):
            return JsonResponse({'status': 'error', 'message': 'Invalid child ID format'}, status=400)
        
        # Security: Verify parent-child relationship
        try:
            child = request.user.children.get(id=child_id)
        except CustomUser.DoesNotExist:
            logger.warning(f"Parent {request.user.id} attempted to add log for non-child user {child_id}")
            return JsonResponse({'status': 'error', 'message': 'Child not found or access denied'}, status=404)
        
        # Validate and sanitize input data
        validated_data = {}
        
        # Optional title field
        title = data.get('title', '').strip()
        if title:
            if len(title) > 255:
                return JsonResponse({'status': 'error', 'message': 'Book title too long (max 255 characters)'}, status=400)
            validated_data['title'] = escape(title)  # Prevent XSS
        
        # Optional fields with validation
        author = data.get('author', '').strip()
        if author:
            if len(author) > 255:
                return JsonResponse({'status': 'error', 'message': 'Author name too long (max 255 characters)'}, status=400)
            validated_data['author'] = escape(author)  # Prevent XSS
        
        # Numeric fields
        pages = data.get('pages')
        if pages is not None:
            try:
                pages = int(pages)
                if pages < 1 or pages > 9999:
                    return JsonResponse({'status': 'error', 'message': 'Pages must be between 1 and 9999'}, status=400)
                validated_data['pages'] = pages
            except (ValueError, TypeError):
                return JsonResponse({'status': 'error', 'message': 'Invalid pages format'}, status=400)
        
        minutes = data.get('minutes')
        if minutes is not None:
            try:
                minutes = int(minutes)
                if minutes < 1 or minutes > 1440:  # Max 24 hours
                    return JsonResponse({'status': 'error', 'message': 'Minutes must be between 1 and 1440'}, status=400)
                validated_data['minutes'] = minutes
            except (ValueError, TypeError):
                return JsonResponse({'status': 'error', 'message': 'Invalid minutes format'}, status=400)
        
        rating = data.get('rating')
        if rating is not None and rating != '':
            try:
                rating = float(rating)
                if rating < 0 or rating > 5:
                    return JsonResponse({'status': 'error', 'message': 'Rating must be between 0 and 5'}, status=400)
                validated_data['rating'] = round(rating, 2)
            except (ValueError, TypeError):
                return JsonResponse({'status': 'error', 'message': 'Invalid rating format'}, status=400)
        
        comments = data.get('comments', '').strip()
        if comments:
            if len(comments) > 2000:
                return JsonResponse({'status': 'error', 'message': 'Comments too long (max 2000 characters)'}, status=400)
            validated_data['comments'] = escape(comments)  # Prevent XSS
        
        # Validate date
        log_date = date.today()  # Default to today
        if data.get('date'):
            try:
                log_date = datetime.strptime(data.get('date'), '%Y-%m-%d').date()
                # Security: Prevent future dates and very old dates
                if log_date > date.today():
                    return JsonResponse({'status': 'error', 'message': 'Cannot log future dates'}, status=400)
                if log_date < date.today() - timedelta(days=365):  # Max 1 year back
                    return JsonResponse({'status': 'error', 'message': 'Date too far in the past'}, status=400)
            except (ValueError, TypeError):
                return JsonResponse({'status': 'error', 'message': 'Invalid date format (use YYYY-MM-DD)'}, status=400)
        
        # Rate limiting: Check if parent is making too many requests
        cache_key = f'parent_log_rate_limit_{request.user.id}'
        recent_requests = cache.get(cache_key, 0)
        if recent_requests >= 10:  # Max 10 logs per minute
            logger.warning(f"Parent {request.user.id} exceeded rate limit for adding child logs")
            return JsonResponse({'status': 'error', 'message': 'Too many requests. Please wait before adding more logs.'}, status=429)
        
        # Create log entry within transaction
        log = Log.objects.create(
            student=child,
            school=child.school,
            date=log_date,
            **validated_data
        )
        
        # Phase 2: Process gamification achievements for the child
        try:
            from .gamification import GamificationEngine
            gamification_engine = GamificationEngine()
            gamification_engine.process_reading_log(log)
        except Exception as gamification_error:
            # Don't fail the log creation if gamification fails
            logger.warning(f"Gamification processing failed for log {log.id}: {str(gamification_error)}")
        
        # Security: Update rate limiting counter
        cache.set(cache_key, recent_requests + 1, 60)  # 1 minute window
        
        # Security: Log successful creation for audit trail
        logger.info(f"Reading log created by parent {request.user.id} for child {child.id}, log_id {log.id}")
        
        return JsonResponse({
            'status': 'success',
            'message': 'Reading log added successfully',
            'log_id': log.id
        })
        
    except Exception as e:
        # Security: Log error without exposing internal details
        logger.error(f"Error in parent_add_log for user {request.user.id}: {str(e)}")
        return JsonResponse({'status': 'error', 'message': 'Unable to add reading log'}, status=500)


@login_required
@require_http_methods(["POST"])
@transaction.atomic
def parent_edit_log(request):
    """Allow parents to edit reading logs for their children - Enterprise security"""
    # Security: Validate user type
    if request.user.user_type != 'parent':
        logger.warning(f"Non-parent user {request.user.id} attempted to edit child reading log")
        return JsonResponse({'status': 'error', 'message': 'Access denied'}, status=403)
    
    try:
        # Parse JSON data
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'}, status=400)
        
        # Security: Validate log_id and child_id
        log_id = data.get('log_id')
        child_id = data.get('child_id')
        
        if not log_id or not child_id:
            return JsonResponse({'status': 'error', 'message': 'Log ID and Child ID are required'}, status=400)
        
        try:
            log_id = int(log_id)
            child_id = int(child_id)
        except (ValueError, TypeError):
            return JsonResponse({'status': 'error', 'message': 'Invalid ID format'}, status=400)
        
        # Security: Verify parent-child relationship
        try:
            child = request.user.children.get(id=child_id)
        except CustomUser.DoesNotExist:
            logger.warning(f"Parent {request.user.id} attempted to edit log for non-child user {child_id}")
            return JsonResponse({'status': 'error', 'message': 'Child not found or access denied'}, status=404)
        
        # Security: Verify log belongs to the child
        try:
            log = Log.objects.get(id=log_id, student=child)
        except Log.DoesNotExist:
            logger.warning(f"Parent {request.user.id} attempted to edit non-existent log {log_id} for child {child_id}")
            return JsonResponse({'status': 'error', 'message': 'Reading log not found'}, status=404)
        
        # Validate and sanitize input data
        validated_data = {}
        
        # Optional title field
        title = data.get('title', '').strip()
        if title:
            if len(title) > 255:
                return JsonResponse({'status': 'error', 'message': 'Book title too long (max 255 characters)'}, status=400)
            validated_data['title'] = escape(title)  # Prevent XSS
        else:
            validated_data['title'] = None
        
        # Optional fields with validation
        author = data.get('author', '').strip()
        if author:
            if len(author) > 255:
                return JsonResponse({'status': 'error', 'message': 'Author name too long (max 255 characters)'}, status=400)
            validated_data['author'] = escape(author)  # Prevent XSS
        else:
            validated_data['author'] = None
        
        # Numeric fields
        pages = data.get('pages')
        if pages is not None and pages != '':
            try:
                pages = int(pages)
                if pages < 1 or pages > 9999:
                    return JsonResponse({'status': 'error', 'message': 'Pages must be between 1 and 9999'}, status=400)
                validated_data['pages'] = pages
            except (ValueError, TypeError):
                return JsonResponse({'status': 'error', 'message': 'Invalid pages format'}, status=400)
        else:
            validated_data['pages'] = None
        
        minutes = data.get('minutes')
        if minutes is not None and minutes != '':
            try:
                minutes = int(minutes)
                if minutes < 1 or minutes > 1440:  # Max 24 hours
                    return JsonResponse({'status': 'error', 'message': 'Minutes must be between 1 and 1440'}, status=400)
                validated_data['minutes'] = minutes
            except (ValueError, TypeError):
                return JsonResponse({'status': 'error', 'message': 'Invalid minutes format'}, status=400)
        else:
            validated_data['minutes'] = None
        
        rating = data.get('rating')
        if rating is not None and rating != '':
            try:
                rating = float(rating)
                if rating < 0 or rating > 5:
                    return JsonResponse({'status': 'error', 'message': 'Rating must be between 0 and 5'}, status=400)
                validated_data['rating'] = round(rating, 2)
            except (ValueError, TypeError):
                return JsonResponse({'status': 'error', 'message': 'Invalid rating format'}, status=400)
        else:
            validated_data['rating'] = None
        
        comments = data.get('comments', '').strip()
        if comments:
            if len(comments) > 2000:
                return JsonResponse({'status': 'error', 'message': 'Comments too long (max 2000 characters)'}, status=400)
            validated_data['comments'] = escape(comments)  # Prevent XSS
        else:
            validated_data['comments'] = None
        
        # Validate date
        if data.get('date'):
            try:
                log_date = datetime.strptime(data.get('date'), '%Y-%m-%d').date()
                # Security: Prevent future dates and very old dates
                if log_date > date.today():
                    return JsonResponse({'status': 'error', 'message': 'Cannot log future dates'}, status=400)
                if log_date < date.today() - timedelta(days=365):  # Max 1 year back
                    return JsonResponse({'status': 'error', 'message': 'Date too far in the past'}, status=400)
                validated_data['date'] = log_date
            except (ValueError, TypeError):
                return JsonResponse({'status': 'error', 'message': 'Invalid date format (use YYYY-MM-DD)'}, status=400)
        
        # Update log entry within transaction
        for field, value in validated_data.items():
            setattr(log, field, value)
        log.save()
        
        # Security: Log successful update for audit trail
        logger.info(f"Reading log updated by parent {request.user.id} for child {child.id}, log_id {log.id}")
        
        return JsonResponse({
            'status': 'success',
            'message': 'Reading log updated successfully',
            'log_id': log.id
        })
        
    except Exception as e:
        # Security: Log error without exposing internal details
        logger.error(f"Error in parent_edit_log for user {request.user.id}: {str(e)}")
        return JsonResponse({'status': 'error', 'message': 'Unable to update reading log'}, status=500)


@login_required
@require_http_methods(["POST"])
@transaction.atomic
def parent_delete_log(request):
    """Allow parents to delete reading logs for their children - Enterprise security"""
    # Security: Validate user type
    if request.user.user_type != 'parent':
        logger.warning(f"Non-parent user {request.user.id} attempted to delete child reading log")
        return JsonResponse({'status': 'error', 'message': 'Access denied'}, status=403)
    
    try:
        # Parse JSON data
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'}, status=400)
        
        # Security: Validate log_id and child_id
        log_id = data.get('log_id')
        child_id = data.get('child_id')
        
        if not log_id or not child_id:
            return JsonResponse({'status': 'error', 'message': 'Log ID and Child ID are required'}, status=400)
        
        try:
            log_id = int(log_id)
            child_id = int(child_id)
        except (ValueError, TypeError):
            return JsonResponse({'status': 'error', 'message': 'Invalid ID format'}, status=400)
        
        # Security: Verify parent-child relationship
        try:
            child = request.user.children.get(id=child_id)
        except CustomUser.DoesNotExist:
            logger.warning(f"Parent {request.user.id} attempted to delete log for non-child user {child_id}")
            return JsonResponse({'status': 'error', 'message': 'Child not found or access denied'}, status=404)
        
        # Security: Verify log belongs to the child
        try:
            log = Log.objects.get(id=log_id, student=child)
        except Log.DoesNotExist:
            logger.warning(f"Parent {request.user.id} attempted to delete non-existent log {log_id} for child {child_id}")
            return JsonResponse({'status': 'error', 'message': 'Reading log not found'}, status=404)
        
        # Store log info for audit before deletion
        log_title = log.title
        log_date = log.date
        
        # Delete log entry within transaction
        log.delete()
        
        # Security: Log successful deletion for audit trail
        logger.info(f"Reading log deleted by parent {request.user.id} for child {child.id}, log was: '{log_title}' on {log_date}")
        
        return JsonResponse({
            'status': 'success',
            'message': 'Reading log deleted successfully'
        })
        
    except Exception as e:
        # Security: Log error without exposing internal details
        logger.error(f"Error in parent_delete_log for user {request.user.id}: {str(e)}")
        return JsonResponse({'status': 'error', 'message': 'Unable to delete reading log'}, status=500)


@login_required
def reading_goals_view(request):
    """Reading goals management page for teachers"""
    if request.user.user_type not in ['teacher', 'administrator']:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("You don't have permission to access goal management")
    
    # Get classrooms and reading groups for the template
    from users.models import Classroom, ReadingGroup
    
    if request.user.user_type == 'teacher':
        classrooms = Classroom.objects.filter(
            school=request.user.school,
            teachers=request.user
        ).order_by('name')
        reading_groups = ReadingGroup.objects.filter(
            school=request.user.school,
            managers=request.user
        ).order_by('name')
    else:  # administrator
        classrooms = Classroom.objects.filter(
            school=request.user.school
        ).order_by('name')
        reading_groups = ReadingGroup.objects.filter(
            school=request.user.school
        ).order_by('name')
    
    context = {
        'data': {
            'classrooms': [{'id': c.id, 'name': c.name} for c in classrooms],
            'reading_groups': [{'id': g.id, 'name': g.name} for g in reading_groups]
        }
    }
    
    return render(request, 'general/reading_goals.html', context)


@login_required
def api_reading_goals(request):
    """API for reading goals data and management"""
    if request.user.user_type not in ['teacher', 'administrator']:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("You don't have permission to access goals")
    
    if request.method == "GET":
        # Get students based on user permissions
        from users.models import CustomUser, Classroom, ReadingGroup
        
        if request.user.user_type == 'teacher':
            students = CustomUser.objects.filter(
                school=request.user.school,
                user_type='student'
            ).filter(
                models.Q(classrooms__teachers=request.user) |
                models.Q(reading_groups__managers=request.user)
            ).distinct()
        else:  # administrator
            students = CustomUser.objects.filter(
                school=request.user.school,
                user_type='student'
            )
        
        # Apply filters
        goal_type = request.GET.get('goal_type', 'daily')
        class_group = request.GET.get('class_group', '')
        status_filter = request.GET.get('status', '')
        
        if class_group:
            if class_group.startswith('class_'):
                classroom_id = class_group.replace('class_', '')
                students = students.filter(classrooms__id=classroom_id)
            elif class_group.startswith('group_'):
                group_id = class_group.replace('group_', '')
                students = students.filter(reading_groups__id=group_id)
        
        # Build response data
        students_data = []
        overview = {'with_goals': 0, 'achieving': 0, 'struggling': 0, 'no_goals': 0}
        
        for student in students:
            if goal_type == 'daily':
                goal = DailyGoal.objects.filter(student=student).first()
            else:
                goal = TotalGoal.objects.filter(student=student).first()
            
            # Calculate progress and status
            progress = None
            status = 'no_goal'
            
            if goal:
                overview['with_goals'] += 1
                # TODO: Calculate actual progress based on recent reading logs
                # For now, using placeholder logic
                progress = {'percentage': 75}  # Placeholder
                status = 'achieving' if progress['percentage'] >= 80 else 'needs_encouragement'
                
                if status == 'achieving':
                    overview['achieving'] += 1
                else:
                    overview['struggling'] += 1
            else:
                overview['no_goals'] += 1
            
            # Apply status filter
            if status_filter:
                if status_filter == 'with_goals' and not goal:
                    continue
                elif status_filter == 'without_goals' and goal:
                    continue
                elif status_filter == 'achieving' and status != 'achieving':
                    continue
                elif status_filter == 'struggling' and status != 'needs_encouragement':
                    continue
            
            student_data = {
                'id': student.id,
                'name': student.full_name or f"{student.first_name} {student.last_initial}",
                'classroom': student.classrooms.first().name if student.classrooms.exists() else None,
                'daily_goal': None,
                'total_goal': None,
                'progress': progress,
                'status': status
            }
            
            if goal_type == 'daily' and goal:
                student_data['daily_goal'] = {
                    'pages': goal.pages,
                    'minutes': goal.minutes
                }
            elif goal_type == 'total' and goal:
                student_data['total_goal'] = {
                    'pages': goal.pages,
                    'deadline': goal.deadline.isoformat() if goal.deadline else None
                }
            
            students_data.append(student_data)
        
        return JsonResponse({
            'students': students_data,
            'overview': overview
        })
    
    elif request.method == "DELETE":
        # Remove individual goal
        try:
            data = json.loads(request.body)
            student_id = data.get('student_id')
            goal_type = data.get('goal_type')
            
            if not student_id or not goal_type:
                return error_response("Student ID and goal type are required", status=400)
            
            # Check permission to manage this student
            from users.models import CustomUser
            if request.user.user_type == 'teacher':
                student = CustomUser.objects.filter(
                    id=student_id,
                    school=request.user.school,
                    user_type='student'
                ).filter(
                    models.Q(classrooms__teachers=request.user) |
                    models.Q(reading_groups__managers=request.user)
                ).first()
            else:  # administrator
                student = CustomUser.objects.filter(
                    id=student_id,
                    school=request.user.school,
                    user_type='student'
                ).first()
            
            if not student:
                return error_response("Student not found or no permission", status=404)
            
            # Remove the goal
            if goal_type == 'daily':
                DailyGoal.objects.filter(student=student).delete()
            else:
                TotalGoal.objects.filter(student=student).delete()
            
            return success_response("Goal removed successfully")
            
        except Exception as e:
            return error_response(f"Failed to remove goal: {str(e)}", status=500)
    
    return error_response("Method not allowed", status=405)


@login_required
def api_bulk_reading_goals(request):
    """API for setting bulk reading goals"""
    if request.method == "POST":
        try:
            target_group = request.POST.get('target_group')
            goal_type = request.POST.get('goal_type')
            
            if not target_group or not goal_type:
                return error_response("Target group and goal type are required", status=400)
            
            # Get students in the target group
            from users.models import CustomUser, Classroom, ReadingGroup
            
            if target_group.startswith('class_'):
                classroom_id = target_group.replace('class_', '')
                classroom = Classroom.objects.filter(
                    id=classroom_id,
                    school=request.user.school
                ).first()
                
                if not classroom:
                    return error_response("Classroom not found", status=404)
                
                # Check permission
                if request.user.user_type == 'teacher' and not classroom.teachers.filter(id=request.user.id).exists():
                    return error_response("No permission to manage this classroom", status=403)
                
                students = classroom.students.all()
                
            elif target_group.startswith('group_'):
                group_id = target_group.replace('group_', '')
                reading_group = ReadingGroup.objects.filter(
                    id=group_id,
                    school=request.user.school
                ).first()
                
                if not reading_group:
                    return error_response("Reading group not found", status=404)
                
                # Check permission
                if request.user.user_type == 'teacher' and not reading_group.managers.filter(id=request.user.id).exists():
                    return error_response("No permission to manage this reading group", status=403)
                
                students = reading_group.students.all()
            else:
                return error_response("Invalid target group format", status=400)
            
            # Create goals for students who don't have them
            count = 0
            
            for student in students:
                if goal_type == 'daily':
                    # Check if daily goal already exists
                    if not DailyGoal.objects.filter(student=student).exists():
                        daily_pages = request.POST.get('daily_pages')
                        daily_minutes = request.POST.get('daily_minutes')
                        
                        if daily_pages or daily_minutes:
                            DailyGoal.objects.create(
                                student=student,
                                pages=int(daily_pages) if daily_pages else None,
                                minutes=int(daily_minutes) if daily_minutes else None
                            )
                            count += 1
                else:  # total goal
                    # Check if total goal already exists
                    if not TotalGoal.objects.filter(student=student).exists():
                        total_pages = request.POST.get('total_pages')
                        deadline = request.POST.get('deadline')
                        
                        if total_pages:
                            goal_data = {
                                'student': student,
                                'pages': int(total_pages)
                            }
                            if deadline:
                                from datetime import datetime
                                goal_data['deadline'] = datetime.strptime(deadline, '%Y-%m-%d').date()
                            
                            TotalGoal.objects.create(**goal_data)
                            count += 1
            
            return success_response(f"Goals set for {count} students", data={'count': count})
            
        except Exception as e:
            return error_response(f"Failed to set bulk goals: {str(e)}", status=500)
    
    return error_response("Method not allowed", status=405)


@login_required
def api_individual_reading_goal(request):
    """API for setting individual reading goals"""
    if request.method == "POST":
        try:
            student_id = request.POST.get('student_id') or request.POST.get('student_select')
            goal_type = request.POST.get('goal_type')
            
            if not student_id or not goal_type:
                return error_response("Student ID and goal type are required", status=400)
            
            # Get and validate student
            from users.models import CustomUser
            
            if request.user.user_type == 'teacher':
                student = CustomUser.objects.filter(
                    id=student_id,
                    school=request.user.school,
                    user_type='student'
                ).filter(
                    models.Q(classrooms__teachers=request.user) |
                    models.Q(reading_groups__managers=request.user)
                ).first()
            else:  # administrator
                student = CustomUser.objects.filter(
                    id=student_id,
                    school=request.user.school,
                    user_type='student'
                ).first()
            
            if not student:
                return error_response("Student not found or no permission", status=404)
            
            # Create or update goal
            if goal_type == 'daily':
                daily_pages = request.POST.get('daily_pages')
                daily_minutes = request.POST.get('daily_minutes')
                
                if not daily_pages and not daily_minutes:
                    return error_response("At least one daily goal (pages or minutes) is required", status=400)
                
                # Update or create daily goal
                goal, created = DailyGoal.objects.update_or_create(
                    student=student,
                    defaults={
                        'pages': int(daily_pages) if daily_pages else None,
                        'minutes': int(daily_minutes) if daily_minutes else None
                    }
                )
                
            else:  # total goal
                total_pages = request.POST.get('total_pages')
                deadline = request.POST.get('deadline')
                
                if not total_pages:
                    return error_response("Total pages goal is required", status=400)
                
                goal_data = {'pages': int(total_pages)}
                if deadline:
                    from datetime import datetime
                    goal_data['deadline'] = datetime.strptime(deadline, '%Y-%m-%d').date()
                
                # Update or create total goal
                goal, created = TotalGoal.objects.update_or_create(
                    student=student,
                    defaults=goal_data
                )
            
            action = "created" if created else "updated"
            return success_response(f"Goal {action} successfully for {student.full_name or student.first_name}")
            
        except Exception as e:
            return error_response(f"Failed to set goal: {str(e)}", status=500)
    
    return error_response("Method not allowed", status=405)


@login_required
def classroom_insights_view(request):
    """Classroom insights sharing page for teachers"""
    if request.user.user_type not in ['teacher', 'administrator']:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("You don't have permission to access classroom insights")
    
    return render(request, 'general/classroom_insights.html')


@login_required
def api_classroom_insights(request):
    """API for fetching shared classroom insights"""
    if request.user.user_type not in ['teacher', 'administrator']:
        return error_response("Access denied", status=403)
    
    if request.method == "GET":
        try:
            from .models import ClassroomInsight
            
            # Get insights for the school
            insights = ClassroomInsight.objects.filter(
                school=request.user.school,
                is_approved=True
            ).order_by('-helpful_count', '-created_date')
            
            # Apply category filter if provided
            category = request.GET.get('category')
            if category:
                insights = insights.filter(category=category)
            
            # Limit results to prevent performance issues
            insights = insights[:50]
            
            insights_data = []
            for insight in insights:
                insights_data.append({
                    'id': insight.id,
                    'title': insight.title,
                    'description': insight.description,
                    'tips': insight.implementation_tips,
                    'category': insight.category,
                    'metric': insight.success_metric,
                    'helpful_count': insight.helpful_count,
                    'created_at': insight.created_date.isoformat(),
                    'allow_contact': insight.allow_contact,
                    'is_featured': insight.is_featured
                })
            
            return JsonResponse({
                'success': True,
                'data': {
                    'insights': insights_data,
                    'total_insights': ClassroomInsight.objects.filter(
                        school=request.user.school,
                        is_approved=True
                    ).count()
                }
            })
            
        except Exception as e:
            return error_response(f"Failed to load insights: {str(e)}", status=500)
    
    return error_response("Method not allowed", status=405)


@login_required
def api_classroom_comparison(request):
    """API for anonymized classroom performance comparison"""
    if request.user.user_type not in ['teacher', 'administrator']:
        return error_response("Access denied", status=403)
    
    if request.method == "GET":
        try:
            from users.models import Classroom
            from django.db.models import Count, Sum, Avg
            from datetime import date, timedelta
            
            # Get date range (default to current month)
            today = date.today()
            start_date = today.replace(day=1)
            end_date = today
            
            if request.GET.get('start_date'):
                start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d').date()
            if request.GET.get('end_date'):
                end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d').date()
            
            # Get all classrooms in the school
            classrooms = Classroom.objects.filter(school=request.user.school)
            
            # Get current user's classroom(s) for teacher users
            my_classrooms = []
            if request.user.user_type == 'teacher':
                my_classrooms = classrooms.filter(teachers=request.user)
            
            anonymous_classrooms = []
            my_classroom_data = None
            total_school_pages = 0
            total_school_students = 0
            
            for classroom in classrooms:
                # Get reading logs for this classroom
                logs = Log.objects.filter(
                    student__classrooms=classroom,
                    date__range=(start_date, end_date)
                )
                
                # Calculate metrics
                stats = logs.aggregate(
                    total_pages=Sum('pages'),
                    total_minutes=Sum('minutes'),
                    total_logs=Count('id'),
                    avg_rating=Avg('rating')
                )
                
                student_count = classroom.students.count()
                if student_count == 0:
                    continue  # Skip empty classrooms
                
                pages_per_student = (stats['total_pages'] or 0) / student_count
                minutes_per_student = (stats['total_minutes'] or 0) / student_count
                
                # Calculate goal achievement (simplified)
                # TODO: Implement actual goal achievement calculation
                goal_achievement = min(pages_per_student / 50 * 100, 100)  # Assume 50 pages is 100%
                
                classroom_data = {
                    'pages_per_student': pages_per_student,
                    'minutes_per_student': minutes_per_student,
                    'avg_rating': stats['avg_rating'] or 0,
                    'goal_achievement': goal_achievement,
                    'student_count': student_count,
                    'is_current_user': request.user.user_type == 'teacher' and classroom in my_classrooms
                }
                
                # Add to school totals
                total_school_pages += stats['total_pages'] or 0
                total_school_students += student_count
                
                # Store current user's classroom data separately
                if classroom_data['is_current_user']:
                    my_classroom_data = classroom_data.copy()
                
                anonymous_classrooms.append(classroom_data)
            
            # Calculate school-wide averages
            school_avg_pages = total_school_pages / total_school_students if total_school_students > 0 else 0
            
            # Sort classrooms by performance for ranking
            sorted_classrooms = sorted(anonymous_classrooms, key=lambda x: x['pages_per_student'], reverse=True)
            
            # Determine current user's rank
            my_rank = 1
            if my_classroom_data:
                for i, classroom in enumerate(sorted_classrooms):
                    if classroom['is_current_user']:
                        my_rank = i + 1
                        break
                
                my_classroom_data['rank'] = my_rank
            
            # Get popular strategies (placeholder - would come from insights data)
            popular_strategies = [
                {'name': 'Daily reading goals', 'usage_count': len(anonymous_classrooms) // 2},
                {'name': 'Book choice variety', 'usage_count': len(anonymous_classrooms) // 3},
                {'name': 'Reading rewards', 'usage_count': len(anonymous_classrooms) // 4},
            ]
            
            return JsonResponse({
                'success': True,
                'data': {
                    'my_classroom': my_classroom_data or {
                        'pages_per_student': 0,
                        'minutes_per_student': 0,
                        'avg_rating': 0,
                        'goal_achievement': 0,
                        'rank': len(anonymous_classrooms)
                    },
                    'school_data': {
                        'avg_pages_per_student': school_avg_pages,
                        'top_pages_per_student': sorted_classrooms[0]['pages_per_student'] if sorted_classrooms else 0,
                        'total_classrooms': len(anonymous_classrooms)
                    },
                    'anonymous_classrooms': anonymous_classrooms[:10],  # Limit for chart
                    'popular_strategies': popular_strategies
                }
            })
            
        except Exception as e:
            return error_response(f"Failed to load comparison data: {str(e)}", status=500)
    
    return error_response("Method not allowed", status=405)


@login_required
def api_share_insight(request):
    """API for sharing a new classroom insight"""
    if request.user.user_type not in ['teacher', 'administrator']:
        return error_response("Access denied", status=403)
    
    if request.method == "POST":
        try:
            from .models import ClassroomInsight
            import hashlib
            
            # Get form data
            category = request.POST.get('category')
            title = request.POST.get('title', '').strip()
            description = request.POST.get('description', '').strip()
            tips = request.POST.get('tips', '').strip()
            metric = request.POST.get('metric')
            allow_contact = request.POST.get('allow_contact') == 'on'
            
            # Validation
            if not category or not title or not description:
                return error_response("Category, title, and description are required", status=400)
            
            if len(title) > 100:
                return error_response("Title too long (max 100 characters)", status=400)
            
            if len(description) > 1000:
                return error_response("Description too long (max 1000 characters)", status=400)
            
            if tips and len(tips) > 500:
                return error_response("Tips too long (max 500 characters)", status=400)
            
            # Create teacher hash for anonymity
            teacher_hash = hashlib.sha256(
                f"teacher_{request.user.id}_{request.user.school.id}".encode()
            ).hexdigest()
            
            # Create insight
            insight = ClassroomInsight.objects.create(
                school=request.user.school,
                teacher_hash=teacher_hash,
                category=category,
                title=title,
                description=description,
                implementation_tips=tips if tips else None,
                success_metric=metric if metric else None,
                allow_contact=allow_contact
            )
            
            return success_response(
                "Your insight has been shared successfully!",
                data={'insight_id': insight.id}
            )
            
        except Exception as e:
            return error_response(f"Failed to share insight: {str(e)}", status=500)
    
    return error_response("Method not allowed", status=405)


@login_required
def api_mark_helpful(request):
    """API for marking an insight as helpful"""
    if request.user.user_type not in ['teacher', 'administrator']:
        return error_response("Access denied", status=403)
    
    if request.method == "POST":
        try:
            from .models import ClassroomInsight, InsightHelpful
            import hashlib
            import json
            
            data = json.loads(request.body)
            insight_id = data.get('insight_id')
            
            if not insight_id:
                return error_response("Insight ID is required", status=400)
            
            # Get the insight
            try:
                insight = ClassroomInsight.objects.get(
                    id=insight_id,
                    school=request.user.school,
                    is_approved=True
                )
            except ClassroomInsight.DoesNotExist:
                return error_response("Insight not found", status=404)
            
            # Create teacher hash for anonymity
            teacher_hash = hashlib.sha256(
                f"teacher_{request.user.id}_{request.user.school.id}".encode()
            ).hexdigest()
            
            # Check if already marked helpful
            if InsightHelpful.objects.filter(insight=insight, teacher_hash=teacher_hash).exists():
                return error_response("You have already marked this insight as helpful", status=400)
            
            # Create helpful vote
            InsightHelpful.objects.create(
                insight=insight,
                teacher_hash=teacher_hash
            )
            
            # Update helpful count
            insight.helpful_count = insight.helpful_votes.count()
            insight.save(update_fields=['helpful_count'])
            
            return success_response("Marked as helpful successfully")
            
        except Exception as e:
            return error_response(f"Failed to mark as helpful: {str(e)}", status=500)
    
    return error_response("Method not allowed", status=405)

