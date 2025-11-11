"""
Test Phase 1 API endpoints
"""
import json
from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.test.utils import override_settings

from ..models import Log, DailyGoal
from users.models import Classroom, School, CustomUser, StudentParentRelation

User = get_user_model()


class StudentAPITests(TestCase):
    """Test student-specific API endpoints"""
    
    @classmethod
    def setUpTestData(cls):
        """Set up data once for all tests in this class - OPTIMIZED"""
        cls.school = School.objects.create(name="Test School")
        
        cls.student = CustomUser.objects.create(
            username="teststudent",
            email="student@test.com",
            user_type="student",
            school=cls.school,
            first_name="Test",
            last_initial="S"
        )
        cls.student.set_password("testpass123")
        cls.student.save()
        
        cls.teacher = CustomUser.objects.create(
            username="testteacher",
            email="teacher@test.com",
            user_type="teacher",
            school=cls.school
        )
        cls.teacher.set_password("testpass123")
        cls.teacher.save()
    
    def setUp(self):
        """Per-test setup - only create client"""
        self.client = Client()
    
    def test_student_quick_log_success(self):
        """Test successful log creation via API"""
        # Use email for login since that's the USERNAME_FIELD
        self.client.login(username="student@test.com", password="testpass123")
        
        data = {
            "title": "Test Book",
            "author": "Test Author",
            "pages": 25,
            "minutes": 30,
            "rating": 4.5,
            "comments": "Great book!"
        }
        
        response = self.client.post(
            reverse('student_quick_log'),
            json.dumps(data),
            content_type='application/json'
        )
        
        # API returns 201 Created for successful log creation
        self.assertEqual(response.status_code, 201)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['status'], 'success')
        self.assertIn('log_id', response_data)
        
        # Verify log was created
        log = Log.objects.get(id=response_data['log_id'])
        self.assertEqual(log.student, self.student)
        self.assertEqual(log.title, "Test Book")
        self.assertEqual(log.pages, 25)
        self.assertEqual(log.minutes, 30)
        self.assertEqual(float(log.rating), 4.5)
    
    def test_student_quick_log_validation(self):
        """Test input validation in quick log API"""
        self.client.login(username="student@test.com", password="testpass123")
        
        # Test negative pages
        data = {"pages": -5}
        response = self.client.post(
            reverse('student_quick_log'),
            json.dumps(data),
            content_type='application/json'
        )
        response_data = json.loads(response.content)
        self.assertEqual(response_data['status'], 'error')
        # Validation message changed to be more specific
        self.assertIn('at least', response_data['message'].lower())
        
        # Test invalid rating
        data = {"rating": 6}
        response = self.client.post(
            reverse('student_quick_log'),
            json.dumps(data),
            content_type='application/json'
        )
        response_data = json.loads(response.content)
        self.assertEqual(response_data['status'], 'error')
        # Error message updated to include 0
        self.assertIn('between 0 and 5', response_data['message'].lower())
    
    def test_student_quick_log_permissions(self):
        """Test that only students can create logs"""
        self.client.login(username="teacher@test.com", password="testpass123")
        
        data = {"title": "Test Book"}
        response = self.client.post(
            reverse('student_quick_log'),
            json.dumps(data),
            content_type='application/json'
        )
        
        # @require_user_types decorator raises PermissionDenied (403)
        self.assertEqual(response.status_code, 403)
    
    def test_student_progress_api(self):
        """Test student progress API"""
        self.client.login(username="student@test.com", password="testpass123")
        
        # Create some logs
        Log.objects.create(
            student=self.student,
            date=date.today(),
            pages=20,
            minutes=25,
            rating=Decimal("4.0")
        )
        Log.objects.create(
            student=self.student,
            date=date.today() - timedelta(days=1),
            pages=15,
            minutes=20,
            rating=Decimal("3.5")
        )
        
        response = self.client.get(reverse('student_progress'))
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['stats']['total_pages'], 35)
        self.assertEqual(data['stats']['total_minutes'], 45)
        self.assertEqual(data['stats']['total_logs'], 2)
        self.assertEqual(float(data['stats']['avg_rating']), 3.75)
    
    def test_student_progress_permissions(self):
        """Test student progress API permissions"""
        self.client.login(username="teacher@test.com", password="testpass123")
        
        response = self.client.get(reverse('student_progress'))
        
        response_data = json.loads(response.content)
        self.assertEqual(response_data['status'], 'error')
        self.assertIn('Student ID required', response_data['message'])


