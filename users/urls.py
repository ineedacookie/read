from django.urls import path, re_path

from . import views

urlpatterns = [
    re_path(r'^activate/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,40})/$', views.activate_account,
            name='activate'),
    re_path(r'^invited/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,40})/$', views.invited_account,
            name='invited'),
]

urlpatterns += [
    path('', views.home, name='home'),
    path('landing/', views.landing_page, name="landing_page"),
    path('register/', views.register_account, name="register"),
    path('users/', views.user_list, name="user_list"),
    path('invite_user/', views.invite_user, name="invite_user"),
    path('delete_user/', views.delete_users, name="delete_users"),
    path('student/<int:id>/', views.edit_record, name="edit_student"),
    path('classrooms/', views.render_classroom_list_view, name='classrooms'),
    path('api/classrooms/', views.classrooms_view, name='api_classrooms'),
    path('groups/', views.render_group_list_view, name='reading_groups'),
    path('api/groups/', views.groups_view, name='api_reading_groups'),
    path('api/students/', views.fetch_user_type, name='api_students'),
    path('api/teachers/', views.fetch_user_type, name='api_teachers'),
    # path('bad/dont/leave/', views.create_custom_users, name='create_custom'),
    # path('dashboard/', views.dashboard, name="dashboard"),
    # path('admin/company_settings/', views.company_settings, name="company_settings"),
    # path('admin/create_employee/', views.create_employee, name="create_employee"),
    # path('admin/send_confirmation_email/<int:employee_id>/', views.send_confirmation_email, name='send_confirmation_email'),
    # path('admin/employee/<int:employee_id>/', views.edit_employee, name="edit_employee"),
    # path('admin/employee/<int:employee_id>/delete/', views.delete_employee, name="delete_employee"),
    # path('admin/change_employee_password/<int:employee_id>/', views.admin_change_password, name='change_employee_password'),
    # path('account_settings/', views.edit_account_settings, name='account_settings'),
    # path('change_password/', views.change_password, name='change_password'),
    path('<str:user_type>/', views.user_list_page, name='user_list_page'),
]
