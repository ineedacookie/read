"""
Reading Log API Endpoints
Handles CRUD operations for reading logs.
"""

from __future__ import annotations

import json
import logging

from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods

from read.utils import (
    error_response,
    reading_log_created_response,
    server_error_response,
    success_response,
)
from read.utils.decorators import (
    ajax_login_required,
    log_action,
    measure_performance,
    rate_limit,
    require_user_types,
)
from read.utils.response_helpers import permission_denied_response
from reading_logs.services.log_service import (
    LogAccessError,
    LogNotFoundError,
    LogService,
    LogServiceError,
    LogValidationError,
)

logger = logging.getLogger('reading_logs.api')


def _parse_payload(request):
    """
    Convert request body/query params into a dictionary.
    Supports JSON bodies and form submissions for backward compatibility.
    """
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body or '{}')
        except json.JSONDecodeError as exc:
            raise ValueError('Invalid JSON data') from exc
        if not isinstance(data, dict):
            raise ValueError('Invalid data format')
        return data

    if request.method == 'GET':
        return request.GET.dict()

    return request.POST.dict()


def _service_error_response(request, error: LogServiceError):
    """Translate service errors into HTTP responses."""
    if isinstance(error, LogValidationError):
        return error_response(str(error), status=400, user_id=request.user.id)
    if isinstance(error, LogAccessError):
        return permission_denied_response(
            request.user.id,
            action_attempted='reading log operation',
        )
    if isinstance(error, LogNotFoundError):
        return error_response(str(error), status=404, user_id=request.user.id)
    return server_error_response(user_id=request.user.id, error_details=str(error))


@login_required
@require_http_methods(["POST"])
@require_user_types('student')
@rate_limit(requests_per_minute=60)
@log_action('student_quick_log')
@measure_performance(threshold_ms=500)
def student_quick_log(request):
    """
    Quick log entry API for students.
    Uses centralized service for validation, persistence, and gamification.
    """
    service = LogService(request.user)

    try:
        payload = _parse_payload(request)
    except ValueError as exc:
        logger.warning(f"Invalid payload for student_quick_log by user {request.user.id}: {exc}")
        return error_response('Invalid data format', status=400, user_id=request.user.id)

    try:
        log = service.create_log(payload)
        return reading_log_created_response(log.id)
    except LogServiceError as exc:
        return _service_error_response(request, exc)
    except Exception as exc:  # pragma: no cover - safety net
        logger.error(f"Unexpected error in student_quick_log: {exc}", exc_info=True)
        return server_error_response(user_id=request.user.id, error_details=str(exc))


@login_required
@require_http_methods(["POST"])
@require_user_types('parent')
@rate_limit(requests_per_minute=60)
@log_action('parent_add_log')
def parent_add_log(request):
    """
    Allow parents to add reading logs for their children using the shared service layer.
    """
    service = LogService(request.user)

    try:
        payload = _parse_payload(request)
    except ValueError:
        return error_response('Invalid JSON data', status=400, user_id=request.user.id)

    child_id = payload.pop('child_id', None)
    if not child_id:
        return error_response('Child ID is required', status=400, user_id=request.user.id)

    try:
        log = service.create_log(payload, student_id=child_id)
        logger.info(
            "Reading log created by parent %s for child %s, log_id %s",
            request.user.id,
            child_id,
            log.id,
        )
        return success_response(
            'Reading log added successfully',
            data={'log_id': log.id},
        )
    except LogServiceError as exc:
        return _service_error_response(request, exc)
    except Exception as exc:  # pragma: no cover - safety net
        logger.error(f"Error in parent_add_log for user {request.user.id}: {exc}", exc_info=True)
        return server_error_response(user_id=request.user.id, error_details=str(exc))


@login_required
@require_http_methods(["POST"])
@require_user_types('parent')
@rate_limit(requests_per_minute=60)
@log_action('parent_edit_log')
def parent_edit_log(request):
    """
    Allow parents to edit reading logs for their children.
    """
    service = LogService(request.user)

    try:
        payload = _parse_payload(request)
    except ValueError:
        return error_response('Invalid JSON data', status=400, user_id=request.user.id)

    log_id = payload.get('log_id')
    child_id = payload.get('child_id')
    if not log_id or not child_id:
        return error_response('Log ID and Child ID are required', status=400, user_id=request.user.id)

    try:
        log = service.update_log(log_id, payload, student_id=child_id)
        logger.info(
            "Reading log updated by parent %s for child %s, log_id %s",
            request.user.id,
            child_id,
            log.id,
        )
        return success_response(
            'Reading log updated successfully',
            data={'log_id': log.id},
        )
    except LogServiceError as exc:
        return _service_error_response(request, exc)
    except Exception as exc:  # pragma: no cover - safety net
        logger.error(f"Error in parent_edit_log for user {request.user.id}: {exc}", exc_info=True)
        return server_error_response(user_id=request.user.id, error_details=str(exc))


