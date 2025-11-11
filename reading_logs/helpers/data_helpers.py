"""
Data retrieval helpers for reading logs.
Provides business logic separate from HTTP layer for reusability.
"""

from collections import defaultdict
from datetime import timedelta

from django.core.cache import cache

from reading_logs.models import Log, DailyGoal, TotalGoal
from users.models import Classroom, ReadingGroup
from .dashboard_helpers import (
    parse_date_range,
    build_student_data,
)


def get_dashboard_data(group_type, group_id, school, date_range_str):
    """
    Get dashboard data for a classroom or reading group.
    Reusable business logic that can be called from views or other contexts.
    
    Args:
        group_type: 'class'/'classroom' or 'group'
        group_id: ID of the classroom or reading group
        school: School object
        date_range_str: Date range string like "Jan 01, 2024 to Jan 31, 2024"
        
    Returns:
        dict: Dashboard data with students, totals, daily_data
        
    Raises:
        ValueError: If parameters are invalid
        Classroom.DoesNotExist / ReadingGroup.DoesNotExist: If group not found
    """
    # Parse date range
    start_date, end_date = parse_date_range(date_range_str)
    num_days = (end_date - start_date).days + 1

    cache_key = (
        f"dashboard:{school.id}:{group_type}:{group_id}:{start_date}:{end_date}"
    )
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    # Get group with prefetched students
    if group_type in ['class', 'classroom']:
        group_obj = Classroom.objects.prefetch_related('students').get(
            id=group_id,
            school=school
        )
    elif group_type == 'group':
        group_obj = ReadingGroup.objects.prefetch_related('students').get(
            id=group_id,
            school=school
        )
    else:
        raise ValueError(f"Invalid group type: {group_type}")
    
    # Get student IDs from prefetched data
    student_ids = [s.id for s in group_obj.students.all()]
    
    # QUERY 1: Batch query all logs
    all_logs = list(
        Log.objects.filter(
            student_id__in=student_ids,
            date__range=(start_date, end_date)
        ).values('student_id', 'pages', 'minutes', 'date')
    )
    
    # QUERY 2 & 3: Batch query all goals
    daily_goals_dict = {g.student_id: g for g in DailyGoal.objects.filter(
        student_id__in=student_ids
    )}
    
    total_goals_dict = {g.student_id: g for g in TotalGoal.objects.filter(
        student_id__in=student_ids
    )}
    
    # Group logs by student (Python processing, no queries)
    logs_by_student = defaultdict(list)
    daily_breakdown = defaultdict(lambda: {'pages': 0, 'minutes': 0, 'logs_count': 0})

    for log in all_logs:
        sid = log['student_id']
        logs_by_student[sid].append(log)

        date_key = log['date'].strftime('%Y-%m-%d')
        entry = daily_breakdown[date_key]
        entry['pages'] += log.get('pages') or 0
        entry['minutes'] += log.get('minutes') or 0
        entry['logs_count'] += 1
    
    # Build student data
    students = group_obj.students.all()  # Uses prefetched data
    student_data, group_totals = build_student_data(
        students, logs_by_student, daily_goals_dict, total_goals_dict, num_days
    )
    
    # Calculate daily breakdown
    # Fill in missing dates for visualization continuity
    current_date = start_date
    while current_date <= end_date:
        date_key = current_date.strftime('%Y-%m-%d')
        daily_breakdown.setdefault(
            date_key,
            {'pages': 0, 'minutes': 0, 'logs_count': 0}
        )
        current_date += timedelta(days=1)
    
    # Calculate group-level metrics
    group_totals['students_count'] = len(students)
    group_totals['avg_pages_per_student'] = round(
        group_totals['pages'] / len(students) if students else 0, 1
    )
    group_totals['avg_minutes_per_student'] = round(
        group_totals['minutes'] / len(students) if students else 0, 1
    )
    group_totals['daily_avg_pages'] = round(
        group_totals['pages'] / (num_days * len(students)) if students and num_days > 0 else 0, 1
    )
    group_totals['daily_avg_minutes'] = round(
        group_totals['minutes'] / (num_days * len(students)) if students and num_days > 0 else 0, 1
    )
    
    # Calculate group goal progress
    if group_totals['students_with_goals'] > 0:
        students_on_track = sum(1 for s in student_data if s['goal_status'] in ['on_track', 'exceeding'])
        group_totals['goal_achievement_rate'] = round(
            (students_on_track / group_totals['students_with_goals']) * 100, 1
        )
    else:
        group_totals['goal_achievement_rate'] = None
    
    # Sort students by goal status
    status_priority = {'struggling': 1, 'behind': 2, 'on_track': 3, 'exceeding': 4, 'no_goal': 5}
    student_data.sort(key=lambda x: (status_priority.get(x['goal_status'], 6), x['name']))
    
    # Format daily data
    daily_data = [
        {'date': date_str, **data}
        for date_str, data in sorted(daily_breakdown.items())
    ]
    
    result = {
        'group_totals': group_totals,
        'students': student_data,
        'daily_data': daily_data,
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

    cache.set(cache_key, result, 300)
    return result


