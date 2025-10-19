"""
Template helper functions and context processors to reduce template duplication.
Provides common template patterns, context data, and utility functions.
"""

from django.urls import reverse
from django.contrib.auth.models import AnonymousUser
from datetime import date, datetime, timedelta
import json


def get_user_navigation_items(user):
    """
    Get navigation items based on user type and permissions.
    
    Args:
        user: Django User object
    
    Returns:
        list: List of navigation item dictionaries
    """
    if isinstance(user, AnonymousUser) or not user.is_authenticated:
        return []
    
    nav_items = []
    
    # Common items for all authenticated users
    nav_items.append({
        'name': 'Dashboard',
        'url': reverse('home'),
        'icon': 'home',
        'active': False  # Set by template context
    })
    
    # User type specific navigation
    if user.user_type == 'administrator':
        nav_items.extend([
            {
                'name': 'Users',
                'url': reverse('user_list_page', kwargs={'user_type': 'student'}),
                'icon': 'users',
                'submenu': [
                    {'name': 'Students', 'url': reverse('user_list_page', kwargs={'user_type': 'student'})},
                    {'name': 'Teachers', 'url': reverse('user_list_page', kwargs={'user_type': 'teacher'})},
                    {'name': 'Parents', 'url': reverse('user_list_page', kwargs={'user_type': 'parent'})},
                    {'name': 'Administrators', 'url': reverse('user_list_page', kwargs={'user_type': 'administrator'})},
                ]
            },
            {
                'name': 'Classrooms',
                'url': reverse('render_classroom_list_view'),
                'icon': 'building'
            },
            {
                'name': 'Reading Groups',
                'url': reverse('render_group_list_view'),
                'icon': 'book-open'
            },
            {
                'name': 'Analytics',
                'url': reverse('analytics_dashboard'),
                'icon': 'chart-bar'
            }
        ])
    
    elif user.user_type == 'teacher':
        nav_items.extend([
            {
                'name': 'My Students',
                'url': reverse('my_students_page'),
                'icon': 'users'
            },
            {
                'name': 'My Classrooms',
                'url': reverse('my_classrooms_page'),
                'icon': 'building'
            },
            {
                'name': 'Reading Groups',
                'url': reverse('render_group_list_view'),
                'icon': 'book-open'
            },
            {
                'name': 'Analytics',
                'url': reverse('analytics_dashboard'),
                'icon': 'chart-bar'
            }
        ])
    
    elif user.user_type == 'student':
        nav_items.extend([
            {
                'name': 'Reading Log',
                'url': reverse('record'),
                'icon': 'book'
            },
            {
                'name': 'My Progress',
                'url': '#',  # Handled by dashboard
                'icon': 'chart-line'
            },
            {
                'name': 'Achievements',
                'url': reverse('gamification_dashboard'),
                'icon': 'trophy'
            }
        ])
    
    elif user.user_type == 'parent':
        nav_items.extend([
            {
                'name': 'My Children',
                'url': '#',  # Handled by dashboard
                'icon': 'heart'
            },
            {
                'name': 'Add Reading Log',
                'url': reverse('record'),
                'icon': 'plus'
            }
        ])
    
    return nav_items


def get_user_dashboard_widgets(user):
    """
    Get dashboard widgets based on user type.
    
    Args:
        user: Django User object
    
    Returns:
        list: List of widget configuration dictionaries
    """
    if isinstance(user, AnonymousUser) or not user.is_authenticated:
        return []
    
    widgets = []
    
    if user.user_type == 'administrator':
        widgets = [
            {
                'name': 'system_overview',
                'title': 'System Overview',
                'template': 'widgets/admin_overview.html',
                'size': 'large'
            },
            {
                'name': 'recent_activity',
                'title': 'Recent Activity',
                'template': 'widgets/recent_activity.html',
                'size': 'medium'
            },
            {
                'name': 'school_stats',
                'title': 'School Statistics',
                'template': 'widgets/school_stats.html',
                'size': 'medium'
            }
        ]
    
    elif user.user_type == 'teacher':
        widgets = [
            {
                'name': 'class_overview',
                'title': 'Class Overview',
                'template': 'widgets/teacher_overview.html',
                'size': 'large'
            },
            {
                'name': 'student_progress',
                'title': 'Student Progress',
                'template': 'widgets/student_progress.html',
                'size': 'medium'
            },
            {
                'name': 'recent_logs',
                'title': 'Recent Reading Logs',
                'template': 'widgets/recent_logs.html',
                'size': 'medium'
            }
        ]
    
    elif user.user_type == 'student':
        widgets = [
            {
                'name': 'reading_progress',
                'title': 'My Reading Progress',
                'template': 'widgets/student_progress.html',
                'size': 'large'
            },
            {
                'name': 'goals',
                'title': 'My Goals',
                'template': 'widgets/student_goals.html',
                'size': 'medium'
            },
            {
                'name': 'achievements',
                'title': 'Recent Achievements',
                'template': 'widgets/student_achievements.html',
                'size': 'medium'
            }
        ]
    
    elif user.user_type == 'parent':
        widgets = [
            {
                'name': 'children_overview',
                'title': 'My Children',
                'template': 'widgets/parent_overview.html',
                'size': 'large'
            },
            {
                'name': 'reading_summary',
                'title': 'Reading Summary',
                'template': 'widgets/reading_summary.html',
                'size': 'medium'
            }
        ]
    
    return widgets


