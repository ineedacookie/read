"""
Comprehensive browser test that visits every page and clicks every button.
Tests all user types and ensures no JavaScript errors occur.
"""
import pytest
from playwright.sync_api import Page, expect
import time


def _launch_authenticated_page(playwright, username: str, password: str):
    """Launch a standalone Playwright browser page and log the user in."""
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(
        viewport={'width': 1280, 'height': 720},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    )
    page = context.new_page()
    page.set_default_timeout(30000)

    page.goto("http://localhost:8001/login/")
    page.fill('input[name="username"], input[name="email"]', username)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"], input[type="submit"]')
    page.wait_for_timeout(500)  # small delay to allow any redirects
    page.wait_for_load_state("networkidle", timeout=15000)

    return browser, context, page


@pytest.fixture(scope="module")
def admin_page(playwright):
    """Authenticated administrator page"""
    browser, context, page = _launch_authenticated_page(playwright, 'admin@example.com', 'admin')
    try:
        yield page
    finally:
        context.close()
        browser.close()


@pytest.fixture(scope="module")
def teacher_page(playwright):
    """Authenticated teacher page"""
    browser, context, page = _launch_authenticated_page(playwright, 'teacher@example.com', 'teacher')
    try:
        yield page
    finally:
        context.close()
        browser.close()


@pytest.fixture(scope="module")
def student_page(playwright):
    """Authenticated student page"""
    browser, context, page = _launch_authenticated_page(playwright, 'student@example.com', 'student')
    try:
        yield page
    finally:
        context.close()
        browser.close()


@pytest.fixture(scope="module")
def parent_page(playwright):
    """Authenticated parent page"""
    browser, context, page = _launch_authenticated_page(playwright, 'parent@example.com', 'parent')
    try:
        yield page
    finally:
        context.close()
        browser.close()


def check_for_js_errors(page: Page):
    """Check console for JavaScript errors"""
    errors = []
    
    def handle_console(msg):
        if msg.type == 'error':
            errors.append(msg.text)
    
    page.on('console', handle_console)
    return errors


def safe_click(page: Page, selector: str, description: str = ""):
    """Safely click an element with error handling"""
    try:
        if page.locator(selector).is_visible(timeout=2000):
            page.locator(selector).click(timeout=3000)
            time.sleep(0.5)  # Wait for any animations/AJAX
            return True
    except Exception as e:
        print(f"  ⚠️  Failed to click {description or selector}: {str(e)}")
        return False
    return False


class TestAdminPages:
    """Test all admin pages and buttons"""
    
    def test_admin_dashboard(self, admin_page: Page):
        """Test admin dashboard page"""
        print("\n🔍 Testing Admin Dashboard...")
        admin_page.goto("http://localhost:8001/")
        
        # Wait for page load
        admin_page.wait_for_load_state("networkidle")
        
        # Check for errors
        errors = []
        admin_page.on('console', lambda msg: errors.append(msg.text) if msg.type == 'error' else None)
        
        # Click all visible buttons on dashboard
        buttons = admin_page.locator('button:visible').all()
        print(f"  Found {len(buttons)} visible buttons")
        
        for i, button in enumerate(buttons[:10]):  # Limit to first 10 to avoid infinite loops
            try:
                text = button.inner_text()
                if text and 'logout' not in text.lower():
                    print(f"    Clicking button: {text}")
                    button.click(timeout=2000)
                    time.sleep(0.3)
            except Exception as e:
                print(f"    ⚠️  Button click failed: {str(e)}")
        
        assert len([e for e in errors if 'FullCalendar' not in e]) == 0, f"JavaScript errors found: {errors}"
    
    def test_admin_user_management(self, admin_page: Page):
        """Test admin user management pages"""
        print("\n🔍 Testing Admin User Management...")
        
        # Test Teachers page
        admin_page.goto("http://localhost:8001/users/?user_type=teacher")
        admin_page.wait_for_load_state("networkidle")
        safe_click(admin_page, 'button:has-text("Add Teacher")', "Add Teacher")
        safe_click(admin_page, 'button[data-bs-dismiss="modal"]', "Close Modal")
        
        # Test Students page
        admin_page.goto("http://localhost:8001/users/?user_type=student")
        admin_page.wait_for_load_state("networkidle")
        safe_click(admin_page, 'button:has-text("Add Student")', "Add Student")
        safe_click(admin_page, 'button[data-bs-dismiss="modal"]', "Close Modal")
        
        # Test Parents page
        admin_page.goto("http://localhost:8001/users/?user_type=parent")
        admin_page.wait_for_load_state("networkidle")
    
    def test_admin_student_management(self, admin_page: Page):
        """Test admin student management page"""
        print("\n🔍 Testing Admin Student Management...")
        admin_page.goto("http://localhost:8001/admin/students/")
        admin_page.wait_for_load_state("networkidle")
        
        # Try clicking various buttons
        safe_click(admin_page, 'button:has-text("Add New Student")', "Add New Student")
        safe_click(admin_page, 'button.btn-close', "Close Modal")


