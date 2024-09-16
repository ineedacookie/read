from django.shortcuts import render
from .forms import LogForm
from .models import Log

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods

from users.models import CustomUser

from datetime import datetime


@login_required
def get_logs_by_date_range(request):
    try:
        start_date = datetime.fromisoformat(request.GET.get('start')).date()
        end_date = datetime.fromisoformat(request.GET.get('end')).date()
    except (ValueError, TypeError):
        return JsonResponse({'status': 'error', 'message': 'Invalid date format'})

    user_id = request.GET.get('user_id')

    # Validate user
    try:
        user = CustomUser.objects.get(id=user_id, user_type="student")
    except CustomUser.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'User not found'})

    # Fetch logs within the date range for the specified user
    logs = Log.objects.filter(student=user, date__range=(start_date, end_date))

    # Serialize logs
    logs_data = [{'id': log.id, 'date': log.date, 'title': log.title, 'author': log.author, 'pages': log.pages, 'minutes': log.minutes, 'rating': log.rating, 'comments': log.comments} for log in logs]

    if not logs_data:
        logs_data = []

    return JsonResponse({'status': 'success', 'logs': logs_data})

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

