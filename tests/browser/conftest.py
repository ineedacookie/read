"""
Shared fixtures for browser-based Playwright tests.
Sets up a live Django server and seed data that the browser workflows expect.
"""

import os
import pytest

# Allow synchronous ORM access within asynchronous Playwright contexts
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

# All browser tests need database access with committed transactions.
pytestmark = pytest.mark.django_db(transaction=True)


def _create_user(user_model, *, username, email, password, user_type, school, **extra_fields):
    """
    Helper to create or update a user with the given credentials.
    Ensures passwords are always set correctly even if the user exists already.
    """
    user = user_model.objects.filter(email=email).first()
    if user is None:
        user, created = user_model.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'user_type': user_type,
                'school': school,
                **extra_fields,
            }
        )
        if not created:
            user.email = email
            user.user_type = user_type
            user.school = school
            for field, value in extra_fields.items():
                setattr(user, field, value)
    else:
        user.username = username
        user.user_type = user_type
        user.school = school
        for field, value in extra_fields.items():
            setattr(user, field, value)
    user.set_password(password)
    user.save(update_fields=None)
    return user


def _seed_playwright_dataset():
    """
    Idempotently populate the database with entities required by browser tests.
    """
    from django.utils import timezone
    from django.contrib.auth import get_user_model
    from users.models import School, Classroom, ReadingGroup, StudentParentRelation
    from reading_logs.models import Log, DailyGoal

    User = get_user_model()

    school, _ = School.objects.get_or_create(name="Playwright Test School")

    admin = _create_user(
        User,
        username="admin@test.com",
        email="admin@test.com",
        password="testpass123",
        user_type="administrator",
        school=school,
        first_name="Admin",
        last_initial="T",
    )
    teacher = _create_user(
        User,
        username="teacher@test.com",
        email="teacher@test.com",
        password="testpass123",
        user_type="teacher",
        school=school,
        first_name="Teacher",
        last_initial="T",
    )
    student = _create_user(
        User,
        username="student@test.com",
        email="student@test.com",
        password="testpass123",
        user_type="student",
        school=school,
        first_name="Student",
        last_initial="S",
    )
    parent = _create_user(
        User,
        username="parent@test.com",
        email="parent@test.com",
        password="testpass123",
        user_type="parent",
        school=school,
        first_name="Parent",
        last_initial="P",
    )

    _create_user(
        User,
        username="admin@example.com",
        email="admin@example.com",
        password="admin",
        user_type="administrator",
        school=school,
        first_name="Admin",
        last_initial="E",
    )
    _create_user(
        User,
        username="teacher@example.com",
        email="teacher@example.com",
        password="teacher",
        user_type="teacher",
        school=school,
        first_name="Teacher",
        last_initial="E",
    )
    student_example = _create_user(
        User,
        username="student@example.com",
        email="student@example.com",
        password="student",
        user_type="student",
        school=school,
        first_name="Student",
        last_initial="E",
    )
    parent_example = _create_user(
        User,
        username="parent@example.com",
        email="parent@example.com",
        password="parent",
        user_type="parent",
        school=school,
        first_name="Parent",
        last_initial="E",
    )

    StudentParentRelation.objects.get_or_create(
        student=student,
        parent=parent,
        school=school,
    )
    StudentParentRelation.objects.get_or_create(
        student=student_example,
        parent=parent_example,
        school=school,
    )

    classroom, _ = Classroom.objects.get_or_create(
        name="Sample Classroom",
        school=school,
        defaults={'created_by': admin},
    )
    classroom.teachers.add(teacher)
    classroom.students.add(student)

    reading_group, _ = ReadingGroup.objects.get_or_create(
        name="Sample Reading Group",
        school=school,
        defaults={'created_by': admin},
    )
    reading_group.managers.add(teacher)
    reading_group.students.add(student)

    DailyGoal.objects.get_or_create(
        student=student,
        school=school,
        defaults={'type': 'pages', 'value': 20},
    )

    for offset in range(5):
        Log.objects.get_or_create(
            student=student,
            school=school,
            date=timezone.now().date() - timezone.timedelta(days=offset),
            defaults={
                'title': f"Test Book {offset}",
                'pages': 25 + offset,
                'minutes': 30 + offset,
            },
        )


@pytest.fixture(scope="session", autouse=True)
def browser_live_server(django_db_setup, django_db_blocker):
    """
    Start a live Django server on http://localhost:8001/ so Playwright tests can connect.
    Uses StaticLiveServerTestCase under the hood to serve static assets as well.
    """
    from django.contrib.staticfiles.testing import StaticLiveServerTestCase

    class BrowserStaticServer(StaticLiveServerTestCase):
        host = "localhost"
        port = 8001
        serve_static = True

        @classmethod
        def setUpClass(cls):  # pragma: no cover - infrastructure setup
            super().setUpClass()

        @classmethod
        def tearDownClass(cls):  # pragma: no cover - infrastructure teardown
            super().tearDownClass()

    django_db_blocker.unblock()
    BrowserStaticServer.setUpClass()
    try:
        yield BrowserStaticServer.live_server_url
    finally:
        BrowserStaticServer.tearDownClass()
        django_db_blocker.block()


@pytest.fixture(scope="session", autouse=True)
def browser_seed_data(django_db_setup, django_db_blocker):
    """
    Seed a deterministic dataset that the Playwright tests rely on
    (users with known credentials, classrooms, reading logs, etc.).
    """
    django_db_blocker.unblock()
    try:
        _seed_playwright_dataset()
    finally:
        django_db_blocker.block()


@pytest.fixture(autouse=True)
def ensure_browser_seed_data(django_db_blocker):
    """
    Ensure each browser test still has access to the seeded data even after
    database flushes performed by Django's TestCase infrastructure.
    """
    django_db_blocker.unblock()
    try:
        _seed_playwright_dataset()
        yield
    finally:
        django_db_blocker.block()


@pytest.fixture(scope="function")
def page(playwright):
    """
    Provide a fresh Playwright page for each test using the shared session-scoped
    Playwright instance supplied by pytest-playwright.
    """
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(
        viewport={'width': 1280, 'height': 720},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    )
    page = context.new_page()
    page.set_default_timeout(30000)
    try:
        yield page
    finally:
        context.close()
        browser.close()

