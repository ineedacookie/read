import json
import logging

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404, HttpResponseBadRequest, JsonResponse
from django.shortcuts import render, redirect
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.http import require_POST

from read.utils import (
    success_response, 
    error_response, 
    validation_error_response,
    permission_denied_response
)

from .forms import OverriddenPasswordChangeForm, ClassroomForm, OverriddenAdminPasswordChangeForm, RegisterUserForm, \
    InviteCombinedForm, InviteStudentsForm, InviteParentForm, InviteUsersForm, ReadingGroupForm, CustomStudentForm, CustomTeacherForm, \
    CustomAdministratorForm, CustomParentForm, CustomClassroomForm, CustomReadingGroupForm
from reading_logs.forms import LogForm
from .models import CustomUser, School, Classroom, ReadingGroup
from .tokens import account_activation_token
from .utils import get_selectable_employees, send_email_with_link

logger = logging.getLogger("django.request")


def landing_page(request):
    page = 'general/landing.html'
    page_arguments = {}
    return render(request, page, page_arguments)


# Note: Development utility functions have been removed for security.
# Use Django management commands for data seeding instead.


@login_required
def home(request, **kwargs):
    """Main page that is the root of the website"""
    """Checks whether the user is part of the staff or a customer"""
    if request.user.is_staff:
        return redirect('/io_admin')
    
    page_arguments = {}
    
    if request.user.user_type == 'teacher':
        page = 'general/teacher_dash.html'
        school = request.user.school
        classrooms = Classroom.objects.filter(school=school, teachers=request.user).order_by('name')
        reading_groups = ReadingGroup.objects.filter(school=school, managers=request.user).order_by('name')

        # Get URL parameters for group and date range
        selected_group = request.GET.get('group')
        date_range = request.GET.get('date_range')
        
        # Default to first classroom if none selected
        if not selected_group and classrooms.exists():
            selected_group = f"class_{classrooms.first().id}"
        elif not selected_group and reading_groups.exists():
            selected_group = f"group_{reading_groups.first().id}"
        
        # Default to current week if no date range specified
        if not date_range:
            from datetime import datetime, timedelta
            today = datetime.now()
            start_of_week = today - timedelta(days=today.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            date_range = f"{start_of_week.strftime('%b %d, %Y')} to {end_of_week.strftime('%b %d, %Y')}"
        
        # Calculate previous and next week ranges for navigation
        try:
            from datetime import datetime, timedelta
            start_date_str, end_date_str = date_range.split(' to ')
            start_date = datetime.strptime(start_date_str, '%b %d, %Y').date()
            
            prev_start = start_date - timedelta(days=7)
            prev_end = prev_start + timedelta(days=6)
            prev_week_range = f"{prev_start.strftime('%b %d, %Y')} to {prev_end.strftime('%b %d, %Y')}"
            
            next_start = start_date + timedelta(days=7)
            next_end = next_start + timedelta(days=6)
            next_week_range = f"{next_start.strftime('%b %d, %Y')} to {next_end.strftime('%b %d, %Y')}"
        except:
            prev_week_range = date_range
            next_week_range = date_range
        
        # Load dashboard data server-side
        dashboard_data = None
        if selected_group:
            from reading_logs.views import teacher_dashboard_logs
            from django.test import RequestFactory
            
            factory = RequestFactory()
            api_request = factory.get('/api/get_logs_by_range_and_group', {
                'date_range': date_range,
                'group': selected_group
            })
            api_request.user = request.user
            
            try:
                response = teacher_dashboard_logs(api_request)
                if response.status_code == 200:
                    import json
                    dashboard_data = json.loads(response.content)
            except:
                dashboard_data = None
        
        # Process classrooms and groups with selected status
        classrooms_data = []
        for classroom in classrooms:
            classrooms_data.append({
                'id': classroom.id,
                'name': classroom.name,
                'value': f'class_{classroom.id}',
                'selected': selected_group == f'class_{classroom.id}'
            })
        
        groups_data = []
        for group in reading_groups:
            groups_data.append({
                'id': group.id,
                'name': group.name,
                'value': f'group_{group.id}',
                'selected': selected_group == f'group_{group.id}'
            })
        
        data = {
            "classrooms": classrooms_data,
            "reading_groups": groups_data,
            "selected_group": selected_group,
            "date_range": date_range,
            "prev_week_range": prev_week_range,
            "next_week_range": next_week_range,
            "dashboard_data": dashboard_data
        }
        page_arguments['data'] = data
    elif request.user.user_type == 'student':
        page = 'general/student_dash.html'
    elif request.user.user_type == 'parent':
        page = 'general/parent_dash.html'
    elif request.user.user_type == 'administrator':
        page = 'general/admin_dash.html'
    else:
        # Fallback for any undefined user types
        page = 'general/home.html'
    
    return render(request, page, page_arguments)


@login_required
def user_list_page(request, **kwargs):
    """Checks whether the user is part of the staff or a customer"""
    if request.user.is_staff:
        return redirect('/io_admin')
    else:
        page = 'general/user_list.html'
        user_type = kwargs.get('user_type', 'student')
        if user_type not in ['student', 'teacher', 'parent', 'administrator']:
            # Forward the user to a 404 page
            raise Http404("Page not found")
        
        # Security: Check if user has permission to access this dashboard type
        user_dashboard_type = request.user.user_type
        
        # Define allowed access patterns
        if user_dashboard_type == 'administrator':
            # Administrators can access all dashboards
            pass
        elif user_dashboard_type == 'teacher':
            # Teachers can access their own dashboard and student management
            if user_type not in ['teacher', 'student']:
                from django.core.exceptions import PermissionDenied
                raise PermissionDenied("You don't have permission to access this dashboard")
        elif user_dashboard_type == 'student':
            # Students can only access their own dashboard
            if user_type != 'student':
                from django.core.exceptions import PermissionDenied
                raise PermissionDenied("You don't have permission to access this dashboard")
        elif user_dashboard_type == 'parent':
            # Parents can access their own dashboard and student reading log interface
            if user_type not in ['parent', 'student']:
                from django.core.exceptions import PermissionDenied
                raise PermissionDenied("You don't have permission to access this dashboard")
        if user_type == 'student':
            invite_form = InviteStudentsForm()
        elif user_type == 'parent':
            invite_form = InviteParentForm(logged_in_user=request.user)
        else:
            invite_form = InviteUsersForm()
        page_arguments = {'user_type': user_type, 'invite_form': invite_form}
        return render(request, page, page_arguments)  # fill the {} with arguments


@login_required
def user_list(request):
    user_type = request.GET.get('user_type', 'student')
    queryset = CustomUser.objects.filter(school=request.user.school, user_type=user_type)

    # Search functionality
    search_query = request.GET.get('search', '')

    if search_query:
        queryset = queryset.filter(Q(email__icontains=search_query) | Q(first_name__icontains=search_query) | Q(
            last_name__icontains=search_query))

    # Sorting functionality
    sort_field = request.GET.get('sort_field', 'id')
    sort_order = request.GET.get('sort_order', 'asc')
    if sort_order == 'desc':
        sort_field = f'-{sort_field}'
    queryset = queryset.order_by(sort_field)

    # Pagination
    paginator = Paginator(queryset, 10)  # Show 10 users per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # If AJAX request, return JSON response
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        users_list = list(page_obj.object_list.values('id', 'first_name', 'last_name', 'email'))
        return JsonResponse({
            'users': users_list,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'page_number': page_obj.number,
            'num_pages': page_obj.paginator.num_pages,
        })
    if user_type == 'student':
        invite_form = InviteStudentsForm()
    elif user_type == 'parent':
        invite_form = InviteParentForm(logged_in_user=request.user)
    else:
        invite_form = InviteUsersForm()

    return render(request, 'general/user_list.html', {'page_obj': page_obj, 'page_type': user_type, 'invite_form': invite_form})

def register_account(request):
    """This view allows a new user to register for an account not linked to any company."""
    page = 'registration/register.html'
    page_arguments = {}
    form = None
    if request.method == 'POST':
        form = RegisterUserForm(request.POST)
        if form.is_valid():
            register_user = form.save(commit=False)
            register_user.is_active = False
            register_user.save()

            send_email_with_link(register_user, request)

            page = 'registration/account_created.html'
            page_arguments = {}
        else:
            page_arguments['form'] = form

    if not form:
        page_arguments['form'] = RegisterUserForm()
    return render(request, page, page_arguments)


def activate_account(request, uidb64, token):
    """This page is for validating an email and getting the initial password set for a user."""
    page = 'registration/activation_link.html'
    page_arguments = {}
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None
    if user is not None and account_activation_token.check_token(user, token):
        page = 'registration/set_initial_password.html'
        if request.POST:
            form = OverriddenAdminPasswordChangeForm(user, request.POST)
            if form.is_valid():
                form.save()
                user.is_active = True
                if user.change_email:
                    user.email = user.change_email
                    user.change_email = None
                user.save()
                login(request, user)
                return redirect('home')
        else:
            form = OverriddenAdminPasswordChangeForm(user)
        page_arguments['form'] = form
    return render(request, page, page_arguments)


@login_required
def invite_user(request):
    """
    Attached to the add button. It will receive either a InviteStudentsform or InviteUsersForm.
    :param request: 
    :return: 
    """
    if request.method == 'POST':
        post_dict = request.POST.copy()
        user_type = post_dict.get('user_type')
        post_dict['school'] = request.user.school.id
        if not post_dict.get('username'):
            post_dict['username'] = post_dict.get('email')
        if user_type == 'student':
            form = InviteStudentsForm(post_dict)
        elif user_type == 'parent':
            form = InviteParentForm(post_dict, logged_in_user=request.user)
        else:
            form = InviteUsersForm(post_dict)

        if form.is_valid():
            form.save()
            return success_response('Form saved successfully')
        else:
            return validation_error_response(form.errors, user_id=request.user.id)


@login_required
@require_POST
def delete_users(request):
    """
    Deletes multiple CustomUsers based on the IDs provided in the POST request.
    The request must contain a JSON body with a list of user IDs to be deleted.
    """
    try:
        data = json.loads(request.body)
        user_ids = data.get('user_ids', [])

        if not isinstance(user_ids, list):
            return error_response('Invalid data format. Expected a list of user IDs.', status=400, user_id=request.user.id)

        CustomUser.objects.filter(id__in=user_ids, school=request.user.school).delete()
        return success_response('Users deleted successfully')

    except json.JSONDecodeError:
        return error_response('Invalid JSON format.', status=400, user_id=request.user.id)

def invited_account(request, uidb64, token):
    """This page is for validating an email and getting the initial info and password set for a user."""
    page = 'registration/activation_link.html'
    page_arguments = {}
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None
    if user is not None and account_activation_token.check_token(user, token):
        page = 'registration/initial_info_collection.html'
        if request.POST:
            form = InviteCombinedForm(user, request.POST)
            if form.is_valid():
                form.save()
                user.is_active = True
                user.save()
                login(request, user)
                return redirect('home')
        else:
            form = InviteCombinedForm(user)
        page_arguments['form'] = form
    return render(request, page, page_arguments)


@login_required
def fetch_user_type(request):
    if request.method == "GET":
        if 'students' in request.path:
            # Handle GET request for students list
            students = CustomUser.objects.filter(school=request.user.school, user_type='student')
            data = [{"id": student.id, "name": student.full_name or student.email} for student in students]
            return JsonResponse(data, safe=False)
        elif 'teachers' in request.path:
            # Handle GET request for students list
            teachers = CustomUser.objects.filter(school=request.user.school, user_type='teacher')
            data = [{"id": teacher.id, "name": teacher.full_name or teacher.email} for teacher in teachers]
            return JsonResponse(data, safe=False)

    return error_response("Method not allowed", status=405)


@login_required
def classrooms_view(request):
    if request.method == "GET":
        # Handle GET request for classrooms list
        classrooms = Classroom.objects.filter(school=request.user.school)
        data = [{"id": classroom.id, "name": classroom.name} for classroom in classrooms]
        return JsonResponse(data, safe=False)
    elif request.method == "POST":
        # Handle POST request to create a classroom
        try:
            input_dict = request.POST.dict()
            input_dict['school'] = request.user.school.id
            input_dict['students'] = json.loads(input_dict.get('students', '[]'))
            input_dict['teachers'] = json.loads(input_dict.get('teachers', '[]'))
            if request.user.user_type == 'teacher' and str(request.user.id) not in input_dict['teachers']:
                input_dict['teachers'].append(str(request.user.id))
            form = ClassroomForm(input_dict)
            if form.is_valid():
                form.save()
                return success_response("Classroom created successfully")
            return validation_error_response(form.errors, user_id=request.user.id)
        except json.JSONDecodeError:
            return HttpResponseBadRequest("Invalid JSON payload")

    elif request.method == "DELETE":
        # Handle DELETE request to delete classrooms
        try:
            data = json.loads(request.body)
            ids = data.get('ids', [])
            Classroom.objects.filter(school=request.user.school, id__in=ids).delete()
            return success_response("Classrooms deleted successfully", status=204)
        except json.JSONDecodeError:
            return HttpResponseBadRequest("Invalid JSON payload")

    # Default response for unsupported methods
    return error_response("Method not allowed", status=405)

@login_required
def render_classroom_list_view(request):
    # Security: Only teachers and administrators can access classroom management
    if request.user.user_type not in ['teacher', 'administrator']:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("You don't have permission to access classroom management")
    
    return render(request, 'general/classroom_list.html')


@login_required
def groups_view(request):
    if request.method == "GET":
        # Handle GET request for groups list
        groups = ReadingGroup.objects.filter(school=request.user.school)
        data = [{"id": group.id, "name": group.name} for group in groups]
        return JsonResponse(data, safe=False)
    elif request.method == "POST":
        # Handle POST request to create a group
        try:
            input_dict = request.POST.dict()
            input_dict['school'] = request.user.school.id
            input_dict['students'] = json.loads(input_dict.get('students', '[]'))
            input_dict['managers'] = json.loads(input_dict.get('managers', '[]'))
            if request.user.user_type == 'teacher' and str(request.user.id) not in input_dict['managers']:
                input_dict['managers'].append(str(request.user.id))
            form = ReadingGroupForm(input_dict)
            if form.is_valid():
                form.save()
                return success_response("Reading group created successfully")
            return validation_error_response(form.errors, user_id=request.user.id)
        except json.JSONDecodeError:
            return HttpResponseBadRequest("Invalid JSON payload")

    elif request.method == "DELETE":
        # Handle DELETE request to delete groups
        try:
            data = json.loads(request.body)
            ids = data.get('ids', [])
            ReadingGroup.objects.filter(school=request.user.school, id__in=ids).delete()
            return success_response("Reading groups deleted successfully", status=204)
        except json.JSONDecodeError:
            return HttpResponseBadRequest("Invalid JSON payload")

    # Default response for unsupported methods
    return error_response("Method not allowed", status=405)


@login_required
def groups_detailed_view(request):
    """Enhanced reading groups API with collaboration details"""
    if request.method == "GET":
        # Get reading groups where user is a manager
        groups = ReadingGroup.objects.filter(
            school=request.user.school,
            managers=request.user
        ).prefetch_related('managers', 'students').order_by('name')
        
        data = []
        for group in groups:
            # Get manager details
            managers_data = []
            for manager in group.managers.all():
                managers_data.append({
                    'id': manager.id,
                    'name': manager.full_name or f"{manager.first_name} {manager.last_initial}"
                })
            
            data.append({
                "id": group.id,
                "name": group.name,
                "created_date": group.created_date.strftime('%b %d, %Y') if hasattr(group, 'created_date') else 'Unknown',
                "created_by_current_user": hasattr(group, 'created_by') and group.created_by == request.user,
                "managers": managers_data,
                "student_count": group.students.count()
            })
        
        return JsonResponse(data, safe=False)
    
    return error_response("Method not allowed", status=405)


@login_required 
def reading_group_detail_view(request, group_id):
    """Individual reading group details API"""
    try:
        group = ReadingGroup.objects.get(
            id=group_id,
            school=request.user.school,
            managers=request.user
        )
        
        # Get manager details
        managers_data = []
        for manager in group.managers.all():
            managers_data.append({
                'id': manager.id,
                'name': manager.full_name or f"{manager.first_name} {manager.last_initial}"
            })
        
        # Get student details
        students_data = []
        for student in group.students.all():
            students_data.append({
                'id': student.id,
                'name': student.full_name or f"{student.first_name} {student.last_initial}"
            })
        
        data = {
            "id": group.id,
            "name": group.name,
            "managers": managers_data,
            "students": students_data,
            "created_date": group.created_date.strftime('%b %d, %Y') if hasattr(group, 'created_date') else 'Unknown'
        }
        
        return JsonResponse(data)
        
    except ReadingGroup.DoesNotExist:
        return error_response("Reading group not found", status=404)


@login_required
def reading_group_invite_view(request):
    """Handle reading group collaboration invitations"""
    if request.method == "POST":
        try:
            group_id = request.POST.get('group_id')
            teacher_id = request.POST.get('teacher_id') 
            message = request.POST.get('message', '')
            
            # Validate inputs
            if not group_id or not teacher_id:
                return error_response("Group ID and Teacher ID are required", status=400)
            
            # Get the reading group (must be managed by current user)
            try:
                group = ReadingGroup.objects.get(
                    id=group_id,
                    school=request.user.school,
                    managers=request.user
                )
            except ReadingGroup.DoesNotExist:
                return error_response("Reading group not found or access denied", status=404)
            
            # Get the teacher to invite
            try:
                teacher = CustomUser.objects.get(
                    id=teacher_id,
                    school=request.user.school,
                    user_type='teacher'
                )
            except CustomUser.DoesNotExist:
                return error_response("Teacher not found", status=404)
            
            # Check if teacher is already a manager
            if group.managers.filter(id=teacher_id).exists():
                return error_response("Teacher is already managing this reading group", status=400)
            
            # Add teacher as manager
            group.managers.add(teacher)
            
            # TODO: Send notification email to the invited teacher
            # For now, we'll just return success
            # In a real implementation, you'd want to:
            # 1. Create a notification record
            # 2. Send an email notification
            # 3. Add to a notifications system
            
            return success_response(
                f"Invitation sent to {teacher.full_name or teacher.first_name}",
                data={
                    'group_id': group.id,
                    'teacher_id': teacher.id,
                    'teacher_name': teacher.full_name or f"{teacher.first_name} {teacher.last_initial}"
                }
            )
            
        except Exception as e:
            return error_response(f"Failed to send invitation: {str(e)}", status=500)
    
    return error_response("Method not allowed", status=405)


@login_required
def render_group_list_view(request):
    # Security: Only teachers and administrators can access reading group management
    if request.user.user_type not in ['teacher', 'administrator']:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("You don't have permission to access reading group management")
    
    return render(request, 'general/reading_group_list.html')


FORM_DICT = {
    'student': {'form': CustomStudentForm, 'obj_type': CustomUser},
    'teacher': {'form': CustomTeacherForm, 'obj_type': CustomUser},
    'parent': {'form': CustomParentForm, 'obj_type': CustomUser},
    'administrator': {'form': CustomAdministratorForm, 'obj_type': CustomUser},
    'classrooms': {'form': CustomClassroomForm, 'obj_type': Classroom},
    'groups': {'form': CustomReadingGroupForm, 'obj_type': ReadingGroup},
}


@login_required
def edit_record(request, id):
    form = None
    log_form = None
    form_name = ''
    prev_url = ''
    change_password_form = None
    for r_type in FORM_DICT:
        if r_type in request.path:
            form_obj = FORM_DICT[r_type]['form']
            obj_type = FORM_DICT[r_type]['obj_type']
            form_name = r_type.capitalize()
            prev_url = '/{}/'.format(r_type)
            try:
                if obj_type == CustomUser:
                    obj = obj_type.objects.get(school=request.user.school, id=id, user_type=r_type)
                else:
                    obj = obj_type.objects.get(school=request.user.school, id=id)
            except obj_type.DoesNotExist:
                return handler404(request)
            if request.method == 'POST':
                form = form_obj(logged_in_user=request.user, instance=obj, data=request.POST)
                if form.is_valid():
                    form.save()
                    return success_response('Record updated successfully')
                else:
                    return validation_error_response(form.errors, user_id=request.user.id)
            elif request.method == 'DELETE':
                try:
                    obj.delete()
                    return success_response("Record deleted successfully", status=204)
                except obj_type.DoesNotExist:
                    return error_response("Record not found.", status=404)
            else:
                if obj_type == CustomUser:
                    if request.user == obj:
                        # add the password form for changing their own password.
                        change_password_form = OverriddenPasswordChangeForm(request.user)
                    else:
                        logged_in_type = request.user.user_type
                        obj_user_type = obj.user_type
                        if logged_in_type == 'administrator':
                            change_password_form = OverriddenAdminPasswordChangeForm(obj)
                        elif logged_in_type == 'teacher' and obj_user_type in ['student', 'parent']:
                            change_password_form = OverriddenAdminPasswordChangeForm(obj)
                        if obj_user_type == 'student':
                            log_form = LogForm()
                form = form_obj(logged_in_user=request.user, instance=obj)

    # Get the display name for the object
    object_name = ''
    if hasattr(obj, 'full_name'):
        object_name = obj.full_name
    elif hasattr(obj, 'name'):
        object_name = obj.name
    elif hasattr(obj, 'first_name'):
        object_name = f"{obj.first_name} {getattr(obj, 'last_initial', '')}"
    else:
        object_name = str(obj)
    
    # Get the default tab from URL parameter
    default_tab = request.GET.get('tab', 'status')
    
    page_arguments = {
        'form': form, 
        'id': id, 
        'prev_url': prev_url, 
        'form_name': form_name, 
        'object_name': object_name,
        'object': obj,
        'default_tab': default_tab,
        'change_password_form': change_password_form, 
        'log_form': log_form
    }
    return render(request, 'general/record.html', page_arguments)


def password_change_view(request, id):
    form = None
    if request.method == 'POST':
        if request.user.id != int(id):
            try:
                obj = CustomUser.objects.get(school=request.user.school, id=id)
            except CustomUser.DoesNotExist:
                return handler404(request)

            logged_in_type = request.user.user_type
            obj_user_type = obj.user_type
            if logged_in_type == 'administrator':
                form = OverriddenAdminPasswordChangeForm(obj, request.POST)
            elif logged_in_type == 'teacher' and obj_user_type in ['student', 'parent']:
                form = OverriddenAdminPasswordChangeForm(obj, request.POST)
        else:
            # the user is changing their own password
            form = OverriddenPasswordChangeForm(request.user, request.POST)

    if form is not None:
        if form.is_valid():
            form.save()
            return success_response('Information updated successfully')
        else:
            return validation_error_response(form.errors, user_id=request.user.id)

    return handler404(request)


@login_required
def list_classrooms_and_groups(request):
    """Currently not used"""
    if request.user.user_type != 'teacher':
        return permission_denied_response(request.user.id, 'access teacher resources')

    school = request.user.school
    classrooms = Classroom.objects.filter(school=school, teachers=request.user).order_by('name').values('id', 'name')
    reading_groups = ReadingGroup.objects.filter(school=school, managers=request.user).order_by('name').values('id', 'name')

    data = {
        "classrooms": list(classrooms),
        "reading_groups": list(reading_groups)
    }

    return JsonResponse(data, safe=False)


@login_required
def my_students_page(request):
    """Dedicated page for teachers to manage their students"""
    # Security: Only teachers and administrators can access
    if request.user.user_type not in ['teacher', 'administrator']:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("You don't have permission to access student management")
    
    school = request.user.school
    
    # Get teacher's classrooms and reading groups
    if request.user.user_type == 'teacher':
        classrooms = Classroom.objects.filter(school=school, teachers=request.user).order_by('name')
        reading_groups = ReadingGroup.objects.filter(school=school, managers=request.user).order_by('name')
    else:  # administrator
        classrooms = Classroom.objects.filter(school=school).order_by('name')
        reading_groups = ReadingGroup.objects.filter(school=school).order_by('name')
    
    # Get all students in teacher's classrooms and groups
    student_ids = set()
    for classroom in classrooms:
        student_ids.update(classroom.students.values_list('id', flat=True))
    for group in reading_groups:
        student_ids.update(group.students.values_list('id', flat=True))
    
    # Get students with parent relationships
    students = CustomUser.objects.filter(
        id__in=student_ids,
        school=school,
        user_type='student'
    ).select_related(
        'school'
    ).prefetch_related(
        'parent_relations__parent',
        'students_classrooms',
        'reading_groups'
    ).order_by('first_name', 'last_initial')
    
    # Get all available parents for assignment
    available_parents = CustomUser.objects.filter(
        school=school,
        user_type='parent'
    ).order_by('first_name', 'last_initial')
    
    # Get all students in school for adding new ones
    all_students = CustomUser.objects.filter(
        school=school,
        user_type='student'
    ).exclude(id__in=student_ids).order_by('first_name', 'last_initial')
    
    context = {
        'students': students,
        'classrooms': classrooms,
        'reading_groups': reading_groups,
        'available_parents': available_parents,
        'all_students': all_students,
        'user_type': 'student',  # For form compatibility
    }
    
    return render(request, 'general/my_students.html', context)


@login_required
def my_classrooms_page(request):
    """Dedicated page for teachers to manage their classrooms"""
    # Security: Only teachers and administrators can access
    if request.user.user_type not in ['teacher', 'administrator']:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("You don't have permission to access classroom management")
    
    school = request.user.school
    
    # Get teacher's classrooms
    from django.db.models import Count
    
    if request.user.user_type == 'teacher':
        classrooms = Classroom.objects.filter(
            school=school, 
            teachers=request.user
        ).select_related('school')\
         .prefetch_related('students', 'teachers')\
         .annotate(student_count=Count('students'))\
         .order_by('name')
    else:  # administrator
        classrooms = Classroom.objects.filter(
            school=school
        ).select_related('school')\
         .prefetch_related('students', 'teachers')\
         .annotate(student_count=Count('students'))\
         .order_by('name')
    
    # Get all students in school for adding to classrooms
    all_students = CustomUser.objects.filter(
        school=school,
        user_type='student'
    ).order_by('first_name', 'last_initial')
    
    # Calculate statistics for each classroom
    classroom_stats = []
    for classroom in classrooms:
        students_count = classroom.student_count  # Use annotated field instead of .count()
        # Calculate reading statistics for the classroom
        # You can add more complex stats here later if needed
        classroom_stats.append({
            'classroom': classroom,
            'students_count': students_count,
        })
    
    context = {
        'classroom_stats': classroom_stats,
        'classrooms': classrooms,
        'all_students': all_students,
        'user_type': 'classroom',  # For form compatibility
    }
    
    return render(request, 'general/my_classrooms.html', context)


@login_required
def add_student_to_class(request):
    """Add existing student to teacher's classroom or reading group"""
    if request.method != 'POST':
        return error_response('POST method required', status=405)
    
    # Security check
    if request.user.user_type not in ['teacher', 'administrator']:
        return permission_denied_response(request.user.id, 'add students to class')
    
    student_id = request.POST.get('student_id')
    classroom_id = request.POST.get('classroom_id')
    group_id = request.POST.get('group_id')
    
    if not student_id:
        return error_response('Student ID required', status=400)
    
    try:
        student = CustomUser.objects.get(id=student_id, school=request.user.school, user_type='student')
        
        # Add to classroom if specified
        if classroom_id:
            classroom = Classroom.objects.get(id=classroom_id, school=request.user.school, teachers=request.user)
            classroom.students.add(student)
        
        # Add to reading group if specified
        if group_id:
            group = ReadingGroup.objects.get(id=group_id, school=request.user.school, managers=request.user)
            group.students.add(student)
        
        return success_response('Student added successfully')
        
    except CustomUser.DoesNotExist:
        return error_response('Student not found', status=404)
    except (Classroom.DoesNotExist, ReadingGroup.DoesNotExist):
        return error_response('Classroom or group not found', status=404)
    except Exception as e:
        return error_response(str(e), status=500)


@login_required
def create_student(request):
    """Create new student and optionally add to classroom/group"""
    if request.method != 'POST':
        return error_response('POST method required', status=405)
    
    # Security check
    if request.user.user_type not in ['teacher', 'administrator']:
        return permission_denied_response(request.user.id, 'create students')
    
    first_name = request.POST.get('first_name')
    last_initial = request.POST.get('last_initial')
    email = request.POST.get('email')
    password = request.POST.get('password')
    classroom_id = request.POST.get('classroom_id')
    group_id = request.POST.get('group_id')
    
    if not all([first_name, last_initial, email, password]):
        return error_response('All required fields must be filled (first name, last initial, email, and password)', status=400)
    
    try:
        # Check if email already exists
        if CustomUser.objects.filter(email=email).exists():
            return error_response('Email already exists', status=400)
        
        # Create student with teacher-provided password
        student = CustomUser.objects.create_user(
            username=email,
            email=email,
            password=password,  # Use teacher-provided password
            first_name=first_name,
            last_initial=last_initial.upper(),
            user_type='student',
            school=request.user.school
        )
        
        # Teacher sets password, so no need to require change on first login
        student.password_change_required = False
        student.save()
        
        # Add to classroom if specified
        if classroom_id:
            classroom = Classroom.objects.get(id=classroom_id, school=request.user.school, teachers=request.user)
            classroom.students.add(student)
        
        # Add to reading group if specified
        if group_id:
            group = ReadingGroup.objects.get(id=group_id, school=request.user.school, managers=request.user)
            group.students.add(student)
        
        return success_response('Student created successfully', data={'student_email': email})
        
    except Exception as e:
        return error_response(str(e), status=500)


@login_required
def add_parent_to_student(request):
    """Add parent to student relationship"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POST method required'})
    
    # Security check
    if request.user.user_type not in ['teacher', 'administrator']:
        return JsonResponse({'success': False, 'message': 'Unauthorized'})
    
    student_id = request.POST.get('student_id')
    parent_id = request.POST.get('parent_id')
    
    if not all([student_id, parent_id]):
        return JsonResponse({'success': False, 'message': 'Student and parent IDs required'})
    
    try:
        student = CustomUser.objects.get(id=student_id, school=request.user.school, user_type='student')
        parent = CustomUser.objects.get(id=parent_id, school=request.user.school, user_type='parent')
        
        # Create or get the relationship
        relationship, created = StudentParentRelation.objects.get_or_create(
            school=request.user.school,
            student=student,
            parent=parent
        )
        
        if created:
            return JsonResponse({'success': True, 'message': 'Parent added successfully'})
        else:
            return JsonResponse({'success': False, 'message': 'Parent relationship already exists'})
        
    except CustomUser.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Student or parent not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
def remove_parent_from_student(request):
    """Remove parent from student relationship"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POST method required'})
    
    # Security check
    if request.user.user_type not in ['teacher', 'administrator']:
        return JsonResponse({'success': False, 'message': 'Unauthorized'})
    
    student_id = request.POST.get('student_id')
    parent_id = request.POST.get('parent_id')
    
    if not all([student_id, parent_id]):
        return JsonResponse({'success': False, 'message': 'Student and parent IDs required'})
    
    try:
        relationship = StudentParentRelation.objects.get(
            school=request.user.school,
            student_id=student_id,
            parent_id=parent_id
        )
        relationship.delete()
        
        return JsonResponse({'success': True, 'message': 'Parent removed successfully'})
        
    except StudentParentRelation.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Parent relationship not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
def remove_student_from_classes(request):
    """Remove student from all teacher's classrooms and reading groups"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POST method required'})
    
    # Security check
    if request.user.user_type not in ['teacher', 'administrator']:
        return JsonResponse({'success': False, 'message': 'Unauthorized'})
    
    student_id = request.POST.get('student_id')
    
    if not student_id:
        return JsonResponse({'success': False, 'message': 'Student ID required'})
    
    try:
        student = CustomUser.objects.get(id=student_id, school=request.user.school, user_type='student')
        
        # Remove from teacher's classrooms
        classrooms = Classroom.objects.filter(school=request.user.school, teachers=request.user)
        for classroom in classrooms:
            classroom.students.remove(student)
        
        # Remove from teacher's reading groups
        groups = ReadingGroup.objects.filter(school=request.user.school, managers=request.user)
        for group in groups:
            group.students.remove(student)
        
        return JsonResponse({'success': True, 'message': 'Student removed from all classes'})
        
    except CustomUser.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Student not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
def get_classroom_students(request, classroom_id):
    """Get students in a specific classroom"""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'message': 'GET method required'})
    
    # Security: Only teachers and administrators can access
    if request.user.user_type not in ['teacher', 'administrator']:
        return JsonResponse({'success': False, 'message': 'Permission denied'})
    
    try:
        # Get the classroom
        classroom = Classroom.objects.get(id=classroom_id, school=request.user.school)
        
        # Security: Teachers can only access their own classrooms
        if request.user.user_type == 'teacher' and request.user not in classroom.teachers.all():
            return JsonResponse({'success': False, 'message': 'Permission denied'})
        
        # Get students in this classroom
        students = classroom.students.all().order_by('first_name', 'last_initial')
        
        students_data = []
        for student in students:
            students_data.append({
                'id': student.id,
                'first_name': student.first_name,
                'last_initial': student.last_initial,
                'email': student.email,
            })
        
        return JsonResponse({
            'success': True,
            'students': students_data,
            'classroom_name': classroom.name
        })
        
    except Classroom.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Classroom not found'})
    except Exception as e:
        print(f"Error getting classroom students: {e}")
        return JsonResponse({'success': False, 'message': 'An error occurred while fetching students'})


@login_required
def remove_student_from_classroom(request):
    """Remove student from a specific classroom"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POST method required'})
    
    # Security: Only teachers and administrators can access
    if request.user.user_type not in ['teacher', 'administrator']:
        return JsonResponse({'success': False, 'message': 'Permission denied'})
    
    try:
        student_id = request.POST.get('student_id')
        classroom_id = request.POST.get('classroom_id')
        
        if not student_id or not classroom_id:
            return JsonResponse({'success': False, 'message': 'Student ID and Classroom ID are required'})
        
        # Get the classroom and student
        classroom = Classroom.objects.get(id=classroom_id, school=request.user.school)
        student = CustomUser.objects.get(id=student_id, school=request.user.school, user_type='student')
        
        # Security: Teachers can only manage their own classrooms
        if request.user.user_type == 'teacher' and request.user not in classroom.teachers.all():
            return JsonResponse({'success': False, 'message': 'Permission denied'})
        
        # Remove student from classroom
        classroom.students.remove(student)
        
        return JsonResponse({
            'success': True,
            'message': f'{student.first_name} {student.last_initial} has been removed from {classroom.name}'
        })
        
    except (Classroom.DoesNotExist, CustomUser.DoesNotExist):
        return JsonResponse({'success': False, 'message': 'Classroom or student not found'})
    except Exception as e:
        print(f"Error removing student from classroom: {e}")
        return JsonResponse({'success': False, 'message': 'An error occurred while removing student'})



@login_required
def admin_student_management_view(request):
    """Admin student management page for bulk transfers and management"""
    if request.user.user_type != 'administrator':
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("You don't have permission to access admin student management")
    
    return render(request, 'general/admin_student_management.html')


@login_required
def api_admin_students(request):
    """API for admin student management data"""
    if request.user.user_type != 'administrator':
        return error_response("Access denied", status=403)
    
    if request.method == "GET":
        try:
            from django.db.models import Count, Max
            
            # Get all students in the school
            students = CustomUser.objects.filter(
                school=request.user.school,
                user_type='student'
            ).prefetch_related(
                'classrooms',
                'reading_groups',
                'parent_relations__parent'
            ).annotate(
                last_log_date=Max('log_set__date')
            )
            
            students_data = []
            for student in students:
                # Get classrooms
                classrooms = [{'id': c.id, 'name': c.name} for c in student.classrooms.all()]
                
                # Get reading groups
                reading_groups = [{'id': g.id, 'name': g.name} for g in student.reading_groups.all()]
                
                # Get parents
                parents = []
                for relation in student.parent_relations.all():
                    parents.append({
                        'id': relation.parent.id,
                        'name': f"{relation.parent.first_name} {relation.parent.last_initial}"
                    })
                
                students_data.append({
                    'id': student.id,
                    'name': f"{student.first_name} {student.last_initial}",
                    'email': student.email,
                    'classrooms': classrooms,
                    'reading_groups': reading_groups,
                    'parents': parents,
                    'last_activity': student.last_log_date.isoformat() if student.last_log_date else None,
                    'is_active': student.is_active
                })
            
            # Get statistics
            total_students = students.count()
            unassigned_students = sum(1 for s in students if not s.classrooms.exists())
            active_classrooms = Classroom.objects.filter(school=request.user.school).count()
            reading_groups_count = ReadingGroup.objects.filter(school=request.user.school).count()
            
            return JsonResponse({
                'success': True,
                'data': {
                    'students': students_data,
                    'stats': {
                        'total_students': total_students,
                        'unassigned_students': unassigned_students,
                        'active_classrooms': active_classrooms,
                        'reading_groups': reading_groups_count
                    }
                }
            })
            
        except Exception as e:
            return error_response(f"Failed to load student data: {str(e)}", status=500)
    
    return error_response("Method not allowed", status=405)


@login_required
def api_bulk_student_transfer(request):
    """API for bulk student transfers"""
    if request.user.user_type != 'administrator':
        return error_response("Access denied", status=403)
    
    if request.method == "POST":
        try:
            import json
            
            # Get form data
            student_ids = json.loads(request.POST.get('student_ids', '[]'))
            action = request.POST.get('action')
            destination = request.POST.get('destination')
            reason = request.POST.get('reason', '')
            notify_teachers = request.POST.get('notify_teachers') == 'on'
            notify_parents = request.POST.get('notify_parents') == 'on'
            
            if not student_ids or not action:
                return error_response("Student IDs and action are required", status=400)
            
            # Get students
            students = CustomUser.objects.filter(
                id__in=student_ids,
                school=request.user.school,
                user_type='student'
            )
            
            if not students.exists():
                return error_response("No valid students found", status=404)
            
            count = 0
            
            # Execute the transfer action
            if action == 'move_classroom':
                if not destination:
                    return error_response("Destination classroom is required", status=400)
                
                try:
                    new_classroom = Classroom.objects.get(
                        id=destination,
                        school=request.user.school
                    )
                    
                    for student in students:
                        # Remove from all current classrooms
                        student.classrooms.clear()
                        # Add to new classroom
                        new_classroom.students.add(student)
                        count += 1
                        
                except Classroom.DoesNotExist:
                    return error_response("Destination classroom not found", status=404)
            
            elif action == 'add_classroom':
                if not destination:
                    return error_response("Destination classroom is required", status=400)
                
                try:
                    classroom = Classroom.objects.get(
                        id=destination,
                        school=request.user.school
                    )
                    
                    for student in students:
                        classroom.students.add(student)
                        count += 1
                        
                except Classroom.DoesNotExist:
                    return error_response("Destination classroom not found", status=404)
            
            elif action == 'remove_classroom':
                for student in students:
                    student.classrooms.clear()
                    count += 1
            
            elif action == 'add_reading_group':
                if not destination:
                    return error_response("Destination reading group is required", status=400)
                
                try:
                    reading_group = ReadingGroup.objects.get(
                        id=destination,
                        school=request.user.school
                    )
                    
                    for student in students:
                        reading_group.students.add(student)
                        count += 1
                        
                except ReadingGroup.DoesNotExist:
                    return error_response("Destination reading group not found", status=404)
            
            elif action == 'remove_reading_group':
                if destination:
                    # Remove from specific reading group
                    try:
                        reading_group = ReadingGroup.objects.get(
                            id=destination,
                            school=request.user.school
                        )
                        
                        for student in students:
                            reading_group.students.remove(student)
                            count += 1
                            
                    except ReadingGroup.DoesNotExist:
                        return error_response("Reading group not found", status=404)
                else:
                    # Remove from all reading groups
                    for student in students:
                        student.reading_groups.clear()
                        count += 1
            
            # TODO: Implement notification system
            if notify_teachers:
                # Send notifications to affected teachers
                pass
            
            if notify_parents:
                # Send notifications to affected parents
                pass
            
            # TODO: Log the transfer for audit trail
            # Create audit log entry with reason, user, etc.
            
            return success_response(
                f"Successfully transferred {count} students",
                data={'count': count}
            )
            
        except Exception as e:
            return error_response(f"Failed to transfer students: {str(e)}", status=500)
    
    return error_response("Method not allowed", status=405)


def handler404(request, *args, **argv):
    page = 'general/404.html'
    return render(request, page, {}, status=404)


def handler500(request, *args, **argv):
    page = 'general/500.html'
    return render(request, page, {}, status=500)


# =============================================================================
# CLASS-BASED VIEWS (New - Using Mixins for Cleaner Code)
# =============================================================================

from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from .view_mixins import (
    SchoolFilterMixin,
    UserTypePermissionMixin,
    SearchableMixin,
    SortableMixin
)


class StudentListView(
    LoginRequiredMixin,
    SchoolFilterMixin,
    UserTypePermissionMixin,
    SearchableMixin,
    SortableMixin,
    ListView
):
    """
    Class-based view for listing students with automatic filtering and permissions
    Uses mixins to eliminate boilerplate code
    """
    model = CustomUser
    template_name = 'general/user_list.html'
    context_object_name = 'page_obj'
    paginate_by = 10
    allowed_user_types = ['teacher', 'administrator', 'parent']
    search_fields = ['email', 'first_name', 'last_name']
    sortable_fields = {
        'id': 'id',
        'first_name': 'first_name',
        'email': 'email'
    }
    default_sort = 'first_name'
    
    def get_queryset(self):
        """Filter for students only, respect teacher permissions"""
        queryset = super().get_queryset()
        queryset = queryset.filter(user_type='student')
        return queryset
    
    def get_context_data(self, **kwargs):
        """Add invite form to context"""
        context = super().get_context_data(**kwargs)
        context['user_type'] = 'student'
        context['invite_form'] = InviteStudentsForm()
        return context
