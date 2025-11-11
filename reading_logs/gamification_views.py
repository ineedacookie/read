"""
Phase 2: Gamification API Views
RESTful endpoints for badges, points, and achievements
"""

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import models
from django.db.models import Count, Sum, Avg, Q, Max
from django.views.decorators.http import require_http_methods
from datetime import date, timedelta
import json
import logging

from .gamification import (
    Badge, StudentBadge, StudentPoints, PointsHistory,
    GamificationEngine, get_student_leaderboard, award_custom_badge
)
from users.models import CustomUser, Classroom, ReadingGroup
from read.utils.permission_helpers import check_user_type
from read.utils.response_helpers import (
    error_response,
    permission_denied_response,
    server_error_response,
    success_response,
)
from read.utils.view_helpers import cached_data, resolve_student_access

logger = logging.getLogger('reading_logs.gamification')


@login_required
@require_http_methods(["GET"])
def student_profile_api(request, student_id=None):
    """
    Get student's gamification profile (points, level, badges)
    Accessible by the student, their parents, teachers, and administrators
    """
    try:
        # Determine target student
        if student_id:
            target_student_id = student_id
        else:
            # Default to requesting user if they're a student
            if request.user.user_type == 'student':
                target_student_id = request.user.id
            else:
                return error_response('Student ID required', status=400, user_id=request.user.id)
        
        student = resolve_student_access(request.user, target_student_id)
        
        # Get or create points profile
        points_profile, created = StudentPoints.objects.get_or_create(
            student=student,
            school=student.school
        )
        
        # Get earned badges
        earned_badges = StudentBadge.objects.filter(
            student=student
        ).select_related('badge').order_by('-earned_at')
        
        # Get recent points history
        recent_points = PointsHistory.objects.filter(
            student=student
        )[:10]
        
        # Calculate next level progress
        total_points_for_current_level = sum(
            100 + (i * 25) for i in range(1, points_profile.current_level)
        )
        progress_percentage = (points_profile.total_points / points_profile.points_to_next_level * 100) if points_profile.points_to_next_level > 0 else 0
        
        # Format response
        profile_data = {
            'student': {
                'id': student.id,
                'name': student.full_name,
                'email': student.email
            },
            'points': {
                'total': points_profile.total_points,
                'level': points_profile.current_level,
                'points_to_next_level': points_profile.points_to_next_level,
                'progress_percentage': round(progress_percentage, 1)
            },
            'achievements': {
                'current_streak': points_profile.current_streak,
                'longest_streak': points_profile.longest_streak,
                'total_books': points_profile.total_books_read,
                'total_pages': points_profile.total_pages_read,
                'total_minutes': points_profile.total_minutes_read
            },
            'badges': [
                {
                    'id': sb.badge.id,
                    'name': sb.badge.name,
                    'description': sb.badge.description,
                    'category': sb.badge.category,
                    'difficulty': sb.badge.difficulty,
                    'icon': sb.badge.icon,
                    'color': sb.badge.color,
                    'earned_at': sb.earned_at.isoformat(),
                    'points_value': sb.badge.points_value
                }
                for sb in earned_badges
            ],
            'recent_activity': [
                {
                    'points': ph.points_earned,
                    'reason': ph.reason,
                    'date': ph.earned_at.isoformat(),
                    'new_level': ph.new_level
                }
                for ph in recent_points
            ]
        }
        
        logger.info(f"Gamification profile accessed for student {target_student_id} by user {request.user.id}")
        
        return success_response("Profile retrieved", {'data': profile_data})
        
    except Exception as e:
        logger.error(f"Error retrieving gamification profile for user {request.user.id}: {str(e)}")
        if isinstance(e, CustomUser.DoesNotExist):
            return error_response('Student not found', status=404, user_id=request.user.id)
        if isinstance(e, PermissionDenied):
            logger.warning(
                f"Unauthorized gamification profile access: user {request.user.id} to student {target_student_id}"
            )
            return permission_denied_response(request.user.id, action_attempted='gamification profile')
        return server_error_response(request.user.id, error_details=str(e))


