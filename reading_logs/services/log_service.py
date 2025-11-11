"""
Centralized business logic for reading log CRUD and retrieval.
Reduces duplication across legacy views, API endpoints, and frontend AJAX hooks.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date as date_cls
from typing import Dict, List, Optional, Tuple

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import QuerySet

from read.utils import (
    ValidationError as UtilsValidationError,
    log_successful_action,
    validate_date_range,
    validate_reading_log_data,
)
from read.utils.permission_helpers import (
    log_security_event,
    verify_parent_child_relationship,
    verify_school_access,
    verify_teacher_student_access,
)
from read.utils.serializers import LogSerializer
from read.utils.validation_helpers import validate_id_parameter
from reading_logs.models import Log
from users.models import Classroom, CustomUser, ReadingGroup


class LogServiceError(Exception):
    """Base exception for log service errors."""


class LogValidationError(LogServiceError):
    """Raised when incoming data fails validation."""


class LogAccessError(LogServiceError):
    """Raised when the acting user lacks access to the requested resource."""


class LogNotFoundError(LogServiceError):
    """Raised when a requested log or related resource does not exist."""


@dataclass(frozen=True)
class LogFetchResult:
    """Structured response for log list queries."""

    logs: List[Dict]
    num_students: int
    start_date: date_cls
    end_date: date_cls


class LogService:
    """
    Encapsulates reading log CRUD operations and access control.

    Typical usage:

        service = LogService(request.user)
        result = service.fetch_logs_for_form('Student', student_id, start, end)
        log = service.create_log(payload, student_id)
    """

    STUDENT_LOG_FIELDS = ['id', 'date', 'title', 'author', 'pages', 'minutes', 'rating', 'comments']
    GROUP_LOG_FIELDS = STUDENT_LOG_FIELDS + ['student_id', 'student_name']

    def __init__(self, acting_user: CustomUser):
        self.user = acting_user

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch_logs_for_form(
        self,
        form_name: str,
        object_id: Optional[str],
        start_date_str: Optional[str],
        end_date_str: Optional[str],
    ) -> LogFetchResult:
        """Fetch logs for student, classroom, or group within a date range."""
        if not form_name or not object_id:
            raise LogValidationError('Missing required parameters: id and form_name')
        if not start_date_str or not end_date_str:
            raise LogValidationError('Missing required parameters: start and end')

        start_date, end_date = self._parse_date_range(start_date_str, end_date_str)
        normalized = form_name.strip().lower()

        if normalized == 'student':
            student_id = validate_id_parameter(object_id, 'Student ID')
            student = self._get_student(student_id)
            logs = (
                Log.objects.filter(
                    student=student,
                    school=self.user.school,
                    date__range=(start_date, end_date),
                )
                .select_related('student')
                .order_by('date', 'id')
            )
            serialized = LogSerializer.serialize_many(logs, fields=self.STUDENT_LOG_FIELDS)
            return LogFetchResult(serialized, num_students=1, start_date=start_date, end_date=end_date)

        if normalized in {'classrooms', 'classroom'}:
            classroom_id = validate_id_parameter(object_id, 'Classroom ID')
            classroom = self._get_classroom(classroom_id)
            students = classroom.students.filter(user_type='student').values_list('id', flat=True)
            logs = (
                Log.objects.filter(
                    student_id__in=list(students),
                    school=self.user.school,
                    date__range=(start_date, end_date),
                )
                .select_related('student')
                .order_by('date', 'id')
            )
            serialized = LogSerializer.serialize_many(logs, fields=self.GROUP_LOG_FIELDS)
            return LogFetchResult(
                serialized,
                num_students=classroom.students.count(),
                start_date=start_date,
                end_date=end_date,
            )

        if normalized in {'groups', 'group'}:
            group_id = validate_id_parameter(object_id, 'Group ID')
            group = self._get_reading_group(group_id)
            students = group.students.filter(user_type='student').values_list('id', flat=True)
            logs = (
                Log.objects.filter(
                    student_id__in=list(students),
                    school=self.user.school,
                    date__range=(start_date, end_date),
                )
                .select_related('student')
                .order_by('date', 'id')
            )
            serialized = LogSerializer.serialize_many(logs, fields=self.GROUP_LOG_FIELDS)
            return LogFetchResult(
                serialized,
                num_students=group.students.count(),
                start_date=start_date,
                end_date=end_date,
            )

        raise LogValidationError('Invalid form_name. Must be Student, Classrooms, or Groups')

    @transaction.atomic
    def create_log(self, data: Dict, student_id: Optional[str] = None) -> Log:
        """Create a reading log for the given student."""
        student = self._resolve_student_for_write(student_id)
        validated = self._validate_log_payload(data)

        log = Log.objects.create(
            school=student.school,
            student=student,
            date=validated.get('date', date_cls.today()),
            title=self._finalize_text_field(validated, data, 'title', default=''),
            author=self._finalize_text_field(validated, data, 'author', default=''),
            pages=self._finalize_numeric_field(validated, data, 'pages', default=0),
            minutes=self._finalize_numeric_field(validated, data, 'minutes', default=0),
            rating=validated.get('rating'),
            comments=self._finalize_text_field(validated, data, 'comments'),
        )

        self._process_gamification(log)
        log_successful_action(self.user.id, 'created reading log', 'Log', log.id)
        return log

    @transaction.atomic
    def update_log(
        self,
        log_id: str,
        data: Dict,
        student_id: Optional[str] = None,
    ) -> Log:
        """Update an existing reading log."""
        log = self._get_log_for_update(log_id, student_id)
        validated = self._validate_log_payload(data)

        fields_to_update: List[str] = []

        if 'date' in validated:
            log.date = validated['date']
            fields_to_update.append('date')

        for field in ('title', 'author', 'comments'):
            if field in data:
                setattr(log, field, self._finalize_text_field(validated, data, field))
                fields_to_update.append(field)

        for field in ('pages', 'minutes', 'rating'):
            if field in data:
                value = self._finalize_numeric_field(validated, data, field)
                setattr(log, field, value)
                fields_to_update.append(field)

        if fields_to_update:
            log.save(update_fields=fields_to_update + ['updated_date'])
            log_successful_action(self.user.id, 'updated reading log', 'Log', log.id)

        return log

    @transaction.atomic
    def delete_log(self, log_id: str, student_id: Optional[str] = None) -> None:
        """Delete a reading log if the user has access."""
        log = self._get_log_for_update(log_id, student_id)
        log.delete()
        log_successful_action(self.user.id, 'deleted reading log', 'Log', log_id)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _parse_date_range(self, start: str, end: str) -> Tuple[date_cls, date_cls]:
        try:
            return validate_date_range(start, end)
        except UtilsValidationError as exc:
            raise LogValidationError(str(exc)) from exc

    def _get_student(self, student_id: int) -> CustomUser:
        try:
            student = CustomUser.objects.select_related('school').get(
                id=student_id,
                user_type='student',
                school=self.user.school,
            )
        except CustomUser.DoesNotExist as exc:
            raise LogNotFoundError('Student not found') from exc

        self._ensure_student_access(student)
        return student

    def _get_classroom(self, classroom_id: int) -> Classroom:
        try:
            classroom = Classroom.objects.prefetch_related('students', 'teachers').get(
                id=classroom_id,
                school=self.user.school,
            )
        except Classroom.DoesNotExist as exc:
            raise LogNotFoundError('Classroom not found') from exc

        self._ensure_classroom_access(classroom)
        return classroom

    def _get_reading_group(self, group_id: int) -> ReadingGroup:
        try:
            group = ReadingGroup.objects.prefetch_related('students', 'managers').get(
                id=group_id,
                school=self.user.school,
            )
        except ReadingGroup.DoesNotExist as exc:
            raise LogNotFoundError('Reading Group not found') from exc

        self._ensure_group_access(group)
        return group

    def _resolve_student_for_write(self, student_id: Optional[str]) -> CustomUser:
        if student_id:
            validated_id = validate_id_parameter(student_id, 'student_id')
            return self._get_student(validated_id)

        if self.user.user_type == 'student':
            return self.user

        raise LogValidationError('student_id is required for this action')

    def _ensure_student_access(self, student: CustomUser) -> None:
        try:
            if self.user.user_type == 'administrator':
                verify_school_access(self.user, student)
            elif self.user.user_type == 'teacher':
                verify_teacher_student_access(self.user, student)
            elif self.user.user_type == 'parent':
                verify_parent_child_relationship(self.user, student)
            elif self.user.user_type == 'student':
                if self.user.id != student.id:
                    raise PermissionDenied('Access denied - can only access your own logs')
            else:
                raise PermissionDenied('Access denied')
        except PermissionDenied as exc:
            raise LogAccessError(str(exc)) from exc

    def _ensure_classroom_access(self, classroom: Classroom) -> None:
        try:
            verify_school_access(self.user, classroom)
            if self.user.user_type == 'administrator':
                return
            if self.user.user_type == 'teacher':
                if classroom.teachers.filter(id=self.user.id).exists():
                    return
                raise PermissionDenied('Access denied - classroom not assigned to you')
            raise PermissionDenied('Access denied - classroom data restricted')
        except PermissionDenied as exc:
            raise LogAccessError(str(exc)) from exc

    def _ensure_group_access(self, group: ReadingGroup) -> None:
        try:
            verify_school_access(self.user, group)
            if self.user.user_type == 'administrator':
                return
            if self.user.user_type == 'teacher':
                if group.managers.filter(id=self.user.id).exists():
                    return
                raise PermissionDenied('Access denied - reading group not assigned to you')
            raise PermissionDenied('Access denied - reading group data restricted')
        except PermissionDenied as exc:
            raise LogAccessError(str(exc)) from exc

    def _validate_log_payload(self, data: Dict) -> Dict:
        try:
            return validate_reading_log_data(data or {})
        except UtilsValidationError as exc:
            raise LogValidationError(str(exc)) from exc

    def _get_log_for_update(self, log_id: str, student_id: Optional[str]) -> Log:
        validated_id = validate_id_parameter(log_id, 'log_id')
        try:
            log = Log.objects.select_related('student', 'school').get(
                id=validated_id,
                school=self.user.school,
            )
        except Log.DoesNotExist as exc:
            raise LogNotFoundError('Reading log not found') from exc

        if student_id:
            validated_student_id = validate_id_parameter(student_id, 'student_id')
            if log.student_id != validated_student_id:
                raise LogAccessError('Reading log does not belong to the specified student')

        self._ensure_student_access(log.student)
        return log

    def _finalize_text_field(
        self,
        validated: Dict,
        original: Dict,
        field: str,
        default: Optional[str] = None,
    ) -> Optional[str]:
        if field in validated:
            value = validated[field]
            return default if value is None and field in original else value
        if field in original:
            return default
        return None

    def _finalize_numeric_field(
        self,
        validated: Dict,
        original: Dict,
        field: str,
        default: Optional[float] = None,
    ) -> Optional[float]:
        if field in validated:
            return validated[field]
        if field in original:
            return default
        return None

    def _process_gamification(self, log: Log) -> None:
        try:
            from reading_logs.gamification import GamificationEngine

            GamificationEngine().process_reading_log(log)
        except Exception as exc:  # pragma: no cover - best effort logging
            log_security_event(
                self.user.id,
                'gamification_processing_failed',
                details=f'log_id={log.id} error={exc}',
            )

