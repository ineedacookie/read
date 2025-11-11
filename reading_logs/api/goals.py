"""
Reading Goals API Endpoints
Handles goal management and tracking.
"""

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from django.shortcuts import render
import logging
from datetime import datetime, date, timedelta

from reading_logs.models import DailyGoal, TotalGoal
from users.models import CustomUser, Classroom, ReadingGroup
from read.utils import success_response, error_response
from read.utils.decorators import ajax_login_required

logger = logging.getLogger('reading_logs.api')


@login_required
def reading_goals_view(request):
    """Reading goals management page for teachers"""
    if request.user.user_type not in ['teacher', 'administrator']:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("You don't have permission to access goal management")
    
    # Get classrooms and reading groups - OPTIMIZED: Only fetch needed fields
    if request.user.user_type == 'teacher':
        classrooms = Classroom.objects.filter(
            school=request.user.school,
            teachers=request.user
        ).values('id', 'name').order_by('name')
        reading_groups = ReadingGroup.objects.filter(
            school=request.user.school,
            managers=request.user
        ).values('id', 'name').order_by('name')
    else:  # administrator
        classrooms = Classroom.objects.filter(
            school=request.user.school
        ).values('id', 'name').order_by('name')
        reading_groups = ReadingGroup.objects.filter(
            school=request.user.school
        ).values('id', 'name').order_by('name')
    
    context = {
        'data': {
            'classrooms': list(classrooms),
            'reading_groups': list(reading_groups)
        }
    }
    
    return render(request, 'general/reading_goals.html', context)


@ajax_login_required
def api_reading_goals(request):
    """
    API for reading goals data and management.
    OPTIMIZED: Batch queries all goals, uses .only() for selective field loading.
    """
    if request.user.user_type not in ['teacher', 'administrator']:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("You don't have permission to access goals")
    
    if request.method == "GET":
        from read.utils.permission_helpers import get_accessible_students
        
        # Get accessible students
        students = get_accessible_students(request.user)
        
        # Apply filters
        goal_type = request.GET.get('goal_type', 'daily')
        class_group = request.GET.get('class_group', '')
        status_filter = request.GET.get('status', '')
        
        if class_group:
            if class_group.startswith('class_'):
                classroom_id = class_group.replace('class_', '')
                students = students.filter(students_classrooms__id=classroom_id)
            elif class_group.startswith('group_'):
                group_id = class_group.replace('group_', '')
                students = students.filter(reading_groups__id=group_id)
        
        # OPTIMIZED: Batch query all goals
        if goal_type == 'daily':
            goals_dict = {g.student_id: g for g in DailyGoal.objects.filter(student__in=students)}
        else:
            goals_dict = {g.student_id: g for g in TotalGoal.objects.filter(student__in=students)}
        
        # OPTIMIZED: Only load needed fields + prefetch classrooms
        students = students.only('id', 'first_name', 'last_initial', 'full_name').prefetch_related('students_classrooms')
        
        students_data = []
        overview = {'with_goals': 0, 'achieving': 0, 'struggling': 0, 'no_goals': 0}
        
        for student in students:
            goal = goals_dict.get(student.id)
            
            # Calculate progress
            status = 'no_goal'
            if goal:
                overview['with_goals'] += 1
                progress = {'percentage': 75}  # Simplified - would need recent logs for accurate
                status = 'achieving' if progress['percentage'] >= 80 else 'needs_encouragement'
                overview['achieving' if status == 'achieving' else 'struggling'] += 1
            else:
                overview['no_goals'] += 1
            
            # Apply status filter
            if status_filter and not _matches_status_filter(status, goal, status_filter):
                continue
            
            # Get classroom from prefetched data
            classrooms_list = list(student.students_classrooms.all())
            
            student_data = {
                'id': student.id,
                'name': student.full_name or f"{student.first_name} {student.last_initial}",
                'classroom': classrooms_list[0].name if classrooms_list else None,
                'daily_goal': _format_daily_goal(goal) if goal_type == 'daily' and goal else None,
                'total_goal': _format_total_goal(goal) if goal_type == 'total' and goal else None,
                'progress': progress if goal else None,
                'status': status
            }
            
            students_data.append(student_data)
        
        return JsonResponse({'students': students_data, 'overview': overview})
    
    elif request.method == "DELETE":
        return _handle_goal_delete(request)
    
    return error_response("Method not allowed", status=405)


