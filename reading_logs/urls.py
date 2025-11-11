from django.urls import path

from . import analytics_views
from . import gamification_views
# OPTIMIZED: Split API endpoints into focused modules
from .api import dashboard as dashboard_api
from .api import goals as goals_api
from .api import insights as insights_api
from .api import logs as log_api

urlpatterns = [
    # Core functionality (calendar + legacy AJAX replacements)
    path('api/logs/calendar/', log_api.calendar_logs, name='calendar_logs'),
    path('api/logs/calendar/<int:log_id>/', log_api.calendar_log_detail, name='calendar_log_detail'),
    
    # OPTIMIZED: Dashboard APIs (from api/dashboard.py)
    path('teacher-dashboard/', dashboard_api.teacher_dashboard_logs, name='teacher_dashboard_logs'),
    path('api/get_logs_by_range_and_group', dashboard_api.teacher_dashboard_logs, name='get_logs_by_range_and_group'),  # Legacy URL
    
    # OPTIMIZED: Log APIs (from api/logs.py)
    path('api/student/quick_log/', log_api.student_quick_log, name='student_quick_log'),
    path('api/student/progress/', dashboard_api.student_progress, name='student_progress'),
    path('api/parent/dashboard/', dashboard_api.parent_dashboard_data, name='parent_dashboard'),
    path('api/parent/add_log/', log_api.parent_add_log, name='parent_add_log'),
    path('api/parent/edit_log/', log_api.parent_edit_log, name='parent_edit_log'),
    path('api/parent/delete_log/', log_api.parent_delete_log, name='parent_delete_log'),
    
    # Phase 2: Advanced Analytics APIs
    path('api/analytics/school/', analytics_views.school_analytics_api, name='school_analytics'),
    path('api/analytics/classroom/<int:classroom_id>/', analytics_views.classroom_analytics_api, name='classroom_analytics'),
    path('api/analytics/student/<int:student_id>/', analytics_views.student_analytics_api, name='student_analytics'),
    path('api/analytics/comparison/', analytics_views.comparison_report_api, name='comparison_report'),
    path('api/analytics/trends/', analytics_views.reading_trends_api, name='reading_trends'),
    
    # Phase 2: Gamification APIs
    path('api/gamification/profile/', gamification_views.student_profile_api, name='gamification_profile'),
    path('api/gamification/profile/<int:student_id>/', gamification_views.student_profile_api, name='gamification_profile_by_id'),
    path('api/gamification/badges/', gamification_views.available_badges_api, name='available_badges'),
    path('api/gamification/leaderboard/', gamification_views.leaderboard_api, name='leaderboard'),
    path('api/gamification/award_badge/', gamification_views.award_custom_badge_api, name='award_custom_badge'),
    path('api/gamification/stats/', gamification_views.gamification_stats_api, name='gamification_stats'),
    
    # OPTIMIZED: Goals Management (from api/goals.py)
    path('goals/', goals_api.reading_goals_view, name='reading_goals'),
    path('api/goals/', goals_api.api_reading_goals, name='api_reading_goals'),
    path('api/goals/bulk/', goals_api.api_bulk_reading_goals, name='api_bulk_reading_goals'),
    path('api/goals/individual/', goals_api.api_individual_reading_goal, name='api_individual_reading_goal'),
    
    # OPTIMIZED: Insights (from api/insights.py)
    path('insights/', insights_api.classroom_insights_view, name='classroom_insights'),
    path('api/insights/', insights_api.api_classroom_insights, name='api_classroom_insights'),
    path('api/insights/comparison/', insights_api.api_classroom_comparison, name='api_classroom_comparison'),
    path('api/insights/share/', insights_api.api_share_insight, name='api_share_insight'),
    path('api/insights/helpful/', insights_api.api_mark_helpful, name='api_mark_helpful'),
]