def get_breadcrumb_items(request, page_title=None):
    """
    Generate breadcrumb navigation items based on current URL.
    
    Args:
        request: Django request object
        page_title: Optional specific page title
    
    Returns:
        list: List of breadcrumb item dictionaries
    """
    breadcrumbs = [
        {'name': 'Home', 'url': reverse('home'), 'active': False}
    ]
    
    path = request.path.strip('/')
    path_parts = path.split('/')
    
    # Build breadcrumbs based on URL structure
    if path_parts[0] == 'student' or 'student' in path:
        breadcrumbs.append({'name': 'Students', 'url': reverse('user_list_page', kwargs={'user_type': 'student'}), 'active': False})
    elif path_parts[0] == 'teacher' or 'teacher' in path:
        breadcrumbs.append({'name': 'Teachers', 'url': reverse('user_list_page', kwargs={'user_type': 'teacher'}), 'active': False})
    elif path_parts[0] == 'parent' or 'parent' in path:
        breadcrumbs.append({'name': 'Parents', 'url': reverse('user_list_page', kwargs={'user_type': 'parent'}), 'active': False})
    elif path_parts[0] == 'administrator' or 'admin' in path:
        breadcrumbs.append({'name': 'Administrators', 'url': reverse('user_list_page', kwargs={'user_type': 'administrator'}), 'active': False})
    elif 'classroom' in path:
        breadcrumbs.append({'name': 'Classrooms', 'url': reverse('render_classroom_list_view'), 'active': False})
    elif 'group' in path:
        breadcrumbs.append({'name': 'Reading Groups', 'url': reverse('render_group_list_view'), 'active': False})
    elif 'analytics' in path:
        breadcrumbs.append({'name': 'Analytics', 'url': reverse('analytics_dashboard'), 'active': False})
    elif 'gamification' in path:
        breadcrumbs.append({'name': 'Achievements', 'url': reverse('gamification_dashboard'), 'active': False})
    
    # Add current page
    if page_title:
        breadcrumbs.append({'name': page_title, 'url': None, 'active': True})
    
    return breadcrumbs


def get_date_range_options():
    """
    Get common date range options for filters.
    
    Returns:
        list: List of date range option dictionaries
    """
    today = date.today()
    
    return [
        {
            'name': 'Today',
            'value': 'today',
            'start_date': today,
            'end_date': today
        },
        {
            'name': 'This Week',
            'value': 'this_week',
            'start_date': today - timedelta(days=today.weekday()),
            'end_date': today - timedelta(days=today.weekday()) + timedelta(days=6)
        },
        {
            'name': 'This Month',
            'value': 'this_month',
            'start_date': today.replace(day=1),
            'end_date': today
        },
        {
            'name': 'Last 7 Days',
            'value': 'last_7_days',
            'start_date': today - timedelta(days=7),
            'end_date': today
        },
        {
            'name': 'Last 30 Days',
            'value': 'last_30_days',
            'start_date': today - timedelta(days=30),
            'end_date': today
        },
        {
            'name': 'Last 90 Days',
            'value': 'last_90_days',
            'start_date': today - timedelta(days=90),
            'end_date': today
        }
    ]


def format_user_display_name(user):
    """
    Format user display name consistently.
    
    Args:
        user: Django User object
    
    Returns:
        str: Formatted display name
    """
    if hasattr(user, 'full_name') and user.full_name:
        return user.full_name
    elif hasattr(user, 'first_name') and user.first_name:
        last_part = f" {user.last_initial}." if hasattr(user, 'last_initial') and user.last_initial else ""
        return f"{user.first_name}{last_part}"
    else:
        return user.email or user.username