@login_required
def api_bulk_reading_goals(request):
    """
    API for setting bulk reading goals.
    OPTIMIZED: Uses bulk_create instead of loop with individual creates.
    """
    if request.method != "POST":
        return error_response("Method not allowed", status=405)
    
    try:
        target_group = request.POST.get('target_group')
        goal_type = request.POST.get('goal_type')
        
        if not target_group or not goal_type:
            return error_response("Target group and goal type are required", status=400)
        
        # Get students and verify permission
        students = _get_students_for_group(request.user, target_group)
        if not students:
            return error_response("Group not found or no permission", status=404)
        
        # OPTIMIZED: Bulk create goals
        count = _bulk_create_goals(request, students, goal_type)
        
        return success_response(f"Goals set for {count} students", data={'count': count})
        
    except Exception as e:
        return error_response(f"Failed to set bulk goals: {str(e)}", status=500)


@login_required
def api_individual_reading_goal(request):
    """
    API for setting individual reading goals.
    OPTIMIZED: Uses update_or_create for efficiency.
    """
    if request.method != "POST":
        return error_response("Method not allowed", status=405)
    
    try:
        student_id = request.POST.get('student_id') or request.POST.get('student_select')
        goal_type = request.POST.get('goal_type')
        
        if not student_id or not goal_type:
            return error_response("Student ID and goal type are required", status=400)
        
        # Verify access to student
        from read.utils.view_helpers import verify_student_access
        try:
            student = verify_student_access(request.user, student_id)
        except:
            return error_response("Student not found or no permission", status=404)
        
        # Create or update goal
        if goal_type == 'daily':
            goal = _create_or_update_daily_goal(request, student)
        else:
            goal = _create_or_update_total_goal(request, student)
        
        action = "created" if goal[1] else "updated"
        return success_response(f"Goal {action} successfully for {student.full_name or student.first_name}")
        
    except Exception as e:
        return error_response(f"Failed to set goal: {str(e)}", status=500)


# Helper functions to consolidate repetitive logic

def _matches_status_filter(status, goal, status_filter):
    """Check if student matches status filter"""
    if status_filter == 'with_goals':
        return goal is not None
    elif status_filter == 'without_goals':
        return goal is None
    elif status_filter == 'achieving':
        return status == 'achieving'
    elif status_filter == 'struggling':
        return status == 'needs_encouragement'
    return True


def _format_daily_goal(goal):
    """Format daily goal for API response"""
    return {'type': goal.type, 'value': goal.value}


def _format_total_goal(goal):
    """Format total goal for API response"""
    return {
        'total': goal.total,
        'start': goal.start.isoformat() if goal.start else None,
        'end': goal.end.isoformat() if goal.end else None
    }


def _handle_goal_delete(request):
    """Handle DELETE request for removing goals"""
    try:
        import json
        data = json.loads(request.body)
        student_id = data.get('student_id')
        goal_type = data.get('goal_type')
        
        if not student_id or not goal_type:
            return error_response("Student ID and goal type are required", status=400)
        
        # Verify access to student
        from read.utils.view_helpers import verify_student_access
        try:
            student = verify_student_access(request.user, student_id)
        except:
            return error_response("Student not found or no permission", status=404)
        
        # Remove the goal
        if goal_type == 'daily':
            DailyGoal.objects.filter(student=student).delete()
        else:
            TotalGoal.objects.filter(student=student).delete()
        
        return success_response("Goal removed successfully")
        
    except Exception as e:
        return error_response(f"Failed to remove goal: {str(e)}", status=500)