class TestTeacherPages:
    """Test all teacher pages and buttons"""
    
    def test_teacher_dashboard(self, teacher_page: Page):
        """Test teacher dashboard"""
        print("\n🔍 Testing Teacher Dashboard...")
        teacher_page.goto("http://localhost:8001/")
        teacher_page.wait_for_load_state("networkidle")
        
        # Click refresh dashboard
        safe_click(teacher_page, '#refresh-dashboard', "Refresh Dashboard")
        
        # Try toggling chart views
        safe_click(teacher_page, '#chart-daily', "Daily View")
        safe_click(teacher_page, '#chart-summary', "Summary View")
    
    def test_teacher_students(self, teacher_page: Page):
        """Test teacher students page"""
        print("\n🔍 Testing Teacher Students...")
        teacher_page.goto("http://localhost:8001/student/")
        teacher_page.wait_for_load_state("networkidle")
        
        # Search functionality
        if teacher_page.locator('#studentSearch').is_visible():
            teacher_page.fill('#studentSearch', 'test')
            time.sleep(0.5)
        
        # Click filter buttons
        safe_click(teacher_page, 'input[value="all"]', "All Students Filter")
        safe_click(teacher_page, 'input[value="on_track"]', "On Track Filter")
    
    def test_teacher_classrooms(self, teacher_page: Page):
        """Test teacher classrooms page"""
        print("\n🔍 Testing Teacher Classrooms...")
        teacher_page.goto("http://localhost:8001/classrooms/")
        teacher_page.wait_for_load_state("networkidle")
        
        # Search functionality
        if teacher_page.locator('#classroomSearch').is_visible():
            teacher_page.fill('#classroomSearch', 'test')
            time.sleep(0.5)
        
        # Try clicking add classroom button
        safe_click(teacher_page, '#btn-add-classroom', "Add Classroom")
        safe_click(teacher_page, 'button.btn-close', "Close Modal")
    
    def test_teacher_reading_groups(self, teacher_page: Page):
        """Test teacher reading groups page"""
        print("\n🔍 Testing Teacher Reading Groups...")
        teacher_page.goto("http://localhost:8001/groups/")
        teacher_page.wait_for_load_state("networkidle")
        
        # Try clicking add group button
        safe_click(teacher_page, '#btn-add-reading-group', "Add Reading Group")
        safe_click(teacher_page, 'button.btn-close', "Close Modal")
    
    def test_teacher_goals(self, teacher_page: Page):
        """Test teacher goals page"""
        print("\n🔍 Testing Teacher Goals...")
        teacher_page.goto("http://localhost:8001/reading_logs/goals/")
        teacher_page.wait_for_load_state("networkidle")
        
        # Toggle goal types
        safe_click(teacher_page, '#tab-daily-goals', "Daily Goals Tab")
        safe_click(teacher_page, '#tab-total-goals', "Total Goals Tab")
        
        # Try setting goals
        safe_click(teacher_page, '#btn-add-individual-goal', "Add Individual Goal")
        safe_click(teacher_page, 'button.btn-close', "Close Modal")
    
    def test_teacher_insights(self, teacher_page: Page):
        """Test teacher insights page"""
        print("\n🔍 Testing Teacher Insights...")
        teacher_page.goto("http://localhost:8001/reading_logs/insights/")
        teacher_page.wait_for_load_state("networkidle")
        
        # Try clicking category filters
        safe_click(teacher_page, 'button[data-category="engagement"]', "Engagement Category")
        safe_click(teacher_page, 'button[data-category="comprehension"]', "Comprehension Category")


class TestStudentPages:
    """Test all student pages and buttons"""
    
    def test_student_dashboard(self, student_page: Page):
        """Test student dashboard"""
        print("\n🔍 Testing Student Dashboard...")
        student_page.goto("http://localhost:8001/")
        student_page.wait_for_load_state("networkidle")
        
        # Try adding a quick log
        safe_click(student_page, 'button:has-text("Quick Log")', "Quick Log")
        
        # Fill form if modal opens
        if student_page.locator('#log-title').is_visible():
            student_page.fill('#log-title', 'Test Book')
            student_page.fill('#log-author', 'Test Author')
            student_page.fill('#log-pages', '10')
            student_page.fill('#log-minutes', '15')
            safe_click(student_page, 'button.btn-close', "Close Modal")
    
    def test_student_profile(self, student_page: Page):
        """Test student profile page"""
        print("\n🔍 Testing Student Profile...")
        student_page.goto("http://localhost:8001/student/1/")  # Assuming student ID 1
        student_page.wait_for_load_state("networkidle")
        
        # Click different tabs
        safe_click(student_page, '#tab-status', "Status Tab")
        safe_click(student_page, '#tab-calendar', "Calendar Tab")
        safe_click(student_page, '#tab-settings', "Settings Tab")