@login_required
@require_http_methods(["GET"])
def available_badges_api(request):
    """
    Get list of all available badges and progress towards earning them
    For students to see what they can work towards
    """
    try:
        if request.user.user_type != 'student':
            return permission_denied_response(request.user.id, action_attempted='available badges')
        
        # Get student's points profile
        points_profile, created = StudentPoints.objects.get_or_create(
            student=request.user,
            school=request.user.school
        )
        
        # Get already earned badges
        earned_badge_ids = StudentBadge.objects.filter(
            student=request.user
        ).values_list('badge_id', flat=True)
        
        # Get all available badges
        all_badges = Badge.objects.filter(is_active=True).order_by('category', 'difficulty')
        
        badge_list = []
        gamification_engine = GamificationEngine()
        
        for badge in all_badges:
            is_earned = badge.id in earned_badge_ids
            
            # Calculate progress towards badge
            progress = _calculate_badge_progress(request.user, badge, points_profile)
            
            badge_data = {
                'id': badge.id,
                'name': badge.name,
                'description': badge.description,
                'category': badge.category,
                'difficulty': badge.difficulty,
                'icon': badge.icon,
                'color': badge.color,
                'points_value': badge.points_value,
                'is_earned': is_earned,
                'progress': progress
            }
            
            badge_list.append(badge_data)
        
        # Group badges by category
        categories = {}
        for badge in badge_list:
            category = badge['category']
            if category not in categories:
                categories[category] = []
            categories[category].append(badge)
        
        return success_response("Badges retrieved", {
            'data': {
                'badges_by_category': categories,
                'total_badges': len(all_badges),
                'earned_count': len(earned_badge_ids)
            }
        })
        
    except Exception as e:
        logger.error(f"Error retrieving available badges for user {request.user.id}: {str(e)}")
        return server_error_response(request.user.id, error_details=str(e))


@login_required
@require_http_methods(["GET"])
def leaderboard_api(request):
    """
    Get leaderboard data for the school or classroom
    With privacy controls and appropriate access
    """
    try:
        # Get scope and timeframe
        scope = request.GET.get('scope', 'school')  # school, classroom
        timeframe = request.GET.get('timeframe', 'month')  # week, month, all
        scope_id = request.GET.get('scope_id')  # classroom_id if scope=classroom
        
        # Security: Verify access permissions
        if scope == 'classroom':
            if not scope_id:
                return error_response('Classroom ID required', status=400, user_id=request.user.id)
            
            try:
                classroom = Classroom.objects.get(id=scope_id, school=request.user.school)
                
                has_access = False
                if request.user.user_type == 'teacher':
                    has_access = classroom.teachers.filter(id=request.user.id).exists()
                elif request.user.user_type == 'student':
                    has_access = classroom.students.filter(id=request.user.id).exists()
                elif request.user.user_type == 'administrator':
                    has_access = True
                
                if not has_access:
                    return permission_denied_response(
                        request.user.id,
                        action_attempted=f'leaderboard classroom {scope_id}'
                    )
                
                # Get classroom students for leaderboard
                students = classroom.students.filter(user_type='student')
                
            except Classroom.DoesNotExist:
                return error_response('Classroom not found', status=404, user_id=request.user.id)
        else:
            # School-wide leaderboard
            if request.user.user_type not in ['administrator', 'teacher']:
                # Students can only see limited school leaderboard
                pass
            
            students = CustomUser.objects.filter(
                school=request.user.school,
                user_type='student'
            )
        
        cache_key = f"leaderboard_{scope}_{scope_id}_{timeframe}_{request.user.school.id}"
        
        def _build_leaderboard():
            if timeframe == 'week':
                start_date = date.today() - timedelta(days=7)
            elif timeframe == 'month':
                start_date = date.today() - timedelta(days=30)
            else:
                start_date = None
            
            students_with_points = students.select_related('points_profile').prefetch_related(
                models.Prefetch(
                    'earned_badges',
                    queryset=StudentBadge.objects.all()
                )
            )
            
            recent_points_dict = {}
            if start_date:
                recent_points_qs = PointsHistory.objects.filter(
                    student__in=students,
                    earned_at__date__gte=start_date
                ).values('student_id').annotate(
                    total=Sum('points_earned')
                )
                recent_points_dict = {item['student_id']: item['total'] or 0 for item in recent_points_qs}
            
            shared_classrooms_dict = {}
            user_classrooms = set()
            if request.user.user_type == 'student':
                user_classrooms = set(Classroom.objects.filter(
                    students=request.user
                ).values_list('id', flat=True))
                
                student_classroom_mapping = Classroom.objects.filter(
                    students__in=students
                ).values('students__id', 'id')
                
                for mapping in student_classroom_mapping:
                    student_id = mapping['students__id']
                    classroom_id = mapping['id']
                    if student_id not in shared_classrooms_dict:
                        shared_classrooms_dict[student_id] = set()
                    shared_classrooms_dict[student_id].add(classroom_id)
            
            leaderboard_data = []
            
            for student in students_with_points:
                try:
                    points_profile = student.points_profile
                    total_points = points_profile.total_points
                    level = points_profile.current_level
                except (StudentPoints.DoesNotExist, AttributeError):
                    total_points = 0
                    level = 1
                
                badges_count = len(student.earned_badges.all())
                
                recent_points = recent_points_dict.get(student.id, total_points)
                
                show_full_info = True
                if request.user.user_type == 'student' and request.user.id != student.id:
                    student_classrooms = shared_classrooms_dict.get(student.id, set())
                    shared = bool(user_classrooms & student_classrooms)
                    
                    if not shared:
                        show_full_info = False
                
                student_data = {
                    'student_id': student.id,
                    'name': student.full_name if show_full_info else student.first_name,
                    'level': level,
                    'total_points': total_points if timeframe == 'all' else recent_points,
                    'badges_count': badges_count,
                    'rank': 0
                }
                
                leaderboard_data.append(student_data)
            
            leaderboard_data.sort(key=lambda x: x['total_points'], reverse=True)
            
            for i, student_data in enumerate(leaderboard_data):
                student_data['rank'] = i + 1
            
            leaderboard_data = leaderboard_data[:50]
            
            return {
                'leaderboard': leaderboard_data,
                'timeframe': timeframe,
                'scope': scope,
                'total_students': len(students)
            }
        
        result, from_cache = cached_data(cache_key, 600, _build_leaderboard)
        
        if from_cache:
            return success_response("Leaderboard retrieved", {'data': result, 'cached': True})
        
        logger.info(f"Leaderboard accessed by user {request.user.id} for scope {scope}")
        
        return success_response("Leaderboard retrieved", {'data': result})
        
    except Exception as e:
        logger.error(f"Error generating leaderboard for user {request.user.id}: {str(e)}")
        return server_error_response(request.user.id, error_details=str(e))


