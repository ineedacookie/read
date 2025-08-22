"""
Phase 2: Gamification & Achievement System
Badges, rewards, and engagement features for reading motivation
"""

from django.db import models
from django.db.models import Sum, Count, Avg, Max, Q, F
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
import json

from .models import Log, DailyGoal
from users.models import School

User = get_user_model()


class Badge(models.Model):
    """
    Represents achievement badges that students can earn
    """
    CATEGORY_CHOICES = [
        ('reading', 'Reading Achievement'),
        ('consistency', 'Consistency & Habits'),
        ('milestone', 'Milestone Achievement'),
        ('special', 'Special Achievement'),
        ('social', 'Social Achievement'),
    ]
    
    DIFFICULTY_CHOICES = [
        ('bronze', 'Bronze'),
        ('silver', 'Silver'),
        ('gold', 'Gold'),
        ('platinum', 'Platinum'),
    ]
    
    name = models.CharField(max_length=100)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES)
    icon = models.CharField(max_length=50, help_text="FontAwesome icon class")
    color = models.CharField(max_length=7, default="#007bff", help_text="Hex color code")
    
    # Achievement criteria (JSON field for flexibility)
    criteria = models.JSONField(
        help_text="JSON object defining achievement criteria",
        default=dict
    )
    
    points_value = models.IntegerField(default=10, help_text="Points awarded for earning this badge")
    is_active = models.BooleanField(default=True)
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['name', 'difficulty']
        ordering = ['category', 'difficulty', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.difficulty.title()})"


class StudentBadge(models.Model):
    """
    Records badges earned by students
    """
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='earned_badges',
        limit_choices_to={'user_type': 'student'}
    )
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    
    earned_at = models.DateTimeField(auto_now_add=True)
    progress_data = models.JSONField(
        default=dict,
        help_text="JSON data about how the badge was earned"
    )
    
    class Meta:
        unique_together = ['student', 'badge']
        ordering = ['-earned_at']
    
    def __str__(self):
        return f"{self.student.full_name} - {self.badge.name}"


class StudentPoints(models.Model):
    """
    Tracks student points and levels
    """
    student = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='points_profile',
        limit_choices_to={'user_type': 'student'}
    )
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    
    total_points = models.IntegerField(default=0)
    current_level = models.IntegerField(default=1)
    points_to_next_level = models.IntegerField(default=100)
    
    # Achievement streaks
    current_streak = models.IntegerField(default=0, help_text="Current daily reading streak")
    longest_streak = models.IntegerField(default=0, help_text="Longest reading streak achieved")
    
    # Reading milestones
    total_books_read = models.IntegerField(default=0)
    total_pages_read = models.IntegerField(default=0)
    total_minutes_read = models.IntegerField(default=0)
    
    # Tracking
    last_activity = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.student.full_name} - Level {self.current_level}"
    
    def add_points(self, points, reason=""):
        """Add points and check for level up"""
        self.total_points += points
        
        # Check for level up
        while self.total_points >= self.points_to_next_level:
            self.total_points -= self.points_to_next_level
            self.current_level += 1
            self.points_to_next_level = self._calculate_next_level_points()
        
        self.save()
        
        # Log the points activity
        PointsHistory.objects.create(
            student=self.student,
            school=self.school,
            points_earned=points,
            reason=reason,
            new_total=self.total_points,
            new_level=self.current_level
        )
    
    def _calculate_next_level_points(self):
        """Calculate points needed for next level (increases with level)"""
        return 100 + ((self.current_level - 1) * 25)


class PointsHistory(models.Model):
    """
    Track points earning history for transparency
    """
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='points_history'
    )
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    
    points_earned = models.IntegerField()
    reason = models.CharField(max_length=200)
    new_total = models.IntegerField()
    new_level = models.IntegerField()
    
    earned_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-earned_at']
    
    def __str__(self):
        return f"{self.student.full_name}: +{self.points_earned} - {self.reason}"


