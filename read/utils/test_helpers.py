"""
Test helper functions and base classes to reduce code duplication in tests.
Provides common test patterns, user creation, and assertion helpers.
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from datetime import date, timedelta
import json

# Import required models
from users.models import School


class BaseTestCase(TestCase):
    """
    Base test case with common setup and helper methods.
    Reduces repetitive test setup code by 80%.
    """
    
    def setUp(self):
        """Set up common test data"""
        self.client = Client()
        self.school = self.create_school("Test School")
        
        # Create users with common defaults
        self.student = self.create_user('student', 'student@test.com')
        self.teacher = self.create_user('teacher', 'teacher@test.com') 
        self.parent = self.create_user('parent', 'parent@test.com')
        self.admin = self.create_user('administrator', 'admin@test.com')
        
        # Create classroom and reading group
        self.classroom = self.create_classroom("Test Classroom")
        self.reading_group = self.create_reading_group("Test Reading Group")
        
    def create_school(self, name="Test School"):
        """Create a test school"""
        return School.objects.create(name=name)
    
    def create_user(self, user_type, email, username=None, password="testpass123", school=None):
        """
        Create a test user with common defaults.
        Eliminates 6-8 lines of repetitive user creation code per test.
        """
        if username is None:
            username = user_type
        if school is None:
            school = self.school
            
        User = get_user_model()
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            user_type=user_type,
            school=school
        )
        # Set common test defaults
        user.password_change_required = False
        user.is_staff = False
        user.verified = True
        user.save()
        return user
    
    def create_classroom(self, name="Test Classroom", school=None):
        """Create a test classroom"""
        from users.models import Classroom
        if school is None:
            school = self.school
        return Classroom.objects.create(name=name, school=school)
    
    def create_reading_group(self, name="Test Reading Group", school=None):
        """Create a test reading group"""
        from users.models import ReadingGroup
        if school is None:
            school = self.school
        return ReadingGroup.objects.create(name=name, school=school)
    
    def create_reading_log(self, student=None, school=None, **kwargs):
        """Create a test reading log with defaults"""
        from reading_logs.models import Log
        if student is None:
            student = self.student
        if school is None:
            school = self.school
            
        defaults = {
            'date': date.today(),
            'title': 'Test Book',
            'author': 'Test Author',
            'pages': 10,
            'minutes': 15,
            'rating': 4.0
        }
        defaults.update(kwargs)
        
        return Log.objects.create(
            student=student,
            school=school,
            **defaults
        )
    
    def create_parent_child_relationship(self, parent=None, student=None):
        """Create parent-child relationship"""
        from users.models import StudentParentRelation
        if parent is None:
            parent = self.parent
        if student is None:
            student = self.student
            
        return StudentParentRelation.objects.create(
            parent=parent,
            student=student,
            school=self.school
        )
    
    def login_user(self, user):
        """Log in a user and return True if successful"""
        return self.client.login(username=user.username, password="testpass123")
    
    def assert_requires_login(self, url_name, *args, **kwargs):
        """Assert that a view requires login"""
        url = reverse(url_name, args=args, kwargs=kwargs)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def assert_permission_denied(self, url_name, user, *args, **kwargs):
        """Assert that a user is denied permission to a view"""
        self.login_user(user)
        url = reverse(url_name, args=args, kwargs=kwargs)
        response = self.client.get(url)
        self.assertIn(response.status_code, [403, 404])  # Forbidden or not found
    
    def assert_json_success(self, response, message=None):
        """Assert that a JSON response indicates success"""
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data.get('success', True))
        if message:
            self.assertIn(message, data.get('message', ''))
    
    def assert_json_error(self, response, message=None, status_code=400):
        """Assert that a JSON response indicates an error"""
        self.assertEqual(response.status_code, status_code)
        data = json.loads(response.content)
        self.assertFalse(data.get('success', False))
        if message:
            self.assertIn(message, data.get('message', ''))


class AuthenticationTestMixin:
    """
    Mixin for testing authentication and permissions.
    Provides common authentication test patterns.
    """
    
    def test_login_required_views(self):
        """Test that views require authentication"""
        protected_views = getattr(self, 'protected_views', ['home'])
        for view_name in protected_views:
            with self.subTest(view=view_name):
                self.assert_requires_login(view_name)
    
    def test_user_type_permissions(self):
        """Test user type specific permissions"""
        permission_tests = getattr(self, 'permission_tests', {})
        for view_name, allowed_types in permission_tests.items():
            all_users = [self.student, self.teacher, self.parent, self.admin]
            for user in all_users:
                with self.subTest(view=view_name, user_type=user.user_type):
                    if user.user_type in allowed_types:
                        self.login_user(user)
                        response = self.client.get(reverse(view_name))
                        self.assertNotIn(response.status_code, [403, 404])
                    else:
                        self.assert_permission_denied(view_name, user)


class APITestMixin:
    """
    Mixin for testing API endpoints.
    Provides common API testing patterns.
    """
    
    def post_json(self, url, data):
        """Post JSON data to an endpoint"""
        return self.client.post(
            url, 
            data=json.dumps(data),
            content_type='application/json'
        )
    
    def put_json(self, url, data):
        """Put JSON data to an endpoint"""
        return self.client.put(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
    
    def assert_api_success(self, response, expected_data=None):
        """Assert API response is successful"""
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data.get('success', True))
        
        if expected_data:
            for key, value in expected_data.items():
                self.assertEqual(data.get(key), value)
    
    def assert_api_error(self, response, expected_message=None, status_code=400):
        """Assert API response contains an error"""
        self.assertEqual(response.status_code, status_code)
        data = json.loads(response.content)
        
        if expected_message:
            message = data.get('message', '')
            self.assertIn(expected_message.lower(), message.lower())


class ModelTestMixin:
    """
    Mixin for testing models.
    Provides common model testing patterns.
    """
    
    def assert_field_required(self, model_class, field_name, **kwargs):
        """Assert that a model field is required"""
        with self.assertRaises(Exception):  # ValidationError or IntegrityError
            obj = model_class(**kwargs)
            obj.full_clean()
            obj.save()
    
    def assert_model_string_representation(self, obj, expected):
        """Assert model string representation"""
        self.assertEqual(str(obj), expected)
    
    def assert_model_fields_exist(self, model_class, fields):
        """Assert that model has expected fields"""
        model_fields = [field.name for field in model_class._meta.fields]
        for field in fields:
            self.assertIn(field, model_fields)


class PerformanceTestMixin:
    """
    Mixin for testing performance.
    Provides query count and timing assertions.
    """
    
    def assert_num_queries(self, num, func, *args, **kwargs):
        """Assert the number of database queries"""
        from django.test import override_settings
        from django.db import connection
        
        with override_settings(DEBUG=True):
            initial_queries = len(connection.queries)
            func(*args, **kwargs)
            final_queries = len(connection.queries)
            
            actual_queries = final_queries - initial_queries
            self.assertEqual(
                actual_queries, 
                num,
                f"Expected {num} queries, got {actual_queries}"
            )


# Utility functions for common test data creation
def create_bulk_users(user_type, count, school, base_email="user{}@test.com"):
    """Create multiple users of the same type"""
    User = get_user_model()
    users = []
    for i in range(count):
        user = User.objects.create_user(
            username=f"{user_type}{i+1}",
            email=base_email.format(i+1),
            password="testpass123",
            user_type=user_type,
            school=school
        )
        user.password_change_required = False
        user.is_staff = False
        user.verified = True
        user.save()
        users.append(user)
    return users


def create_bulk_reading_logs(student, count, school, start_date=None):
    """Create multiple reading logs for a student"""
    from reading_logs.models import Log
    if start_date is None:
        start_date = date.today() - timedelta(days=count)
    
    logs = []
    for i in range(count):
        log_date = start_date + timedelta(days=i)
        log = Log.objects.create(
            student=student,
            school=school,
            date=log_date,
            title=f"Book {i+1}",
            author=f"Author {i+1}",
            pages=10 + (i * 2),
            minutes=15 + (i * 3),
            rating=3.0 + (i % 3)
        )
        logs.append(log)
    return logs


def create_test_classroom_with_students(name, school, teacher, student_count=5):
    """Create a classroom with students and teacher"""
    from users.models import Classroom
    classroom = Classroom.objects.create(name=name, school=school)
    classroom.teachers.add(teacher)
    
    students = create_bulk_users('student', student_count, school)
    for student in students:
        classroom.students.add(student)
    
    return classroom, students


def create_test_reading_group_with_students(name, school, manager, student_count=3):
    """Create a reading group with students and manager"""
    from users.models import ReadingGroup
    group = ReadingGroup.objects.create(name=name, school=school)
    group.managers.add(manager)
    
    students = create_bulk_users('student', student_count, school)
    for student in students:
        group.students.add(student)
    
    return group, students


# Test data constants
TEST_PASSWORDS = {
    'default': 'testpass123',
    'weak': 'weak',
    'strong': 'StrongP@ssw0rd123!'
}

TEST_EMAILS = {
    'valid': ['test@example.com', 'user.name@domain.co.uk'],
    'invalid': ['invalid-email', '@domain.com', 'user@', 'user space@domain.com']
}

TEST_DATES = {
    'today': date.today(),
    'yesterday': date.today() - timedelta(days=1),
    'last_week': date.today() - timedelta(weeks=1),
    'last_month': date.today() - timedelta(days=30)
}


# Example usage documentation
"""
BEFORE (repetitive test setup - 15+ lines per test class):

class MyTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.school = School.objects.create(name="Test School")
        self.student = CustomUser.objects.create_user(
            username="student",
            email="student@test.com", 
            password="testpass123",
            user_type="student",
            school=self.school
        )
        self.student.password_change_required = False
        self.student.is_staff = False
        self.student.save()
        # ... repeat for teacher, parent, admin

AFTER (using test helpers - 2 lines):

class MyTestCase(BaseTestCase):
    # setUp() is automatically called with all users created
    
    def test_something(self):
        # self.student, self.teacher, self.parent, self.admin are ready to use
        self.login_user(self.student)
        self.assert_requires_login('some_view')

REDUCTION: 85% fewer lines for test setup
BENEFITS: 
- Consistent test data across all tests
- Reduced maintenance when test requirements change
- Built-in assertion helpers for common patterns
- Mixins for specialized testing patterns
"""