@login_required
@require_http_methods(["POST"])
@require_user_types('parent')
@rate_limit(requests_per_minute=60)
@log_action('parent_delete_log')
def parent_delete_log(request):
    """
    Allow parents to delete reading logs for their children.
    """
    service = LogService(request.user)

    try:
        payload = _parse_payload(request)
    except ValueError:
        return error_response('Invalid JSON data', status=400, user_id=request.user.id)

    log_id = payload.get('log_id')
    child_id = payload.get('child_id')
    if not log_id or not child_id:
        return error_response('Log ID and Child ID are required', status=400, user_id=request.user.id)

    try:
        service.delete_log(log_id, student_id=child_id)
        logger.info(
            "Reading log deleted by parent %s for child %s, log_id %s",
            request.user.id,
            child_id,
            log_id,
        )
        return success_response('Reading log deleted successfully')
    except LogServiceError as exc:
        return _service_error_response(request, exc)
    except Exception as exc:  # pragma: no cover - safety net
        logger.error(f"Error in parent_delete_log for user {request.user.id}: {exc}", exc_info=True)
        return server_error_response(user_id=request.user.id, error_details=str(exc))


@ajax_login_required
@require_http_methods(["GET", "POST"])
def calendar_logs(request):
    """
    Combined endpoint for calendar log retrieval (GET) and creation (POST).
    """
    service = LogService(request.user)

    if request.method == 'GET':
        try:
            result = service.fetch_logs_for_form(
                request.GET.get('form_name'),
                request.GET.get('id'),
                request.GET.get('start'),
                request.GET.get('end'),
            )
            data = {
                'logs': result.logs,
                'num_students': result.num_students,
                'date_range': {
                    'start': result.start_date.isoformat(),
                    'end': result.end_date.isoformat(),
                },
            }
            return success_response('Logs retrieved successfully', data=data)
        except LogServiceError as exc:
            return _service_error_response(request, exc)
        except Exception as exc:  # pragma: no cover - safety net
            logger.error(f"Unexpected error in calendar_logs GET: {exc}", exc_info=True)
            return server_error_response(user_id=request.user.id, error_details=str(exc))

    try:
        payload = _parse_payload(request)
    except ValueError as exc:
        logger.warning(f"Invalid payload for calendar_logs POST by user {request.user.id}: {exc}")
        return error_response('Invalid data format', status=400, user_id=request.user.id)

    student_id = payload.get('student_id') or payload.get('student')

    try:
        log = service.create_log(payload, student_id=student_id)
        return success_response('Reading log created successfully', data={'log_id': log.id})
    except LogServiceError as exc:
        return _service_error_response(request, exc)
    except Exception as exc:  # pragma: no cover - safety net
        logger.error(f"Unexpected error in calendar_logs POST: {exc}", exc_info=True)
        return server_error_response(user_id=request.user.id, error_details=str(exc))


@ajax_login_required
@require_http_methods(["PATCH", "DELETE"])
def calendar_log_detail(request, log_id: int):
    """
    Endpoint for updating or deleting an individual calendar log entry.
    """
    service = LogService(request.user)

    try:
        payload = _parse_payload(request)
    except ValueError as exc:
        logger.warning(f"Invalid payload for calendar_log_detail by user {request.user.id}: {exc}")
        return error_response('Invalid data format', status=400, user_id=request.user.id)

    student_id = payload.get('student_id') or payload.get('student')

    try:
        if request.method == 'PATCH':
            log = service.update_log(log_id, payload, student_id=student_id)
            return success_response('Reading log updated successfully', data={'log_id': log.id})

        service.delete_log(log_id, student_id=student_id)
        return success_response('Reading log deleted successfully')
    except LogServiceError as exc:
        return _service_error_response(request, exc)
    except Exception as exc:  # pragma: no cover - safety net
        logger.error(f"Unexpected error in calendar_log_detail: {exc}", exc_info=True)
        return server_error_response(user_id=request.user.id, error_details=str(exc))