class GamificationEngine:
    """
    Main engine for processing achievements and awarding badges
    """
    
    def __init__(self):
        self.default_badges = self._get_default_badges()
    
    def process_reading_log(self, log):
        """
        Process a new reading log for achievements
        Called after a student creates a reading log
        """
        student = log.student
        school = log.school
        
        # Ensure student has points profile
        points_profile, created = StudentPoints.objects.get_or_create(
            student=student,
            school=school
        )
        
        # Award base points for logging
        self._award_base_points(log, points_profile)
        
        # Update reading streaks
        self._update_streaks(student, points_profile)
        
        # Update milestone counters first
        self._update_milestones(log, points_profile)
        
        # Check for badge achievements after milestones are updated
        self._check_badge_achievements(student, points_profile)
    
    def _award_base_points(self, log, points_profile):
        """Award base points for reading activities"""
        points = 0
        reasons = []
        
        # Points for logging reading (base reward)
        points += 5
        reasons.append("Reading log entry")
        
        # Points for pages read
        if log.pages:
            page_points = min(log.pages, 50)  # Cap at 50 pages for points
            points += page_points
            reasons.append(f"{log.pages} pages read")
        
        # Points for time spent reading
        if log.minutes:
            minute_points = min(log.minutes // 5, 20)  # 1 point per 5 minutes, cap at 20
            points += minute_points
            reasons.append(f"{log.minutes} minutes reading")
        
        # Bonus for high ratings
        if log.rating and log.rating >= 4.0:
            points += 5
            reasons.append("High rating (4+ stars)")
        
        # Award the points
        if points > 0:
            points_profile.add_points(points, "; ".join(reasons))
    
    def _update_streaks(self, student, points_profile):
        """Update reading streaks"""
        yesterday = date.today() - timedelta(days=1)
        today = date.today()
        
        # Check if student read yesterday and today
        yesterday_logs = Log.objects.filter(student=student, date=yesterday).exists()
        today_logs = Log.objects.filter(student=student, date=today).exists()
        
        if today_logs:
            if yesterday_logs or points_profile.last_activity == yesterday:
                # Continue streak
                points_profile.current_streak += 1
            else:
                # Start new streak
                points_profile.current_streak = 1
            
            # Update longest streak
            if points_profile.current_streak > points_profile.longest_streak:
                points_profile.longest_streak = points_profile.current_streak
            
            points_profile.last_activity = today
            points_profile.save()
            
            # Award streak bonuses
            if points_profile.current_streak % 7 == 0:  # Weekly streak
                bonus_points = points_profile.current_streak * 2
                points_profile.add_points(bonus_points, f"{points_profile.current_streak} day streak bonus!")
    
    def _check_badge_achievements(self, student, points_profile):
        """Check if student has earned any new badges"""
        
        # Get all active badges student hasn't earned yet
        earned_badge_ids = StudentBadge.objects.filter(
            student=student
        ).values_list('badge_id', flat=True)
        
        available_badges = Badge.objects.filter(
            is_active=True
        ).exclude(id__in=earned_badge_ids)
        
        for badge in available_badges:
            if self._check_badge_criteria(student, badge, points_profile):
                # Award the badge
                StudentBadge.objects.create(
                    student=student,
                    badge=badge,
                    school=student.school,
                    progress_data=self._get_badge_progress_data(student, badge)
                )
                
                # Award points for earning badge
                points_profile.add_points(
                    badge.points_value,
                    f"Earned badge: {badge.name}"
                )
    
    def _check_badge_criteria(self, student, badge, points_profile):
        """Check if student meets criteria for a specific badge"""
        criteria = badge.criteria
        
        if badge.category == 'reading':
            return self._check_reading_criteria(student, criteria)
        elif badge.category == 'consistency':
            return self._check_consistency_criteria(student, criteria, points_profile)
        elif badge.category == 'milestone':
            return self._check_milestone_criteria(student, criteria, points_profile)
        elif badge.category == 'special':
            return self._check_special_criteria(student, criteria, points_profile)
        
        return False
    
    def _check_reading_criteria(self, student, criteria):
        """Check reading-based achievement criteria"""
        if 'total_logs' in criteria:
            total_logs = Log.objects.filter(student=student).count()
            if total_logs >= criteria['total_logs']:
                return True
        
        if 'total_pages' in criteria:
            total_pages = Log.objects.filter(student=student).aggregate(
                total=Sum('pages')
            )['total'] or 0
            if total_pages >= criteria['total_pages']:
                return True
        
        if 'total_books' in criteria:
            unique_books = Log.objects.filter(
                student=student
            ).exclude(
                title__isnull=True
            ).exclude(
                title__exact=''
            ).values('title').distinct().count()
            if unique_books >= criteria['total_books']:
                return True
        
        if 'single_session_pages' in criteria:
            max_pages = Log.objects.filter(student=student).aggregate(
                max_pages=Max('pages')
            )['max_pages'] or 0
            if max_pages >= criteria['single_session_pages']:
                return True
        
        return False
    
    def _check_consistency_criteria(self, student, criteria, points_profile):
        """Check consistency-based achievement criteria"""
        if 'streak_days' in criteria:
            if points_profile.longest_streak >= criteria['streak_days']:
                return True
        
        if 'consecutive_weeks' in criteria:
            # Check for reading activity in consecutive weeks
            weeks_count = 0
            current_date = date.today()
            
            for i in range(criteria['consecutive_weeks']):
                week_start = current_date - timedelta(days=current_date.weekday() + (i * 7))
                week_end = week_start + timedelta(days=6)
                
                week_logs = Log.objects.filter(
                    student=student,
                    date__range=(week_start, week_end)
                ).exists()
                
                if week_logs:
                    weeks_count += 1
                else:
                    break
            
            if weeks_count >= criteria['consecutive_weeks']:
                return True
        
        return False
    
    def _check_milestone_criteria(self, student, criteria, points_profile):
        """Check milestone-based achievement criteria"""
        if 'level' in criteria:
            if points_profile.current_level >= criteria['level']:
                return True
        
        if 'total_points' in criteria:
            # Calculate lifetime points (current + spent on levels)
            lifetime_points = points_profile.total_points
            for level in range(1, points_profile.current_level):
                lifetime_points += 100 + (level * 25)
            
            if lifetime_points >= criteria['total_points']:
                return True
        
        return False
    
    def _check_special_criteria(self, student, criteria, points_profile):
        """Check special achievement criteria"""
        if 'perfect_ratings_count' in criteria:
            perfect_ratings = Log.objects.filter(
                student=student,
                rating=5.0
            ).count()
            if perfect_ratings >= criteria['perfect_ratings_count']:
                return True
        
        return False
    
    def _get_badge_progress_data(self, student, badge):
        """Get data about how the badge was earned"""
        return {
            'earned_date': date.today().isoformat(),
            'criteria_met': badge.criteria,
            'student_stats': self._get_student_current_stats(student)
        }
    
    def _get_student_current_stats(self, student):
        """Get current statistics for a student"""
        stats = Log.objects.filter(student=student).aggregate(
            total_logs=models.Count('id'),
            total_pages=models.Sum('pages'),
            total_minutes=models.Sum('minutes'),
            avg_rating=models.Avg('rating')
        )
        
        return {
            'total_logs': stats['total_logs'] or 0,
            'total_pages': stats['total_pages'] or 0,
            'total_minutes': stats['total_minutes'] or 0,
            'avg_rating': float(stats['avg_rating']) if stats['avg_rating'] else 0
        }
    
    def _update_milestones(self, log, points_profile):
        """Update milestone counters"""
        # Update total pages
        if log.pages:
            points_profile.total_pages_read += log.pages
        
        # Update total minutes
        if log.minutes:
            points_profile.total_minutes_read += log.minutes
        
        # Update books count (simplified - count unique titles)
        if log.title:
            unique_books = Log.objects.filter(
                student=log.student
            ).exclude(
                title__isnull=True
            ).exclude(
                title__exact=''
            ).values('title').distinct().count()
            points_profile.total_books_read = unique_books
        
        points_profile.save()
    
    def _get_default_badges(self):
        """Define default badges for the system"""
        return [
            # Reading Achievement Badges
            {
                'name': 'First Steps',
                'description': 'Complete your first reading log!',
                'category': 'reading',
                'difficulty': 'bronze',
                'icon': 'fas fa-baby',
                'color': '#CD7F32',
                'criteria': {'total_logs': 1},
                'points_value': 10
            },
            {
                'name': 'Page Turner',
                'description': 'Read 100 pages total',
                'category': 'reading',
                'difficulty': 'bronze',
                'icon': 'fas fa-book',
                'color': '#CD7F32',
                'criteria': {'total_pages': 100},
                'points_value': 25
            },
            {
                'name': 'Bookworm',
                'description': 'Read 500 pages total',
                'category': 'reading',
                'difficulty': 'silver',
                'icon': 'fas fa-book-open',
                'color': '#C0C0C0',
                'criteria': {'total_pages': 500},
                'points_value': 50
            },
            {
                'name': 'Reading Champion',
                'description': 'Read 1000 pages total',
                'category': 'reading',
                'difficulty': 'gold',
                'icon': 'fas fa-crown',
                'color': '#FFD700',
                'criteria': {'total_pages': 1000},
                'points_value': 100
            },
            
            # Consistency Badges
            {
                'name': 'Steady Reader',
                'description': 'Read for 7 days in a row',
                'category': 'consistency',
                'difficulty': 'bronze',
                'icon': 'fas fa-calendar-check',
                'color': '#CD7F32',
                'criteria': {'streak_days': 7},
                'points_value': 30
            },
            {
                'name': 'Reading Habit',
                'description': 'Read for 30 days in a row',
                'category': 'consistency',
                'difficulty': 'silver',
                'icon': 'fas fa-fire',
                'color': '#C0C0C0',
                'criteria': {'streak_days': 30},
                'points_value': 75
            },
            
            # Milestone Badges
            {
                'name': 'Level Up',
                'description': 'Reach level 5',
                'category': 'milestone',
                'difficulty': 'bronze',
                'icon': 'fas fa-arrow-up',
                'color': '#CD7F32',
                'criteria': {'level': 5},
                'points_value': 25
            },
            
            # Special Badges
            {
                'name': 'Perfectionist',
                'description': 'Give 10 books a 5-star rating',
                'category': 'special',
                'difficulty': 'silver',
                'icon': 'fas fa-star',
                'color': '#C0C0C0',
                'criteria': {'perfect_ratings_count': 10},
                'points_value': 40
            }
        ]
    
    def initialize_default_badges(self):
        """Create default badges in the database"""
        for badge_data in self.default_badges:
            badge, created = Badge.objects.get_or_create(
                name=badge_data['name'],
                difficulty=badge_data['difficulty'],
                defaults=badge_data
            )
            if created:
                print(f"Created badge: {badge.name}")


# Utility functions
def get_student_leaderboard(school, timeframe='month'):
    """Get leaderboard for a school"""
    if timeframe == 'week':
        start_date = date.today() - timedelta(days=7)
    elif timeframe == 'month':
        start_date = date.today() - timedelta(days=30)
    else:  # all-time
        start_date = None
    
    query = StudentPoints.objects.filter(school=school)
    
    if start_date:
        # For time-limited leaderboards, calculate points from logs
        students = User.objects.filter(
            user_type='student',
            school=school
        )
        
        leaderboard = []
        for student in students:
            logs = Log.objects.filter(student=student, date__gte=start_date)
            points = logs.count() * 5  # Base calculation
            
            leaderboard.append({
                'student': student,
                'points': points,
                'logs_count': logs.count()
            })
        
        leaderboard.sort(key=lambda x: x['points'], reverse=True)
        return leaderboard[:20]  # Top 20
    else:
        # All-time leaderboard
        return query.order_by('-total_points')[:20]


def award_custom_badge(student, name, description, points=10):
    """Award a custom badge to a student (for special occasions)"""
    badge, created = Badge.objects.get_or_create(
        name=name,
        difficulty='special',
        defaults={
            'description': description,
            'category': 'special',
            'icon': 'fas fa-trophy',
            'color': '#FF6B35',
            'criteria': {},
            'points_value': points
        }
    )
    
    student_badge, created = StudentBadge.objects.get_or_create(
        student=student,
        badge=badge,
        school=student.school
    )
    
    if created:
        # Award points
        points_profile, _ = StudentPoints.objects.get_or_create(
            student=student,
            school=student.school
        )
        points_profile.add_points(points, f"Special badge: {name}")
    
    return student_badge
