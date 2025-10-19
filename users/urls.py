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
    path('classrooms/', views.render_classroom_list_view, name='classrooms'),
    path('api/classrooms/', views.classrooms_view, name='api_classrooms'),
    path('groups/', views.render_group_list_view, name='reading_groups'),
    path('api/groups/', views.groups_view, name='api_reading_groups'),
    path('api/groups-detailed/', views.groups_detailed_view, name='api_reading_groups_detailed'),
    path('api/reading-groups/<int:group_id>/', views.reading_group_detail_view, name='api_reading_group_detail'),
    path('api/reading-group-invite/', views.reading_group_invite_view, name='api_reading_group_invite'),
    path('api/classrooms_and_groups', views.list_classrooms_and_groups, name="api_classrooms_groups"),
    path('api/students/', views.fetch_user_type, name='api_students'),
    path('api/teachers/', views.fetch_user_type, name='api_teachers'),
    path('student/<int:id>/', views.edit_record, name="edit_student"),
    path('parent/<int:id>/', views.edit_record, name="edit_parent"),
    path('teacher/<int:id>/', views.edit_record, name="edit_teacher"),
    path('administrator/<int:id>/', views.edit_record, name="edit_administrator"),
    path('classrooms/<int:id>/', views.edit_record, name="edit_classrooms"),
    path('groups/<int:id>/', views.edit_record, name="edit_groups"),
    path('api/password_change/<int:id>', views.password_change_view, name='api_password_change'),
    path('my-students/', views.my_students_page, name='my_students'),
    path('my-classrooms/', views.my_classrooms_page, name='my_classrooms'),
    path('api/add-student-to-class/', views.add_student_to_class, name='add_student_to_class'),
    path('api/create-student/', views.create_student, name='create_student'),
    path('api/add-parent-to-student/', views.add_parent_to_student, name='add_parent_to_student'),
    path('api/remove-parent-from-student/', views.remove_parent_from_student, name='remove_parent_from_student'),
    path('api/remove-student-from-classes/', views.remove_student_from_classes, name='remove_student_from_classes'),
    path('api/classrooms/<int:classroom_id>/students/', views.get_classroom_students, name='get_classroom_students'),
    path('api/remove-student-from-classroom/', views.remove_student_from_classroom, name='remove_student_from_classroom'),
    
    # Admin student management
    path('admin/student-management/', views.admin_student_management_view, name='admin_student_management'),
    path('api/admin/students/', views.api_admin_students, name='api_admin_students'),
    path('api/admin/bulk-transfer/', views.api_bulk_student_transfer, name='api_bulk_student_transfer'),
    
    path('<str:user_type>/', views.user_list_page, name='user_list_page'),
]
