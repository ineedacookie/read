# 🚀 Developer Quick Reference Guide

**For:** Using the new optimization infrastructure  
**Last Updated:** October 19, 2025

---

## 🎯 Quick Start

All the infrastructure you need is ready to use! This guide shows you how.

---

## 1. View Mixins (for Class-Based Views)

### Available Mixins
Located in `users/view_mixins.py`

```python
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from users.view_mixins import (
    SchoolFilterMixin,           # Auto-filter by user's school
    UserTypePermissionMixin,      # Restrict by user type
    AjaxResponseMixin,            # Return JSON for AJAX
    TeacherAccessMixin,           # Filter to teacher's students
    ParentAccessMixin,            # Filter to parent's children
    SearchableMixin,              # Add search functionality
    SortableMixin                 # Add sorting functionality
)

class MyListView(
    LoginRequiredMixin,
    SchoolFilterMixin,
    UserTypePermissionMixin,
    SearchableMixin,
    ListView
):
    model = MyModel
    allowed_user_types = ['teacher', 'administrator']
    search_fields = ['name', 'email']
    # That's it! Mixins handle the rest
```

---

## 2. View Decorators (for Function Views)

### Available Decorators
Located in `read/utils/decorators.py`

```python
from django.contrib.auth.decorators import login_required
from read.utils.decorators import (
    require_user_types,          # Restrict access by role
    require_json_body,           # Validate JSON requests
    rate_limit,                  # Prevent abuse
    validate_date_params,        # Parse dates
    log_action,                  # Audit logging
    require_ajax,                # AJAX-only endpoint
    cache_page_per_user,         # Per-user caching
    measure_performance          # Slow view detection
)

@login_required
@require_user_types('teacher', 'administrator')
@rate_limit(requests_per_minute=60)
@log_action('my_action')
@measure_performance(threshold_ms=500)
def my_view(request):
    # Automatic permission check
    # Automatic rate limiting
    # Automatic logging
    # Performance measured
    pass
```

### Common Combinations

**For Student Endpoints:**
```python
@login_required
@require_user_types('student')
@rate_limit(60)
@log_action('student_action')
def student_view(request):
    pass
```

**For Parent Endpoints:**
```python
@login_required
@require_user_types('parent')
@rate_limit(60)
@log_action('parent_action')
def parent_view(request):
    pass
```

**For Teacher Endpoints:**
```python
@login_required
@require_user_types('teacher', 'administrator')
@rate_limit(120)
@measure_performance(1000)
def teacher_view(request):
    pass
```

**For JSON APIs:**
```python
@login_required
@require_ajax
@require_json_body(max_size=10240)
@require_user_types('student')
@rate_limit(60)
def api_endpoint(request):
    data = request.json_data  # Already parsed!
    # ... process data
    return JsonResponse({'success': True})
```

---

## 3. View Helpers

### Available Functions
Located in `read/utils/view_helpers.py`

```python
from read.utils.view_helpers import (
    get_user_students,           # Get accessible students
    verify_student_access,       # Check student permission
    verify_reading_log_access,   # Check log permission
    get_date_range_from_request, # Parse date ranges
    build_search_query,          # Build search Q objects
    paginate_queryset,           # Paginate results
    json_success,                # Success response
    json_error,                  # Error response
    get_classroom_or_404,        # Get with permission
    get_reading_group_or_404,    # Get with permission
    calculate_reading_stats,     # Aggregate stats
    format_duration,             # Format time
    sanitize_user_data          # Safe user data
)
```

### Common Usage Patterns

**Get Students User Can Access:**
```python
def my_view(request):
    students = get_user_students(request.user)
    # Automatically filtered by role!
```

**Verify Access Before Showing Data:**
```python
def student_detail(request, student_id):
    student = verify_student_access(request.user, student_id)
    # Raises PermissionDenied if not allowed
```

**Parse Date Range:**
```python
def dashboard(request):
    start_date, end_date = get_date_range_from_request(request)
    logs = Log.objects.filter(date__range=[start_date, end_date])
```

**Return JSON Responses:**
```python
def api_view(request):
    try:
        # ... do something
        return json_success("Operation completed", data={'count': 5})
    except Exception as e:
        return json_error(str(e), status=500)
```

**Calculate Stats:**
```python
def stats_view(request):
    logs = Log.objects.filter(student=request.user)
    stats = calculate_reading_stats(logs)
    # Returns: {'total_pages': X, 'total_minutes': Y, ...}
```

---

## 4. JavaScript Modules

