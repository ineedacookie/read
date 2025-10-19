"""
Email helper functions to reduce duplication in sending emails.
Provides standardized email sending patterns and template rendering.
"""

from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)


def send_template_email(to_email, template_name, context, subject=None, from_email=None, fail_silently=False):
    """
    Send an email using a template with standardized context.
    
    Args:
        to_email: Recipient email address or list of addresses
        template_name: Template name (without .html extension)
        context: Dictionary of template context variables
        subject: Email subject (if not provided, will look for subject in context)
        from_email: Sender email (defaults to DEFAULT_FROM_EMAIL)
        fail_silently: Whether to fail silently on errors
        
    Returns:
        Boolean indicating if email was sent successfully
    """
    try:
        # Ensure to_email is a list
        if isinstance(to_email, str):
            to_email = [to_email]
        
        # Set default values
        if from_email is None:
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com')
        
        # Add common context variables
        context.update({
            'site_name': getattr(settings, 'SITE_NAME', 'Reading App'),
            'domain': getattr(settings, 'SITE_DOMAIN', 'localhost:8000'),
        })
        
        # Render email content
        html_content = render_to_string(f'email/{template_name}.html', context)
        text_content = strip_tags(html_content)
        
        # Get subject from context or parameter
        email_subject = subject or context.get('email_title', 'Notification')
        
        # Create email message
        msg = EmailMultiAlternatives(
            subject=email_subject,
            body=text_content,
            from_email=from_email,
            to=to_email
        )
        msg.attach_alternative(html_content, "text/html")
        
        # Send email
        result = msg.send()
        
        logger.info(f"Email sent successfully to {to_email} using template {template_name}")
        return result > 0
        
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        if not fail_silently:
            raise
        return False


def send_activation_email(user, request=None, domain=None):
    """
    Send account activation email.
    
    Args:
        user: User object
        request: HTTP request object (optional)
        domain: Domain name (optional, will be determined from request or settings)
        
    Returns:
        Boolean indicating if email was sent successfully
    """
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.encoding import force_bytes
    from django.utils.http import urlsafe_base64_encode
    
    # Generate activation token
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    
    # Determine domain
    if domain is None:
        if request:
            domain = get_current_site(request).domain
        else:
            domain = getattr(settings, 'SITE_DOMAIN', 'localhost:8000')
    
    context = {
        'user': user,
        'domain': domain,
        'uid': uid,
        'token': token,
        'email_title': 'Activate Your Account',
    }
    
    return send_template_email(
        to_email=user.email,
        template_name='acc_active_email',
        context=context,
        subject=f'Welcome to {getattr(settings, "SITE_NAME", "Reading App")} - Activate Your Account'
    )


def send_invitation_email(user, request=None, domain=None):
    """
    Send account invitation email.
    
    Args:
        user: User object
        request: HTTP request object (optional)
        domain: Domain name (optional)
        
    Returns:
        Boolean indicating if email was sent successfully
    """
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.encoding import force_bytes
    from django.utils.http import urlsafe_base64_encode
    
    # Generate invitation token
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    
    # Determine domain
    if domain is None:
        if request:
            domain = get_current_site(request).domain
        else:
            domain = getattr(settings, 'SITE_DOMAIN', 'localhost:8000')
    
    context = {
        'user': user,
        'domain': domain,
        'uid': uid,
        'token': token,
        'email_title': 'You\'re Invited!',
    }
    
    return send_template_email(
        to_email=user.email,
        template_name='acc_invite_email',
        context=context,
        subject=f'You\'re invited to join {getattr(settings, "SITE_NAME", "Reading App")}'
    )


def send_email_change_validation(user, request=None, domain=None):
    """
    Send email change validation email.
    
    Args:
        user: User object
        request: HTTP request object (optional)
        domain: Domain name (optional)
        
    Returns:
        Boolean indicating if email was sent successfully
    """
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.encoding import force_bytes
    from django.utils.http import urlsafe_base64_encode
    
    # Generate validation token
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    
    # Determine domain
    if domain is None:
        if request:
            domain = get_current_site(request).domain
        else:
            domain = getattr(settings, 'SITE_DOMAIN', 'localhost:8000')
    
    context = {
        'user': user,
        'domain': domain,
        'uid': uid,
        'token': token,
        'email_title': 'Validate Your New Email',
    }
    
    # Send to the new email address (assuming it's in change_email field)
    email_to_validate = getattr(user, 'change_email', user.email)
    
    return send_template_email(
        to_email=email_to_validate,
        template_name='change_validation',
        context=context,
        subject='Validate Your New Email Address'
    )


def send_feedback_notification(user, subject, content, admin_emails=None):
    """
    Send feedback notification to administrators.
    
    Args:
        user: User who submitted feedback
        subject: Feedback subject
        content: Feedback content
        admin_emails: List of admin emails (optional, will use ADMIN_EMAILS setting)
        
    Returns:
        Boolean indicating if email was sent successfully
    """
    from datetime import datetime
    
    if admin_emails is None:
        admin_emails = getattr(settings, 'ADMIN_EMAILS', ['admin@example.com'])
    
    context = {
        'user': user,
        'subject': subject,
        'content': content,
        'current_date': datetime.now(),
        'email_title': 'New Feedback Submitted',
    }
    
    return send_template_email(
        to_email=admin_emails,
        template_name='feedback_submitted',
        context=context,
        subject=f'New Feedback: {subject}',
        fail_silently=True  # Don't break the app if admin notification fails
    )


