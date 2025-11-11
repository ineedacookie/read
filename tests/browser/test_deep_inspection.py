"""
Deep inspection tests to find real issues
"""
import pytest
from playwright.sync_api import Page
import json


def test_login_session_persists(page: Page):
    """Test that login actually creates a session"""
    page.goto("http://localhost:8001/login/")
    page.wait_for_load_state('networkidle', timeout=15000)
    
    # Get form fields
    username_field = page.locator('input[type="text"], input[type="email"], input[name="username"], input[id="id_username"]').first
    password_field = page.locator('input[type="password"], input[name="password"], input[id="id_password"]').first
    
    if username_field.count() > 0 and password_field.count() > 0:
        print(f"✅ Found username and password fields")
        
        # Fill with test data
        username_field.fill('teacher@test.com')
        password_field.fill('testpass123')
        
        # Submit
        page.click('button[type="submit"], input[type="submit"]')
        page.wait_for_load_state('networkidle', timeout=15000)
        
        # Check cookies
        cookies = page.context.cookies()
        session_cookies = [c for c in cookies if 'session' in c['name'].lower()]
        
        print(f"Cookies after login: {len(cookies)}")
        print(f"Session cookies: {len(session_cookies)}")
        
        for cookie in session_cookies:
            print(f"  - {cookie['name']}: {cookie['value'][:20]}...")
        
        # Try to access protected page
        page.goto("http://localhost:8001/student/")
        page.wait_for_load_state('networkidle', timeout=15000)
        
        current_url = page.url
        print(f"After accessing /student/: {current_url}")
        
        if '/login' in current_url:
            print("⚠️ ISSUE: Login session not persisting - redirected back to login")
        else:
            print("✅ Login session working - stayed on protected page")
    else:
        print(f"⚠️ Could not find login form fields")
        print(f"Username field count: {page.locator('input').count()}")


def test_check_all_api_endpoints(page: Page):
    """Check status of all major API endpoints"""
    page.goto("http://localhost:8001/login/")
    
    endpoints = [
        "/reading_logs/api/student/progress/",
        "/reading_logs/api/parent/dashboard/",
        "/reading_logs/api/gamification/leaderboard/?scope=school",
        "/reading_logs/api/goals/",
        "/reading_logs/api/analytics/school/",
    ]
    
    print("\n=== API Endpoint Health Check ===")
    for endpoint in endpoints:
        response = page.request.get(f"http://localhost:8001{endpoint}")
        print(f"{endpoint}")
        print(f"  Status: {response.status}")
        print(f"  Redirects to login: {response.status == 302}")
        
        if response.status == 200:
            try:
                data = response.json()
                print(f"  Returns JSON: ✅")
            except:
                print(f"  Returns HTML: ⚠️")


def test_check_static_file_paths(page: Page):
    """Check that all static files have correct paths"""
    page.goto("http://localhost:8001/")
    page.wait_for_load_state('networkidle', timeout=15000)
    
    # Check CSS
    css_links = page.locator('link[rel="stylesheet"]').all()
    print(f"\n=== CSS Files ({len(css_links)}) ===")
    for i, link in enumerate(css_links[:5]):  # First 5
        href = link.get_attribute('href')
        print(f"{i+1}. {href}")
    
    # Check JS
    js_scripts = page.locator('script[src]').all()
    print(f"\n=== JavaScript Files ({len(js_scripts)}) ===")
    for i, script in enumerate(js_scripts[:5]):  # First 5
        src = script.get_attribute('src')
        print(f"{i+1}. {src}")


def test_check_for_javascript_errors(page: Page):
    """Capture and report all JavaScript errors"""
    errors = []
    warnings = []
    logs = []
    
    page.on("console", lambda msg: (
        errors.append(msg.text) if msg.type == 'error' else
        warnings.append(msg.text) if msg.type == 'warning' else
        logs.append(msg.text) if msg.type == 'log' else None
    ))
    
    page.goto("http://localhost:8001/")
    page.wait_for_load_state('networkidle', timeout=15000)
    page.wait_for_timeout(3000)  # Wait for all JS to execute
    
    print(f"\n=== JavaScript Console Output ===")
    print(f"Errors: {len(errors)}")
    for error in errors[:10]:  # First 10
        print(f"  ❌ {error}")
    
    print(f"\nWarnings: {len(warnings)}")
    for warning in warnings[:5]:  # First 5
        print(f"  ⚠️ {warning}")
    
    print(f"\nLog messages: {len(logs)}")
    for log in logs[:5]:  # First 5
        print(f"  ℹ️ {log}")


def test_check_network_requests(page: Page):
    """Monitor all network requests and find failures"""
    failed_requests = []
    
    page.on("response", lambda response: 
        failed_requests.append({
            'url': response.url,
            'status': response.status,
            'type': response.request.resource_type
        })
        if response.status >= 400
        else None
    )
    
    page.goto("http://localhost:8001/")
    page.wait_for_load_state('networkidle', timeout=15000)
    page.wait_for_timeout(2000)
    
    print(f"\n=== Failed Network Requests ({len(failed_requests)}) ===")
    for req in failed_requests[:20]:  # First 20
        print(f"  {req['status']} - {req['type']} - {req['url']}")
    
    # Categorize
    errors_404 = [r for r in failed_requests if r['status'] == 404]
    errors_403 = [r for r in failed_requests if r['status'] == 403]
    errors_500 = [r for r in failed_requests if r['status'] >= 500]
    
    print(f"\nSummary:")
    print(f"  404 errors: {len(errors_404)}")
    print(f"  403 errors: {len(errors_403)}")
    print(f"  500 errors: {len(errors_500)}")
    
    assert len(errors_500) == 0, f"Should have no 500 errors, found {len(errors_500)}"

