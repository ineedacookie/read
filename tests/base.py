"""
Base test classes for the project.
Provides common setup and utilities for consistent testing.
"""

from django.test import TestCase, Client, TransactionTestCase
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from users.models import School, Classroom, ReadingGroup, StudentParentRelation
from reading_logs.models import Log, DailyGoal, TotalGoal
from datetime import date, timedelta
import json

User = get_user_model()


class BaseTestCase(TestCase):
    """
    Base test case with common setup for all tests.
    Provides fixtures for users, school, and basic data.
    """
    
    def setUp(self):
        """Create basic test data"""
        self.school = School.objects.create(name="Test School")
        self.create_users()
    
    def create_users(self):
        """Create test users of each type"""
        self.admin = User.objects.create_user(
            username="admin@test.com",
            email="admin@test.com",
            password="testpass123",
            user_type="administrator",
            school=self.school,
            first_name="Admin",
            last_initial="A"
        )
        
        self.teacher = User.objects.create_user(
            username="teacher@test.com",
            email="teacher@test.com",
            password="testpass123",
            user_type="teacher",
            school=self.school,
            first_name="Teacher",
            last_initial="T"
        )
        
        self.student = User.objects.create_user(
            username="student@test.com",
            email="student@test.com",
            password="testpass123",
            user_type="student",
            school=self.school,
            first_name="Student",
            last_initial="S"
        )
        
        self.parent = User.objects.create_user(
            username="parent@test.com",
            email="parent@test.com",
            password="testpass123",
            user_type="parent",
            school=self.school,
            first_name="Parent",
            last_initial="P"
        )
        
        # Create parent-student relationship
        StudentParentRelation.objects.create(
            student=self.student,
            parent=self.parent,
            school=self.school
        )
    
    def create_classroom(self, name="Test Class", students=None, teachers=None):
        """Helper to create a classroom with students and teachers"""
        classroom = Classroom.objects.create(
            name=name,
            school=self.school,
            created_by=self.admin
        )
        
        if teachers is None:
            teachers = [self.teacher]
        classroom.teachers.set(teachers)
        
        if students:
            classroom.students.set(students)
        
        return classroom
    
    def create_reading_group(self, name="Test Group", students=None, managers=None):
        """Helper to create a reading group"""
        reading_group = ReadingGroup.objects.create(
            name=name,
            school=self.school,
            created_by=self.admin
        )
        
        if managers is None:
            managers = [self.teacher]
        reading_group.managers.set(managers)
        
        if students:
            reading_group.students.set(students)
        
        return reading_group
    
    def create_student(self, username=None, first_name=None):
        """Helper to create an additional student"""
        if username is None:
            import uuid
            username = f"student_{uuid.uuid4().hex[:8]}@test.com"
        
        if first_name is None:
            first_name = username.split('@')[0]
        
        return User.objects.create_user(
            username=username,
            email=username,
            password="testpass123",
            user_type="student",
            school=self.school,
            first_name=first_name,
            last_initial="S"
        )
    
    def create_log(self, student=None, **kwargs):
        """Helper to create a reading log"""
        if student is None:
            student = self.student
        
        defaults = {
            'student': student,
            'school': self.school,
            'date': date.today(),
            'pages': 10,
            'minutes': 30
        }
        defaults.update(kwargs)
        
        return Log.objects.create(**defaults)
    
    def create_daily_goal(self, student=None, goal_type='pages', value=20):
        """Helper to create a daily goal"""
        if student is None:
            student = self.student
        
        return DailyGoal.objects.create(
            student=student,
            school=self.school,
            type=goal_type,
            value=value
        )
    
    def create_total_goal(self, student=None, start=None, end=None, total=100):
        """Helper to create a total goal"""
        if student is None:
            student = self.student
        
        if start is None:
            start = date.today()
        if end is None:
            end = start + timedelta(days=30)
        
        return TotalGoal.objects.create(
            student=student,
            school=self.school,
            start=start,
            end=end,
            total=total
        )


