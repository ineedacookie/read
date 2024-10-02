from django.shortcuts import render
from .forms import LogForm
from .models import Log

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods

from users.models import CustomUser, Classroom, ReadingGroup

from datetime import datetime


@login_required
def get_logs_by_date_range(request):
    try:
        start_date = datetime.fromisoformat(request.GET.get('start')).date()
        end_date = datetime.fromisoformat(request.GET.get('end')).date()
    except (ValueError, TypeError):
        return JsonResponse({'status': 'error', 'message': 'Invalid date format'})

    obj_id = request.GET.get('id')
    form_name = request.GET.get('form_name')

    num_students = 0

    if form_name == 'Student':
        # Validate user
        try:
            user = CustomUser.objects.get(id=obj_id, user_type="student", school=request.user.school)
        except CustomUser.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'User not found'})
    
        # Fetch logs within the date range for the specified user
        logs = Log.objects.filter(school=request.user.school, student=user, date__range=(start_date, end_date))

        num_students = 1
        # Serialize logs
        logs_data = [{'id': log.id, 'date': log.date, 'title': log.title, 'author': log.author, 'pages': log.pages, 'minutes': log.minutes, 'rating': log.rating, 'comments': log.comments} for log in logs]
    elif form_name in ['Classrooms', 'Groups']:
        if form_name == 'Classrooms':
            try:
                temp_obj = Classroom.objects.get(school=request.user.school, id=obj_id)
            except Classroom.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Classroom not found'})
        else:
            try:
                temp_obj = ReadingGroup.objects.get(school=request.user.school, id=obj_id)
            except ReadingGroup.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Reading Group not found'})
        logs = Log.objects.filter(school=request.user.school, student__in=temp_obj.students.all(),
                                  date__range=(start_date, end_date)).values('id', 'date', 'pages', 'minutes')
        num_students = temp_obj.students.count()

        logs_data = [{'id': log['id'], 'date': log['date'], 'pages': log['pages'], 'minutes': log['minutes']} for log in logs]


    if not logs_data:
        logs_data = []

    return JsonResponse({'status': 'success', 'logs': logs_data, 'num_students': num_students})


@login_required
def teacher_dashboard_logs(request):
    if request.method == 'GET':
        date_range = request.GET.get('date_range')
        group = request.GET.get('group')
        group_type, group_id = group.split('_')
        if group_type == 'class':
            group_obj = Classroom.objects.get(id=group_id, school=request.user.school)
        elif group_type == 'group':
            group_obj = ReadingGroup.objects.get(id=group_id, school=request.user.school)
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid group type'})

        if date_range:
            try:
                if ' to ' in date_range:
                    start_date_str, end_date_str = date_range.split(' to ')
                    start_date = datetime.strptime(start_date_str, '%b %d, %Y').date()
                    end_date = datetime.strptime(end_date_str, '%b %d, %Y').date()
                else:
                    start_date = datetime.strptime(date_range, '%b %d, %Y').date()
                    end_date = start_date
            except ValueError:
                return JsonResponse({'status': 'error', 'message': 'Invalid date format'})
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid date range'})

        students = group_obj.students.all()

        log_dict = {}
        for student in students:
            log_dict[student.id] = {'pages': 0, 'minutes': 0, 'name': student.full_name}

        logs = Log.objects.filter(school=request.user.school, date__range=(start_date, end_date),
                                  student__in=group_obj.students.all()).values('student__id', 'pages', 'minutes')

        total_pages = total_minutes = 0
        for log in logs:
            log_dict[log['student__id']]['pages'] += log['pages']
            log_dict[log['student__id']]['minutes'] += log['minutes']
            total_pages += log['pages']
            total_minutes += log['minutes']

        return JsonResponse({'status': 'success', 'logs': list(log_dict.values()), 'pages': total_pages, 'minutes': total_minutes})
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'})


@login_required
def manage_log(request):
    if request.method == 'POST':
        delete = request.POST.get('del', False)
        if delete:
            try:
                log_id = request.POST.get('id')
                log = Log.objects.get(id=log_id)
                log.delete()
                return JsonResponse({'status': 'success', 'message': 'Log deleted'})
            except Log.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Log not found'})
        else:
            # Create a new log entry
            form = LogForm(request.POST)
            if form.is_valid():
                log = form.save()
                return JsonResponse({'status': 'success', 'message': 'Log created', 'log_id': log.id})
            else:
                return JsonResponse({'status': 'error', 'errors': form.errors})

    elif request.method == 'PUT':
        # Update an existing log entry
        try:
            log_id = request.PUT.get('id')
            log = Log.objects.get(id=log_id)
            form = LogForm(request.PUT, instance=log)
            if form.is_valid():
                log = form.save()
                return JsonResponse({'status': 'success', 'message': 'Log updated', 'log_id': log.id})
            else:
                return JsonResponse({'status': 'error', 'errors': form.errors})
        except Log.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Log not found'})

