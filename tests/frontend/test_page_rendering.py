"""
Frontend integration tests - verify pages render correctly
Tests templates, static files, and basic JavaScript loading
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from datetime import date

from users.models import School, Classroom, ReadingGroup
from reading_logs.models import Log

User = get_user_model()


class FrontendPageRenderingTests(TestCase):
    """Test that all major pages render without errors"""
    
    @classmethod
    def setUpTestData(cls):
        """Create test data for all user types"""
        cls.school = School.objects.create(name="Test School")
        
        # Create users
        cls.teacher = User.objects.create_user(
            username="teacher",
            email="teacher@test.com",
            password="testpass123",
            user_type='teacher',
            school=cls.school,
            first_name="Test",
            last_initial="T"
        )
        
        cls.student = User.objects.create_user(
            username="student",
            email="student@test.com",
            password="testpass123",
            user_type='student',
            school=cls.school,
            first_name="Test",
            last_initial="S"
        )
        
        cls.parent = User.objects.create_user(
            username="parent",
            email="parent@test.com",
            password="testpass123",
            user_type='parent',
            school=cls.school,
            first_name="Test",
            last_initial="P"
        )
        
        cls.admin = User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="testpass123",
            user_type='administrator',
            school=cls.school,
            first_name="Admin",
            last_initial="A"
        )
        
        # Create classroom
        cls.classroom = Classroom.objects.create(
            name="Test Class",
            school=cls.school,
            created_by=cls.teacher
        )
        cls.classroom.teachers.add(cls.teacher)
        cls.classroom.students.add(cls.student)
        
        # Create some logs
        for i in range(5):
            Log.objects.create(
                student=cls.student,
                school=cls.school,
                date=date.today(),
                title=f"Book {i}",
                pages=50,
                minutes=30
            )
    
    def test_teacher_dashboard_renders(self):
        """Teacher dashboard should render with all elements"""
        self.client.force_login(self.teacher)
        response = self.client.get('/')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Active Readers')  # Stat card
        self.assertContains(response, 'dashboard-manager.js', msg_prefix="Dashboard manager should be loaded")
        self.assertContains(response, 'chart-builder.js', msg_prefix="Chart builder should be loaded")
    
    def test_student_dashboard_renders(self):
        """Student dashboard should render correctly"""
        self.client.force_login(self.student)
        response = self.client.get('/')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'My Reading Progress')
    
    def test_parent_dashboard_renders(self):
        """Parent dashboard should render correctly"""
        self.client.force_login(self.parent)
        response = self.client.get('/')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Children')
    
    def test_my_students_page_renders(self):
        """My students page should render with table"""
        self.client.force_login(self.teacher)
        response = self.client.get('/my_students/')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'My Students')
        self.assertContains(response, self.student.email)
    
    def test_my_classrooms_page_renders(self):
        """My classrooms page should render"""
        self.client.force_login(self.teacher)
        response = self.client.get('/my_classrooms/')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'My Classrooms')
        self.assertContains(response, self.classroom.name)
    
    def test_static_files_referenced(self):
        """Verify static files are properly referenced"""
        self.client.force_login(self.teacher)
        response = self.client.get('/')
        
        # Check for CSS
        self.assertContains(response, 'user.css')
        self.assertContains(response, 'theme.css')
        
        # Check for JS
        self.assertContains(response, 'theme.js')
    
    def test_navigation_links_present(self):
        """Navigation should have correct links for user type"""
        self.client.force_login(self.teacher)
        response = self.client.get('/')
        
        self.assertContains(response, 'My Students')
        self.assertContains(response, 'My Classrooms')
    
    def test_forms_render_with_csrf(self):
        """Forms should include CSRF token"""
        self.client.force_login(self.student)
        response = self.client.get('/')
        
        self.assertContains(response, 'csrfmiddlewaretoken')
    
    def test_error_pages_render(self):
        """Test custom error pages if they exist"""
        # Test 404
        response = self.client.get('/nonexistent-page/')
        self.assertEqual(response.status_code, 404)
    
    def test_responsive_meta_tags(self):
        """Check for responsive design meta tags"""
        self.client.force_login(self.teacher)
        response = self.client.get('/')
        
        self.assertContains(response, 'viewport')


class FrontendAPIEndpointTests(TestCase):
    """Test that frontend can properly call API endpoints"""
    
    @classmethod
    def setUpTestData(cls):
        """Create test data"""
        cls.school = School.objects.create(name="Test School")
        
        cls.teacher = User.objects.create_user(
            username="teacher",
            email="teacher@test.com",
            password="testpass123",
            user_type='teacher',
            school=cls.school,
            first_name="Test",
            last_initial="T"
        )
        
        cls.student = User.objects.create_user(
            username="student",
            email="student@test.com",
            password="testpass123",
            user_type='student',
            school=cls.school,
            first_name="Test",
            last_initial="S"
        )
        
        # Create some test data
        for i in range(10):
            Log.objects.create(
                student=cls.student,
                school=cls.school,
                date=date.today(),
                title=f"Book {i}",
                pages=50,
                minutes=30
            )
    
    def test_leaderboard_api_returns_json(self):
        """Leaderboard API should return valid JSON"""
        self.client.force_login(self.teacher)
        response = self.client.get('/reading_logs/api/gamification/leaderboard/?scope=school')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('data', data)
    
    def test_student_progress_api_returns_json(self):
        """Student progress API should return valid JSON"""
        self.client.force_login(self.student)
        response = self.client.get('/reading_logs/api/student/progress/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
    
    def test_api_handles_invalid_params(self):
        """API should handle invalid parameters gracefully"""
        self.client.force_login(self.teacher)
        response = self.client.get('/reading_logs/api/gamification/leaderboard/?scope=invalid')
        
        # Should not crash
        self.assertIn(response.status_code, [200, 400])


class FrontendJavaScriptLoadingTests(TestCase):
    """Test that JavaScript modules load correctly"""
    
    def setUp(self):
        self.school = School.objects.create(name="Test School")
        self.teacher = User.objects.create_user(
            username="teacher",
            email="teacher@test.com",
            password="testpass123",
            user_type='teacher',
            school=self.school,
            first_name="Test",
            last_initial="T"
        )
    
    def test_dashboard_manager_module_loads(self):
        """Dashboard manager JavaScript should be included"""
        self.client.force_login(self.teacher)
        response = self.client.get('/')
        
        self.assertContains(response, 'dashboard-manager.js')
    
    def test_chart_builder_module_loads(self):
        """Chart builder JavaScript should be included"""
        self.client.force_login(self.teacher)
        response = self.client.get('/')
        
        self.assertContains(response, 'chart-builder.js')
    
    def test_utility_scripts_load(self):
        """Utility scripts should be loaded"""
        self.client.force_login(self.teacher)
        response = self.client.get('/')
        
        self.assertContains(response, 'theme.js')


class FrontendAccessControlTests(TestCase):
    """Test that frontend properly enforces access control"""
    
    @classmethod
    def setUpTestData(cls):
        cls.school = School.objects.create(name="Test School")
        
        cls.teacher = User.objects.create_user(
            username="teacher",
            email="teacher@test.com",
            password="testpass123",
            user_type='teacher',
            school=cls.school,
            first_name="Test",
            last_initial="T"
        )
        
        cls.student = User.objects.create_user(
            username="student",
            email="student@test.com",
            password="testpass123",
            user_type='student',
            school=cls.school,
            first_name="Test",
            last_initial="S"
        )
    
    def test_student_cannot_access_teacher_pages(self):
        """Students should not access teacher-only pages"""
        self.client.force_login(self.student)
        response = self.client.get('/my_students/')
        
        self.assertIn(response.status_code, [403, 302])  # Forbidden or redirect
    
    def test_unauthenticated_redirects_to_login(self):
        """Unauthenticated users should redirect to login"""
        response = self.client.get('/')
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
    
    def test_teacher_can_access_teacher_pages(self):
        """Teachers should access teacher pages"""
        self.client.force_login(self.teacher)
        response = self.client.get('/my_students/')
        
        self.assertEqual(response.status_code, 200)

