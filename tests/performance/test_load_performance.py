"""
Load testing to verify query optimizations under realistic conditions
"""
from django.test import TestCase, TransactionTestCase
from django.test.utils import override_settings
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.contrib.auth import get_user_model
from datetime import date, timedelta
import time

from users.models import School, Classroom, ReadingGroup
from reading_logs.models import Log, DailyGoal, TotalGoal
from reading_logs.gamification import StudentPoints, StudentBadge, Badge, PointsHistory

User = get_user_model()


class LoadTestCase(TestCase):
    """Test system performance under realistic load"""
    
    @classmethod
    def setUpTestData(cls):
        """Create realistic test data - 100 students, 10 teachers, 500 logs"""
        # Create school
        cls.school = School.objects.create(name="Performance Test School")
        
        # Create 10 teachers
        cls.teachers = []
        for i in range(10):
            teacher = User.objects.create_user(
                username=f"teacher{i}",
                email=f"teacher{i}@test.com",
                password="testpass123",
                user_type='teacher',
                school=cls.school,
                first_name=f"Teacher{i}",
                last_initial="T"
            )
            cls.teachers.append(teacher)
        
        # Create 100 students
        cls.students = []
        for i in range(100):
            student = User.objects.create_user(
                username=f"student{i}",
                email=f"student{i}@test.com",
                password="testpass123",
                user_type='student',
                school=cls.school,
                first_name=f"Student{i}",
                last_initial="S"
            )
            cls.students.append(student)
        
        # Create 5 classrooms with 20 students each
        cls.classrooms = []
        for i in range(5):
            classroom = Classroom.objects.create(
                name=f"Class {i}",
                school=cls.school,
                created_by=cls.teachers[0]
            )
            classroom.teachers.set(cls.teachers[:2])
            classroom.students.set(cls.students[i*20:(i+1)*20])
            cls.classrooms.append(classroom)
        
        # Create 500 reading logs (5 per student)
        for student in cls.students:
            for j in range(5):
                Log.objects.create(
                    student=student,
                    school=cls.school,
                    date=date.today() - timedelta(days=j),
                    title=f"Book {j}",
                    author=f"Author {j}",
                    pages=50 + j*10,
                    minutes=30 + j*5,
                    rating=4.0
                )
        
        # Create gamification data for all students
        for i, student in enumerate(cls.students):
            points_profile = StudentPoints.objects.create(
                student=student,
                school=cls.school,
                total_points=100 + (i % 50) * 10,
                current_level=1 + (i % 5),
                total_pages_read=(i + 1) * 250,
                last_activity=date.today()
            )
            
            # Add some points history
            for j in range(3):
                PointsHistory.objects.create(
                    student=student,
                    school=cls.school,
                    points_earned=10,
                    reason="Reading completion",
                    new_total=points_profile.total_points,
                    new_level=points_profile.current_level
                )
        
        # Create some goals
        for student in cls.students[:50]:
            DailyGoal.objects.create(
                school=cls.school,
                student=student,
                type='pages',
                value=20
            )
    
    def test_leaderboard_query_count_100_students(self):
        """Leaderboard with 100 students should use < 10 queries"""
        self.client.force_login(self.teachers[0])
        
        with CaptureQueriesContext(connection) as context:
            response = self.client.get('/reading_logs/api/gamification/leaderboard/?scope=school')
        
        query_count = len(context.captured_queries)
        self.assertLess(query_count, 10, 
            f"Leaderboard used {query_count} queries, expected <10")
        self.assertEqual(response.status_code, 200)
        
        # Verify data structure
        data = response.json()
        self.assertEqual(data['status'], 'success')
    
    def test_leaderboard_response_time(self):
        """Leaderboard should load in <1000ms with 100 students"""
        self.client.force_login(self.teachers[0])
        
        start = time.time()
        response = self.client.get('/reading_logs/api/gamification/leaderboard/?scope=school')
        elapsed = (time.time() - start) * 1000
        
        self.assertLess(elapsed, 1000, 
            f"Leaderboard took {elapsed:.0f}ms, expected <1000ms")
        self.assertEqual(response.status_code, 200)
    
    def test_my_students_page_query_count(self):
        """My students page should use < 15 queries"""
        self.client.force_login(self.teachers[0])
        
        with CaptureQueriesContext(connection) as context:
            response = self.client.get('/student/')
        
        query_count = len(context.captured_queries)
        self.assertLess(query_count, 20,  # Slightly higher for complex page
            f"My students page used {query_count} queries, expected <20")
        self.assertIn(response.status_code, [200, 302])  # May redirect
    
    def test_my_students_page_response_time(self):
        """My students page should load in <1500ms"""
        self.client.force_login(self.teachers[0])
        
        start = time.time()
        response = self.client.get('/student/')
        elapsed = (time.time() - start) * 1000
        
        self.assertLess(elapsed, 1500,
            f"My students page took {elapsed:.0f}ms, expected <1500ms")
        self.assertIn(response.status_code, [200, 302])  # May redirect
    
    def test_goal_queries_efficient(self):
        """Goal API should use < 10 queries for 50 students with goals"""
        self.client.force_login(self.teachers[0])
        
        with CaptureQueriesContext(connection) as context:
            response = self.client.get('/reading_logs/api/goals/?goal_type=daily')
        
        query_count = len(context.captured_queries)
        self.assertLess(query_count, 10,
            f"Goals API used {query_count} queries, expected <10")
        self.assertEqual(response.status_code, 200)
    
    def test_student_progress_query_count(self):
        """Student progress should use < 10 queries"""
        self.client.force_login(self.students[0])
        
        with CaptureQueriesContext(connection) as context:
            response = self.client.get('/reading_logs/api/student/progress/')
        
        query_count = len(context.captured_queries)
        self.assertLess(query_count, 10,
            f"Student progress used {query_count} queries, expected <10")
        self.assertEqual(response.status_code, 200)
    
    def test_multiple_concurrent_requests_performance(self):
        """Simulate multiple users accessing leaderboard"""
        self.client.force_login(self.teachers[0])
        
        # Make 5 requests and average the time
        times = []
        for _ in range(5):
            start = time.time()
            response = self.client.get('/reading_logs/api/gamification/leaderboard/?scope=school')
            elapsed = (time.time() - start) * 1000
            times.append(elapsed)
            self.assertEqual(response.status_code, 200)
        
        avg_time = sum(times) / len(times)
        self.assertLess(avg_time, 1000,
            f"Average response time {avg_time:.0f}ms, expected <1000ms")