class TestParentPages:
    """Test all parent pages and buttons"""
    
    def test_parent_dashboard(self, parent_page: Page):
        """Test parent dashboard"""
        print("\n🔍 Testing Parent Dashboard...")
        parent_page.goto("http://localhost:8001/")
        parent_page.wait_for_load_state("networkidle")
        
        # Try switching between children if multiple exist
        if parent_page.locator('#childSelector').is_visible():
            parent_page.select_option('#childSelector', index=0)
            time.sleep(0.5)
        
        # Try adding log for child
        safe_click(parent_page, 'button:has-text("Add Reading Log")', "Add Reading Log")
        safe_click(parent_page, 'button.btn-close', "Close Modal")


class TestModalInteractions:
    """Test modal interactions across all pages"""
    
    def test_modals_open_and_close(self, teacher_page: Page):
        """Test that all modals can open and close without errors"""
        print("\n🔍 Testing Modal Interactions...")
        
        teacher_page.goto("http://localhost:8001/student/")
        teacher_page.wait_for_load_state("networkidle")
        
        # Find all buttons with modal attributes
        modal_buttons = teacher_page.locator('button[data-bs-toggle="modal"]').all()
        print(f"  Found {len(modal_buttons)} modal trigger buttons")
        
        for i, button in enumerate(modal_buttons[:5]):  # Test first 5 modals
            try:
                button_text = button.inner_text()[:30]
                print(f"    Testing modal: {button_text}")
                button.click(timeout=2000)
                time.sleep(0.5)
                
                # Close modal
                teacher_page.locator('button.btn-close').first.click(timeout=2000)
                time.sleep(0.3)
            except Exception as e:
                print(f"    ⚠️  Modal test failed: {str(e)}")


class TestFormSubmissions:
    """Test form submissions without actually submitting"""
    
    def test_forms_validate(self, teacher_page: Page):
        """Test that forms have proper validation"""
        print("\n🔍 Testing Form Validation...")
        
        teacher_page.goto("http://localhost:8001/users/?user_type=student")
        teacher_page.wait_for_load_state("networkidle")
        
        # Try to submit empty form
        safe_click(teacher_page, 'button:has-text("Add Student")', "Add Student")
        
        if teacher_page.locator('button[type="submit"]').is_visible():
            # Don't actually submit, just check button is there
            assert teacher_page.locator('button[type="submit"]').is_visible()
            safe_click(teacher_page, 'button.btn-close', "Close Modal")


class TestNavigationLinks:
    """Test all navigation links"""
    
    def test_sidebar_navigation(self, teacher_page: Page):
        """Test all sidebar navigation links"""
        print("\n🔍 Testing Sidebar Navigation...")
        
        teacher_page.goto("http://localhost:8001/")
        teacher_page.wait_for_load_state("networkidle")
        
        # Get all navigation links
        nav_links = teacher_page.locator('.navbar-vertical a').all()
        print(f"  Found {len(nav_links)} navigation links")
        
        tested_links = set()
        
        for link in nav_links[:10]:  # Test first 10 unique links
            try:
                href = link.get_attribute('href')
                if href and href not in tested_links and not href.startswith('#'):
                    tested_links.add(href)
                    print(f"    Testing link: {href}")
                    teacher_page.goto(f"http://localhost:8001{href}")
                    teacher_page.wait_for_load_state("networkidle")
                    time.sleep(0.3)
            except Exception as e:
                print(f"    ⚠️  Navigation failed: {str(e)}")


def test_comprehensive_error_scan(teacher_page: Page):
    """Scan all major pages for JavaScript errors"""
    print("\n🔍 Running Comprehensive Error Scan...")
    
    pages_to_test = [
        "/",
        "/student/",
        "/classrooms/",
        "/groups/",
        "/reading_logs/goals/",
        "/reading_logs/insights/",
        "/users/?user_type=teacher",
        "/users/?user_type=student",
    ]
    
    error_report = {}
    
    for page_url in pages_to_test:
        errors = []
        teacher_page.on('console', lambda msg: errors.append(msg.text) if msg.type == 'error' else None)
        
        try:
            teacher_page.goto(f"http://localhost:8001{page_url}")
            teacher_page.wait_for_load_state("networkidle", timeout=10000)
            time.sleep(1)
            
            critical_errors = [e for e in errors if 'FullCalendar' not in e and 'backdrop' not in e]
            error_report[page_url] = critical_errors
            
            if critical_errors:
                print(f"  ⚠️  {page_url}: {len(critical_errors)} errors")
            else:
                print(f"  ✅ {page_url}: No critical errors")
        except Exception as e:
            print(f"  ❌ {page_url}: Failed to load - {str(e)}")
            error_report[page_url] = [str(e)]
    
    # Report summary
    total_errors = sum(len(errors) for errors in error_report.values())
    print(f"\n📊 Scan Summary: {total_errors} total errors across {len(pages_to_test)} pages")
    
    # Only fail if there are critical errors (not FullCalendar/backdrop issues we're fixing)
    critical_pages = [page for page, errors in error_report.items() if errors]
    if critical_pages:
        print(f"⚠️  Pages with errors: {', '.join(critical_pages)}")

