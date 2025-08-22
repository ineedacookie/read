"""
Management command to set up the gamification system
Creates default badges and initializes the system
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from reading_logs.gamification import GamificationEngine, Badge


class Command(BaseCommand):
    help = 'Set up the gamification system with default badges'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset all badges and recreate defaults',
        )
        parser.add_argument(
            '--school-id',
            type=int,
            help='Initialize for a specific school only',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🎮 Setting up Reading Logs Gamification System')
        )
        
        try:
            with transaction.atomic():
                # Reset badges if requested
                if options['reset']:
                    self.stdout.write('🗑️  Resetting existing badges...')
                    Badge.objects.all().delete()
                    self.stdout.write(
                        self.style.WARNING('All existing badges have been deleted.')
                    )
                
                # Initialize gamification engine
                gamification_engine = GamificationEngine()
                
                # Create default badges
                self.stdout.write('🏆 Creating default badges...')
                
                created_count = 0
                for badge_data in gamification_engine.default_badges:
                    badge, created = Badge.objects.get_or_create(
                        name=badge_data['name'],
                        difficulty=badge_data['difficulty'],
                        defaults=badge_data
                    )
                    
                    if created:
                        created_count += 1
                        self.stdout.write(
                            f"   ✅ Created: {badge.name} ({badge.difficulty.title()})"
                        )
                    else:
                        self.stdout.write(
                            f"   📍 Exists: {badge.name} ({badge.difficulty.title()})"
                        )
                
                # Summary
                total_badges = Badge.objects.count()
                active_badges = Badge.objects.filter(is_active=True).count()
                
                self.stdout.write('\n' + '='*50)
                self.stdout.write(
                    self.style.SUCCESS(f'✨ Gamification Setup Complete!')
                )
                self.stdout.write(f'📊 Total Badges: {total_badges}')
                self.stdout.write(f'🟢 Active Badges: {active_badges}')
                self.stdout.write(f'🆕 New Badges Created: {created_count}')
                
                # Badge breakdown by category
                categories = Badge.objects.values_list('category', flat=True).distinct()
                self.stdout.write('\n📋 Badge Categories:')
                for category in categories:
                    count = Badge.objects.filter(category=category, is_active=True).count()
                    self.stdout.write(f'   {category.title()}: {count} badges')
                
                self.stdout.write('\n🚀 Students can now earn badges and points!')
                self.stdout.write('💡 Use the admin panel to create custom badges')
                self.stdout.write('📈 Check gamification stats at /api/gamification/stats/')
                
        except Exception as e:
            raise CommandError(f'Failed to set up gamification: {str(e)}')