class APITestCase(BaseTestCase):
    """
    Base class for API endpoint tests.
    Includes HTTP client and helpers for API testing.
    """
    
    def setUp(self):
        super().setUp()
        self.client = Client()
    
    def api_get(self, url, user=None, **params):
        """
        Helper for GET requests.
        
        Args:
            url: API endpoint URL
            user: User to authenticate as (optional)
            **params: Query parameters
            
        Returns:
            Response object
        """
        if user:
            self.client.force_login(user)
        return self.client.get(url, params)
    
    def api_post(self, url, user=None, data=None):
        """
        Helper for POST requests with JSON data.
        
        Args:
            url: API endpoint URL
            user: User to authenticate as (optional)
            data: Dict to send as JSON
            
        Returns:
            Response object
        """
        if user:
            self.client.force_login(user)
        return self.client.post(
            url,
            data=json.dumps(data) if data else None,
            content_type='application/json'
        )
    
    def api_put(self, url, user=None, data=None):
        """Helper for PUT requests"""
        if user:
            self.client.force_login(user)
        return self.client.put(
            url,
            data=json.dumps(data) if data else None,
            content_type='application/json'
        )
    
    def api_delete(self, url, user=None, data=None):
        """Helper for DELETE requests"""
        if user:
            self.client.force_login(user)
        return self.client.delete(
            url,
            data=json.dumps(data) if data else None,
            content_type='application/json'
        )
    
    def assertJSONSuccess(self, response, msg=None):
        """Assert response is successful JSON"""
        self.assertEqual(response.status_code, 200, msg)
        data = json.loads(response.content)
        self.assertIn('status', data)
        self.assertEqual(data['status'], 'success', msg or data.get('message'))
        return data
    
    def assertJSONError(self, response, expected_status=400, msg=None):
        """Assert response is an error"""
        self.assertEqual(response.status_code, expected_status, msg)
        data = json.loads(response.content)
        self.assertIn('status', data)
        self.assertEqual(data['status'], 'error')
        return data
    
    def assertQueryCountLessThan(self, max_queries, func, *args, **kwargs):
        """
        Assert function uses fewer than max queries.
        
        Args:
            max_queries: Maximum number of queries allowed
            func: Function to call
            *args, **kwargs: Arguments to pass to function
        """
        with CaptureQueriesContext(connection) as context:
            result = func(*args, **kwargs)
        
        query_count = len(context.captured_queries)
        self.assertLessEqual(
            query_count,
            max_queries,
            f"Expected ≤{max_queries} queries, got {query_count}. "
            f"Queries: {[q['sql'] for q in context.captured_queries]}"
        )
        return result
    
    def assertQueryCount(self, expected_count, func, *args, **kwargs):
        """Assert exact query count"""
        with CaptureQueriesContext(connection) as context:
            result = func(*args, **kwargs)
        
        query_count = len(context.captured_queries)
        self.assertEqual(
            query_count,
            expected_count,
            f"Expected exactly {expected_count} queries, got {query_count}"
        )
        return result


class PerformanceTestCase(APITestCase):
    """
    Base class for performance tests.
    Includes helpers for testing query counts and response times.
    """
    
    # Override these in subclasses
    MAX_QUERIES = 10  # Maximum queries allowed
    MAX_RESPONSE_TIME = 1.0  # Maximum response time in seconds
    
    def assertPerformance(self, func, max_queries=None, max_time=None):
        """
        Assert function meets performance requirements.
        
        Args:
            func: Function to test
            max_queries: Max queries (default: self.MAX_QUERIES)
            max_time: Max time in seconds (default: self.MAX_RESPONSE_TIME)
        """
        import time
        
        if max_queries is None:
            max_queries = self.MAX_QUERIES
        if max_time is None:
            max_time = self.MAX_RESPONSE_TIME
        
        with CaptureQueriesContext(connection) as context:
            start_time = time.time()
            result = func()
            elapsed_time = time.time() - start_time
        
        query_count = len(context.captured_queries)
        
        # Assert query count
        self.assertLessEqual(
            query_count,
            max_queries,
            f"Too many queries: {query_count} > {max_queries}"
        )
        
        # Assert response time
        self.assertLessEqual(
            elapsed_time,
            max_time,
            f"Too slow: {elapsed_time:.2f}s > {max_time}s"
        )
        
        return result
    
    def create_bulk_test_data(self, num_students=10, logs_per_student=5):
        """
        Create bulk test data for performance testing.
        
        Args:
            num_students: Number of students to create
            logs_per_student: Number of logs per student
            
        Returns:
            tuple: (classroom, students list, logs list)
        """
        students = []
        for i in range(num_students):
            student = self.create_student(
                username=f"student{i}@test.com",
                first_name=f"Student{i}"
            )
            students.append(student)
        
        classroom = self.create_classroom(
            name="Performance Test Class",
            students=students
        )
        
        logs = []
        for student in students:
            for j in range(logs_per_student):
                log = self.create_log(
                    student=student,
                    date=date.today() - timedelta(days=j),
                    pages=10 + j,
                    minutes=20 + j
                )
                logs.append(log)
        
        return classroom, students, logs


class IntegrationTestCase(TransactionTestCase):
    """
    Base class for integration tests that need to test transactions.
    Use this sparingly as TransactionTestCase is slower than TestCase.
    """
    
    def setUp(self):
        """Set up integration test data"""
        self.school = School.objects.create(name="Integration Test School")
        self.admin = User.objects.create_user(
            username="admin@integration.com",
            email="admin@integration.com",
            password="testpass123",
            user_type="administrator",
            school=self.school
        )


