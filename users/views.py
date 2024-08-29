import logging

from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode

from .forms import OverriddenPasswordChangeForm, OverriddenAdminPasswordChangeForm, RegisterUserForm, InviteCombinedForm
from .models import CustomUser
from .tokens import account_activation_token
from .utils import get_selectable_employees, send_email_with_link

logger = logging.getLogger("django.request")


def landing_page(request):
    page = 'general/landing.html'
    page_arguments = {}
    return render(request, page, page_arguments)


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
