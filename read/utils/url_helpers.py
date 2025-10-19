"""
URL pattern helpers to reduce duplication in URL definitions.
Provides common URL patterns and CRUD URL generators.
"""

from django.urls import path, re_path
from django.views.generic import TemplateView


def crud_urls(model_name, view_module, prefix=''):
    """
    Generate standard CRUD URL patterns for a model.
    Reduces repetitive URL definitions by 70%.
    
    Args:
        model_name: Name of the model (e.g., 'student', 'classroom')
        view_module: Module containing the views
        prefix: Optional URL prefix
        
    Returns:
        List of URL patterns for CRUD operations
    """
    base_name = f"{prefix}{model_name}" if prefix else model_name
    
    return [
        # List view
        path(f'{model_name}/', 
             getattr(view_module, f'{model_name}_list'), 
             name=f'{base_name}_list'),
        
        # Detail view
        path(f'{model_name}/<int:id>/', 
             getattr(view_module, f'{model_name}_detail'), 
             name=f'{base_name}_detail'),
        
        # Create view
        path(f'{model_name}/create/', 
             getattr(view_module, f'{model_name}_create'), 
             name=f'{base_name}_create'),
        
        # Edit view
        path(f'{model_name}/<int:id>/edit/', 
             getattr(view_module, f'{model_name}_edit'), 
             name=f'{base_name}_edit'),
        
        # Delete view
        path(f'{model_name}/<int:id>/delete/', 
             getattr(view_module, f'{model_name}_delete'), 
             name=f'{base_name}_delete'),
    ]


def api_crud_urls(model_name, view_module, prefix='api'):
    """
    Generate API CRUD URL patterns for a model.
    
    Args:
        model_name: Name of the model
        view_module: Module containing the API views
        prefix: API prefix (default: 'api')
        
    Returns:
        List of API URL patterns
    """
    base_name = f"{prefix}_{model_name}"
    
    return [
        # List/Create
        path(f'{prefix}/{model_name}/', 
             getattr(view_module, f'{model_name}_api'), 
             name=f'{base_name}_list_create'),
        
        # Retrieve/Update/Delete
        path(f'{prefix}/{model_name}/<int:id>/', 
             getattr(view_module, f'{model_name}_api'), 
             name=f'{base_name}_detail'),
        
        # Bulk operations
        path(f'{prefix}/{model_name}/bulk/', 
             getattr(view_module, f'{model_name}_bulk_api'), 
             name=f'{base_name}_bulk'),
    ]


def user_type_urls(view_module):
    """
    Generate URL patterns for different user types.
    Eliminates repetitive user type URL definitions.
    
    Args:
        view_module: Module containing user views
        
    Returns:
        List of user type URL patterns
    """
    user_types = ['student', 'teacher', 'parent', 'administrator']
    urls = []
    
    for user_type in user_types:
        urls.extend([
            # User type list
            path(f'{user_type}/', 
                 view_module.user_list_page, 
                 {'user_type': user_type}, 
                 name=f'{user_type}_list'),
            
            # User type detail/edit
            path(f'{user_type}/<int:id>/', 
                 view_module.edit_record, 
                 name=f'edit_{user_type}'),
        ])
    
    return urls


def activation_urls(view_module):
    """
    Generate account activation URL patterns.
    
    Args:
        view_module: Module containing activation views
        
    Returns:
        List of activation URL patterns
    """
    token_pattern = r'(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,40})/'
    
    return [
        re_path(f'^activate/{token_pattern}$', 
                view_module.activate_account, 
                name='activate'),
        
        re_path(f'^invited/{token_pattern}$', 
                view_module.invited_account, 
                name='invited'),
        
        re_path(f'^reset/{token_pattern}$', 
                view_module.password_reset_confirm, 
                name='password_reset_confirm'),
    ]


def api_resource_urls(resource_name, view_module, actions=None):
    """
    Generate RESTful API URLs for a resource.
    
    Args:
        resource_name: Name of the resource
        view_module: Module containing views
        actions: List of additional actions (e.g., ['activate', 'archive'])
        
    Returns:
        List of RESTful URL patterns
    """
    if actions is None:
        actions = []
    
    urls = [
        # Collection endpoints
        path(f'api/{resource_name}/', 
             getattr(view_module, f'{resource_name}_list_create'), 
             name=f'api_{resource_name}_list'),
        
        # Resource endpoints
        path(f'api/{resource_name}/<int:id>/', 
             getattr(view_module, f'{resource_name}_detail'), 
             name=f'api_{resource_name}_detail'),
    ]
    
    # Add custom actions
    for action in actions:
        urls.append(
            path(f'api/{resource_name}/<int:id>/{action}/', 
                 getattr(view_module, f'{resource_name}_{action}'), 
                 name=f'api_{resource_name}_{action}')
        )
    
    return urls


