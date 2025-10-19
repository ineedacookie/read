"""
View Decorators for Enhanced Functionality
Provides reusable decorators for:
- User type validation
- JSON body validation
- Rate limiting
- Date parameter validation
"""

import json
import logging
from functools import wraps
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.core.cache import cache
from django.core.exceptions import PermissionDenied

logger = logging.getLogger(__name__)


def require_user_types(*user_types):
    """
    Decorator to restrict view access to specific user types.
    
    Usage:
        @require_user_types('teacher', 'administrator')
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse({
                    'success': False,
                    'error': 'Authentication required'
                }, status=401)
            
            if request.user.user_type not in user_types:
                logger.warning(
                    f"Access denied for user {request.user.id} "
                    f"(type: {request.user.user_type}) to view requiring: {user_types}"
                )
                raise PermissionDenied(
                    f"Access denied. This resource is only accessible to: {', '.join(user_types)}"
                )
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_json_body(max_size=10240):
    """
    Decorator to validate JSON request body.
    Parses JSON and adds it to request.json_data
    
    Usage:
        @require_json_body(max_size=10240)
        def my_view(request):
            data = request.json_data
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Check content type
            content_type = request.META.get('CONTENT_TYPE', '')
            if 'application/json' not in content_type:
                return JsonResponse({
                    'success': False,
                    'error': 'Content-Type must be application/json'
                }, status=400)
            
            # Check content length
            try:
                content_length = int(request.META.get('CONTENT_LENGTH', 0))
            except ValueError:
                content_length = 0
            
            if content_length > max_size:
                return JsonResponse({
                    'success': False,
                    'error': f'Request body too large. Maximum size: {max_size} bytes'
                }, status=413)
            
            if content_length == 0:
                return JsonResponse({
                    'success': False,
                    'error': 'Empty request body'
                }, status=400)
            
            # Parse JSON
            try:
                request.json_data = json.loads(request.body)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {str(e)}")
                return JsonResponse({
                    'success': False,
                    'error': f'Invalid JSON: {str(e)}'
                }, status=400)
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def rate_limit(requests_per_minute=60, block_duration=60):
    """
    Decorator to rate limit requests per user.
    
    Usage:
        @rate_limit(requests_per_minute=60)
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return view_func(request, *args, **kwargs)
            
            # Create cache key for this user and view
            cache_key = f"rate_limit:{request.user.id}:{view_func.__name__}"
            
            # Get current request count
            request_count = cache.get(cache_key, 0)
            
            # Check if rate limit exceeded
            if request_count >= requests_per_minute:
                logger.warning(
                    f"Rate limit exceeded for user {request.user.id} "
                    f"on {view_func.__name__}"
                )
                return JsonResponse({
                    'success': False,
                    'error': 'Rate limit exceeded. Please try again later.',
                    'retry_after': block_duration
                }, status=429)
            
            # Increment counter
            cache.set(cache_key, request_count + 1, 60)  # 60 seconds
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def validate_date_params(*param_names):
    """
    Decorator to validate date parameters in request.
    Converts string dates to datetime objects.
    
    Usage:
        @validate_date_params('start_date', 'end_date')
        def my_view(request):
            start = request.validated_dates['start_date']
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            validated_dates = {}
            
            for param_name in param_names:
                date_str = request.GET.get(param_name) or request.POST.get(param_name)
                
                if not date_str:
                    # Parameter is optional if not provided
                    validated_dates[param_name] = None
                    continue
                
                # Try to parse date in various formats
                date_formats = [
                    '%Y-%m-%d',
                    '%m/%d/%Y',
                    '%d/%m/%Y',
                    '%Y-%m-%d %H:%M:%S',
                ]
                
                parsed_date = None
                for date_format in date_formats:
                    try:
                        parsed_date = datetime.strptime(date_str, date_format)
                        break
                    except ValueError:
                        continue
                
                if parsed_date is None:
                    return JsonResponse({
                        'success': False,
                        'error': f'Invalid date format for {param_name}. Expected YYYY-MM-DD'
                    }, status=400)
                
                validated_dates[param_name] = parsed_date
            
            # Add validated dates to request
            request.validated_dates = validated_dates
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def log_action(action_name=None):
    """
    Decorator to log user actions.
    
    Usage:
        @log_action('created_reading_log')
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            action = action_name or view_func.__name__
            
            # Log the action
            if request.user.is_authenticated:
                logger.info(
                    f"User {request.user.id} ({request.user.user_type}) "
                    f"performed action: {action}"
                )
            
            # Execute view
            response = view_func(request, *args, **kwargs)
            
            # Log result
            if hasattr(response, 'status_code'):
                logger.info(f"Action {action} completed with status {response.status_code}")
            
            return response
        return wrapper
    return decorator


def require_ajax():
    """
    Decorator to ensure request is AJAX.
    
    Usage:
        @require_ajax
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'This endpoint only accepts AJAX requests'
                }, status=400)
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def cache_page_per_user(timeout=300):
    """
    Decorator to cache page results per user.
    
    Usage:
        @cache_page_per_user(timeout=300)
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return view_func(request, *args, **kwargs)
            
            # Create cache key
            cache_key = f"view_cache:{request.user.id}:{view_func.__name__}:{request.GET.urlencode()}"
            
            # Try to get from cache
            cached_response = cache.get(cache_key)
            if cached_response is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_response
            
            # Execute view
            response = view_func(request, *args, **kwargs)
            
            # Cache the response
            cache.set(cache_key, response, timeout)
            
            return response
        return wrapper
    return decorator


def measure_performance(threshold_ms=1000):
    """
    Decorator to measure and log view performance.
    
    Usage:
        @measure_performance(threshold_ms=1000)
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            import time
            start_time = time.time()
            
            # Execute view
            response = view_func(request, *args, **kwargs)
            
            # Measure execution time
            execution_time = (time.time() - start_time) * 1000  # Convert to ms
            
            # Log if over threshold
            if execution_time > threshold_ms:
                logger.warning(
                    f"Slow view: {view_func.__name__} took {execution_time:.2f}ms "
                    f"(threshold: {threshold_ms}ms)"
                )
            else:
                logger.debug(f"View {view_func.__name__} took {execution_time:.2f}ms")
            
            return response
        return wrapper
    return decorator