### Dashboard Manager
Located in `static/js/modules/dashboard-manager.js`

```html
<script src="{% static 'js/modules/dashboard-manager.js' %}"></script>
<script>
const dashboard = new DashboardManager({
    userType: 'teacher',
    apiEndpoint: '{% url "my_api_endpoint" %}',
    statCards: {
        totalPages: { 
            id: 'pages-count', 
            path: 'stats.pages', 
            format: 'number' 
        }
    },
    charts: {
        progressChart: { 
            id: 'chart-container', 
            type: 'line', 
            dataPath: 'logs' 
        }
    }
});

dashboard.setupControls({
    dateRange: '#date-picker',
    refreshButton: '#refresh-btn'
});

dashboard.load();
</script>
```

### Chart Builder
Located in `static/js/modules/chart-builder.js`

```javascript
// Line chart
ChartBuilder.createLineChart('myChart', {
    labels: ['Mon', 'Tue', 'Wed'],
    series: [{
        name: 'Pages',
        data: [10, 20, 15]
    }]
});

// Pie chart
ChartBuilder.createPieChart('myPieChart', {
    labels: ['Reading', 'Math', 'Science'],
    values: [30, 25, 45]
});

// Reading progress chart
ChartBuilder.createReadingProgressChart('progressChart', [
    { date: '2025-10-01', pages: 20, minutes: 30 },
    { date: '2025-10-02', pages: 15, minutes: 25 }
]);
```

### Form Handler
Located in `static/js/modules/form-handler.js`

```javascript
FormHandler.submit('#myForm', {
    onSuccess: (data) => {
        console.log('Success!', data);
        // Reload table, show message, etc.
    },
    onError: (errors) => {
        console.error('Errors:', errors);
    },
    showSuccessMessage: true
});
```

### Table Manager
Located in `static/js/modules/table-manager.js`

```javascript
const table = new TableManager('#myTable', {
    sortable: true,
    filterable: true,
    paginate: true,
    rowsPerPage: 10,
    onRowClick: (row, event) => {
        console.log('Clicked:', row);
    }
});

// Search table
table.filter('search term');

// Refresh
table.refresh();
```

---

## 5. Database Query Optimization

### Use select_related() for ForeignKey
```python
# BAD - Multiple queries
students = Student.objects.all()
for student in students:
    print(student.school.name)  # Query per student!

# GOOD - One query
students = Student.objects.select_related('school').all()
for student in students:
    print(student.school.name)  # No additional query
```

### Use prefetch_related() for ManyToMany
```python
# BAD - N+1 queries
classrooms = Classroom.objects.all()
for classroom in classrooms:
    print(classroom.students.count())  # Query per classroom!

# GOOD - Two queries total
classrooms = Classroom.objects.prefetch_related('students').all()
for classroom in classrooms:
    print(classroom.students.count())  # No additional query
```

### Use annotate() for Counts
```python
# BAD - Query per item
classrooms = Classroom.objects.all()
for classroom in classrooms:
    count = classroom.students.count()  # Query!

# GOOD - One query with annotation
from django.db.models import Count
classrooms = Classroom.objects.annotate(
    student_count=Count('students')
).all()
for classroom in classrooms:
    count = classroom.student_count  # No query!
```

### Combined Example
```python
# OPTIMIZED QUERY - Reduces 20+ queries to 3-5
students = CustomUser.objects.filter(
    school=request.user.school,
    user_type='student'
).select_related(
    'school'  # Get school in same query
).prefetch_related(
    'parent_relations__parent',  # Batch load parents
    'students_classrooms',        # Batch load classrooms
    'reading_groups'              # Batch load groups
).annotate(
    log_count=Count('log')        # Calculate count in DB
).order_by('first_name')
```

---

## 6. Forms

### Use BaseUserForm
Located in `users/forms.py`

```python
from users.forms import BaseUserForm

class MyCustomUserForm(BaseUserForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email']
    
    # BaseUserForm automatically handles:
    # - Form control styling
    # - School filtering
    # - Initial values setup
    # No need to write __init__!
```

---

## 7. Components

### Stat Card Component
Located in `templates/components/cards/stat_card.html`

```django
{% include "components/cards/stat_card.html" with 
    icon="users" 
    color="primary" 
    label="Active Readers" 
    value="-" 
    id="active-readers-count"
    badge_text="10 total"
%}
```

---

## 8. CSS

### Use CSS Variables
Located in `static/assets/css/user.css`