def send_password_reset_email(user, request=None, domain=None):
    """
    Send password reset email.
    
    Args:
        user: User object
        request: HTTP request object (optional)
        domain: Domain name (optional)
        
    Returns:
        Boolean indicating if email was sent successfully
    """
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.encoding import force_bytes
    from django.utils.http import urlsafe_base64_encode
    
    # Generate reset token
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    
    # Determine domain
    if domain is None:
        if request:
            domain = get_current_site(request).domain
        else:
            domain = getattr(settings, 'SITE_DOMAIN', 'localhost:8000')
    
    context = {
        'user': user,
        'domain': domain,
        'uid': uid,
        'token': token,
        'email_title': 'Reset Your Password',
    }
    
    return send_template_email(
        to_email=user.email,
        template_name='password_reset_email',
        context=context,
        subject='Reset Your Password'
    )


def send_bulk_email(users, template_name, context_generator, subject, from_email=None):
    """
    Send bulk emails to multiple users with personalized context.
    
    Args:
        users: Queryset or list of user objects
        template_name: Email template name
        context_generator: Function that takes a user and returns context dict
        subject: Email subject
        from_email: Sender email
        
    Returns:
        Dictionary with success/failure counts
    """
    results = {'success': 0, 'failed': 0, 'errors': []}
    
    for user in users:
        try:
            context = context_generator(user)
            success = send_template_email(
                to_email=user.email,
                template_name=template_name,
                context=context,
                subject=subject,
                from_email=from_email,
                fail_silently=True
            )
            
            if success:
                results['success'] += 1
            else:
                results['failed'] += 1
                
        except Exception as e:
            results['failed'] += 1
            results['errors'].append(f"{user.email}: {str(e)}")
    
    logger.info(f"Bulk email completed: {results['success']} sent, {results['failed']} failed")
    return results


def send_welcome_email(user, request=None):
    """
    Send welcome email to new users.
    
    Args:
        user: User object
        request: HTTP request object (optional)
        
    Returns:
        Boolean indicating if email was sent successfully
    """
    context = {
        'user': user,
        'email_title': 'Welcome to Reading App!',
    }
    
    return send_template_email(
        to_email=user.email,
        template_name='welcome_email',
        context=context,
        subject=f'Welcome to {getattr(settings, "SITE_NAME", "Reading App")}!'
    )


def send_reading_goal_reminder(user, goal, days_left):
    """
    Send reading goal reminder email.
    
    Args:
        user: User object
        goal: Goal object
        days_left: Number of days left to achieve goal
        
    Returns:
        Boolean indicating if email was sent successfully
    """
    context = {
        'user': user,
        'goal': goal,
        'days_left': days_left,
        'email_title': 'Reading Goal Reminder',
    }
    
    return send_template_email(
        to_email=user.email,
        template_name='goal_reminder_email',
        context=context,
        subject=f'Don\'t forget your reading goal - {days_left} days left!'
    )


# Email template validation helpers
def validate_email_template(template_name):
    """
    Validate that an email template exists and can be rendered.
    
    Args:
        template_name: Template name to validate
        
    Returns:
        Boolean indicating if template is valid
    """
    try:
        render_to_string(f'email/{template_name}.html', {})
        return True
    except Exception as e:
        logger.error(f"Email template validation failed for {template_name}: {str(e)}")
        return False


def get_email_context_defaults():
    """
    Get default context variables for all emails.
    
    Returns:
        Dictionary with default context variables
    """
    return {
        'site_name': getattr(settings, 'SITE_NAME', 'Reading App'),
        'domain': getattr(settings, 'SITE_DOMAIN', 'localhost:8000'),
        'support_email': getattr(settings, 'SUPPORT_EMAIL', 'support@example.com'),
        'company_name': getattr(settings, 'COMPANY_NAME', 'Reading App Inc.'),
    }


# Example usage and documentation
"""
BEFORE (repetitive email sending - 20+ lines per email type):

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

def send_activation_email(user, request):
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    domain = get_current_site(request).domain
    
    context = {
        'user': user,
        'domain': domain,
        'uid': uid,
        'token': token,
    }
    
    html_content = render_to_string('email/acc_active_email.html', context)
    text_content = strip_tags(html_content)
    
    send_mail(
        subject='Activate Your Account',
        message=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_content
    )

AFTER (using email helpers - 2 lines):

from read.utils.email_helpers import send_activation_email

send_activation_email(user, request)

REDUCTION: 90% fewer lines for email sending
BENEFITS:
- Consistent email formatting across all emails
- Standardized token generation and URL building
- Built-in error handling and logging
- Template validation and context defaults
- Bulk email capabilities for mass communications
"""

