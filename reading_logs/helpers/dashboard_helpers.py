"""
Helper functions for dashboard data processing.
Keeps views clean and logic reusable.
"""

from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
from datetime import timedelta


def calculate_daily_breakdown(student_ids, start_date, end_date):
    """
    Calculate daily reading statistics for a group of students.
    OPTIMIZED: Uses database aggregation instead of Python loops.
    
    Args:
        student_ids: List of student IDs
        start_date: Start date for range
        end_date: End date for range
        
    Returns:
        dict: Daily breakdown with pages, minutes, logs_count per date
    """
    from reading_logs.models import Log
    
    # OPTIMIZED: Let database do the grouping
    daily_data = Log.objects.filter(
        student_id__in=student_ids,
        date__range=(start_date, end_date)
    ).values('date').annotate(
        pages=Sum('pages'),
        minutes=Sum('minutes'),
        logs_count=Count('id')
    ).order_by('date')
    
    # Convert to dict and fill in missing dates with zeros
    breakdown = {}
    
    # First, add actual data
    for item in daily_data:
        date_str = item['date'].strftime('%Y-%m-%d')
        breakdown[date_str] = {
            'pages': item['pages'] or 0,
            'minutes': item['minutes'] or 0,
            'logs_count': item['logs_count']
        }
    
    # Fill in missing dates
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        if date_str not in breakdown:
            breakdown[date_str] = {
                'pages': 0,
                'minutes': 0,
                'logs_count': 0
            }
        current_date += timedelta(days=1)
    
    return breakdown


def calculate_goal_status(daily_avg, goal):
    """
    Calculate if student is meeting their goal.
    
    Args:
        daily_avg: Average pages/minutes per day
        goal: DailyGoal object
        
    Returns:
        tuple: (progress_percentage, status_string)
    """
    if not goal or goal.value == 0:
        return None, 'no_goal'
    
    progress = (daily_avg / goal.value) * 100
    
    if progress < 50:
        status = 'struggling'
    elif progress < 80:
        status = 'behind'
    elif progress >= 100:
        status = 'exceeding'
    else:
        status = 'on_track'
    
    return round(progress, 1), status


def build_student_data(students, logs_by_student, daily_goals_dict, total_goals_dict, num_days):
    """
    Build student performance data for dashboard.
    
    Args:
        students: QuerySet of students
        logs_by_student: Dict mapping student_id to list of log dicts
        daily_goals_dict: Dict mapping student_id to DailyGoal
        total_goals_dict: Dict mapping student_id to TotalGoal
        num_days: Number of days in date range
        
    Returns:
        tuple: (student_data list, group_totals dict)
    """
    student_data = []
    group_totals = {
        'pages': 0, 
        'minutes': 0, 
        'students_with_goals': 0, 
        'struggling_students': 0
    }
    
    for student in students:
        logs = logs_by_student.get(student.id, [])
        
        total_pages = sum(log['pages'] or 0 for log in logs)
        total_minutes = sum(log['minutes'] or 0 for log in logs)
        
        daily_avg_pages = total_pages / num_days if num_days > 0 else 0
        daily_avg_minutes = total_minutes / num_days if num_days > 0 else 0
        
        # Get goals
        daily_goal = daily_goals_dict.get(student.id)
        total_goal = total_goals_dict.get(student.id)
        
        # Calculate goal progress
        goal_progress = None
        goal_status = 'no_goal'
        
        if daily_goal:
            group_totals['students_with_goals'] += 1
            if daily_goal.type == 'pages':
                goal_progress, goal_status = calculate_goal_status(daily_avg_pages, daily_goal)
            else:
                goal_progress, goal_status = calculate_goal_status(daily_avg_minutes, daily_goal)
            
            if goal_status == 'struggling':
                group_totals['struggling_students'] += 1
        
        student_info = {
            'id': student.id,
            'name': student.full_name,
            'pages': total_pages,
            'minutes': total_minutes,
            'daily_avg_pages': round(daily_avg_pages, 1),
            'daily_avg_minutes': round(daily_avg_minutes, 1),
            'goal_progress': goal_progress,
            'goal_status': goal_status,
            'goal_type': daily_goal.type if daily_goal else None,
            'goal_value': daily_goal.value if daily_goal else None,
            'has_total_goal': total_goal is not None,
            'logs_count': len(logs)
        }
        
        student_data.append(student_info)
        group_totals['pages'] += total_pages
        group_totals['minutes'] += total_minutes
    
    return student_data, group_totals


def parse_date_range(date_range_str):
    """
    Parse date range string into start_date and end_date.
    
    Args:
        date_range_str: String like "Jan 01, 2024 to Jan 31, 2024"
        
    Returns:
        tuple: (start_date, end_date)
    """
    from datetime import datetime
    
    if not date_range_str or ' to ' not in date_range_str:
        raise ValueError("Invalid date range format")
    
    start_str, end_str = date_range_str.split(' to ')
    start_date = datetime.strptime(start_str.strip(), '%b %d, %Y').date()
    end_date = datetime.strptime(end_str.strip(), '%b %d, %Y').date()
    
    return start_date, end_date


def get_group_with_students(group_type, group_id, school):
    """
    Get classroom or reading group with prefetched students.
    
    Args:
        group_type: 'class' or 'group'
        group_id: ID of the classroom/group
        school: School object
        
    Returns:
        Classroom or ReadingGroup object with students prefetched
    """
    from users.models import Classroom, ReadingGroup
    
    if group_type == 'class' or group_type == 'classroom':
        return Classroom.objects.prefetch_related('students').get(
            id=group_id,
            school=school
        )
    elif group_type == 'group':
        return ReadingGroup.objects.prefetch_related('students').get(
            id=group_id,
            school=school
        )
    else:
        raise ValueError(f"Invalid group type: {group_type}")


