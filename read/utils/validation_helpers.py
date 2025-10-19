"""
Validation helper functions to reduce code duplication across the application.
Contains common validation patterns for dates, numeric fields, text fields, etc.
"""

from datetime import date, timedelta
from django.core.exceptions import ValidationError
from django.utils.html import escape
import logging

logger = logging.getLogger('reading_logs.security')


class ValidationError(Exception):
    """Custom validation error with standardized message format"""
    pass


def validate_date_range(start_date_str, end_date_str, max_days_back=1095, max_range_days=365):
    """
    Validate and parse date range parameters with security constraints.
    
    Args:
        start_date_str: String representation of start date (YYYY-MM-DD format)
        end_date_str: String representation of end date (YYYY-MM-DD format)
        max_days_back: Maximum days in the past allowed (default: 3 years)
        max_range_days: Maximum range between start and end dates (default: 1 year)
    
    Returns:
        tuple: (start_date, end_date) as date objects
    
    Raises:
        ValidationError: If dates are invalid or violate constraints
    """
    from datetime import datetime
    
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        raise ValidationError(f'Invalid start date format: {start_date_str}. Use YYYY-MM-DD')
    
    try:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        raise ValidationError(f'Invalid end date format: {end_date_str}. Use YYYY-MM-DD')
    
    # Security: Prevent unreasonable date ranges
    today = date.today()
    if start_date < today - timedelta(days=max_days_back):
        raise ValidationError(f'Start date too far in the past (max {max_days_back} days)')
    
    if end_date > today:
        raise ValidationError('End date cannot be in the future')
    
    if start_date > end_date:
        raise ValidationError('Start date must be before end date')
    
    if (end_date - start_date).days > max_range_days:
        raise ValidationError(f'Date range cannot exceed {max_range_days} days')
    
    return start_date, end_date


def validate_single_date(date_str, allow_future=False, max_days_back=365):
    """
    Validate and parse a single date with security constraints.
    
    Args:
        date_str: String representation of date (YYYY-MM-DD format)
        allow_future: Whether future dates are allowed (default: False)
        max_days_back: Maximum days in the past allowed (default: 1 year)
    
    Returns:
        date: Parsed date object
    
    Raises:
        ValidationError: If date is invalid or violates constraints
    """
    from datetime import datetime
    
    try:
        parsed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        raise ValidationError(f'Invalid date format: {date_str}. Use YYYY-MM-DD')
    
    today = date.today()
    
    if not allow_future and parsed_date > today:
        raise ValidationError('Cannot log future dates')
    
    if parsed_date < today - timedelta(days=max_days_back):
        raise ValidationError(f'Date too far in the past (max {max_days_back} days)')
    
    return parsed_date


def validate_positive_integer(value, field_name, min_value=1, max_value=None):
    """
    Validate a positive integer with optional bounds.
    
    Args:
        value: Value to validate (can be string or int)
        field_name: Name of the field for error messages
        min_value: Minimum allowed value (default: 1)
        max_value: Maximum allowed value (optional)
    
    Returns:
        int: Validated integer value
    
    Raises:
        ValidationError: If value is invalid or out of bounds
    """
    if value is None or value == '':
        return None
    
    try:
        int_value = int(value)
    except (ValueError, TypeError):
        raise ValidationError(f'{field_name} must be a valid number')
    
    if int_value < min_value:
        raise ValidationError(f'{field_name} must be at least {min_value}')
    
    if max_value is not None and int_value > max_value:
        raise ValidationError(f'{field_name} cannot exceed {max_value}')
    
    return int_value


def validate_rating(value):
    """
    Validate a rating value (0-5 scale).
    
    Args:
        value: Rating value to validate
    
    Returns:
        float: Validated rating value (rounded to 2 decimal places)
    
    Raises:
        ValidationError: If rating is invalid or out of range
    """
    if value is None or value == '':
        return None
    
    try:
        rating = float(value)
    except (ValueError, TypeError):
        raise ValidationError('Rating must be a valid number')
    
    if not 0 <= rating <= 5:
        raise ValidationError('Rating must be between 0 and 5')
    
    return round(rating, 2)