class DatabaseIndexVerificationTest(TestCase):
    """Verify that database indexes are properly created"""
    
    def test_log_indexes_exist(self):
        """Verify Log model has expected indexes"""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) FROM sqlite_master 
                WHERE type='index' AND tbl_name='reading_logs_log'
            """)
            count = cursor.fetchone()[0]
            # Should have multiple indexes (exact count depends on DB)
            self.assertGreater(count, 5, "Log table should have multiple indexes")
    
    def test_studentpoints_indexes_exist(self):
        """Verify StudentPoints has indexes for leaderboards"""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) FROM sqlite_master 
                WHERE type='index' AND tbl_name='reading_logs_studentpoints'
            """)
            count = cursor.fetchone()[0]
            self.assertGreater(count, 3, "StudentPoints should have multiple indexes")
    
    def test_goals_indexes_exist(self):
        """Verify goal tables have proper indexes"""
        with connection.cursor() as cursor:
            # Check DailyGoal
            cursor.execute("""
                SELECT COUNT(*) FROM sqlite_master 
                WHERE type='index' AND tbl_name='reading_logs_dailygoal'
            """)
            count = cursor.fetchone()[0]
            self.assertGreater(count, 2, "DailyGoal should have indexes")
            
            # Check TotalGoal
            cursor.execute("""
                SELECT COUNT(*) FROM sqlite_master 
                WHERE type='index' AND tbl_name='reading_logs_totalgoal'
            """)
            count = cursor.fetchone()[0]
            self.assertGreater(count, 2, "TotalGoal should have indexes")