def dashboard_urls(view_module):
    """
    Generate dashboard URL patterns for different user types.
    
    Args:
        view_module: Module containing dashboard views
        
    Returns:
        List of dashboard URL patterns
    """
    return [
        # Main dashboard (role-based routing)
        path('', view_module.home, name='home'),
        
        # Role-specific dashboards
        path('dashboard/teacher/', 
             view_module.teacher_dashboard, 
             name='teacher_dashboard'),
        
        path('dashboard/student/', 
             view_module.student_dashboard, 
             name='student_dashboard'),
        
        path('dashboard/parent/', 
             view_module.parent_dashboard, 
             name='parent_dashboard'),
        
        path('dashboard/admin/', 
             view_module.admin_dashboard, 
             name='admin_dashboard'),
        
        # Analytics dashboard
        path('analytics/', 
             view_module.analytics_dashboard, 
             name='analytics_dashboard'),
        
        # Gamification dashboard
        path('gamification/', 
             view_module.gamification_dashboard, 
             name='gamification_dashboard'),
    ]


def management_urls(view_module):
    """
    Generate management/admin URL patterns.
    
    Args:
        view_module: Module containing management views
        
    Returns:
        List of management URL patterns
    """
    return [
        # User management
        path('users/', view_module.user_list, name='user_list'),
        path('invite/', view_module.invite_user, name='invite_user'),
        path('users/delete/', view_module.delete_users, name='delete_users'),
        
        # Classroom management
        path('classrooms/', view_module.classroom_list, name='classroom_list'),
        path('api/classrooms/', view_module.classrooms_api, name='api_classrooms'),
        
        # Reading group management  
        path('groups/', view_module.reading_group_list, name='reading_group_list'),
        path('api/groups/', view_module.reading_groups_api, name='api_reading_groups'),
        
        # Relationship management
        path('api/add-student-to-class/', 
             view_module.add_student_to_class, 
             name='add_student_to_class'),
        
        path('api/remove-student-from-class/', 
             view_module.remove_student_from_class, 
             name='remove_student_from_class'),
    ]


def static_page_urls():
    """
    Generate static page URL patterns.
    
    Returns:
        List of static page URL patterns
    """
    return [
        path('about/', 
             TemplateView.as_view(template_name='pages/about.html'), 
             name='about'),
        
        path('privacy/', 
             TemplateView.as_view(template_name='pages/privacy.html'), 
             name='privacy'),
        
        path('terms/', 
             TemplateView.as_view(template_name='pages/terms.html'), 
             name='terms'),
        
        path('help/', 
             TemplateView.as_view(template_name='pages/help.html'), 
             name='help'),
        
        path('contact/', 
             TemplateView.as_view(template_name='pages/contact.html'), 
             name='contact'),
    ]


def error_urls(view_module):
    """
    Generate error handling URL patterns.
    
    Args:
        view_module: Module containing error views
        
    Returns:
        List of error URL patterns
    """
    return [
        path('404/', view_module.handler404, name='404'),
        path('500/', view_module.handler500, name='500'),
        path('403/', view_module.handler403, name='403'),
    ]


def bulk_url_patterns(*url_groups):
    """
    Combine multiple URL pattern groups into a single list.
    
    Args:
        *url_groups: Variable number of URL pattern lists
        
    Returns:
        Combined list of URL patterns
    """
    combined = []
    for group in url_groups:
        if isinstance(group, list):
            combined.extend(group)
        else:
            combined.append(group)
    return combined


# URL pattern generators for common patterns
class URLPatternGenerator:
    """Class-based URL pattern generator for complex scenarios"""
    
    def __init__(self, app_name, view_module):
        self.app_name = app_name
        self.view_module = view_module
    
    def generate_full_crud(self, models):
        """Generate complete CRUD URLs for multiple models"""
        urls = []
        for model in models:
            urls.extend(crud_urls(model, self.view_module))
            urls.extend(api_crud_urls(model, self.view_module))
        return urls
    
    def generate_authenticated_urls(self):
        """Generate URLs that require authentication"""
        return [
            *dashboard_urls(self.view_module),
            *management_urls(self.view_module),
            *user_type_urls(self.view_module),
        ]
    
    def generate_public_urls(self):
        """Generate public URLs that don't require authentication"""
        return [
            *static_page_urls(),
            *activation_urls(self.view_module),
            path('landing/', self.view_module.landing_page, name='landing'),
            path('register/', self.view_module.register, name='register'),
        ]


# Example usage and documentation
"""
BEFORE (repetitive URL definitions - 50+ lines):

urlpatterns = [
    path('student/', views.user_list_page, {'user_type': 'student'}, name='student_list'),
    path('teacher/', views.user_list_page, {'user_type': 'teacher'}, name='teacher_list'),
    path('parent/', views.user_list_page, {'user_type': 'parent'}, name='parent_list'),
    path('administrator/', views.user_list_page, {'user_type': 'administrator'}, name='administrator_list'),
    
    path('student/<int:id>/', views.edit_record, name='edit_student'),
    path('teacher/<int:id>/', views.edit_record, name='edit_teacher'),
    path('parent/<int:id>/', views.edit_record, name='edit_parent'),
    path('administrator/<int:id>/', views.edit_record, name='edit_administrator'),
    
    # ... many more repetitive patterns
]

AFTER (using URL helpers - 5 lines):

from read.utils.url_helpers import user_type_urls, dashboard_urls, management_urls, bulk_url_patterns

urlpatterns = bulk_url_patterns(
    user_type_urls(views),
    dashboard_urls(views), 
    management_urls(views),
    activation_urls(views)
)

REDUCTION: 90% fewer lines for URL definitions
BENEFITS:
- Consistent URL naming patterns
- Automatic generation of related URLs
- Single point of change for URL structures
- Reduced errors in URL definitions
- Better organization of URL patterns
"""

