"""
Management command to create comprehensive sample data for 2 schools
Generates realistic data for testing and demonstration purposes
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.contrib.auth import get_user_model
from datetime import date, timedelta
import random

from reading_logs.models import Log, DailyGoal, TotalGoal
from reading_logs.gamification import GamificationEngine, Badge, StudentBadge, StudentPoints
from users.models import School, Classroom, ReadingGroup, StudentParentRelation
from read.utils.user_creation_helpers import (
    create_school_with_data,
    create_superuser_if_needed,
    get_default_school_names
)
from django.db import models

User = get_user_model()


class Command(BaseCommand):
    help = 'Create comprehensive sample data for 2 schools with realistic reading data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete all existing data before creating sample data',
        )
        parser.add_argument(
            '--school-count',
            type=int,
            default=2,
            help='Number of schools to create (default: 2)',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('📚 Creating Sample Data for Reading Tracking System')
        )
        
        if options['reset']:
            self.stdout.write('🗑️  Resetting existing data...')
            self._reset_data()
            self.stdout.write(self.style.WARNING('All existing data has been deleted.'))
        
        try:
            with transaction.atomic():
                school_count = options['school_count']
                default_names = get_default_school_names()
                
                for i in range(school_count):
                    # Get school name
                    school_name = default_names[i] if i < len(default_names) else f"Sample School {i + 1}"
                    
                    self.stdout.write(f'\n🏫 Creating {school_name}...')
                    
                    # Create complete school with data using helper function
                    school, users, classrooms, reading_groups, relationships_count = create_school_with_data(i, school_name)
                    
                    self.stdout.write(f'   ✅ Created school: {school.name}')
                    self.stdout.write(f'   ✅ Created 1 administrator, {len(users["teachers"])} teachers, '
                                     f'{len(users["students"])} students, {len(users["parents"])} parents')
                    self.stdout.write(f'   ✅ Created {len(classrooms)} classrooms and {len(reading_groups)} reading groups')
                    self.stdout.write('   ✅ Assigned students to classrooms and reading groups')
                    self.stdout.write(f'   ✅ Created {relationships_count} parent-child relationships')
                    
                    # Create superuser only for the first school to avoid duplicates
                    if i == 0:
                        self.stdout.write('🔑 Creating superuser...')
                        superuser = create_superuser_if_needed()
                        self.stdout.write(f'   ✅ Created superuser: {superuser.username} ({superuser.email})')
                    
                    self.stdout.write('🎯 Creating goals...')
                    self._create_goals(users['students'])
                    
                    self.stdout.write('📖 Creating reading logs...')
                    self._create_reading_logs(users['students'])
                    
                    self.stdout.write('🎮 Processing gamification...')
                    self._process_gamification(users['students'])
                
                self._display_summary()
                
        except Exception as e:
            raise CommandError(f'Failed to create sample data: {str(e)}')

    def _reset_data(self):
        """Reset all data in the system"""
        # Delete in correct order to avoid foreign key constraints
        StudentBadge.objects.all().delete()
        StudentPoints.objects.all().delete()
        Log.objects.all().delete()
        DailyGoal.objects.all().delete()
        TotalGoal.objects.all().delete()
        StudentParentRelation.objects.all().delete()
        ReadingGroup.objects.all().delete()
        Classroom.objects.all().delete()
        User.objects.all().delete()  # Delete all users including superusers
        School.objects.all().delete()


    def _create_goals(self, students):
        """Create daily and total goals for students"""
        goals_created = 0
        
        for student in students:
            # 70% of students have daily goals
            if random.random() < 0.7:
                goal_type = random.choice(['pages', 'minutes'])
                value = random.choice([20, 30, 50]) if goal_type == 'pages' else random.choice([15, 20, 30])
                
                DailyGoal.objects.create(
                    student=student,
                    school=student.school,
                    type=goal_type,
                    value=value
                )
                goals_created += 1
            
            # 50% of students have total goals
            if random.random() < 0.5:
                total_value = random.choice([500, 1000, 1500, 2000])
                start_date = date.today() - timedelta(days=random.randint(0, 30))
                end_date = start_date + timedelta(days=random.randint(60, 120))
                
                TotalGoal.objects.create(
                    student=student,
                    school=student.school,
                    start=start_date,
                    end=end_date,
                    total=total_value
                )
                goals_created += 1
        
        self.stdout.write(f'   ✅ Created {goals_created} goals')

    def _create_reading_logs(self, students):
        """Create realistic reading logs over the past 60 days"""
        book_titles = [
            "Harry Potter and the Sorcerer's Stone", "Charlotte's Web", "The Lion, the Witch and the Wardrobe",
            "Where the Red Fern Grows", "Bridge to Terabithia", "The Giver", "Holes", "Wonder",
            "The One and Only Ivan", "Because of Winn-Dixie", "The Tale of Despereaux", "Frindle",
            "The BFG", "Matilda", "James and the Giant Peach", "The Witches", "Charlie and the Chocolate Factory",
            "The Secret Garden", "A Wrinkle in Time", "The Phantom Tollbooth", "Island of the Blue Dolphins",
            "Hatchet", "My Side of the Mountain", "The Sign of the Beaver", "Number the Stars",
            "Roll of Thunder, Hear My Cry", "Walk Two Moons", "Maniac Magee", "Shiloh", "The Cricket in Times Square"
        ]
        
        authors = [
            "J.K. Rowling", "E.B. White", "C.S. Lewis", "Wilson Rawls", "Katherine Paterson",
            "Lois Lowry", "Louis Sachar", "R.J. Palacio", "Katherine Applegate", "Kate DiCamillo",
            "Roald Dahl", "Frances Hodgson Burnett", "Madeleine L'Engle", "Norton Juster",
            "Scott O'Dell", "Gary Paulsen", "Jean Craighead George", "Elizabeth George Speare",
            "Lois Lowry", "Mildred D. Taylor", "Sharon Creech", "Jerry Spinelli", "Phyllis Reynolds Naylor"
        ]
        
        comments = [
            "I loved this book! The characters were so interesting.",
            "This was a really good story. I couldn't put it down!",
            "The ending was surprising. I didn't see that coming.",
            "This book was okay. Some parts were exciting.",
            "Amazing book! I want to read more by this author.",
            "The story was fun but a little long for me.",
            "I really enjoyed reading this. The adventure was exciting!",
            "This book taught me a lot about friendship.",
            "The main character reminded me of myself.",
            "I would recommend this book to my friends.",
            "", "", ""  # Some logs have no comments
        ]
        
        logs_created = 0
        end_date = date.today()
        
        for student in students:
            # Each student has 5-25 reading logs over 60 days
            num_logs = random.randint(5, 25)
            
            # Generate random dates for logs
            log_dates = []
            for _ in range(num_logs):
                days_ago = random.randint(0, 59)
                log_date = end_date - timedelta(days=days_ago)
                log_dates.append(log_date)
            
            # Sort dates to create realistic progression
            log_dates.sort()
            
            for log_date in log_dates:
                # Realistic reading session data
                pages = random.choices(
                    [None, 5, 10, 15, 20, 25, 30, 40, 50, 75, 100],
                    weights=[1, 2, 3, 4, 5, 4, 3, 2, 1, 1, 1]
                )[0]
                
                minutes = random.choices(
                    [None, 10, 15, 20, 25, 30, 45, 60, 90, 120],
                    weights=[1, 2, 3, 4, 5, 4, 3, 2, 1, 1]
                )[0]
                
                # 80% of logs have a rating
                rating = None
                if random.random() < 0.8:
                    rating = random.choices(
                        [1.0, 2.0, 3.0, 4.0, 5.0],
                        weights=[1, 2, 4, 5, 3]
                    )[0]
                
                # 60% of logs have a book title
                title = None
                author = None
                if random.random() < 0.6:
                    title = random.choice(book_titles)
                    author = random.choice(authors)
                
                # 40% of logs have comments
                comment = None
                if random.random() < 0.4:
                    comment = random.choice(comments)
                
                _ = Log.objects.create(
                    student=student,
                    school=student.school,
                    date=log_date,
                    title=title,
                    author=author,
                    pages=pages,
                    minutes=minutes,
                    rating=rating,
                    comments=comment
                )
                logs_created += 1
        
        self.stdout.write(f'   ✅ Created {logs_created} reading logs')

    def _process_gamification(self, students):
        """Process gamification for all student logs"""
        engine = GamificationEngine()
        points_profiles_created = 0
        badges_awarded = 0
        
        for student in students:
            # Get all logs for this student
            logs = Log.objects.filter(student=student).order_by('date', 'created_date')
            
            for log in logs:
                engine.process_reading_log(log)
            
            # Check if points profile was created
            if StudentPoints.objects.filter(student=student).exists():
                points_profiles_created += 1
            
            # Count badges earned
            badges_awarded += StudentBadge.objects.filter(student=student).count()
        
        self.stdout.write(f'   ✅ Created {points_profiles_created} student profiles and awarded {badges_awarded} badges')

    def _display_summary(self):
        """Display a comprehensive summary of created data"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('📊 SAMPLE DATA CREATION SUMMARY'))
        self.stdout.write('='*60)
        
        # Schools
        school_count = School.objects.count()
        self.stdout.write(f'🏫 Schools Created: {school_count}')
        
        # Users by type
        superuser_count = User.objects.filter(is_superuser=True).count()
        admin_count = User.objects.filter(user_type='administrator').count()
        teacher_count = User.objects.filter(user_type='teacher').count()
        student_count = User.objects.filter(user_type='student').count()
        parent_count = User.objects.filter(user_type='parent').count()
        
        self.stdout.write('👥 Users Created:')
        self.stdout.write(f'   • Superusers: {superuser_count}')
        self.stdout.write(f'   • Administrators: {admin_count}')
        self.stdout.write(f'   • Teachers: {teacher_count}')
        self.stdout.write(f'   • Students: {student_count}')
        self.stdout.write(f'   • Parents: {parent_count}')
        self.stdout.write(f'   • Total: {superuser_count + admin_count + teacher_count + student_count + parent_count}')
        
        # Classrooms and Groups
        classroom_count = Classroom.objects.count()
        group_count = ReadingGroup.objects.count()
        self.stdout.write(f'🏛️  Classrooms: {classroom_count}')
        self.stdout.write(f'📚 Reading Groups: {group_count}')
        
        # Relationships
        relationship_count = StudentParentRelation.objects.count()
        self.stdout.write(f'👨‍👩‍👧‍👦 Parent-Child Relationships: {relationship_count}')
        
        # Goals
        daily_goal_count = DailyGoal.objects.count()
        total_goal_count = TotalGoal.objects.count()
        self.stdout.write('🎯 Goals Created:')
        self.stdout.write(f'   • Daily Goals: {daily_goal_count}')
        self.stdout.write(f'   • Total Goals: {total_goal_count}')
        
        # Reading Data
        log_count = Log.objects.count()
        total_pages = Log.objects.aggregate(total=models.Sum('pages'))['total'] or 0
        total_minutes = Log.objects.aggregate(total=models.Sum('minutes'))['total'] or 0
        
        self.stdout.write('📖 Reading Data:')
        self.stdout.write(f'   • Reading Logs: {log_count:,}')
        self.stdout.write(f'   • Total Pages: {total_pages:,}')
        self.stdout.write(f'   • Total Minutes: {total_minutes:,}')
        
        # Gamification
        badge_count = Badge.objects.count()
        student_badge_count = StudentBadge.objects.count()
        points_profile_count = StudentPoints.objects.count()
        
        self.stdout.write('🎮 Gamification:')
        self.stdout.write(f'   • Available Badges: {badge_count}')
        self.stdout.write(f'   • Badges Earned: {student_badge_count}')
        self.stdout.write(f'   • Student Profiles: {points_profile_count}')
        
        # School Breakdown
        self.stdout.write('\n🏫 School Breakdown:')
        for school in School.objects.all():
            school_students = User.objects.filter(school=school, user_type='student').count()
            school_teachers = User.objects.filter(school=school, user_type='teacher').count()
            school_parents = User.objects.filter(school=school, user_type='parent').count()
            school_admins = User.objects.filter(school=school, user_type='administrator').count()
            school_classrooms = Classroom.objects.filter(school=school).count()
            school_groups = ReadingGroup.objects.filter(school=school).count()
            school_logs = Log.objects.filter(school=school).count()
            school_badges = StudentBadge.objects.filter(school=school).count()
            
            # Count students in classrooms and groups
            students_in_classrooms = 0
            students_in_groups = 0
            for classroom in Classroom.objects.filter(school=school):
                students_in_classrooms += classroom.students.count()
            for group in ReadingGroup.objects.filter(school=school):
                students_in_groups += group.students.count()
            
            self.stdout.write(f'   • {school.name}:')
            self.stdout.write(f'     - Administrators: {school_admins}')
            self.stdout.write(f'     - Teachers: {school_teachers}')
            self.stdout.write(f'     - Students: {school_students}')
            self.stdout.write(f'     - Parents: {school_parents}')
            self.stdout.write(f'     - Classrooms: {school_classrooms} (with {students_in_classrooms} student assignments)')
            self.stdout.write(f'     - Reading Groups: {school_groups} (with {students_in_groups} student assignments)')
            self.stdout.write(f'     - Reading Logs: {school_logs}')
            self.stdout.write(f'     - Badges Earned: {school_badges}')
        
        self.stdout.write('\n🔑 Sample Login Credentials:')
        self.stdout.write('   Regular users have password: password123')
        self.stdout.write('')
        self.stdout.write('   🔑 Superuser Account (Django Admin):')
        self.stdout.write('      • Email: temp@temp.com / Password: temp')
        self.stdout.write('')
        self.stdout.write('   📧 Administrator Accounts:')
        self.stdout.write('      • admin@school1.edu (Riverside Elementary)')
        self.stdout.write('      • admin@school2.edu (Oak Valley Middle)')
        self.stdout.write('')
        self.stdout.write('   👩‍🏫 Teacher Account Examples:')
        self.stdout.write('      • emma.smith@school1.edu')
        self.stdout.write('      • james.johnson@school1.edu')
        self.stdout.write('')
        self.stdout.write('   👨‍👩‍👧‍👦 Parent Account Examples:')
        self.stdout.write('      • jennifer.martinez@parent1.com')
        self.stdout.write('      • robert.davis@parent1.com')
        self.stdout.write('')
        self.stdout.write('   🎓 Student Account Examples:')
        self.stdout.write('      • student1@school1.edu (Alex M.)')
        self.stdout.write('      • student2@school1.edu (Bailey S.)')
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('✨ Sample Data Creation Complete!'))
        self.stdout.write('📚 Ready for testing and demonstration')
        self.stdout.write('🎯 All systems populated with realistic data')
        self.stdout.write('🔐 Django Admin: temp@temp.com / password: temp')
        self.stdout.write('🔐 App Login: Any account above / password: password123')
        self.stdout.write('='*60)

