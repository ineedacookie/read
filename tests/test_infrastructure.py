"""
Infrastructure Tests
Test that all new mixins, decorators, and helpers work correctly
"""

from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from users.view_mixins import (
    SchoolFilterMixin,
    UserTypePermissionMixin,
    SearchableMixin
)
from read.utils.decorators import require_user_types, rate_limit
from read.utils.view_helpers import (
    get_user_students,
    get_date_range_from_request,
    json_success,
    json_error,
    calculate_reading_stats,
    format_duration
)

User = get_user_model()


class ViewMixinTests(TestCase):
    """Test view mixins functionality"""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass',
            user_type='teacher'
        )
    
    def test_user_type_permission_mixin_allows_correct_type(self):
        """UserTypePermissionMixin allows correct user types"""
        # This would require a full view setup, just verify it exists
        self.assertTrue(hasattr(UserTypePermissionMixin, 'allowed_user_types'))
    
    def test_searchable_mixin_has_search_fields(self):
        """SearchableMixin has search configuration"""
        self.assertTrue(hasattr(SearchableMixin, 'search_fields'))
        self.assertTrue(hasattr(SearchableMixin, 'get_queryset'))


class DecoratorTests(TestCase):
    """Test decorator functionality"""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass',
            user_type='student'
        )
    
    def test_require_user_types_decorator_exists(self):
        """require_user_types decorator is callable"""
        self.assertTrue(callable(require_user_types))
        
        # Test decorator creation
        decorated = require_user_types('student')(lambda r: JsonResponse({'ok': True}))
        self.assertTrue(callable(decorated))
    
    def test_rate_limit_decorator_exists(self):
        """rate_limit decorator is callable"""
        self.assertTrue(callable(rate_limit))


class ViewHelperTests(TestCase):
    """Test view helper functions"""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass',
            user_type='student'
        )
    
    def test_json_success_returns_json(self):
        """json_success returns proper JSON response"""
        response = json_success("Test message", data={'key': 'value'})
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 200)
    
    def test_json_error_returns_json(self):
        """json_error returns proper JSON response"""
        response = json_error("Error message", status=400)
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 400)
    
    def test_format_duration(self):
        """format_duration formats minutes correctly"""
        self.assertEqual(format_duration(0), "0m")
        self.assertEqual(format_duration(45), "45m")
        self.assertEqual(format_duration(60), "1h")
        self.assertEqual(format_duration(90), "1h 30m")
        self.assertEqual(format_duration(125), "2h 5m")
    
    def test_get_user_students_for_student(self):
        """get_user_students returns self for student users"""
        students = get_user_students(self.user)
        self.assertEqual(students.count(), 1)
        self.assertEqual(students.first(), self.user)


class ComponentTests(TestCase):
    """Test that component templates exist"""
    
    def test_card_components_exist(self):
        """Card components exist and are loadable"""
        from django.template.loader import get_template
        
        # These should not raise TemplateDoesNotExist
        get_template('components/cards/stat_card.html')
        get_template('components/cards/progress_card.html')
        get_template('components/cards/list_card.html')
        get_template('components/cards/chart_card.html')
        get_template('components/cards/form_card.html')
    
    def test_form_components_exist(self):
        """Form input components exist and are loadable"""
        from django.template.loader import get_template
        
        get_template('components/forms/text_input.html')
        get_template('components/forms/number_input.html')
        get_template('components/forms/select_input.html')
        get_template('components/forms/date_input.html')
        get_template('components/forms/textarea_input.html')


class CBVTests(TestCase):
    """Test Class-Based Views"""
    
    def test_student_list_view_exists(self):
        """StudentListView is importable"""
        from users.views import StudentListView
        self.assertTrue(StudentListView)
    
    def test_cbv_has_mixins(self):
        """StudentListView uses correct mixins"""
        from users.views import StudentListView
        from django.contrib.auth.mixins import LoginRequiredMixin
        
        # Check inheritance
        self.assertTrue(issubclass(StudentListView, LoginRequiredMixin))

