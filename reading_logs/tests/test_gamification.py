"""
Test the gamification system (badges, points, achievements)
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.db.models import Sum
from datetime import date, timedelta
import json

from reading_logs.models import Log, DailyGoal
from reading_logs.gamification import (
    Badge, StudentBadge, StudentPoints, PointsHistory,
    GamificationEngine
)
from users.models import School

User = get_user_model()


class GamificationEngineTests(TestCase):
    """Test the core gamification engine functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.school = School.objects.create(name="Test School")
        
        self.student = User.objects.create_user(
            username="teststudent",
            email="student@test.com",
            password="testpass123",
            user_type="student",
            first_name="Test",
            last_initial="S",
            school=self.school
        )
        
        # Create a few badges for testing
        self.badge_first_log = Badge.objects.create(
            name="First Steps",
            description="Complete your first reading log",
            category="reading",
            difficulty="bronze",
            icon="fas fa-baby",
            color="#CD7F32",
            criteria={"total_logs": 1},
            points_value=10
        )
        
        self.badge_page_turner = Badge.objects.create(
            name="Page Turner",
            description="Read 100 pages total",
            category="reading",
            difficulty="bronze",
            icon="fas fa-book",
            color="#CD7F32",
            criteria={"total_pages": 100},
            points_value=25
        )
        
        self.badge_streak = Badge.objects.create(
            name="Steady Reader",
            description="Read for 7 days in a row",
            category="consistency",
            difficulty="bronze",
            icon="fas fa-calendar-check",
            color="#CD7F32",
            criteria={"streak_days": 7},
            points_value=30
        )
        
        self.engine = GamificationEngine()
    
    def test_badge_creation(self):
        """Test that badges are created correctly"""
        self.assertEqual(Badge.objects.count(), 3)
        self.assertEqual(self.badge_first_log.points_value, 10)
        self.assertEqual(self.badge_page_turner.criteria["total_pages"], 100)
    
    def test_first_log_badge_awarded(self):
        """Test that student gets First Steps badge for first log"""
        # Create first reading log
        log = Log.objects.create(
            student=self.student,
            school=self.school,
            date=date.today(),
            title="Test Book",
            pages=10,
            minutes=30
        )
        
        # Process with gamification engine
        self.engine.process_reading_log(log)
        
        # Check badge was awarded
        earned_badges = StudentBadge.objects.filter(student=self.student)
        self.assertEqual(earned_badges.count(), 1)
        
        first_badge = earned_badges.first()
        self.assertEqual(first_badge.badge, self.badge_first_log)
        
        # Check points were awarded
        points_profile = StudentPoints.objects.get(student=self.student)
        self.assertGreater(points_profile.total_points, 0)
        
        # Check points history
        points_history = PointsHistory.objects.filter(student=self.student)
        self.assertGreater(points_history.count(), 0)
    
    def test_page_turner_badge_progression(self):
        """Test progression towards Page Turner badge"""
        # Create logs with total of 100+ pages
        for i in range(5):
            log = Log.objects.create(
                student=self.student,
                school=self.school,
                date=date.today() - timedelta(days=i),
                title=f"Test Book {i}",
                pages=25,  # 5 logs × 25 pages = 125 pages total
                minutes=30
            )
            self.engine.process_reading_log(log)
        
        # Check Page Turner badge was awarded
        page_turner_badge = StudentBadge.objects.filter(
            student=self.student,
            badge=self.badge_page_turner
        )
        self.assertEqual(page_turner_badge.count(), 1)
        
        # Should also have First Steps badge
        self.assertEqual(StudentBadge.objects.filter(student=self.student).count(), 2)
    
    def test_points_and_level_system(self):
        """Test points accumulation and level progression"""
        # Create a reading log
        log = Log.objects.create(
            student=self.student,
            school=self.school,
            date=date.today(),
            title="Amazing Book",
            pages=50,
            minutes=60,
            rating=5.0
        )
        
        self.engine.process_reading_log(log)
        
        points_profile = StudentPoints.objects.get(student=self.student)
        
        # Should have points for: logging (5) + pages (50) + minutes (12) + rating (5) + badge (10)
        self.assertGreater(points_profile.total_points, 80)
        self.assertEqual(points_profile.current_level, 1)  # Should still be level 1
        
        # Check milestones are updated
        self.assertEqual(points_profile.total_pages_read, 50)
        self.assertEqual(points_profile.total_minutes_read, 60)
    
    def test_reading_streak_calculation(self):
        """Test reading streak tracking"""
        # Create logs for consecutive days
        for i in range(3):
            log = Log.objects.create(
                student=self.student,
                school=self.school,
                date=date.today() - timedelta(days=i),
                title=f"Book {i}",
                pages=10,
                minutes=20
            )
            self.engine.process_reading_log(log)
        
        points_profile = StudentPoints.objects.get(student=self.student)
        self.assertEqual(points_profile.current_streak, 3)  # All logs processed so streak is 3
        self.assertEqual(points_profile.longest_streak, 3)
    
    def test_level_up_mechanism(self):
        """Test level progression"""
        points_profile = StudentPoints.objects.create(
            student=self.student,
            school=self.school,
            total_points=95,  # Close to level up (needs 100)
            current_level=1,
            points_to_next_level=100
        )
        
        # Add enough points to level up
        points_profile.add_points(20, "Test points")
        
        # Should be level 2 now
        points_profile.refresh_from_db()
        self.assertEqual(points_profile.current_level, 2)
        self.assertEqual(points_profile.total_points, 15)  # 115 - 100 for level up
        self.assertEqual(points_profile.points_to_next_level, 125)  # Next level needs more