class ParentAPITests(TestCase):
    """Test parent dashboard API functionality"""
    
    @classmethod
    def setUpTestData(cls):
        """Set up data once for all tests in this class - OPTIMIZED"""
        cls.school = School.objects.create(name="Test School")
        
        cls.parent = CustomUser.objects.create(
            username="testparent",
            email="parent@test.com",
            user_type="parent",
            school=cls.school
        )
        cls.parent.set_password("testpass123")
        cls.parent.save()
        
        cls.student1 = CustomUser.objects.create(
            username="student1",
            email="student1@test.com",
            user_type="student",
            school=cls.school,
            first_name="Student",
            last_initial="A"
        )
        
        cls.student2 = CustomUser.objects.create(
            username="student2",
            email="student2@test.com",
            user_type="student",
            school=cls.school,
            first_name="Student",
            last_initial="B"
        )
        
        # Create parent-child relationships
        StudentParentRelation.objects.create(
            school=cls.school,
            parent=cls.parent,
            student=cls.student1
        )
        StudentParentRelation.objects.create(
            school=cls.school,
            parent=cls.parent,
            student=cls.student2
        )
    
    def setUp(self):
        """Per-test setup - only create client"""
        self.client = Client()
    
    def test_parent_dashboard_success(self):
        """Test parent dashboard API with children data"""
        self.client.login(username="parent@test.com", password="testpass123")
        
        # Create logs for children
        Log.objects.create(
            student=self.student1,
            date=date.today(),
            pages=20,
            minutes=30,
            rating=Decimal("4.0")
        )
        Log.objects.create(
            student=self.student2,
            date=date.today(),
            pages=15,
            minutes=25,
            rating=Decimal("3.5")
        )
        
        response = self.client.get(reverse('parent_dashboard'))
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(len(data['children']), 2)
        
        # Check child data structure
        child_data = data['children'][0]
        self.assertIn('id', child_data)
        self.assertIn('name', child_data)
        self.assertIn('stats', child_data)
        self.assertIn('recent_logs', child_data)
    
    def test_parent_dashboard_permissions(self):
        """Test parent dashboard API permissions"""
        # Test with non-parent user
        student = CustomUser.objects.create(
            username="testuser",
            email="user@test.com",
            user_type="student",
            school=self.school
        )
        student.set_password("testpass123")
        student.save()
        
        self.client.login(username="user@test.com", password="testpass123")
        
        response = self.client.get(reverse('parent_dashboard'))
        response_data = json.loads(response.content)
        self.assertEqual(response_data['status'], 'error')
        self.assertIn('Access denied', response_data['message'])
    
    def test_parent_dashboard_date_filtering(self):
        """Test parent dashboard with date range filtering"""
        self.client.login(username="parent@test.com", password="testpass123")
        
        # Create logs on different dates
        Log.objects.create(
            student=self.student1,
            date=date.today(),
            pages=20
        )
        Log.objects.create(
            student=self.student1,
            date=date.today() - timedelta(days=10),
            pages=15
        )
        
        # Test with date range
        start_date = date.today().strftime('%Y-%m-%d')
        end_date = date.today().strftime('%Y-%m-%d')
        
        response = self.client.get(
            reverse('parent_dashboard'),
            {'start_date': start_date, 'end_date': end_date}
        )
        
        data = json.loads(response.content)
        child_stats = data['children'][0]['stats']
        
        # Should only include today's log
        self.assertEqual(child_stats['total_pages'], 20)
        self.assertEqual(child_stats['total_logs'], 1)


class CalendarApiTests(TestCase):
    """Test calendar-centric log endpoints"""

    @classmethod
    def setUpTestData(cls):
        cls.school = School.objects.create(name="Calendar School")

        cls.teacher = CustomUser.objects.create(
            username="calendar_teacher",
            email="calendar_teacher@test.com",
            user_type="teacher",
            school=cls.school
        )
        cls.teacher.set_password("testpass123")
        cls.teacher.save()

        cls.student = CustomUser.objects.create(
            username="calendar_student",
            email="calendar_student@test.com",
            user_type="student",
            school=cls.school,
            first_name="Calendar",
            last_initial="S"
        )

        cls.classroom = Classroom.objects.create(
            name="Calendar Room",
            school=cls.school,
            created_by=cls.teacher
        )
        cls.classroom.teachers.add(cls.teacher)
        cls.classroom.students.add(cls.student)

        cls.existing_log = Log.objects.create(
            student=cls.student,
            school=cls.school,
            date=date.today(),
            title="Existing Entry",
            pages=10,
            minutes=15
        )

    def setUp(self):
        self.client = Client()
        self.client.login(username="calendar_teacher@test.com", password="testpass123")

    def test_calendar_logs_fetch_student(self):
        """Teachers can fetch student logs via calendar endpoint"""
        response = self.client.get(
            reverse('calendar_logs'),
            {
                'start': date.today().strftime('%Y-%m-%d'),
                'end': date.today().strftime('%Y-%m-%d'),
                'id': self.student.id,
                'form_name': 'Student'
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(len(data['logs']), 1)
        self.assertEqual(data['logs'][0]['id'], self.existing_log.id)

    def test_calendar_logs_create_student(self):
        """Teachers can create logs for accessible students via calendar API"""
        payload = {
            'student_id': self.student.id,
            'date': date.today().strftime('%Y-%m-%d'),
            'title': 'Calendar Created',
            'pages': 12,
            'minutes': 20,
            'comments': 'Created from calendar endpoint'
        }

        response = self.client.post(
            reverse('calendar_logs'),
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')
        self.assertIn('log_id', data)
        self.assertTrue(Log.objects.filter(id=data['log_id']).exists())

    def test_calendar_log_delete_student(self):
        """Teachers can delete logs via calendar detail endpoint"""
        log = Log.objects.create(
            student=self.student,
            school=self.school,
            date=date.today(),
            title="Delete Me"
        )

        response = self.client.delete(
            reverse('calendar_log_detail', args=[log.id]),
            data=json.dumps({'student_id': self.student.id}),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')
        self.assertFalse(Log.objects.filter(id=log.id).exists())
