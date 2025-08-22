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
from datetime import datetime

# Set up logging for security events
logger = logging.getLogger('reading_logs.security')

from users.models import CustomUser, Classroom, ReadingGroup

from datetime import datetime, date, timedelta
import json


@login_required
def get_logs_by_date_range(request):
    try:
        start_date = datetime.fromisoformat(request.GET.get('start')).date()
        end_date = datetime.fromisoformat(request.GET.get('end')).date()
    except (ValueError, TypeError):
        return JsonResponse({'status': 'error', 'message': 'Invalid date format'})

    obj_id = request.GET.get('id')
    form_name = request.GET.get('form_name')

    num_students = 0

    if form_name == 'Student':
        # Validate user
        try:
            user = CustomUser.objects.get(id=obj_id, user_type="student", school=request.user.school)
        except CustomUser.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'User not found'})
    
        # Fetch logs within the date range for the specified user
        logs = Log.objects.filter(school=request.user.school, student=user, date__range=(start_date, end_date))

        num_students = 1
        # Serialize logs
        logs_data = [{'id': log.id, 'date': log.date, 'title': log.title, 'author': log.author, 'pages': log.pages, 'minutes': log.minutes, 'rating': log.rating, 'comments': log.comments} for log in logs]
    elif form_name in ['Classrooms', 'Groups']:
        if form_name == 'Classrooms':
            try:
                temp_obj = Classroom.objects.get(school=request.user.school, id=obj_id)
            except Classroom.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Classroom not found'})
        else:
            try:
                temp_obj = ReadingGroup.objects.get(school=request.user.school, id=obj_id)
            except ReadingGroup.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Reading Group not found'})
        logs = Log.objects.filter(school=request.user.school, student__in=temp_obj.students.all(),
                                  date__range=(start_date, end_date)).values('id', 'date', 'pages', 'minutes')
        num_students = temp_obj.students.count()

        logs_data = [{'id': log['id'], 'date': log['date'], 'pages': log['pages'], 'minutes': log['minutes']} for log in logs]


    if not logs_data:
        logs_data = []

    return JsonResponse({'status': 'success', 'logs': logs_data, 'num_students': num_students})


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
    # Security: Check request size (prevent DoS)
    content_length = len(request.body) if hasattr(request, 'body') else 0
    if content_length > 10240:  # 10KB limit
        logger.warning(f"Oversized request from user {request.user.id}: {content_length} bytes")
        return JsonResponse({'status': 'error', 'message': 'Request too large'}, status=413)
    
    # Security: Rate limiting check
    cache_key = f"student_log_rate_{request.user.id}"
    recent_requests = cache.get(cache_key, 0)
    if recent_requests >= 10:  # Max 10 logs per minute
        logger.warning(f"Rate limit exceeded for user {request.user.id}")
        return JsonResponse({'status': 'error', 'message': 'Too many requests. Please wait.'}, status=429)
    
    try:
        # Security: Handle both JSON and form data
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
            return JsonResponse({'status': 'error', 'message': 'Invalid data format'}, status=400)
        
        # Security: Ensure the user is a student
        if request.user.user_type != 'student':
            logger.warning(f"Non-student user {request.user.id} attempted to create log")
            return JsonResponse({'status': 'error', 'message': 'Access denied'}, status=403)
        
        # Security: Validate and sanitize all input fields
        validated_data = {}
        
        # Validate pages (with reasonable limits)
        pages = data.get('pages')
        if pages is not None:
            try:
                pages = int(pages)
                if pages < 0:
                    return JsonResponse({'status': 'error', 'message': 'Pages must be positive'}, status=400)
                if pages > 10000:  # Reasonable upper limit
                    return JsonResponse({'status': 'error', 'message': 'Pages cannot exceed 10,000'}, status=400)
                validated_data['pages'] = pages
            except (ValueError, TypeError):
                return JsonResponse({'status': 'error', 'message': 'Pages must be a valid number'}, status=400)
        
        # Validate minutes (with reasonable limits)
        minutes = data.get('minutes')
        if minutes is not None:
            try:
                minutes = int(minutes)
                if minutes < 0:
                    return JsonResponse({'status': 'error', 'message': 'Minutes must be positive'}, status=400)
                if minutes > 1440:  # Max 24 hours
                    return JsonResponse({'status': 'error', 'message': 'Minutes cannot exceed 24 hours'}, status=400)
                validated_data['minutes'] = minutes
            except (ValueError, TypeError):
                return JsonResponse({'status': 'error', 'message': 'Minutes must be a valid number'}, status=400)
        
        # Validate rating
        rating = data.get('rating')
        if rating is not None:
            try:
                rating = float(rating)
                if not 1 <= rating <= 5:
                    return JsonResponse({'status': 'error', 'message': 'Rating must be between 1 and 5'}, status=400)
                validated_data['rating'] = rating
            except (ValueError, TypeError):
                return JsonResponse({'status': 'error', 'message': 'Rating must be a valid number'}, status=400)
        
        # Validate and sanitize text fields
        title = data.get('title', '').strip()
        if title:
            if len(title) > 255:
                return JsonResponse({'status': 'error', 'message': 'Title too long (max 255 characters)'}, status=400)
            validated_data['title'] = escape(title)  # Prevent XSS
        
        author = data.get('author', '').strip()
        if author:
            if len(author) > 255:
                return JsonResponse({'status': 'error', 'message': 'Author name too long (max 255 characters)'}, status=400)
            validated_data['author'] = escape(author)  # Prevent XSS
        
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
        
        # Create log entry within transaction
        log = Log.objects.create(
            student=request.user,
            school=request.user.school,
            date=log_date,
            **validated_data
        )
        
        # Phase 2: Process gamification achievements
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
        logger.info(f"Reading log created successfully by user {request.user.id}, log_id {log.id}")
        
        return JsonResponse({
            'status': 'success', 
            'message': 'Reading log saved successfully!',
            'log_id': log.id
        })
        
    except ValidationError as e:
        logger.warning(f"Validation error from user {request.user.id}: {str(e)}")
        return JsonResponse({'status': 'error', 'message': 'Data validation failed'}, status=400)
    except Exception as e:
        # Security: Never expose internal errors to users
        logger.error(f"Unexpected error in student_quick_log for user {request.user.id}: {str(e)}")
        return JsonResponse({'status': 'error', 'message': 'An internal error occurred. Please try again.'}, status=500)


@login_required
def student_progress(request):
    """Get student's reading progress and stats - Enterprise security"""
    # Security: Validate user type
    if request.user.user_type != 'student':
        logger.warning(f"Non-student user {request.user.id} attempted to access student progress")
        return JsonResponse({'status': 'error', 'message': 'Access denied'}, status=403)
    
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
            student=request.user, 
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
            student=request.user
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
        
        # Security: Log successful data access
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

