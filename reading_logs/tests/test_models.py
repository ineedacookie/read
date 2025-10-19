"""
Test reading log models
"""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model

from ..models import Log, DailyGoal, TotalGoal
from users.models import School, CustomUser, StudentParentRelation
from read.utils.test_helpers import BaseTestCase

User = get_user_model()


class ReadingLogModelTests(BaseTestCase):
    """Test reading log model functionality"""
    
    def test_log_creation(self):
        """Test basic log creation"""
        log = Log.objects.create(
            student=self.student,
            school=self.school,
            date=date.today(),
            title="Test Book",
            author="Test Author",
            pages=25,
            minutes=30,
            rating=Decimal("4.5"),
            comments="Great book!"
        )
        
        self.assertEqual(log.student, self.student)
        self.assertEqual(log.school, self.school)
        self.assertEqual(log.title, "Test Book")
        self.assertEqual(log.pages, 25)
        self.assertEqual(log.minutes, 30)
        self.assertEqual(log.rating, Decimal("4.5"))
        self.assertTrue(str(log).endswith(str(date.today())))
    
    def test_log_auto_school_assignment(self):
        """Test that school is auto-assigned from student"""
        log = Log.objects.create(
            student=self.student,
            date=date.today(),
            title="Test Book"
        )
        
        self.assertEqual(log.school, self.student.school)
    
    def test_log_optional_fields(self):
        """Test log creation with minimal required fields"""
        log = Log.objects.create(
            student=self.student,
            date=date.today()
        )
        
        self.assertEqual(log.student, self.student)
        self.assertEqual(log.date, date.today())
        self.assertIsNone(log.title)
        self.assertIsNone(log.pages)
        self.assertIsNone(log.minutes)
        self.assertIsNone(log.rating)


class DailyGoalModelTests(TestCase):
    """Test daily goal model functionality"""
    
    def setUp(self):
        self.school = School.objects.create(name="Test School")
        self.student = CustomUser.objects.create(
            username="teststudent",
            email="student@test.com",
            user_type="student",
            school=self.school
        )
    
    def test_daily_goal_creation(self):
        """Test daily goal creation"""
        goal = DailyGoal.objects.create(
            school=self.school,
            student=self.student,
            type="pages",
            value=20
        )
        
        self.assertEqual(goal.school, self.school)
        self.assertEqual(goal.student, self.student)
        self.assertEqual(goal.type, "pages")
        self.assertEqual(goal.value, 20)
        self.assertIn("20 pages daily", str(goal))
    
    def test_goal_types(self):
        """Test different goal types"""
        pages_goal = DailyGoal.objects.create(
            school=self.school,
            type="pages",
            value=15
        )
        
        minutes_goal = DailyGoal.objects.create(
            school=self.school,
            type="minutes",
            value=30
        )
        
        self.assertEqual(pages_goal.type, "pages")
        self.assertEqual(minutes_goal.type, "minutes")


class UserModelTests(TestCase):
    """Test user model functionality"""
    
    def setUp(self):
        self.school = School.objects.create(name="Test School")
    
    def test_user_creation(self):
        """Test basic user creation"""
        user = CustomUser.objects.create(
            username="testuser",
            email="test@test.com",
            user_type="student",
            first_name="Test",
            last_initial="U"
        )
        
        self.assertEqual(user.email, "test@test.com")
        self.assertEqual(user.user_type, "student")
        self.assertEqual(user.full_name, "TEST U.")
    
    def test_parent_child_relationship(self):
        """Test parent-child relationship through StudentParentRelation"""
        parent = CustomUser.objects.create(
            username="parent",
            email="parent@test.com",
            user_type="parent",
            school=self.school
        )
        
        student = CustomUser.objects.create(
            username="student",
            email="student@test.com",
            user_type="student",
            school=self.school
        )
        
        relation = StudentParentRelation.objects.create(
            school=self.school,
            parent=parent,
            student=student
        )
        
        # Test relationship works both ways
        self.assertIn(student, parent.children.all())
        self.assertIn(parent, student.parents.all())
    
    def test_school_auto_creation(self):
        """Test automatic school creation when none provided"""
        user = CustomUser.objects.create(
            username="testuser",
            email="test@test.com",
            user_type="student"
        )
        
        self.assertIsNotNone(user.school)
        self.assertTrue(School.objects.filter(id=user.school.id).exists())