def get_user_permissions_context(user):
    """
    Get user permissions context for templates.
    
    Args:
        user: Django User object
    
    Returns:
        dict: Permissions context dictionary
    """
    if isinstance(user, AnonymousUser) or not user.is_authenticated:
        return {
            'can_view_all_students': False,
            'can_edit_students': False,
            'can_manage_classrooms': False,
            'can_view_analytics': False,
            'can_manage_users': False,
            'is_administrator': False,
            'is_teacher': False,
            'is_student': False,
            'is_parent': False
        }
    
    user_type = getattr(user, 'user_type', None)
    
    return {
        'can_view_all_students': user_type in ['administrator', 'teacher'],
        'can_edit_students': user_type in ['administrator', 'teacher'],
        'can_manage_classrooms': user_type in ['administrator', 'teacher'],
        'can_view_analytics': user_type in ['administrator', 'teacher'],
        'can_manage_users': user_type == 'administrator',
        'is_administrator': user_type == 'administrator',
        'is_teacher': user_type == 'teacher',
        'is_student': user_type == 'student',
        'is_parent': user_type == 'parent'
    }


def get_form_field_classes():
    """
    Get standard form field CSS classes.
    
    Returns:
        dict: CSS class mappings for form fields
    """
    return {
        'text_input': 'form-control',
        'textarea': 'form-control',
        'select': 'form-select',
        'checkbox': 'form-check-input',
        'radio': 'form-check-input',
        'file': 'form-control',
        'date': 'form-control',
        'datetime': 'form-control',
        'number': 'form-control',
        'email': 'form-control',
        'password': 'form-control',
        'url': 'form-control'
    }


def get_alert_classes():
    """
    Get standard alert CSS classes.
    
    Returns:
        dict: Alert type to CSS class mappings
    """
    return {
        'success': 'alert alert-success alert-dismissible fade show',
        'error': 'alert alert-danger alert-dismissible fade show',
        'warning': 'alert alert-warning alert-dismissible fade show',
        'info': 'alert alert-info alert-dismissible fade show'
    }


def get_button_classes():
    """
    Get standard button CSS classes.
    
    Returns:
        dict: Button type to CSS class mappings
    """
    return {
        'primary': 'btn btn-primary',
        'secondary': 'btn btn-secondary',
        'success': 'btn btn-success',
        'danger': 'btn btn-danger',
        'warning': 'btn btn-warning',
        'info': 'btn btn-info',
        'light': 'btn btn-light',
        'dark': 'btn btn-dark',
        'link': 'btn btn-link',
        'outline_primary': 'btn btn-outline-primary',
        'outline_secondary': 'btn btn-outline-secondary'
    }


def get_card_classes():
    """
    Get standard card CSS classes.
    
    Returns:
        dict: Card type to CSS class mappings
    """
    return {
        'default': 'card',
        'primary': 'card border-primary',
        'secondary': 'card border-secondary',
        'success': 'card border-success',
        'danger': 'card border-danger',
        'warning': 'card border-warning',
        'info': 'card border-info',
        'light': 'card border-light',
        'dark': 'card border-dark'
    }


def format_reading_stats(stats):
    """
    Format reading statistics for display.
    
    Args:
        stats: Dictionary of reading statistics
    
    Returns:
        dict: Formatted statistics
    """
    formatted = {}
    
    # Format numbers with commas
    for key in ['total_pages', 'total_minutes', 'total_logs']:
        if key in stats:
            value = stats[key] or 0
            formatted[key] = f"{value:,}"
    
    # Format averages with decimal places
    for key in ['avg_rating', 'avg_pages_per_day', 'avg_minutes_per_day']:
        if key in stats:
            value = stats[key] or 0
            formatted[key] = f"{value:.1f}"
    
    # Calculate derived stats
    if 'total_minutes' in stats and stats['total_minutes']:
        hours = stats['total_minutes'] // 60
        minutes = stats['total_minutes'] % 60
        formatted['total_time_display'] = f"{hours}h {minutes}m"
    
    return formatted


def get_common_template_context():
    """
    Get common template context data used across multiple templates.
    
    Returns:
        dict: Common context dictionary
    """
    return {
        'form_classes': get_form_field_classes(),
        'alert_classes': get_alert_classes(),
        'button_classes': get_button_classes(),
        'card_classes': get_card_classes(),
        'date_range_options': get_date_range_options(),
        'current_year': date.today().year
    }


# Context processor
def template_helpers_context(request):
    """
    Context processor that adds helper functions and common data to all templates.
    
    Args:
        request: Django request object
    
    Returns:
        dict: Context dictionary
    """
    context = get_common_template_context()
    
    if hasattr(request, 'user') and request.user.is_authenticated:
        context.update({
            'user_nav_items': get_user_navigation_items(request.user),
            'user_dashboard_widgets': get_user_dashboard_widgets(request.user),
            'user_permissions': get_user_permissions_context(request.user),
            'user_display_name': format_user_display_name(request.user)
        })
    
    # Add helper functions to template context
    context.update({
        'get_breadcrumbs': lambda page_title=None: get_breadcrumb_items(request, page_title),
        'format_stats': format_reading_stats,
        'format_user_name': format_user_display_name
    })
    
    return context