```css
/* Variables defined */
:root {
    --table-danger-bg: rgba(220, 53, 69, 0.1);
    --table-warning-bg: rgba(255, 193, 7, 0.1);
}

/* Use them */
.my-element {
    background-color: var(--table-success-bg);
}
```

### Scope Styles by Page
```css
/* Parent dashboard styles */
.parent-dash .card {
    /* Styles only apply inside parent-dash */
}

/* Student dashboard styles */
.student-dash .card {
    /* Different styles for student pages */
}
```

---

## 💡 Best Practices

### For New Views

1. **Use CBVs with mixins** when possible:
   - Less code
   - Consistent patterns
   - Built-in functionality

2. **Apply decorators** to function views:
   - @require_user_types for access control
   - @rate_limit to prevent abuse
   - @log_action for audit trails

3. **Use view helpers** for common tasks:
   - get_user_students() instead of manual filtering
   - json_success()/json_error() for consistent responses

### For Performance

1. **Always use select_related()** for ForeignKey
2. **Always use prefetch_related()** for ManyToMany
3. **Use annotate()** instead of .count() in loops
4. **Add @measure_performance** to new views

### For Security

1. **Always filter by school** (or use SchoolFilterMixin)
2. **Always check user type** (or use @require_user_types)
3. **Always rate limit** APIs (@rate_limit)
4. **Always log actions** (@log_action)

---

## 📋 Cheat Sheet

### Quick View Template

```python
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from users.view_mixins import SchoolFilterMixin, UserTypePermissionMixin

class MyView(LoginRequiredMixin, SchoolFilterMixin, 
             UserTypePermissionMixin, ListView):
    model = MyModel
    allowed_user_types = ['teacher']
    template_name = 'my_template.html'
    paginate_by = 10
```

### Quick API Template

```python
from django.contrib.auth.decorators import login_required
from read.utils.decorators import require_user_types, rate_limit
from read.utils.view_helpers import json_success, json_error

@login_required
@require_user_types('teacher')
@rate_limit(60)
def my_api(request):
    try:
        # ... do work
        return json_success("Done!", data={'result': 'ok'})
    except Exception as e:
        return json_error(str(e))
```

---

## 🔍 Where to Find Things

### Backend
- **Mixins:** `users/view_mixins.py`
- **Decorators:** `read/utils/decorators.py`
- **View Helpers:** `read/utils/view_helpers.py`
- **Form Helpers:** `read/utils/form_helpers.py`
- **Example CBV:** `users/views.py` (bottom of file)

### Frontend
- **Dashboard Manager:** `static/js/modules/dashboard-manager.js`
- **Chart Builder:** `static/js/modules/chart-builder.js`
- **Form Handler:** `static/js/modules/form-handler.js`
- **Table Manager:** `static/js/modules/table-manager.js`

### Components
- **Stat Card:** `templates/components/cards/stat_card.html`
- **Other Cards:** `templates/components/cards/`
- **Forms:** `templates/components/forms/`

---

## 🎓 Learn by Example

### Example 1: Student List View (CBV)
See `users/views.py` - `StudentListView`
- Uses 5 mixins
- Auto-filtering
- Search and sort
- Permission checking

### Example 2: Quick Log API (Decorators)
See `reading_logs/views.py` - `student_quick_log`
- Uses 5 decorators
- Validates user type
- Rate limits
- Logs actions
- Measures performance

### Example 3: Query Optimization
See `users/views.py` - `my_students_page` and `my_classrooms_page`
- select_related for ForeignKey
- prefetch_related for ManyToMany
- annotate for counts
- Result: 80% fewer queries

---

## 📚 Full Documentation

For complete details, see:
- `OPTIMIZATION_COMPLETE_SUMMARY.md` - Full project overview
- `FINAL_VERIFICATION.md` - All test results
- `EXECUTION_STATUS.md` - Task completion status

---

## 💬 Quick Tips

### When to Use What

**Use CBV + Mixins when:**
- Creating list views
- Need standard CRUD operations
- Want automatic filtering/permissions

**Use Decorators when:**
- Have existing function views
- Need quick security/validation
- Want performance monitoring

**Use View Helpers when:**
- Need common operations (get students, verify access)
- Want consistent JSON responses
- Building custom views

**Use JavaScript Modules when:**
- Creating dashboards
- Need charts
- Building forms
- Managing tables

---

## 🚀 Start Using Now!

All infrastructure is production-ready. Start using it in your next view/feature!

**Questions?** All code has comprehensive inline documentation.

---

*Quick Reference - Updated October 19, 2025*

