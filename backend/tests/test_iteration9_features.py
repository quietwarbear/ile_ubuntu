"""
Iteration 9 Backend Tests
Tests for 4 new features:
1. Advanced Analytics Dashboard (GET /api/analytics/dashboard)
2. Cross-Platform Search (GET /api/search?q=term)
3. Stripe Subscription/Membership tiers
4. Edit/Delete Course Controls (RBAC)

Uses direct MongoDB access to create test users with sessions.
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'test_database')


@pytest.fixture(scope="module")
def db():
    """MongoDB connection"""
    client = MongoClient(MONGO_URL)
    database = client[DB_NAME]
    yield database
    client.close()


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def faculty_user(db):
    """Create a faculty user directly in MongoDB"""
    user_id = f"test_faculty_{uuid.uuid4().hex[:8]}"
    session_id = f"test_session_faculty_{uuid.uuid4().hex[:8]}"
    
    user_data = {
        "id": user_id,
        "email": f"test_faculty_{uuid.uuid4().hex[:6]}@test.com",
        "name": "TEST_Faculty User",
        "picture": "https://example.com/pic.jpg",
        "role": "faculty",
        "bio": "",
        "created_at": datetime.now(timezone.utc),
    }
    db.users.insert_one(user_data)
    
    session_data = {
        "session_id": session_id,
        "user_id": user_id,
        "session_token": f"token_{uuid.uuid4().hex}",
        "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
    }
    db.sessions.insert_one(session_data)
    
    yield {"user_id": user_id, "session_id": session_id, "user_data": user_data}
    
    # Cleanup
    db.users.delete_one({"id": user_id})
    db.sessions.delete_one({"session_id": session_id})


@pytest.fixture(scope="module")
def student_user(db):
    """Create a student user directly in MongoDB"""
    user_id = f"test_student_{uuid.uuid4().hex[:8]}"
    session_id = f"test_session_student_{uuid.uuid4().hex[:8]}"
    
    user_data = {
        "id": user_id,
        "email": f"test_student_{uuid.uuid4().hex[:6]}@test.com",
        "name": "TEST_Student User",
        "picture": "https://example.com/pic.jpg",
        "role": "student",
        "bio": "",
        "created_at": datetime.now(timezone.utc),
    }
    db.users.insert_one(user_data)
    
    session_data = {
        "session_id": session_id,
        "user_id": user_id,
        "session_token": f"token_{uuid.uuid4().hex}",
        "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
    }
    db.sessions.insert_one(session_data)
    
    yield {"user_id": user_id, "session_id": session_id, "user_data": user_data}
    
    # Cleanup
    db.users.delete_one({"id": user_id})
    db.sessions.delete_one({"session_id": session_id})


class TestSubscriptionTiers:
    """Test subscription tier endpoints - no auth required"""
    
    def test_get_tiers_returns_three_tiers(self, api_client):
        """GET /api/subscriptions/tiers returns 3 tiers"""
        response = api_client.get(f"{BASE_URL}/api/subscriptions/tiers")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        tiers = response.json()
        assert isinstance(tiers, list), "Tiers should be a list"
        assert len(tiers) == 3, f"Expected 3 tiers, got {len(tiers)}"
        
        tier_names = [t["name"] for t in tiers]
        assert "Explorer" in tier_names, "Explorer tier missing"
        assert "Scholar" in tier_names, "Scholar tier missing"
        assert "Elder Circle" in tier_names, "Elder Circle tier missing"
    
    def test_explorer_tier_is_free(self, api_client):
        """Explorer tier should have price 0"""
        response = api_client.get(f"{BASE_URL}/api/subscriptions/tiers")
        tiers = response.json()
        
        explorer = next((t for t in tiers if t["name"] == "Explorer"), None)
        assert explorer is not None, "Explorer tier not found"
        assert explorer["price"] == 0.0, f"Explorer should be free, got {explorer['price']}"
    
    def test_scholar_tier_price(self, api_client):
        """Scholar tier should cost $19.99"""
        response = api_client.get(f"{BASE_URL}/api/subscriptions/tiers")
        tiers = response.json()
        
        scholar = next((t for t in tiers if t["name"] == "Scholar"), None)
        assert scholar is not None, "Scholar tier not found"
        assert scholar["price"] == 19.99, f"Scholar should be $19.99, got {scholar['price']}"
    
    def test_elder_circle_tier_price(self, api_client):
        """Elder Circle tier should cost $49.99"""
        response = api_client.get(f"{BASE_URL}/api/subscriptions/tiers")
        tiers = response.json()
        
        elder = next((t for t in tiers if t["name"] == "Elder Circle"), None)
        assert elder is not None, "Elder Circle tier not found"
        assert elder["price"] == 49.99, f"Elder Circle should be $49.99, got {elder['price']}"
    
    def test_tiers_have_features(self, api_client):
        """Each tier should have features list"""
        response = api_client.get(f"{BASE_URL}/api/subscriptions/tiers")
        tiers = response.json()
        
        for tier in tiers:
            assert "features" in tier, f"Tier {tier['name']} missing features"
            assert isinstance(tier["features"], list), f"Features should be list for {tier['name']}"
            assert len(tier["features"]) > 0, f"Tier {tier['name']} should have at least one feature"


class TestMySubscription:
    """Test user subscription status"""
    
    def test_my_subscription_returns_default_explorer(self, api_client, faculty_user):
        """GET /api/subscriptions/my-subscription returns explorer by default"""
        api_client.headers.update({"X-Session-ID": faculty_user["session_id"]})
        response = api_client.get(f"{BASE_URL}/api/subscriptions/my-subscription")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "tier" in data, "Response should have 'tier' field"
        assert data["tier"] == "explorer", f"Default tier should be explorer, got {data['tier']}"


class TestSubscriptionCheckout:
    """Test subscription checkout flow"""
    
    def test_free_tier_checkout_sets_immediately(self, api_client, faculty_user):
        """POST /api/subscriptions/checkout with explorer sets free tier immediately"""
        api_client.headers.update({"X-Session-ID": faculty_user["session_id"]})
        
        response = api_client.post(f"{BASE_URL}/api/subscriptions/checkout", json={
            "tier_id": "explorer",
            "origin_url": "https://test.com"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, "Free tier checkout should succeed"
        assert data.get("free") == True, "Should indicate free tier"
        assert data.get("tier") == "explorer", "Should return explorer tier"
    
    def test_paid_tier_checkout_returns_url(self, api_client, faculty_user):
        """POST /api/subscriptions/checkout with scholar creates Stripe checkout session"""
        api_client.headers.update({"X-Session-ID": faculty_user["session_id"]})
        
        response = api_client.post(f"{BASE_URL}/api/subscriptions/checkout", json={
            "tier_id": "scholar",
            "origin_url": "https://test.com"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "url" in data, "Paid tier checkout should return URL"
        assert "session_id" in data, "Should return session_id"
        assert data["url"].startswith("http"), f"URL should be valid: {data.get('url')}"
    
    def test_elder_circle_checkout_returns_url(self, api_client, faculty_user):
        """POST /api/subscriptions/checkout with elder_circle creates Stripe checkout session"""
        api_client.headers.update({"X-Session-ID": faculty_user["session_id"]})
        
        response = api_client.post(f"{BASE_URL}/api/subscriptions/checkout", json={
            "tier_id": "elder_circle",
            "origin_url": "https://test.com"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "url" in data, "Paid tier checkout should return URL"
        assert "session_id" in data, "Should return session_id"
    
    def test_invalid_tier_returns_error(self, api_client, faculty_user):
        """POST /api/subscriptions/checkout with invalid tier returns 400"""
        api_client.headers.update({"X-Session-ID": faculty_user["session_id"]})
        
        response = api_client.post(f"{BASE_URL}/api/subscriptions/checkout", json={
            "tier_id": "invalid_tier",
            "origin_url": "https://test.com"
        })
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"


class TestTransactions:
    """Test transaction history"""
    
    def test_transactions_returns_list(self, api_client, faculty_user):
        """GET /api/subscriptions/transactions returns user's payment history"""
        api_client.headers.update({"X-Session-ID": faculty_user["session_id"]})
        
        response = api_client.get(f"{BASE_URL}/api/subscriptions/transactions")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Transactions should be a list"


