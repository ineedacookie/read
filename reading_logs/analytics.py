"""
Phase 2: Advanced Analytics & Reporting Engine
Enterprise-grade analytics for reading tracking system
"""

from django.db.models import Sum, Count, Avg, Q, F, Max
from django.db.models.functions import TruncWeek, TruncMonth, TruncYear
from django.db import models
from datetime import date, timedelta, datetime
from decimal import Decimal
import json

from .models import Log, DailyGoal, TotalGoal
from users.models import CustomUser, School, Classroom, ReadingGroup


class ReadingAnalytics:
    """
    Comprehensive analytics engine for reading data
    Provides insights for teachers, administrators, and parents
    """
    
    def __init__(self, user=None, school=None):
        self.user = user
        self.school = school or (user.school if user else None)
    
    def get_school_overview(self, start_date=None, end_date=None):
        """
        Get comprehensive school-wide analytics
        For administrators and district managers
        """
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()
        
        logs = Log.objects.filter(
            school=self.school,
            date__range=(start_date, end_date)
        )
        
        # Basic metrics
        total_stats = logs.aggregate(
            total_logs=Count('id'),
            total_pages=Sum('pages'),
            total_minutes=Sum('minutes'),
            avg_rating=Avg('rating'),
            unique_students=Count('student', distinct=True)
        )
        
        # Reading trends by week
        weekly_trends = logs.annotate(
            week=TruncWeek('date')
        ).values('week').annotate(
            logs_count=Count('id'),
            pages_sum=Sum('pages'),
            minutes_sum=Sum('minutes')
        ).order_by('week')
        
        # Top performing students
        top_students = logs.values(
            'student__first_name', 
            'student__last_initial',
            'student__id'
        ).annotate(
            total_pages=Sum('pages'),
            total_minutes=Sum('minutes'),
            total_logs=Count('id'),
            avg_rating=Avg('rating')
        ).order_by('-total_pages')[:10]
        
        # Reading levels analysis
        rating_distribution = logs.exclude(
            rating__isnull=True
        ).values('rating').annotate(
            count=Count('id')
        ).order_by('rating')
        
        # Goal achievement analysis
        students_with_goals = DailyGoal.objects.filter(
            school=self.school
        ).values_list('student_id', flat=True)
        
        goal_achievement = self._calculate_goal_achievement_rates(
            students_with_goals, start_date, end_date
        )
        
        return {
            'overview': total_stats,
            'trends': list(weekly_trends),
            'top_students': list(top_students),
            'rating_distribution': list(rating_distribution),
            'goal_achievement': goal_achievement,
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            }
        }
    
    def get_classroom_analytics(self, classroom_id, start_date=None, end_date=None):
        """
        Detailed analytics for a specific classroom
        For teachers and classroom managers
        """
        try:
            classroom = Classroom.objects.get(id=classroom_id, school=self.school)
        except Classroom.DoesNotExist:
            return {'error': 'Classroom not found'}
        
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()
        
        # Get classroom students
        students = classroom.students.all()
        
        logs = Log.objects.filter(
            student__in=students,
            date__range=(start_date, end_date)
        )
        
        # Individual student performance
        student_performance = []
        for student in students:
            student_logs = logs.filter(student=student)
            stats = student_logs.aggregate(
                total_pages=Sum('pages'),
                total_minutes=Sum('minutes'),
                total_logs=Count('id'),
                avg_rating=Avg('rating')
            )
            
            # Calculate reading consistency (days with logs)
            reading_days = student_logs.values('date').distinct().count()
            total_days = (end_date - start_date).days + 1
            consistency_rate = (reading_days / total_days) * 100 if total_days > 0 else 0
            
            student_performance.append({
                'student_id': student.id,
                'name': student.full_name,
                'email': student.email,
                'stats': stats,
                'consistency_rate': round(consistency_rate, 1),
                'reading_days': reading_days
            })
        
        # Classroom averages
        classroom_stats = logs.aggregate(
            avg_pages_per_log=Avg('pages'),
            avg_minutes_per_log=Avg('minutes'),
            avg_rating=Avg('rating'),
            total_logs=Count('id')
        )
        
        # Reading frequency analysis
        daily_activity = logs.extra(
            select={'day': 'date'}
        ).values('day').annotate(
            logs_count=Count('id'),
            unique_students=Count('student', distinct=True)
        ).order_by('day')
        
        return {
            'classroom': {
                'id': classroom.id,
                'name': classroom.name,
                'student_count': students.count()
            },
            'stats': classroom_stats,
            'student_performance': student_performance,
            'daily_activity': list(daily_activity),
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            }
        }
    
    def get_student_detailed_analytics(self, student_id, start_date=None, end_date=None):
        """
        Comprehensive analytics for individual student
        For parents, teachers, and the student themselves
        """
        try:
            student = CustomUser.objects.get(
                id=student_id, 
                school=self.school,
                user_type='student'
            )
        except CustomUser.DoesNotExist:
            return {'error': 'Student not found'}
        
        if not start_date:
            start_date = date.today() - timedelta(days=90)  # 3 months default
        if not end_date:
            end_date = date.today()
        
        logs = Log.objects.filter(
            student=student,
            date__range=(start_date, end_date)
        )
        
        # Basic statistics
        basic_stats = logs.aggregate(
            total_logs=Count('id'),
            total_pages=Sum('pages'),
            total_minutes=Sum('minutes'),
            avg_pages_per_session=Avg('pages'),
            avg_minutes_per_session=Avg('minutes'),
            avg_rating=Avg('rating'),
            highest_rating=models.Max('rating'),
            total_books=Count('title', distinct=True)
        )
        
        # Reading progression over time
        monthly_progression = logs.annotate(
            month=TruncMonth('date')
        ).values('month').annotate(
            pages=Sum('pages'),
            minutes=Sum('minutes'),
            logs=Count('id'),
            avg_rating=Avg('rating')
        ).order_by('month')
        
        # Goal progress
        goals = DailyGoal.objects.filter(student=student)
        goal_progress = []
        for goal in goals:
            progress = self._calculate_individual_goal_progress(
                student, goal, start_date, end_date
            )
            goal_progress.append(progress)
        
        # Reading habits analysis
        reading_habits = self._analyze_reading_habits(logs)
        
        # Book preferences
        favorite_authors = logs.exclude(
            author__isnull=True
        ).exclude(
            author__exact=''
        ).values('author').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        # Reading streaks
        reading_streak = self._calculate_reading_streak(student, end_date)
        
        return {
            'student': {
                'id': student.id,
                'name': student.full_name,
                'email': student.email
            },
            'stats': basic_stats,
            'progression': list(monthly_progression),
            'goals': goal_progress,
            'habits': reading_habits,
            'favorite_authors': list(favorite_authors),
            'reading_streak': reading_streak,
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            }
        }
    
    def generate_comparison_report(self, student_ids, start_date=None, end_date=None):
        """
        Compare multiple students' reading performance
        For teachers and parents with multiple children
        """
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()
        
        students = CustomUser.objects.filter(
            id__in=student_ids,
            school=self.school,
            user_type='student'
        )
        
        comparison_data = []
        
        for student in students:
            logs = Log.objects.filter(
                student=student,
                date__range=(start_date, end_date)
            )
            
            stats = logs.aggregate(
                total_pages=Sum('pages'),
                total_minutes=Sum('minutes'),
                total_logs=Count('id'),
                avg_rating=Avg('rating')
            )
            
            # Calculate percentiles
            all_students_logs = Log.objects.filter(
                school=self.school,
                date__range=(start_date, end_date)
            )
            
            pages_percentile = self._calculate_percentile(
                stats['total_pages'] or 0,
                all_students_logs.values('student').annotate(
                    total=Sum('pages')
                ).values_list('total', flat=True)
            )
            
            comparison_data.append({
                'student': {
                    'id': student.id,
                    'name': student.full_name
                },
                'stats': stats,
                'percentiles': {
                    'pages': pages_percentile
                }
            })
        
        return {
            'comparison': comparison_data,
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            }
        }
    
    def _calculate_goal_achievement_rates(self, student_ids, start_date, end_date):
        """Calculate goal achievement rates for given students"""
        if not student_ids:
            return {'achievement_rate': 0, 'total_goals': 0}
        
        achieved = 0
        total_goals = 0
        
        for student_id in student_ids:
            goals = DailyGoal.objects.filter(student_id=student_id)
            for goal in goals:
                days_in_range = (end_date - max(start_date, goal.created_at.date())).days + 1
                if days_in_range <= 0:
                    continue
                
                total_goals += days_in_range
                
                # Check each day in range
                current_date = max(start_date, goal.created_at.date())
                while current_date <= end_date:
                    day_logs = Log.objects.filter(
                        student_id=student_id,
                        date=current_date
                    )
                    
                    if goal.type == 'pages':
                        daily_total = day_logs.aggregate(
                            total=Sum('pages')
                        )['total'] or 0
                    else:  # minutes
                        daily_total = day_logs.aggregate(
                            total=Sum('minutes')
                        )['total'] or 0
                    
                    if daily_total >= goal.value:
                        achieved += 1
                    
                    current_date += timedelta(days=1)
        
        achievement_rate = (achieved / total_goals * 100) if total_goals > 0 else 0
        
        return {
            'achievement_rate': round(achievement_rate, 1),
            'total_goals': total_goals,
            'achieved': achieved
        }
    
    def _calculate_individual_goal_progress(self, student, goal, start_date, end_date):
        """Calculate progress for a specific goal"""
        logs = Log.objects.filter(
            student=student,
            date__range=(start_date, end_date)
        )
        
        if goal.type == 'pages':
            total_achieved = logs.aggregate(total=Sum('pages'))['total'] or 0
            target = goal.value * (end_date - start_date).days
        else:  # minutes
            total_achieved = logs.aggregate(total=Sum('minutes'))['total'] or 0
            target = goal.value * (end_date - start_date).days
        
        progress_percentage = (total_achieved / target * 100) if target > 0 else 0
        
        return {
            'goal_type': goal.type,
            'daily_target': goal.value,
            'total_target': target,
            'achieved': total_achieved,
            'progress_percentage': round(progress_percentage, 1)
        }
    
    def _analyze_reading_habits(self, logs):
        """Analyze reading patterns and habits"""
        # Reading time preferences
        time_distribution = logs.extra(
            select={'hour': "strftime('%%H', created_at)"}
        ).values('hour').annotate(
            count=Count('id')
        ).order_by('hour')
        
        # Session length analysis
        session_lengths = logs.exclude(
            minutes__isnull=True
        ).values_list('minutes', flat=True)
        
        if session_lengths:
            avg_session = sum(session_lengths) / len(session_lengths)
            short_sessions = len([s for s in session_lengths if s < 15])
            medium_sessions = len([s for s in session_lengths if 15 <= s < 45])
            long_sessions = len([s for s in session_lengths if s >= 45])
        else:
            avg_session = 0
            short_sessions = medium_sessions = long_sessions = 0
        
        return {
            'avg_session_length': round(avg_session, 1),
            'session_distribution': {
                'short': short_sessions,  # < 15 minutes
                'medium': medium_sessions,  # 15-45 minutes
                'long': long_sessions  # > 45 minutes
            },
            'time_preferences': list(time_distribution)
        }
    
    def _calculate_reading_streak(self, student, end_date):
        """Calculate current and longest reading streaks"""
        logs = Log.objects.filter(
            student=student,
            date__lte=end_date
        ).values('date').distinct().order_by('-date')
        
        if not logs:
            return {'current_streak': 0, 'longest_streak': 0}
        
        dates = [log['date'] for log in logs]
        
        # Calculate current streak
        current_streak = 0
        current_date = end_date
        
        for log_date in dates:
            if log_date == current_date:
                current_streak += 1
                current_date -= timedelta(days=1)
            else:
                break
        
        # Calculate longest streak
        longest_streak = 0
        temp_streak = 1
        
        for i in range(1, len(dates)):
            if dates[i-1] - dates[i] == timedelta(days=1):
                temp_streak += 1
            else:
                longest_streak = max(longest_streak, temp_streak)
                temp_streak = 1
        
        longest_streak = max(longest_streak, temp_streak)
        
        return {
            'current_streak': current_streak,
            'longest_streak': longest_streak
        }
    
    def _calculate_percentile(self, value, dataset):
        """Calculate percentile ranking"""
        dataset = [x for x in dataset if x is not None]
        if not dataset:
            return 0
        
        below = len([x for x in dataset if x < value])
        return round((below / len(dataset)) * 100, 1)


# Export utilities for external use
def get_school_analytics(school, start_date=None, end_date=None):
    """Convenience function for school analytics"""
    analytics = ReadingAnalytics(school=school)
    return analytics.get_school_overview(start_date, end_date)


def get_classroom_analytics(classroom_id, school, start_date=None, end_date=None):
    """Convenience function for classroom analytics"""
    analytics = ReadingAnalytics(school=school)
    return analytics.get_classroom_analytics(classroom_id, start_date, end_date)


def get_student_analytics(student_id, school, start_date=None, end_date=None):
    """Convenience function for student analytics"""
    analytics = ReadingAnalytics(school=school)
    return analytics.get_student_detailed_analytics(student_id, start_date, end_date)