@login_required
@require_http_methods(["POST"])
def award_custom_badge_api(request):
    """
    Award a custom badge to a student
    Only administrators and teachers can award custom badges
    """
    try:
        try:
            check_user_type(request.user, ['administrator', 'teacher'])
        except PermissionDenied:
            return permission_denied_response(request.user.id, action_attempted='award custom badge')
        
        data = json.loads(request.body)
        student_id = data.get('student_id')
        badge_name = data.get('badge_name', '').strip()
        description = data.get('description', '').strip()
        points = data.get('points', 10)
        
        # Validation
        if not student_id or not badge_name or not description:
            return error_response('Student ID, badge name, and description are required', status=400, user_id=request.user.id)
        
        if len(badge_name) > 100:
            return error_response('Badge name too long', status=400, user_id=request.user.id)
        
        if len(description) > 500:
            return error_response('Description too long', status=400, user_id=request.user.id)
        
        try:
            points = int(points)
            if points < 1 or points > 100:
                return error_response('Points must be between 1 and 100', status=400, user_id=request.user.id)
        except (ValueError, TypeError):
            return error_response('Invalid points value', status=400, user_id=request.user.id)
        
        # Get target student using centralized helper
        try:
            student = resolve_student_access(request.user, student_id)
        except CustomUser.DoesNotExist:
            return error_response('Student not found', status=404, user_id=request.user.id)
        except PermissionDenied:
            return permission_denied_response(request.user.id, action_attempted='award custom badge student access')
        
        # Award the badge
        student_badge = award_custom_badge(student, badge_name, description, points)
        
        # Log the action
        logger.info(f"Custom badge '{badge_name}' awarded to student {student_id} by user {request.user.id}")
        
        return success_response(
            f"Badge '{badge_name}' awarded to {student.full_name}",
            {'badge_id': student_badge.badge.id}
        )
        
    except json.JSONDecodeError:
        return error_response('Invalid JSON data', status=400, user_id=request.user.id)
    except Exception as e:
        logger.error(f"Error awarding custom badge by user {request.user.id}: {str(e)}")
        return server_error_response(request.user.id, error_details=str(e))


