import logging

from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.db.models import Q

from .forms import OverriddenPasswordChangeForm, OverriddenAdminPasswordChangeForm, RegisterUserForm, InviteCombinedForm
from .models import CustomUser
from .tokens import account_activation_token
from .utils import get_selectable_employees, send_email_with_link

logger = logging.getLogger("django.request")


def landing_page(request):
    page = 'general/landing.html'
    page_arguments = {}
    return render(request, page, page_arguments)


from django.contrib.auth.hashers import make_password


def create_custom_users(request):
    # Define custom users data
    users_data = [
                     {'username': f'teacher_{i}', 'email': f'teacher_{i}@example.com', 'user_type': 'teacher'} for i in
                     range(3)
                 ] + [
                     {'username': f'student_{i}', 'email': f'student_{i}@example.com', 'user_type': 'student'} for i in
                     range(20)
                 ] + [
                     {'username': f'admin_{i}', 'email': f'admin_{i}@example.com', 'user_type': 'administrator'} for i
                     in range(2)
                 ] + [
                     {'username': f'parent_{i}', 'email': f'parent_{i}@example.com', 'user_type': 'parent'} for i in
                     range(10)
                 ]

    # Create users
    for user_data in users_data:
        CustomUser.objects.create(
            username=user_data['username'],
            email=user_data['email'],
            user_type=user_data['user_type'],
            password=make_password('defaultpassword')  # Default password for initial creation
        )

    # Return a response
    return render(request, 'general/home.html', {'message': 'Custom users created successfully'})


@login_required
def home(request):
    """Main page that is the root of the website"""
    """check that the user is logged in. if not send them to the log in page."""
    # if not request.user.password:
    #     return create_account(request)
    """Checks whether the user is part of the staff or a customer"""
    if request.user.is_staff:
        return redirect('/io_admin')
    else:
        page = 'general/home.html'
        page_arguments = {}
        return render(request, page, page_arguments)  # fill the {} with arguments


@login_required
def user_list(request):
    queryset = CustomUser.objects.all()  # TODO filter this using the information from the user

    # Filter by user type
    user_type = request.GET.get('user_type')
    if user_type:
        queryset = queryset.filter(user_type=user_type)

    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        queryset = queryset.filter(Q(email__icontains=search_query) | Q(full_name__icontains=search_query))

    # Sorting functionality
    sort_field = request.GET.get('sort_field', 'first_name')
    sort_order = request.GET.get('sort_order', 'asc')
    if sort_order == 'desc':
        sort_field = f'-{sort_field}'
    queryset = queryset.order_by(sort_field)

    # Pagination
    paginator = Paginator(queryset, 10)  # Show 10 users per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # If AJAX request, return JSON response
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        users_list = list(page_obj.object_list.values('id', 'first_name', 'last_name', 'email'))
        return JsonResponse({
            'users': users_list,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'page_number': page_obj.number,
            'num_pages': page_obj.paginator.num_pages,
        })

    return render(request, 'general/home.html', {'page_obj': page_obj})


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


def handler404(request, *args, **argv):
    page = 'general/404.html'
    return render(request, page, {}, status=404)


def handler500(request, *args, **argv):
    page = 'general/500.html'
    return render(request, page, {}, status=500)
