"""
Iteration 13 Backend Tests
Tests for new features:
- Certificates: /api/certificates/my-certificates, /check/{course_id}, /download/{course_id}
- Push Notifications: /api/push/vapid-key, /status, /subscribe
- Search: /api/search?q=...
"""
import pytest
import requests
import os
import uuid
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001').rstrip('/')

# MongoDB connection using same config as server
from pymongo import MongoClient
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'test_database')
client = MongoClient(MONGO_URL)
db = client[DB_NAME]

@pytest.fixture(scope="module")
def test_session_id():
    """Create a test session for authenticated requests"""
    session_id = f"ITER13_TEST_{uuid.uuid4().hex[:12]}"
    user_id = f"ITER13_USER_{uuid.uuid4().hex[:12]}"
    
    # Create test user directly in DB
    test_user = {
        "id": user_id,
        "email": f"iter13test_{uuid.uuid4().hex[:8]}@test.com",
        "name": "Iteration 13 Test User",
        "picture": "https://example.com/pic.jpg",
        "role": "student",
        "bio": "",
        "created_at": datetime.now(timezone.utc),
        "onboarding_complete": True,
        "language": "en",
    }
    db.users.insert_one(test_user)
    
    # Create session directly in DB
    session_data = {
        "session_id": session_id,
        "user_id": user_id,
        "session_token": f"test_token_{uuid.uuid4().hex}",
        "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
    }
    db.sessions.insert_one(session_data)
    
    yield session_id
    
    # Cleanup
    db.users.delete_one({"id": user_id})
    db.sessions.delete_one({"session_id": session_id})

