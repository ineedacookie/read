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