class TestAnalyticsDashboard:
    """Test analytics dashboard endpoint"""
    
    def test_analytics_requires_faculty(self, api_client, student_user):
        """GET /api/analytics/dashboard requires faculty+ role"""
        api_client.headers.update({"X-Session-ID": student_user["session_id"]})
        
        response = api_client.get(f"{BASE_URL}/api/analytics/dashboard")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        # Should return error for non-faculty
        assert "error" in data, "Should return error for non-faculty user"
    
    def test_analytics_returns_overview(self, api_client, faculty_user):
        """GET /api/analytics/dashboard returns overview stats for faculty"""
        api_client.headers.update({"X-Session-ID": faculty_user["session_id"]})
        
        response = api_client.get(f"{BASE_URL}/api/analytics/dashboard")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "overview" in data, "Response should have 'overview'"
        
        overview = data["overview"]
        assert "total_users" in overview, "Overview should have total_users"
        assert "users_by_role" in overview, "Overview should have users_by_role"
        assert "total_courses" in overview, "Overview should have total_courses"
        assert "active_courses" in overview, "Overview should have active_courses"
    
    def test_analytics_users_by_role_structure(self, api_client, faculty_user):
        """GET /api/analytics/dashboard returns users_by_role with all roles"""
        api_client.headers.update({"X-Session-ID": faculty_user["session_id"]})
        
        response = api_client.get(f"{BASE_URL}/api/analytics/dashboard")
        data = response.json()
        
        users_by_role = data["overview"]["users_by_role"]
        expected_roles = ["admin", "elder", "faculty", "assistant", "student"]
        for role in expected_roles:
            assert role in users_by_role, f"users_by_role should have {role}"
    
    def test_analytics_returns_enrollment_stats(self, api_client, faculty_user):
        """GET /api/analytics/dashboard returns enrollment stats"""
        api_client.headers.update({"X-Session-ID": faculty_user["session_id"]})
        
        response = api_client.get(f"{BASE_URL}/api/analytics/dashboard")
        data = response.json()
        
        assert "enrollment" in data, "Response should have 'enrollment'"
        
        enrollment = data["enrollment"]
        assert "total" in enrollment, "Enrollment should have total"
        assert "new_this_week" in enrollment, "Enrollment should have new_this_week"
        assert "completion_rate" in enrollment, "Enrollment should have completion_rate"
        assert "new_this_month" in enrollment, "Enrollment should have new_this_month"
        assert "completed" in enrollment, "Enrollment should have completed"
    
    def test_analytics_returns_course_performance(self, api_client, faculty_user):
        """GET /api/analytics/dashboard returns course performance"""
        api_client.headers.update({"X-Session-ID": faculty_user["session_id"]})
        
        response = api_client.get(f"{BASE_URL}/api/analytics/dashboard")
        data = response.json()
        
        assert "courses" in data, "Response should have 'courses'"
        assert isinstance(data["courses"], list), "Courses should be a list"
    
    def test_analytics_returns_cohort_stats(self, api_client, faculty_user):
        """GET /api/analytics/dashboard returns cohort stats"""
        api_client.headers.update({"X-Session-ID": faculty_user["session_id"]})
        
        response = api_client.get(f"{BASE_URL}/api/analytics/dashboard")
        data = response.json()
        
        assert "cohorts" in data, "Response should have 'cohorts'"
        assert isinstance(data["cohorts"], list), "Cohorts should be a list"
    
    def test_analytics_returns_community_activity(self, api_client, faculty_user):
        """GET /api/analytics/dashboard returns community activity"""
        api_client.headers.update({"X-Session-ID": faculty_user["session_id"]})
        
        response = api_client.get(f"{BASE_URL}/api/analytics/dashboard")
        data = response.json()
        
        assert "community" in data, "Response should have 'community'"
        
        community = data["community"]
        assert "total_posts" in community, "Community should have total_posts"
        assert "total_replies" in community, "Community should have total_replies"
        assert "total_likes" in community, "Community should have total_likes"
        assert "top_contributors" in community, "Community should have top_contributors"