class GamificationAPITests(TestCase):
    """Test the gamification API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.school = School.objects.create(name="Test School")
        
        self.student = User.objects.create_user(
            username="teststudent",
            email="student@test.com",
            password="testpass123",
            user_type="student",
            first_name="Test",
            last_initial="S",
            school=self.school
        )
        
        self.teacher = User.objects.create_user(
            username="testteacher",
            email="teacher@test.com",
            password="testpass123",
            user_type="teacher",
            first_name="Teacher",
            last_initial="T",
            school=self.school
        )
        
        # Create a badge
        self.badge = Badge.objects.create(
            name="Test Badge",
            description="Test badge description",
            category="reading",
            difficulty="bronze",
            icon="fas fa-test",
            color="#123456",
            criteria={"total_pages": 10},
            points_value=15
        )
        
        # Create points profile for student
        self.points_profile = StudentPoints.objects.create(
            student=self.student,
            school=self.school,
            total_points=50,
            current_level=2,
            points_to_next_level=125,
            current_streak=3,
            longest_streak=5,
            total_books_read=2,
            total_pages_read=150,
            total_minutes_read=300
        )
    
    def test_student_profile_api_success(self):
        """Test successful student profile retrieval"""
        self.client.login(username="student@test.com", password="testpass123")
        
        response = self.client.get('/reading_logs/api/gamification/profile/')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')
        
        profile = data['data']
        self.assertEqual(profile['student']['id'], self.student.id)
        self.assertEqual(profile['points']['level'], 2)
        self.assertEqual(profile['points']['total'], 50)
        self.assertEqual(profile['achievements']['current_streak'], 3)
    
    def test_student_profile_api_permissions(self):
        """Test that only authorized users can access student profiles"""
        # Test without login
        response = self.client.get('/reading_logs/api/gamification/profile/')
        self.assertEqual(response.status_code, 302)  # Redirect to login
        
        # Test teacher accessing student profile without permission
        self.client.login(username="teacher@test.com", password="testpass123")
        response = self.client.get(f'/reading_logs/api/gamification/profile/{self.student.id}/')
        self.assertEqual(response.status_code, 403)
    
    def test_available_badges_api(self):
        """Test available badges API"""
        self.client.login(username="student@test.com", password="testpass123")
        
        response = self.client.get('/reading_logs/api/gamification/badges/')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')
        
        badges_data = data['data']
        self.assertGreater(badges_data['total_badges'], 0)
        self.assertIn('badges_by_category', badges_data)
    
    def test_award_custom_badge_api(self):
        """Test custom badge awarding by teachers"""
        self.client.login(username="teacher@test.com", password="testpass123")
        
        badge_data = {
            'student_id': self.student.id,
            'badge_name': 'Amazing Reader',
            'description': 'For exceptional reading effort',
            'points': 25
        }
        
        response = self.client.post(
            '/reading_logs/api/gamification/award_badge/',
            data=json.dumps(badge_data),
            content_type='application/json'
        )
        
        # This will fail due to no classroom relationship, but should return proper error
        self.assertEqual(response.status_code, 403)
        
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'error')
        self.assertIn('access', data['message'].lower())
    
    def test_gamification_stats_api(self):
        """Test gamification statistics API"""
        self.client.login(username="teacher@test.com", password="testpass123")
        
        response = self.client.get('/reading_logs/api/gamification/stats/')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')
        
        stats = data['data']
        self.assertIn('overview', stats)
        self.assertIn('points_and_levels', stats)
        self.assertIn('badges', stats)


class BadgeProgressTests(TestCase):
    """Test badge progress calculation"""
    
    def setUp(self):
        """Set up test data"""
        self.school = School.objects.create(name="Test School")
        
        self.student = User.objects.create_user(
            username="teststudent",
            email="student@test.com",
            password="testpass123",
            user_type="student",
            first_name="Test",
            last_initial="S",
            school=self.school
        )
        
        self.engine = GamificationEngine()
    
    def test_reading_criteria_check(self):
        """Test reading-based badge criteria checking"""
        # Create some reading logs
        for i in range(3):
            Log.objects.create(
                student=self.student,
                school=self.school,
                date=date.today() - timedelta(days=i),
                title=f"Book {i}",
                pages=30,
                minutes=45
            )
        
        # Test total pages criteria
        pages_criteria = {"total_pages": 80}
        result = self.engine._check_reading_criteria(self.student, pages_criteria)
        self.assertTrue(result)  # 3 × 30 = 90 pages >= 80
        
        # Test total books criteria
        books_criteria = {"total_books": 2}
        result = self.engine._check_reading_criteria(self.student, books_criteria)
        self.assertTrue(result)  # 3 unique books >= 2
    
    def test_consistency_criteria_check(self):
        """Test consistency-based badge criteria checking"""
        points_profile = StudentPoints.objects.create(
            student=self.student,
            school=self.school,
            longest_streak=10
        )
        
        # Test streak criteria
        streak_criteria = {"streak_days": 7}
        result = self.engine._check_consistency_criteria(
            self.student, streak_criteria, points_profile
        )
        self.assertTrue(result)  # 10 day streak >= 7
    
    def test_milestone_criteria_check(self):
        """Test milestone-based badge criteria checking"""
        points_profile = StudentPoints.objects.create(
            student=self.student,
            school=self.school,
            current_level=5,
            total_points=200
        )
        
        # Test level criteria
        level_criteria = {"level": 3}
        result = self.engine._check_milestone_criteria(
            self.student, level_criteria, points_profile
        )
        self.assertTrue(result)  # Level 5 >= 3