@login_required
@require_http_methods(["GET"])
def gamification_stats_api(request):
    """
    Get overall gamification statistics
    For administrators and teachers to track engagement
    """
    try:
        try:
            check_user_type(request.user, ['administrator', 'teacher'])
        except PermissionDenied:
            return permission_denied_response(request.user.id, action_attempted='gamification stats')
        
        cache_key = f"gamification_stats_{request.user.school.id}"
        
        def _build_stats():
            students = CustomUser.objects.filter(
                school=request.user.school,
                user_type='student'
            )
            
            total_students = students.count()
            active_students = StudentPoints.objects.filter(
                school=request.user.school
            ).count()
            
            points_stats = StudentPoints.objects.filter(
                school=request.user.school
            ).aggregate(
                total_points=Sum('total_points'),
                avg_level=Avg('current_level'),
                max_level=models.Max('current_level'),
                avg_streak=Avg('current_streak'),
                max_streak=models.Max('longest_streak')
            )
            
            badge_stats = Badge.objects.aggregate(
                total_badges=Count('id'),
                active_badges=Count('id', filter=models.Q(is_active=True))
            )
            
            badges_awarded = StudentBadge.objects.filter(
                school=request.user.school
            ).count()
            
            week_ago = date.today() - timedelta(days=7)
            recent_activity = PointsHistory.objects.filter(
                school=request.user.school,
                earned_at__date__gte=week_ago
            ).count()
            
            top_students = StudentPoints.objects.filter(
                school=request.user.school
            ).order_by('-total_points')[:5]
            
            top_performers = [
                {
                    'name': sp.student.full_name,
                    'level': sp.current_level,
                    'total_points': sp.total_points,
                    'badges_count': StudentBadge.objects.filter(student=sp.student).count()
                }
                for sp in top_students
            ]
            
            return {
                'overview': {
                    'total_students': total_students,
                    'active_students': active_students,
                    'engagement_rate': round((active_students / total_students * 100) if total_students > 0 else 0, 1)
                },
                'points_and_levels': {
                    'total_points_awarded': points_stats['total_points'] or 0,
                    'average_level': round(points_stats['avg_level'] or 1, 1),
                    'highest_level': points_stats['max_level'] or 1,
                    'average_streak': round(points_stats['avg_streak'] or 0, 1),
                    'longest_streak': points_stats['max_streak'] or 0
                },
                'badges': {
                    'total_available': badge_stats['active_badges'] or 0,
                    'total_awarded': badges_awarded,
                    'avg_per_student': round((badges_awarded / active_students) if active_students > 0 else 0, 1)
                },
                'activity': {
                    'recent_points_events': recent_activity
                },
                'top_performers': top_performers
            }
        
        stats_data, from_cache = cached_data(cache_key, 1800, _build_stats)
        
        if from_cache:
            return success_response("Gamification stats retrieved", {'data': stats_data, 'cached': True})
        
        logger.info(f"Gamification stats accessed by user {request.user.id}")
        
        return success_response("Gamification stats retrieved", {'data': stats_data})
        
    except Exception as e:
        logger.error(f"Error generating gamification stats for user {request.user.id}: {str(e)}")
        return server_error_response(request.user.id, error_details=str(e))


def _calculate_badge_progress(student, badge, points_profile):
    """Helper function to calculate progress towards a badge"""
    criteria = badge.criteria
    progress = {}
    
    if badge.category == 'reading':
        if 'total_pages' in criteria:
            from .models import Log
            current_pages = Log.objects.filter(student=student).aggregate(
                total=Sum('pages')
            )['total'] or 0
            
            progress['pages'] = {
                'current': current_pages,
                'target': criteria['total_pages'],
                'percentage': min(100, (current_pages / criteria['total_pages'] * 100))
            }
        
        if 'total_books' in criteria:
            from .models import Log
            current_books = Log.objects.filter(
                student=student
            ).exclude(
                title__isnull=True
            ).exclude(
                title__exact=''
            ).values('title').distinct().count()
            
            progress['books'] = {
                'current': current_books,
                'target': criteria['total_books'],
                'percentage': min(100, (current_books / criteria['total_books'] * 100))
            }
    
    elif badge.category == 'consistency':
        if 'streak_days' in criteria:
            progress['streak'] = {
                'current': points_profile.longest_streak,
                'target': criteria['streak_days'],
                'percentage': min(100, (points_profile.longest_streak / criteria['streak_days'] * 100))
            }
    
    elif badge.category == 'milestone':
        if 'level' in criteria:
            progress['level'] = {
                'current': points_profile.current_level,
                'target': criteria['level'],
                'percentage': min(100, (points_profile.current_level / criteria['level'] * 100))
            }
    
    return progress