class TestSearch:
    """Test cross-platform search endpoint"""
    
    def test_search_short_query_returns_empty(self, api_client, faculty_user):
        """GET /api/search with short query (<2 chars) returns empty results"""
        api_client.headers.update({"X-Session-ID": faculty_user["session_id"]})
        
        response = api_client.get(f"{BASE_URL}/api/search?q=a")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["courses"] == [], "Courses should be empty for short query"
        assert data["community"] == [], "Community should be empty for short query"
        assert data["archives"] == [], "Archives should be empty for short query"
        assert data["cohorts"] == [], "Cohorts should be empty for short query"
        assert data["spaces"] == [], "Spaces should be empty for short query"
    
    def test_search_empty_query_returns_empty(self, api_client, faculty_user):
        """GET /api/search with empty query returns empty results"""
        api_client.headers.update({"X-Session-ID": faculty_user["session_id"]})
        
        response = api_client.get(f"{BASE_URL}/api/search?q=")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["courses"] == [], "Courses should be empty for empty query"
    
    def test_search_returns_all_categories(self, api_client, faculty_user):
        """GET /api/search returns results from all categories"""
        api_client.headers.update({"X-Session-ID": faculty_user["session_id"]})
        
        response = api_client.get(f"{BASE_URL}/api/search?q=test")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "courses" in data, "Response should have 'courses'"
        assert "community" in data, "Response should have 'community'"
        assert "archives" in data, "Response should have 'archives'"
        assert "cohorts" in data, "Response should have 'cohorts'"
        assert "spaces" in data, "Response should have 'spaces'"


