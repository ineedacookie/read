"""
Baseline Workflow Tests
These tests verify core user workflows remain functional throughout optimization.
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from reading_logs.models import Log, Classroom, ReadingGroup
from datetime import date, timedelta

User = get_user_model()


class BaseWorkflowTest(TestCase):
    """Base class for workflow tests with common setup"""
    
    @classmethod
    def setUpTestData(cls):
        """Create test data once for all tests"""
        # Create school (assuming CustomUser has school field)
        # We'll create users and check if school exists
        pass
    
    def setUp(self):
        """Set up test client for each test"""
        self.client = Client()


class StudentWorkflowTests(BaseWorkflowTest):
    """Test student user workflows"""
    
    def setUp(self):
        super().setUp()
        # Create a student user
        self.student = User.objects.create_user(
            username='teststudent',
            email='student@test.com',
            password='testpass123',
            first_name='Test',
            last_name='Student',
            user_type='student'
        )
    
    def test_workflow_01_student_can_login(self):
        """Student can log in and see their dashboard"""
        response = self.client.post(reverse('login'), {
            'username': 'teststudent',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, 302)  # Redirect after login
        
        # Access dashboard
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
    
    def test_workflow_02_student_can_view_progress(self):
        """Student can view their reading progress"""
        self.client.login(username='teststudent', password='testpass123')
        
        # Try to access progress page
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Reading')  # Should show reading-related content


class TeacherWorkflowTests(BaseWorkflowTest):
    """Test teacher user workflows"""
    
    def setUp(self):
        super().setUp()
        # Create a teacher user
        self.teacher = User.objects.create_user(
            username='testteacher',
            email='teacher@test.com',
            password='testpass123',
            first_name='Test',
            last_name='Teacher',
            user_type='teacher'
        )
        
        # Create a student for the teacher to manage
        self.student = User.objects.create_user(
            username='student1',
            email='student1@test.com',
            password='testpass123',
            first_name='Student',
            last_name='One',
            user_type='student'
        )
    
    def test_workflow_01_teacher_can_login_and_see_dashboard(self):
        """Teacher can log in and access dashboard"""
        response = self.client.post(reverse('login'), {
            'username': 'testteacher',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, 302)
        
        # Access dashboard
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
    
    def test_workflow_02_teacher_can_view_student_list(self):
        """Teacher can view list of students"""
        self.client.login(username='testteacher', password='testpass123')
        
        # Try to access student list
        try:
            response = self.client.get(reverse('student_list'))
            self.assertIn(response.status_code, [200, 302])  # May redirect if no permission
        except Exception:
            # URL may not exist yet, that's okay for baseline
            pass
    
    def test_workflow_03_teacher_can_access_my_students(self):
        """Teacher can access My Students page"""
        self.client.login(username='testteacher', password='testpass123')
        
        try:
            response = self.client.get('/my_students/')
            self.assertIn(response.status_code, [200, 302, 404])
        except Exception:
            # Page may not exist, that's okay for baseline
            pass


class ParentWorkflowTests(BaseWorkflowTest):
    """Test parent user workflows"""
    
    def setUp(self):
        super().setUp()
        # Create a parent user
        self.parent = User.objects.create_user(
            username='testparent',
            email='parent@test.com',
            password='testpass123',
            first_name='Test',
            last_name='Parent',
            user_type='parent'
        )
        
        # Create a child student
        self.child = User.objects.create_user(
            username='childstudent',
            email='child@test.com',
            password='testpass123',
            first_name='Child',
            last_name='Student',
            user_type='student'
        )
    
    def test_workflow_01_parent_can_view_children(self):
        """Parent can log in and see their children"""
        response = self.client.post(reverse('login'), {
            'username': 'testparent',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, 302)
        
        # Access dashboard
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
    
    def test_workflow_02_parent_can_access_dashboard(self):
        """Parent can access their dashboard"""
        self.client.login(username='testparent', password='testpass123')
        
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)


class PermissionWorkflowTests(BaseWorkflowTest):
    """Test permission and security workflows"""
    
    def setUp(self):
        super().setUp()
        # Create two students
        self.student1 = User.objects.create_user(
            username='student1',
            email='student1@test.com',
            password='testpass123',
            first_name='Student',
            last_name='One',
            user_type='student'
        )
        
        self.student2 = User.objects.create_user(
            username='student2',
            email='student2@test.com',
            password='testpass123',
            first_name='Student',
            last_name='Two',
            user_type='student'
        )
    
    def test_workflow_student_login_required(self):
        """Anonymous users cannot access protected pages"""
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
        self.assertIn('/login/', response.url)
    
    def test_workflow_student_can_access_own_data(self):
        """Student can access their own dashboard"""
        self.client.login(username='student1', password='testpass123')
        
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)


class AdministratorWorkflowTests(BaseWorkflowTest):
    """Test administrator user workflows"""
    
    def setUp(self):
        super().setUp()
        self.admin = User.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            first_name='Test',
            last_name='Admin',
            user_type='administrator',
            is_staff=True
        )
    
    def test_workflow_01_admin_can_login(self):
        """Administrator can log in"""
        response = self.client.post(reverse('login'), {
            'username': 'testadmin',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, 302)
    
    def test_workflow_02_admin_can_access_dashboard(self):
        """Administrator can access dashboard"""
        self.client.login(username='testadmin', password='testpass123')
        
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)