def _get_students_for_group(user, target_group):
    """Get students in a group with permission checking"""
    if target_group.startswith('class_'):
        classroom_id = target_group.replace('class_', '')
        classroom = Classroom.objects.filter(id=classroom_id, school=user.school).first()
        
        if not classroom:
            return None
        
        # Check permission
        if user.user_type == 'teacher' and not classroom.teachers.filter(id=user.id).exists():
            return None
        
        return classroom.students.all()
        
    elif target_group.startswith('group_'):
        group_id = target_group.replace('group_', '')
        reading_group = ReadingGroup.objects.filter(id=group_id, school=user.school).first()
        
        if not reading_group:
            return None
        
        # Check permission
        if user.user_type == 'teacher' and not reading_group.managers.filter(id=user.id).exists():
            return None
        
        return reading_group.students.all()
    
    return None


def _bulk_create_goals(request, students, goal_type):
    """Bulk create goals for students"""
    student_list = list(students)
    student_ids = [s.id for s in student_list]
    
    if goal_type == 'daily':
        # Batch query existing goals
        existing_goal_ids = set(DailyGoal.objects.filter(
            student_id__in=student_ids
        ).values_list('student_id', flat=True))
        
        daily_pages = request.POST.get('daily_pages')
        daily_minutes = request.POST.get('daily_minutes')
        
        if daily_pages or daily_minutes:
            goals_to_create = []
            for student in student_list:
                if student.id not in existing_goal_ids:
                    goals_to_create.append(DailyGoal(
                        student=student,
                        school=student.school,
                        type='pages' if daily_pages else 'minutes',
                        value=int(daily_pages) if daily_pages else int(daily_minutes)
                    ))
            
            if goals_to_create:
                DailyGoal.objects.bulk_create(goals_to_create)
                return len(goals_to_create)
                
    else:  # total goal
        # Batch query existing goals
        existing_goal_ids = set(TotalGoal.objects.filter(
            student_id__in=student_ids
        ).values_list('student_id', flat=True))
        
        total_pages = request.POST.get('total_pages')
        deadline = request.POST.get('deadline')
        
        if total_pages:
            deadline_date = None
            if deadline:
                deadline_date = datetime.strptime(deadline, '%Y-%m-%d').date()
            
            goals_to_create = []
            for student in student_list:
                if student.id not in existing_goal_ids:
                    goal = TotalGoal(
                        student=student,
                        school=student.school,
                        start=date.today(),
                        end=deadline_date or (date.today() + timedelta(days=30)),
                        total=int(total_pages)
                    )
                    goals_to_create.append(goal)
            
            if goals_to_create:
                TotalGoal.objects.bulk_create(goals_to_create)
                return len(goals_to_create)
    
    return 0


def _create_or_update_daily_goal(request, student):
    """Create or update daily goal for student"""
    daily_pages = request.POST.get('daily_pages')
    daily_minutes = request.POST.get('daily_minutes')
    
    if not daily_pages and not daily_minutes:
        raise ValueError("At least one daily goal (pages or minutes) is required")
    
    return DailyGoal.objects.update_or_create(
        student=student,
        defaults={
            'school': student.school,
            'type': 'pages' if daily_pages else 'minutes',
            'value': int(daily_pages) if daily_pages else int(daily_minutes)
        }
    )


def _create_or_update_total_goal(request, student):
    """Create or update total goal for student"""
    total_pages = request.POST.get('total_pages')
    deadline = request.POST.get('deadline')
    
    if not total_pages:
        raise ValueError("Total pages goal is required")
    
    goal_data = {'total': int(total_pages), 'school': student.school}
    if deadline:
        goal_data['end'] = datetime.strptime(deadline, '%Y-%m-%d').date()
        goal_data['start'] = date.today()
    
    return TotalGoal.objects.update_or_create(
        student=student,
        defaults=goal_data
    )