class TestCourseEditDelete:
    """Test course edit/delete RBAC"""
    
    def test_course_edit_works_for_owner(self, api_client, faculty_user, db):
        """PUT /api/courses/{id} works for course owner"""
        api_client.headers.update({"X-Session-ID": faculty_user["session_id"]})
        
        # Create course first
        create_response = api_client.post(f"{BASE_URL}/api/courses", json={
            "title": "TEST_Course to Edit",
            "description": "Original description",
            "tags": ["test"]
        })
        
        assert create_response.status_code == 200, f"Create failed: {create_response.text}"
        course_id = create_response.json()["id"]
        
        try:
            # Edit course
            edit_response = api_client.put(f"{BASE_URL}/api/courses/{course_id}", json={
                "title": "TEST_Course Edited",
                "description": "Updated description"
            })
            
            assert edit_response.status_code == 200, f"Expected 200, got {edit_response.status_code}: {edit_response.text}"
            
            data = edit_response.json()
            assert data["title"] == "TEST_Course Edited", "Title should be updated"
            assert data["description"] == "Updated description", "Description should be updated"
        finally:
            # Cleanup
            db.courses.delete_one({"id": course_id})
            db.lessons.delete_many({"course_id": course_id})
    
    def test_course_edit_denied_for_non_owner(self, api_client, faculty_user, student_user, db):
        """PUT /api/courses/{id} denied for non-owner"""
        # Create course as faculty
        api_client.headers.update({"X-Session-ID": faculty_user["session_id"]})
        
        create_response = api_client.post(f"{BASE_URL}/api/courses", json={
            "title": "TEST_Course Owner Only",
            "description": "Only owner can edit",
            "tags": ["test"]
        })
        
        assert create_response.status_code == 200
        course_id = create_response.json()["id"]
        
        try:
            # Try to edit as student
            api_client.headers.update({"X-Session-ID": student_user["session_id"]})
            
            edit_response = api_client.put(f"{BASE_URL}/api/courses/{course_id}", json={
                "title": "Hacked Title"
            })
            
            assert edit_response.status_code == 403, f"Expected 403, got {edit_response.status_code}"
        finally:
            # Cleanup
            db.courses.delete_one({"id": course_id})
            db.lessons.delete_many({"course_id": course_id})
    
    def test_course_delete_works_for_owner(self, api_client, faculty_user, db):
        """DELETE /api/courses/{id} works for course owner"""
        api_client.headers.update({"X-Session-ID": faculty_user["session_id"]})
        
        # Create course first
        create_response = api_client.post(f"{BASE_URL}/api/courses", json={
            "title": "TEST_Course to Delete",
            "description": "Will be deleted",
            "tags": ["test"]
        })
        
        assert create_response.status_code == 200
        course_id = create_response.json()["id"]
        
        # Delete course
        delete_response = api_client.delete(f"{BASE_URL}/api/courses/{course_id}")
        
        assert delete_response.status_code == 200, f"Expected 200, got {delete_response.status_code}: {delete_response.text}"
        
        data = delete_response.json()
        assert data.get("success") == True, "Delete should return success"
        
        # Verify deleted
        get_response = api_client.get(f"{BASE_URL}/api/courses/{course_id}")
        assert get_response.status_code == 404, "Deleted course should return 404"
    
    def test_course_delete_denied_for_non_owner(self, api_client, faculty_user, student_user, db):
        """DELETE /api/courses/{id} denied for non-owner"""
        # Create course as faculty
        api_client.headers.update({"X-Session-ID": faculty_user["session_id"]})
        
        create_response = api_client.post(f"{BASE_URL}/api/courses", json={
            "title": "TEST_Course No Delete",
            "description": "Cannot be deleted by others",
            "tags": ["test"]
        })
        
        assert create_response.status_code == 200
        course_id = create_response.json()["id"]
        
        try:
            # Try to delete as student
            api_client.headers.update({"X-Session-ID": student_user["session_id"]})
            
            delete_response = api_client.delete(f"{BASE_URL}/api/courses/{course_id}")
            
            assert delete_response.status_code == 403, f"Expected 403, got {delete_response.status_code}"
        finally:
            # Cleanup
            api_client.headers.update({"X-Session-ID": faculty_user["session_id"]})
            db.courses.delete_one({"id": course_id})
            db.lessons.delete_many({"course_id": course_id})
    
    def test_course_publish_works_for_owner(self, api_client, faculty_user, db):
        """PUT /api/courses/{id} with status=active publishes course"""
        api_client.headers.update({"X-Session-ID": faculty_user["session_id"]})
        
        # Create course first
        create_response = api_client.post(f"{BASE_URL}/api/courses", json={
            "title": "TEST_Course to Publish",
            "description": "Will be published",
            "tags": ["test"]
        })
        
        assert create_response.status_code == 200
        course_id = create_response.json()["id"]
        
        try:
            # Publish course
            publish_response = api_client.put(f"{BASE_URL}/api/courses/{course_id}", json={
                "status": "active"
            })
            
            assert publish_response.status_code == 200, f"Expected 200, got {publish_response.status_code}"
            
            data = publish_response.json()
            assert data["status"] == "active", "Course should be active after publish"
        finally:
            # Cleanup
            db.courses.delete_one({"id": course_id})
            db.lessons.delete_many({"course_id": course_id})


class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_data(self, db):
        """Clean up all test data"""
        # Delete test courses
        result = db.courses.delete_many({"title": {"$regex": "^TEST_"}})
        print(f"Deleted {result.deleted_count} test courses")
        
        # Delete test lessons
        result = db.lessons.delete_many({"title": {"$regex": "^TEST_"}})
        print(f"Deleted {result.deleted_count} test lessons")
        
        # Delete test payment transactions
        result = db.payment_transactions.delete_many({"user_email": {"$regex": "^test_"}})
        print(f"Deleted {result.deleted_count} test transactions")
        
        assert True, "Cleanup completed"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