def validate_text_field(value, field_name, max_length, allow_empty=True, sanitize=True):
    """
    Validate and sanitize text field input.
    
    Args:
        value: Text value to validate
        field_name: Name of the field for error messages
        max_length: Maximum allowed length
        allow_empty: Whether empty values are allowed (default: True)
        sanitize: Whether to escape HTML for XSS prevention (default: True)
    
    Returns:
        str: Validated and sanitized text (or None if empty and allowed)
    
    Raises:
        ValidationError: If text is invalid or too long
    """
    if not value:
        if allow_empty:
            return None
        else:
            raise ValidationError(f'{field_name} is required')
    
    text = str(value).strip()
    
    if not text and not allow_empty:
        raise ValidationError(f'{field_name} is required')
    
    if len(text) > max_length:
        raise ValidationError(f'{field_name} too long (max {max_length} characters)')
    
    if sanitize:
        text = escape(text)  # Prevent XSS
    
    return text if text else None


def validate_pages_field(value):
    """Validate pages field with standard constraints."""
    return validate_positive_integer(value, 'Pages', min_value=0, max_value=10000)


def validate_minutes_field(value):
    """Validate minutes field with standard constraints (max 24 hours)."""
    return validate_positive_integer(value, 'Minutes', min_value=0, max_value=1440)


def validate_title_field(value):
    """Validate book title field with standard constraints."""
    return validate_text_field(value, 'Book title', max_length=255)


def validate_author_field(value):
    """Validate author field with standard constraints."""
    return validate_text_field(value, 'Author name', max_length=255)


def validate_comments_field(value):
    """Validate comments field with standard constraints."""
    return validate_text_field(value, 'Comments', max_length=2000)


def validate_request_size(request, max_size=10240):
    """
    Validate request size to prevent DoS attacks.
    
    Args:
        request: Django request object
        max_size: Maximum allowed size in bytes (default: 10KB)
    
    Raises:
        ValidationError: If request is too large
    """
    content_length = len(request.body) if hasattr(request, 'body') else 0
    if content_length > max_size:
        logger.warning(f"Oversized request from user {request.user.id}: {content_length} bytes")
        raise ValidationError('Request too large')


def validate_json_data(data):
    """
    Validate that data is a dictionary.
    
    Args:
        data: Data to validate
    
    Raises:
        ValidationError: If data format is invalid
    """
    if not isinstance(data, dict):
        raise ValidationError("Invalid data format")


def validate_id_parameter(value, field_name):
    """
    Validate an ID parameter (must be positive integer).
    
    Args:
        value: ID value to validate
        field_name: Name of the field for error messages
    
    Returns:
        int: Validated ID
    
    Raises:
        ValidationError: If ID is invalid
    """
    if not value:
        raise ValidationError(f'{field_name} is required')
    
    try:
        id_value = int(value)
        if id_value <= 0:
            raise ValueError()
        return id_value
    except (ValueError, TypeError):
        raise ValidationError(f'Invalid {field_name} format')


# Common validation combinations for reading logs
def validate_reading_log_data(data):
    """
    Validate all fields for a reading log entry.
    
    Args:
        data: Dictionary containing reading log data
    
    Returns:
        dict: Dictionary of validated data
    
    Raises:
        ValidationError: If any field validation fails
    """
    validated_data = {}
    
    # Validate pages
    if 'pages' in data and data['pages'] is not None:
        validated_data['pages'] = validate_pages_field(data['pages'])
    
    # Validate minutes
    if 'minutes' in data and data['minutes'] is not None:
        validated_data['minutes'] = validate_minutes_field(data['minutes'])
    
    # Validate rating
    if 'rating' in data and data['rating'] is not None:
        validated_data['rating'] = validate_rating(data['rating'])
    
    # Validate text fields
    if 'title' in data:
        validated_data['title'] = validate_title_field(data['title'])
    
    if 'author' in data:
        validated_data['author'] = validate_author_field(data['author'])
    
    if 'comments' in data:
        validated_data['comments'] = validate_comments_field(data['comments'])
    
    # Validate date
    if 'date' in data and data['date']:
        validated_data['date'] = validate_single_date(data['date'])
    
    return validated_data

