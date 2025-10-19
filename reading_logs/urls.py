from django.urls import path

from . import views
from . import analytics_views
from . import gamification_views

urlpatterns = [
    # Phase 1: Core functionality
    path('get_logs/', views.get_logs_by_date_range, name='get_logs'),
    path('manage_log/', views.manage_log, name='manage_log'),
    path('api/get_logs_by_range_and_group', views.teacher_dashboard_logs, name='get_logs_by_range_and_group'),
    
    # Phase 1: Student and parent APIs
    path('api/student/quick_log/', views.student_quick_log, name='student_quick_log'),
    path('api/student/progress/', views.student_progress, name='student_progress'),
    path('api/parent/dashboard/', views.parent_dashboard_data, name='parent_dashboard'),
    path('api/parent/add_log/', views.parent_add_log, name='parent_add_log'),
    path('api/parent/edit_log/', views.parent_edit_log, name='parent_edit_log'),
    path('api/parent/delete_log/', views.parent_delete_log, name='parent_delete_log'),
    
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
    
    # Phase 3: Reading Goals Management
    path('goals/', views.reading_goals_view, name='reading_goals'),
    path('api/goals/', views.api_reading_goals, name='api_reading_goals'),
    path('api/goals/bulk/', views.api_bulk_reading_goals, name='api_bulk_reading_goals'),
    path('api/goals/individual/', views.api_individual_reading_goal, name='api_individual_reading_goal'),
    
    # Phase 4: Classroom Insights Sharing
    path('insights/', views.classroom_insights_view, name='classroom_insights'),
    path('api/insights/', views.api_classroom_insights, name='api_classroom_insights'),
    path('api/insights/comparison/', views.api_classroom_comparison, name='api_classroom_comparison'),
    path('api/insights/share/', views.api_share_insight, name='api_share_insight'),
    path('api/insights/helpful/', views.api_mark_helpful, name='api_mark_helpful'),
]
