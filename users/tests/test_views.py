"""
Test user views and authentication
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from ..models import School, CustomUser, Classroom, ReadingGroup
from read.utils.test_helpers import BaseTestCase

User = get_user_model()


class AuthenticationTests(BaseTestCase):
    """Test authentication and permissions"""
    
    def test_login_required_views(self):
        """Test that views require authentication"""
        # Test without login
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_student_home_redirect(self):
        """Test student dashboard loads correctly"""
        self.client.login(username="student@test.com", password="testpass123")
        
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Quick Reading Log')
    
    def test_teacher_home_redirect(self):
        """Test teacher dashboard loads correctly"""
        self.client.login(username="teacher@test.com", password="testpass123")
        
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dashboard')
    
    def test_admin_home_redirect(self):
        """Test admin dashboard loads correctly"""
        self.client.login(username="admin@test.com", password="testpass123")
        
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Administrator Dashboard')
    
    def test_user_type_restrictions(self):
        """Test that user types are properly restricted"""
        # Student should access student APIs
        self.client.login(username="student@test.com", password="testpass123")
        
        response = self.client.get('/reading_logs/api/student/progress/')
        self.assertEqual(response.status_code, 200)
        
        # Student should NOT access parent APIs
        response = self.client.get('/reading_logs/api/parent/dashboard/')
        self.assertNotEqual(response.status_code, 200)


class UserManagementTests(TestCase):
    """Test user management functionality"""
    
    def setUp(self):
        self.client = Client()
        self.school = School.objects.create(name="Test School")
        
        self.teacher = CustomUser.objects.create_user(
            username="teacher",
            email="teacher@test.com",
            password="testpass123",
            user_type="teacher",
            school=self.school
        )
        self.teacher.password_change_required = False
        self.teacher.is_staff = False
        self.teacher.save()
    
    def test_user_list_view(self):
        """Test user list page loads"""
        self.client.login(username="teacher@test.com", password="testpass123")
        
        response = self.client.get(reverse('user_list_page', kwargs={'user_type': 'student'}))
        self.assertEqual(response.status_code, 200)
    
    def test_classroom_management(self):
        """Test classroom views"""
        self.client.login(username="teacher@test.com", password="testpass123")
        
        response = self.client.get(reverse('classrooms'))
        self.assertEqual(response.status_code, 200)
    
    def test_reading_group_management(self):
        """Test reading group views"""
        self.client.login(username="teacher@test.com", password="testpass123")
        
        response = self.client.get(reverse('reading_groups'))
        self.assertEqual(response.status_code, 200)


class ClassroomAPITests(TestCase):
    """Test classroom API functionality"""
    
    def setUp(self):
        self.client = Client()
        self.school = School.objects.create(name="Test School")
        
        self.teacher = CustomUser.objects.create_user(
            username="teacher",
            email="teacher@test.com",
            password="testpass123",
            user_type="teacher",
            school=self.school
        )
        self.teacher.password_change_required = False
        self.teacher.is_staff = False
        self.teacher.save()
        
        self.student = CustomUser.objects.create_user(
            username="student",
            email="student@test.com",
            password="studentpass123",
            user_type="student",
            school=self.school
        )
        self.student.password_change_required = False
        self.student.is_staff = False
        self.student.save()
    
    def test_get_classrooms(self):
        """Test getting classrooms list"""
        self.client.login(username="teacher@test.com", password="testpass123")
        
        # Create a classroom
        classroom = Classroom.objects.create(
            name="Test Classroom",
            school=self.school
        )
        classroom.teachers.add(self.teacher)
        
        response = self.client.get('/api/classrooms/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'Test Classroom')


class DataIntegrityTests(TestCase):
    """Test data integrity and constraints"""
    
    def setUp(self):
        self.school = School.objects.create(name="Test School")
    
    def test_unique_email_constraint(self):
        """Test that email addresses must be unique"""
        CustomUser.objects.create(
            username="user1",
            email="same@test.com",
            user_type="student"
        )
        
        # Should raise an error for duplicate email
        with self.assertRaises(Exception):
            CustomUser.objects.create(
                username="user2", 
                email="same@test.com",
                user_type="teacher"
            )
    
    def test_user_school_consistency(self):
        """Test user-school relationship consistency"""
        user = CustomUser.objects.create(
            username="testuser",
            email="test@test.com",
            user_type="student",
            school=self.school
        )
        
        self.assertEqual(user.school, self.school)
        
        # Test auto-school creation
        user2 = CustomUser.objects.create(
            username="testuser2",
            email="test2@test.com",
            user_type="student"
        )
        
        self.assertIsNotNone(user2.school)
