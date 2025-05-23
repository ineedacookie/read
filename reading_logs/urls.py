from django.urls import path

from . import views

urlpatterns = [
    path('get_logs/', views.get_logs_by_date_range, name='get_logs'),
    path('manage_log/', views.manage_log, name='manage_log'),
    path('api/get_logs_by_range_and_group', views.teacher_dashboard_logs, name='get_logs_by_range_and_group')
]
