"""
Utility modules for the reading logs application.
Provides helper functions to reduce code duplication across the application.
"""

# Import commonly used helpers for easy access
from .validation_helpers import (
    validate_date_range,
    validate_single_date,
    validate_positive_integer,
    validate_rating,
    validate_text_field,
    validate_pages_field,
    validate_minutes_field,
    validate_title_field,
    validate_author_field,
    validate_comments_field,
    validate_reading_log_data,
    ValidationError
)

from .response_helpers import (
    success_response,
    error_response,
    validation_error_response,
    permission_denied_response,
    not_found_response,
    rate_limit_response,
    server_error_response,
    created_response,
    reading_log_created_response,
    reading_log_updated_response,
    student_progress_response,
    teacher_dashboard_response,
    parent_dashboard_response
)

from .permission_helpers import (
    check_user_type,
    check_rate_limit,
    verify_school_access,
    verify_parent_child_relationship,
    verify_teacher_student_access,
    get_accessible_students,
    get_accessible_reading_logs,
    require_user_types,
    require_rate_limit,
    can_edit_reading_log,
    can_view_student_data,
    log_successful_action,
    log_permission_denied
)

from .form_helpers import (
    apply_form_control_styling,
    setup_school_filtered_querysets,
    setup_initial_values_for_instance,
    handle_user_type_clean,
    handle_password_validation_for_new_user,
    save_user_with_password,
    update_many_to_many_relationships,
    FormMixin
)

from .user_creation_helpers import (
    create_user_with_defaults,
    create_administrator,
    create_teachers,
    create_students,
    create_parents,
    create_school_users,
    create_classrooms_for_school,
    create_reading_groups_for_school,
    create_parent_child_relationships,
    setup_school_structure,
    create_superuser_if_needed,
    create_school_with_data
)

from .template_helpers import (
    get_user_navigation_items,
    get_user_dashboard_widgets,
    get_breadcrumb_items,
    get_date_range_options,
    format_user_display_name,
    get_user_permissions_context,
    format_reading_stats,
    get_common_template_context,
    template_helpers_context
)

# Test helpers are imported directly in test files to avoid circular imports

from .url_helpers import (
    crud_urls,
    api_crud_urls,
    user_type_urls,
    activation_urls,
    api_resource_urls,
    dashboard_urls,
    management_urls,
    static_page_urls,
    bulk_url_patterns,
    URLPatternGenerator
)

from .settings_helpers import (
    get_env_variable,
    get_boolean_env,
    get_list_env,
    get_database_config,
    get_cache_config,
    get_email_config,
    get_logging_config,
    get_security_settings,
    get_static_media_config,
    EnvironmentConfig
)

from .email_helpers import (
    send_template_email,
    send_activation_email,
    send_invitation_email,
    send_email_change_validation,
    send_feedback_notification,
    send_password_reset_email,
    send_bulk_email,
    send_welcome_email,
    send_reading_goal_reminder,
    validate_email_template,
    get_email_context_defaults
)

from .analytics_helpers import (
    ReadingStatsCalculator,
    GoalProgressCalculator
)

__all__ = [
    # Validation helpers
    'validate_date_range',
    'validate_single_date', 
    'validate_positive_integer',
    'validate_rating',
    'validate_text_field',
    'validate_pages_field',
    'validate_minutes_field',
    'validate_title_field',
    'validate_author_field',
    'validate_comments_field',
    'validate_reading_log_data',
    'ValidationError',
    
    # Response helpers
    'success_response',
    'error_response',
    'validation_error_response',
    'permission_denied_response',
    'not_found_response',
    'rate_limit_response',
    'server_error_response',
    'created_response',
    'reading_log_created_response',
    'reading_log_updated_response',
    'student_progress_response',
    'teacher_dashboard_response',
    'parent_dashboard_response',
    
    # Permission helpers
    'check_user_type',
    'check_rate_limit',
    'verify_school_access',
    'verify_parent_child_relationship',
    'verify_teacher_student_access',
    'get_accessible_students',
    'get_accessible_reading_logs',
    'require_user_types',
    'require_rate_limit',
    'can_edit_reading_log',
    'can_view_student_data',
    'log_successful_action',
    'log_permission_denied',
    
    # Form helpers
    'apply_form_control_styling',
    'setup_school_filtered_querysets',
    'setup_initial_values_for_instance',
    'handle_user_type_clean',
    'handle_password_validation_for_new_user',
    'save_user_with_password',
    'update_many_to_many_relationships',
    'FormMixin',
    
    # User creation helpers
    'create_user_with_defaults',
    'create_administrator',
    'create_teachers',
    'create_students',
    'create_parents',
    'create_school_users',
    'create_classrooms_for_school',
    'create_reading_groups_for_school',
    'create_parent_child_relationships',
    'setup_school_structure',
    'create_superuser_if_needed',
    'create_school_with_data',
    
    # Template helpers
    'get_user_navigation_items',
    'get_user_dashboard_widgets',
    'get_breadcrumb_items',
    'get_date_range_options',
    'format_user_display_name',
    'get_user_permissions_context',
    'format_reading_stats',
    'get_common_template_context',
    'template_helpers_context',
    
    # Test helpers removed to avoid circular imports - import directly in test files
    
    # URL helpers
    'crud_urls',
    'api_crud_urls',
    'user_type_urls',
    'activation_urls',
    'api_resource_urls',
    'dashboard_urls',
    'management_urls',
    'static_page_urls',
    'bulk_url_patterns',
    'URLPatternGenerator',
    
    # Settings helpers
    'get_env_variable',
    'get_boolean_env',
    'get_list_env',
    'get_database_config',
    'get_cache_config',
    'get_email_config',
    'get_logging_config',
    'get_security_settings',
    'get_static_media_config',
    'EnvironmentConfig',
    
    # Email helpers
    'send_template_email',
    'send_activation_email',
    'send_invitation_email',
    'send_email_change_validation',
    'send_feedback_notification',
    'send_password_reset_email',
    'send_bulk_email',
    'send_welcome_email',
    'send_reading_goal_reminder',
    'validate_email_template',
    'get_email_context_defaults',
    
    # Analytics helpers
    'ReadingStatsCalculator',
    'GoalProgressCalculator',
]
