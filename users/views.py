import logging
import json

from django.contrib.auth.forms import PasswordChangeForm, AdminPasswordChangeForm
from django.views.decorators.http import require_POST
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.db.models import Q
from django.http import Http404, HttpResponseBadRequest

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


from django.contrib.auth.hashers import make_password


def create_custom_users(request):
    from django.utils.crypto import get_random_string
    import random
    from datetime import date, timedelta
    from reading_logs.models import Log

    # Create schools
    schools = [School.objects.create(name=f'School {i}') for i in range(1, 4)]

    # Define custom users data
    users_data = [
                     {'username': f'teacher_{i}', 'email': f'teacher_{i}@example.com', 'user_type': 'teacher'} for i in
                     range(3)
                 ] + [
                     {'username': f'student_{i}', 'email': f'student_{i}@example.com', 'user_type': 'student'} for i in
                     range(30)
                 ] + [
                     {'username': f'admin_{i}', 'email': f'admin_{i}@example.com', 'user_type': 'administrator'} for i
                     in range(2)
                 ] + [
                     {'username': f'parent_{i}', 'email': f'parent_{i}@example.com', 'user_type': 'parent'} for i in
                     range(10)
                 ]

    all_students = []

    # Create users and assign to schools
    for i, school in enumerate(schools):
        for j, user_data in enumerate(users_data):
            user = CustomUser.objects.create(
                username=str(i) + "_" + user_data['username'],
                email=str(i) + "_" + user_data['email'],
                user_type=user_data['user_type'],
                password=make_password('temp'),  # Default password for initial creation
                school=school
            )
            if user_data['user_type'] == 'student':
                all_students.append(user)

    # Create logs for students
    def create_logs(user):
        today = date.today()
        start_date = today.replace(day=1)
        end_date = today
        current_date = start_date
        while current_date <= end_date:
            num_logs = random.randint(1, 2)
            for _ in range(num_logs):
                Log.objects.create(
                    school=user.school,
                    student=user,
                    pages=random.randint(2, 10),
                    minutes=random.randint(5, 45),
                    date=current_date
                )
            current_date += timedelta(days=1)

    for student in all_students:
        create_logs(student)

    # Assign students to classrooms and reading groups
    unassigned_students = all_students[:]
    for teacher in CustomUser.objects.filter(user_type='teacher'):
        # Create classroom and assign students
        classroom = Classroom.objects.create(name=f"Classroom_{teacher.username}", school=teacher.school)
        assigned_students = random.sample(unassigned_students, 10)
        for student in assigned_students:
            student.classroom_set.add(classroom)
            unassigned_students.remove(student)

        # Create reading groups and split students
        reading_group1 = ReadingGroup.objects.create(name=f"Reading_Group_1_{teacher.username}", school=teacher.school)
        reading_group2 = ReadingGroup.objects.create(name=f"Reading_Group_2_{teacher.username}", school=teacher.school)
        half = len(assigned_students) // 2
        reading_group1.students.set(assigned_students[:half])
        reading_group2.students.set(assigned_students[half:])

    # Return a response
    return render(request, 'general/home.html', {'message': 'Custom users created successfully'})


@login_required
def home(request, **kwargs):
    """Main page that is the root of the website"""
    """Checks whether the user is part of the staff or a customer"""
    if request.user.is_staff:
        return redirect('/io_admin')
    else:
        page_arguments = {}
        if request.user.user_type == 'teacher':
            page = 'general/teacher_dash.html'
            school = request.user.school
            classrooms = Classroom.objects.filter(school=school, teachers=request.user).order_by('name').values('id',
                                                                                                                'name')
            reading_groups = ReadingGroup.objects.filter(school=school, managers=request.user).order_by('name').values(
                'id', 'name')

            data = {
                "classrooms": list(classrooms),
                "reading_groups": list(reading_groups)
            }
            page_arguments['data'] = data
        return render(request, page, page_arguments)  # fill the {} with arguments


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
            return JsonResponse({'success': True}, status=200)
        else:
            return JsonResponse({'form_errors': form.errors}, status=400)


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
            return JsonResponse({'error': 'Invalid data format. Expected a list of user IDs.'}, status=400)

        CustomUser.objects.filter(id__in=user_ids, school=request.user.school).delete()
        return JsonResponse({'success': True}, status=200)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON format.'}, status=400)

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

    return JsonResponse({"error": "Method not allowed"}, status=405)


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
                return JsonResponse({"success": True}, status=200)
            return JsonResponse({"errors": form.errors}, status=400)
        except json.JSONDecodeError:
            return HttpResponseBadRequest("Invalid JSON payload")

    elif request.method == "DELETE":
        # Handle DELETE request to delete classrooms
        try:
            data = json.loads(request.body)
            ids = data.get('ids', [])
            Classroom.objects.filter(school=request.user.school, id__in=ids).delete()
            return JsonResponse({"success": True}, status=204)
        except json.JSONDecodeError:
            return HttpResponseBadRequest("Invalid JSON payload")

    # Default response for unsupported methods
    return JsonResponse({"error": "Method not allowed"}, status=405)

@login_required
def render_classroom_list_view(request):
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
                return JsonResponse({"success": True}, status=200)
            return JsonResponse({"errors": form.errors}, status=400)
        except json.JSONDecodeError:
            return HttpResponseBadRequest("Invalid JSON payload")

    elif request.method == "DELETE":
        # Handle DELETE request to delete groups
        try:
            data = json.loads(request.body)
            ids = data.get('ids', [])
            ReadingGroup.objects.filter(school=request.user.school, id__in=ids).delete()
            return JsonResponse({"success": True}, status=204)
        except json.JSONDecodeError:
            return HttpResponseBadRequest("Invalid JSON payload")

    # Default response for unsupported methods
    return JsonResponse({"error": "Method not allowed"}, status=405)

@login_required
def render_group_list_view(request):
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
                    return JsonResponse({'success': True}, status=200)
                else:
                    return JsonResponse({'errors': form.errors}, status=400)
            elif request.method == 'DELETE':
                try:
                    obj.delete()
                    return JsonResponse({"success": True}, status=204)
                except obj_type.DoesNotExist:
                    return JsonResponse({"error": "Record not found."}, status=404)
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

    page_arguments = {'form': form, 'id': id, 'prev_url': prev_url, 'form_name': form_name, 'change_password_form': change_password_form, 'log_form': log_form}
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
            return JsonResponse({'success': True}, status=200)
        else:
            return JsonResponse({'errors': form.errors}, status=400)

    return handler404(request)


@login_required
def list_classrooms_and_groups(request):
    """Currently not used"""
    if request.user.user_type != 'teacher':
        return JsonResponse({"error": "Unauthorized access"}, status=403)

    school = request.user.school
    classrooms = Classroom.objects.filter(school=school, teachers=request.user).order_by('name').values('id', 'name')
    reading_groups = ReadingGroup.objects.filter(school=school, managers=request.user).order_by('name').values('id', 'name')

    data = {
        "classrooms": list(classrooms),
        "reading_groups": list(reading_groups)
    }

    return JsonResponse(data, safe=False)

def handler404(request, *args, **argv):
    page = 'general/404.html'
    return render(request, page, {}, status=404)


def handler500(request, *args, **argv):
    page = 'general/500.html'
    return render(request, page, {}, status=500)
