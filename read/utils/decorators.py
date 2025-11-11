"""
Enhanced decorators for views with security, rate limiting, and performance monitoring.
"""

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from functools import wraps
import time
import logging

logger = logging.getLogger('reading_logs.security')


def ajax_login_required(view_func):
    """
    AJAX-aware login required decorator.
    Returns JSON error for AJAX requests, redirects for regular requests.
    CONSOLIDATED: Moved from views.py to eliminate duplication across 4+ files.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
               request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': 'Authentication required'}, status=401)
            return login_required(view_func)(request, *args, **kwargs)
        return view_func(request, *args, **kwargs)
    return wrapper


def require_user_types(*allowed_types):
    """
    Decorator to restrict view access to specific user types.
    Usage: @require_user_types('teacher', 'administrator')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.user.user_type not in allowed_types:
                logger.warning(f"User {request.user.id} ({request.user.user_type}) attempted to access {view_func.__name__}")
                return JsonResponse({'status': 'error', 'message': 'Access denied'}, status=403)
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def rate_limit(requests_per_minute=60):
    """
    Basic rate limiting decorator.
    Usage: @rate_limit(requests_per_minute=30)
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            from django.core.cache import cache
            cache_key = f"rate_limit:{request.user.id}:{view_func.__name__}"
            request_count = cache.get(cache_key, 0)
            
            if request_count >= requests_per_minute:
                logger.warning(f"Rate limit exceeded for user {request.user.id} on {view_func.__name__}")
                return JsonResponse({
                    'status': 'error', 
                    'message': 'Rate limit exceeded. Please try again later.'
                }, status=429)
            
            cache.set(cache_key, request_count + 1, 60)
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def log_action(action_name):
    """
    Decorator to log successful actions for audit trail.
    Usage: @log_action('student_quick_log')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            response = view_func(request, *args, **kwargs)
            
            # Only log if successful (status 200-299)
            if hasattr(response, 'status_code') and 200 <= response.status_code < 300:
                logger.info(f"Action '{action_name}' by user {request.user.id}")
            
            return response
        return wrapper
    return decorator


def measure_performance(threshold_ms=1000):
    """
    Decorator to measure and log slow requests.
    Usage: @measure_performance(threshold_ms=500)
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            start_time = time.time()
            response = view_func(request, *args, **kwargs)
            elapsed_ms = (time.time() - start_time) * 1000
            
            if elapsed_ms > threshold_ms:
                logger.warning(f"Slow request: {view_func.__name__} took {elapsed_ms:.2f}ms (threshold: {threshold_ms}ms)")
            
            return response
        return wrapper
    return decorator


def require_json_body(view_func):
    """
    Decorator to ensure request body is valid JSON.
    Usage: @require_json_body
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        import json
        try:
            if request.body:
                json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON in request body'}, status=400)
        return view_func(request, *args, **kwargs)
    return wrapper