@pytest.fixture(scope="module")
def authenticated_client(test_session_id):
    """Session with auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "X-Session-ID": test_session_id
    })
    return session


class TestCertificatesEndpoints:
    """Certificate endpoint tests"""
    
    def test_my_certificates_requires_auth(self):
        """GET /api/certificates/my-certificates requires authentication"""
        response = requests.get(f"{BASE_URL}/api/certificates/my-certificates")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASSED: /api/certificates/my-certificates requires auth")
    
    def test_my_certificates_returns_list(self, authenticated_client):
        """GET /api/certificates/my-certificates returns list with auth"""
        response = authenticated_client.get(f"{BASE_URL}/api/certificates/my-certificates")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "Expected list response"
        print(f"PASSED: /api/certificates/my-certificates returns list (count: {len(data)})")
    
    def test_check_certificate_requires_auth(self):
        """GET /api/certificates/check/{course_id} requires authentication"""
        response = requests.get(f"{BASE_URL}/api/certificates/check/test-course-id")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASSED: /api/certificates/check/{course_id} requires auth")
    
    def test_check_certificate_not_enrolled(self, authenticated_client):
        """GET /api/certificates/check/{course_id} returns not eligible if not enrolled"""
        response = authenticated_client.get(f"{BASE_URL}/api/certificates/check/nonexistent-course")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "eligible" in data, "Response should have 'eligible' field"
        assert data["eligible"] == False, "Should not be eligible for non-enrolled course"
        print(f"PASSED: /api/certificates/check returns eligibility status: {data}")
    
    def test_download_certificate_requires_auth(self):
        """GET /api/certificates/download/{course_id} requires authentication"""
        response = requests.get(f"{BASE_URL}/api/certificates/download/test-course-id")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASSED: /api/certificates/download/{course_id} requires auth")
    
    def test_download_certificate_not_enrolled(self, authenticated_client):
        """GET /api/certificates/download/{course_id} returns 404 if not enrolled"""
        response = authenticated_client.get(f"{BASE_URL}/api/certificates/download/nonexistent-course")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASSED: /api/certificates/download returns 404 for non-enrolled course")


class TestPushNotificationEndpoints:
    """Push notification endpoint tests"""
    
    def test_vapid_key_public(self):
        """GET /api/push/vapid-key is public and returns public_key"""
        response = requests.get(f"{BASE_URL}/api/push/vapid-key")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "public_key" in data, "Response should have 'public_key' field"
        print(f"PASSED: /api/push/vapid-key returns public_key (empty is ok): '{data.get('public_key', '')[:20]}...'")
    
    def test_push_status_requires_auth(self):
        """GET /api/push/status requires authentication"""
        response = requests.get(f"{BASE_URL}/api/push/status")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASSED: /api/push/status requires auth")
    
    def test_push_status_returns_subscribed(self, authenticated_client):
        """GET /api/push/status returns subscribed status with auth"""
        response = authenticated_client.get(f"{BASE_URL}/api/push/status")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "subscribed" in data, "Response should have 'subscribed' field"
        assert isinstance(data["subscribed"], bool), "'subscribed' should be boolean"
        print(f"PASSED: /api/push/status returns subscribed: {data['subscribed']}")
    
    def test_push_subscribe_requires_auth(self):
        """POST /api/push/subscribe requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/push/subscribe",
            json={"subscription": {"endpoint": "test"}},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASSED: POST /api/push/subscribe requires auth")
    
    def test_push_subscribe_requires_subscription_data(self, authenticated_client):
        """POST /api/push/subscribe requires subscription data"""
        response = authenticated_client.post(
            f"{BASE_URL}/api/push/subscribe",
            json={}
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("PASSED: POST /api/push/subscribe requires subscription data")
    
    def test_push_subscribe_accepts_subscription(self, authenticated_client):
        """POST /api/push/subscribe accepts valid subscription"""
        subscription = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/test-endpoint",
            "keys": {
                "p256dh": "test-p256dh-key",
                "auth": "test-auth-key"
            }
        }
        response = authenticated_client.post(
            f"{BASE_URL}/api/push/subscribe",
            json={"subscription": subscription}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("success") == True, "Should return success: true"
        print("PASSED: POST /api/push/subscribe accepts subscription")
    
    def test_push_unsubscribe(self, authenticated_client):
        """DELETE /api/push/subscribe removes subscription"""
        response = authenticated_client.delete(f"{BASE_URL}/api/push/subscribe")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("success") == True, "Should return success: true"
        print("PASSED: DELETE /api/push/subscribe removes subscription")


class TestSearchEndpoint:
    """Search endpoint tests"""
    
    def test_search_requires_auth(self):
        """GET /api/search requires authentication"""
        response = requests.get(f"{BASE_URL}/api/search?q=test")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASSED: /api/search requires auth")
    
    def test_search_returns_structured_results(self, authenticated_client):
        """GET /api/search?q=test returns structured results"""
        response = authenticated_client.get(f"{BASE_URL}/api/search?q=test")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        # Check for expected structure
        expected_keys = ["courses", "community", "archives", "cohorts", "spaces", "total"]
        for key in expected_keys:
            assert key in data, f"Response should have '{key}' field"
        assert isinstance(data["total"], int), "'total' should be integer"
        print(f"PASSED: /api/search returns structured results with total: {data['total']}")
    
    def test_search_short_query_returns_empty(self, authenticated_client):
        """GET /api/search with short query returns empty results"""
        response = authenticated_client.get(f"{BASE_URL}/api/search?q=a")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["total"] == 0, "Short query should return 0 results"
        print("PASSED: /api/search with short query returns empty results")
    
    def test_search_with_type_filter(self, authenticated_client):
        """GET /api/search with type filter works"""
        response = authenticated_client.get(f"{BASE_URL}/api/search?q=test&type=courses")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "courses" in data, "Response should have 'courses' field"
        print(f"PASSED: /api/search with type=courses filter works")
    
    def test_search_with_sort(self, authenticated_client):
        """GET /api/search with sort parameter works"""
        response = authenticated_client.get(f"{BASE_URL}/api/search?q=test&sort=date")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASSED: /api/search with sort=date works")


class TestRegressionEndpoints:
    """Regression tests for existing endpoints"""
    
    def test_root_endpoint(self):
        """GET / returns API info"""
        response = requests.get(f"{BASE_URL}/")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASSED: Root endpoint returns 200")
    
    def test_auth_me_requires_auth(self):
        """GET /api/auth/me requires authentication"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASSED: /api/auth/me requires auth")
    
    def test_auth_me_returns_user(self, authenticated_client):
        """GET /api/auth/me returns user data with auth"""
        response = authenticated_client.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "id" in data, "Response should have 'id' field"
        assert "role" in data, "Response should have 'role' field"
        print(f"PASSED: /api/auth/me returns user data with role: {data.get('role')}")
    
    def test_courses_list(self, authenticated_client):
        """GET /api/courses returns list"""
        response = authenticated_client.get(f"{BASE_URL}/api/courses")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "Expected list response"
        print(f"PASSED: /api/courses returns list (count: {len(data)})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
