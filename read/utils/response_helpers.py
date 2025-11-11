"""
Response helper functions to standardize JSON responses and error handling.
Reduces code duplication in views and APIs.
"""

from django.http import JsonResponse
import logging

logger = logging.getLogger('reading_logs.security')


def success_response(message="Success", data=None, status=200):
    """
    Create a standardized success JSON response.
    
    Args:
        message: Success message (default: "Success")
        data: Optional data to include in response
        status: HTTP status code (default: 200)
    
    Returns:
        JsonResponse: Standardized success response
    """
    response_data = {
        'status': 'success',
        'message': message
    }
    
    if data is not None:
        response_data.update(data)
    
    return JsonResponse(response_data, status=status)


def error_response(message, status=400, user_id=None, log_level='warning'):
    """
    Create a standardized error JSON response with optional logging.
    
    Args:
        message: Error message
        status: HTTP status code (default: 400)
        user_id: Optional user ID for logging context
        log_level: Logging level ('warning', 'error', 'info')
    
    Returns:
        JsonResponse: Standardized error response
    """
    # Log the error if user_id is provided
    if user_id:
        log_message = f"API error for user {user_id}: {message}"
        if log_level == 'error':
            logger.error(log_message)
        elif log_level == 'info':
            logger.info(log_message)
        else:
            logger.warning(log_message)
    
    return JsonResponse({
        'status': 'error',
        'message': message
    }, status=status)


def validation_error_response(errors, user_id=None):
    """
    Create a standardized validation error response.
    
    Args:
        errors: Form errors or validation error messages
        user_id: Optional user ID for logging
    
    Returns:
        JsonResponse: Validation error response
    """
    if user_id:
        logger.warning(f"Validation errors for user {user_id}: {errors}")
    
    return JsonResponse({
        'status': 'error',
        'message': 'Data validation failed',
        'errors': errors
    }, status=400)


def permission_denied_response(user_id, action_attempted=None):
    """
    Create a standardized permission denied response with security logging.
    
    Args:
        user_id: User ID attempting the action
        action_attempted: Description of attempted action for logging
    
    Returns:
        JsonResponse: Permission denied response
    """
    log_message = f"Access denied for user {user_id}"
    if action_attempted:
        log_message += f" attempting: {action_attempted}"
    
    logger.warning(log_message)
    
    return JsonResponse({
        'status': 'error',
        'message': 'Access denied'
    }, status=403)


def server_error_response(user_id=None, error_details=None):
    """
    Create a standardized server error response.
    Logs the actual error but doesn't expose it to the user.
    
    Args:
        user_id: Optional user ID for logging context
        error_details: Internal error details for logging only
    
    Returns:
        JsonResponse: Server error response
    """
    log_message = "Internal server error"
    if user_id:
        log_message += f" for user {user_id}"
    if error_details:
        log_message += f": {error_details}"
    
    logger.error(log_message)
    
    return JsonResponse({
        'status': 'error',
        'message': 'An internal error occurred. Please try again.'
    }, status=500)


def created_response(message, resource_id=None, data=None):
    """
    Create a standardized resource created response.
    
    Args:
        message: Success message
        resource_id: ID of the created resource
        data: Optional additional data
    
    Returns:
        JsonResponse: Created response
    """
    response_data = {
        'status': 'success',
        'message': message
    }
    
    if resource_id is not None:
        response_data['id'] = resource_id
    
    if data is not None:
        response_data.update(data)
    
    return JsonResponse(response_data, status=201)


def paginated_response(data, page_obj, additional_data=None):
    """
    Create a standardized paginated response.
    
    Args:
        data: Main data to return
        page_obj: Django Paginator page object
        additional_data: Optional additional data to include
    
    Returns:
        JsonResponse: Paginated response
    """
    response_data = {
        'status': 'success',
        'data': data,
        'pagination': {
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'page_number': page_obj.number,
            'num_pages': page_obj.paginator.num_pages,
            'total_count': page_obj.paginator.count
        }
    }
    
    if additional_data:
        response_data.update(additional_data)
    
    return JsonResponse(response_data)


def dashboard_response(stats, data, date_range=None, additional_info=None):
    """
    Create a standardized dashboard data response.
    
    Args:
        stats: Statistics data
        data: Main dashboard data
        date_range: Optional date range information
        additional_info: Optional additional information
    
    Returns:
        JsonResponse: Dashboard response
    """
    response_data = {
        'status': 'success',
        'stats': stats,
        'data': data
    }
    
    if date_range:
        response_data['date_range'] = date_range
    
    if additional_info:
        response_data.update(additional_info)
    
    return JsonResponse(response_data)


# Specialized responses for reading logs application
def reading_log_created_response(log_id, message="Reading log saved successfully!"):
    """Create response for successful reading log creation."""
    return created_response(message, resource_id=log_id, data={'log_id': log_id})


# All specialized dashboard response helpers have been removed as they were unused.
# Views now construct JsonResponse directly for better clarity and flexibility.

