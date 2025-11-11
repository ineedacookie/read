"""
Analytics utilities for consolidating duplicate statistics calculations.
Provides common aggregate patterns used across analytics.py, gamification.py, and views.py.
"""

from django.db.models import Sum, Count, Avg
from django.db import models


class ReadingStatsCalculator:
    """Centralized calculations for reading log statistics to eliminate duplication."""
    
    @staticmethod
    def get_basic_stats(queryset):
        """
        Get basic aggregate statistics for a reading log queryset.
        
        Args:
            queryset: QuerySet of Log objects
            
        Returns:
            dict: Contains total_pages, total_minutes, total_logs, avg_rating
        """
        return queryset.aggregate(
            total_pages=Sum('pages'),
            total_minutes=Sum('minutes'),
            total_logs=Count('id'),
            avg_rating=Avg('rating')
        )
    
    @staticmethod
    def get_weekly_stats(queryset):
        """
        Get weekly aggregated statistics.
        
        Args:
            queryset: QuerySet of Log objects
            
        Returns:
            QuerySet: Weekly data with logs_count, pages_sum, minutes_sum
        """
        return queryset.extra(
            select={'week': 'EXTRACT(week from date)'}
        ).values('week').annotate(
            logs_count=Count('id'),
            pages_sum=Sum('pages'),
            minutes_sum=Sum('minutes')
        ).order_by('week')
    
    @staticmethod
    def get_monthly_stats(queryset):
        """
        Get monthly aggregated statistics.
        
        Args:
            queryset: QuerySet of Log objects
            
        Returns:
            QuerySet: Monthly data with pages, minutes, logs, avg_rating
        """
        return queryset.extra(
            select={'month': 'EXTRACT(month from date)'}
        ).values('month').annotate(
            pages=Sum('pages'),
            minutes=Sum('minutes'),
            logs=Count('id'),
            avg_rating=Avg('rating')
        ).order_by('month')
    
    @staticmethod
    def get_student_stats(queryset):
        """
        Get per-student aggregate statistics.
        
        Args:
            queryset: QuerySet of Log objects
            
        Returns:
            QuerySet: Per-student data with total_pages, total_minutes, total_logs, avg_rating
        """
        return queryset.values('student').annotate(
            total_pages=Sum('pages'),
            total_minutes=Sum('minutes'),
            total_logs=Count('id'),
            avg_rating=Avg('rating')
        ).order_by('student')
    
    @staticmethod
    def get_total_pages(queryset):
        """
        Get total pages for a queryset (common gamification pattern).
        
        Args:
            queryset: QuerySet of Log objects
            
        Returns:
            int: Total pages read, defaults to 0 if None
        """
        result = queryset.aggregate(total=Sum('pages'))['total']
        return result or 0
    
    @staticmethod
    def get_total_minutes(queryset):
        """
        Get total minutes for a queryset (common gamification pattern).
        
        Args:
            queryset: QuerySet of Log objects
            
        Returns:
            int: Total minutes read, defaults to 0 if None
        """
        result = queryset.aggregate(total=Sum('minutes'))['total']
        return result or 0
    
    @staticmethod
    def get_detailed_stats(queryset):
        """
        Get detailed analytics statistics including averages per session.
        
        Args:
            queryset: QuerySet of Log objects
            
        Returns:
            dict: Detailed statistics including per-session averages
        """
        return queryset.aggregate(
            total_logs=Count('id'),
            total_pages=Sum('pages'),
            total_minutes=Sum('minutes'),
            avg_pages_per_session=Avg('pages'),
            avg_minutes_per_session=Avg('minutes'),
            avg_rating=Avg('rating'),
            unique_students=Count('student', distinct=True)
        )
    
    @staticmethod
    def get_daily_total(queryset, metric='pages'):
        """
        Get daily total for a specific metric.
        
        Args:
            queryset: QuerySet of Log objects for a specific day
            metric: 'pages' or 'minutes'
            
        Returns:
            int: Daily total for the metric, defaults to 0 if None
        """
        if metric == 'pages':
            field = 'pages'
        else:  # minutes
            field = 'minutes'
            
        result = queryset.aggregate(total=Sum(field))['total']
        return result or 0


class GoalProgressCalculator:
    """Utilities for calculating goal progress (used in gamification)."""
    
    @staticmethod
    def calculate_achievement(queryset, goal):
        """
        Calculate achievement progress for a goal.
        
        Args:
            queryset: QuerySet of Log objects
            goal: Goal object with type and value
            
        Returns:
            dict: Contains total_achieved, target, progress_percentage
        """
        if goal.type == 'pages':
            total_achieved = ReadingStatsCalculator.get_total_pages(queryset)
            target = goal.value
        else:  # minutes  
            total_achieved = ReadingStatsCalculator.get_total_minutes(queryset)
            target = goal.value
            
        progress_percentage = (total_achieved / target * 100) if target > 0 else 0
        
        return {
            'total_achieved': total_achieved,
            'target': target,
            'progress_percentage': min(progress_percentage, 100)
        }


class StudentStatsCalculator:
    """Comprehensive student statistics in optimized queries."""
    
    @staticmethod
    def get_student_comprehensive_stats(student, include_dates=False):
        """
        Get ALL statistics for a student in a SINGLE query.
        This replaces multiple separate queries across the codebase.
        
        Args:
            student: Student user object
            include_dates: If True, also fetch recent reading dates for streaks
            
        Returns:
            dict: Complete statistics including total_pages, total_minutes, 
                  unique_books, max_pages_in_session, total_logs
        """
        from reading_logs.models import Log
        from django.db.models import Max
        from datetime import date, timedelta
        
        stats = Log.objects.filter(student=student).aggregate(
            total_logs=Count('id'),
            total_pages=Sum('pages'),
            total_minutes=Sum('minutes'),
            max_pages=Max('pages'),
            unique_books=Count('title', distinct=True),
            avg_rating=Avg('rating')
        )
        
        result = {
            'total_logs': stats['total_logs'] or 0,
            'total_pages': stats['total_pages'] or 0,
            'total_minutes': stats['total_minutes'] or 0,
            'max_pages': stats['max_pages'] or 0,
            'unique_books': stats['unique_books'] or 0,
            'avg_rating': round(float(stats['avg_rating']), 2) if stats['avg_rating'] else 0
        }
        
        # Optionally include reading dates for streak calculation
        if include_dates:
            thirty_days_ago = date.today() - timedelta(days=30)
            reading_dates = set(
                Log.objects.filter(
                    student=student,
                    date__gte=thirty_days_ago
                ).values_list('date', flat=True).distinct()
            )
            result['reading_dates'] = reading_dates
        
        return result
    
    @staticmethod
    def get_date_range_stats(queryset, start_date, end_date):
        """
        Get statistics for logs within a date range.
        
        Args:
            queryset: Base queryset of Log objects
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            dict: Statistics for the date range
        """
        logs = queryset.filter(date__range=(start_date, end_date))
        return ReadingStatsCalculator.get_detailed_stats(logs)
