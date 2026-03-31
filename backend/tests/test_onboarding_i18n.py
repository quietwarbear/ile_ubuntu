"""
Test suite for Iteration 12 features:
- Student Onboarding Wizard backend endpoints
- Multi-language (i18n) preference endpoints
- Regression tests for analytics and session records
"""
import pytest
import requests
import os
import uuid
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test user data
TEST_PREFIX = "ITER12_TEST_"


class TestAuthMeEndpoint:
    """Test GET /api/auth/me returns new onboarding/language/interests fields"""
    
    def test_auth_me_requires_session(self):
        """GET /api/auth/me without session should return 401"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 401 or "Session ID required" in response.text
        print("PASSED: GET /api/auth/me requires session")
    
    def test_auth_me_returns_onboarding_fields(self, authenticated_session):
        """GET /api/auth/me should return onboarding_complete, language, interests, subscription_tier"""
        response = authenticated_session.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields exist
        assert "onboarding_complete" in data, "Missing onboarding_complete field"
        assert "language" in data, "Missing language field"
        assert "interests" in data, "Missing interests field"
        assert "subscription_tier" in data, "Missing subscription_tier field"
        
        # Check types
        assert isinstance(data["onboarding_complete"], bool), "onboarding_complete should be boolean"
        assert isinstance(data["language"], str), "language should be string"
        assert isinstance(data["interests"], list), "interests should be list"
        assert isinstance(data["subscription_tier"], str), "subscription_tier should be string"
        
        print(f"PASSED: GET /api/auth/me returns all fields: onboarding_complete={data['onboarding_complete']}, language={data['language']}, interests={data['interests']}, tier={data['subscription_tier']}")


class TestOnboardingEndpoint:
    """Test PUT /api/auth/me/onboarding endpoint"""
    
    def test_onboarding_requires_auth(self):
        """PUT /api/auth/me/onboarding without session should return 401"""
        response = requests.put(
            f"{BASE_URL}/api/auth/me/onboarding",
            json={"interests": ["History"]}
        )
        assert response.status_code == 401 or "Session ID required" in response.text
        print("PASSED: PUT /api/auth/me/onboarding requires auth")
    
    def test_onboarding_saves_interests(self, authenticated_session):
        """PUT /api/auth/me/onboarding should save interests and set onboarding_complete=true"""
        test_interests = ["African Studies", "Philosophy", "Leadership"]
        
        response = authenticated_session.put(
            f"{BASE_URL}/api/auth/me/onboarding",
            json={"interests": test_interests}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        
        # Verify by fetching /me
        me_response = authenticated_session.get(f"{BASE_URL}/api/auth/me")
        assert me_response.status_code == 200
        me_data = me_response.json()
        
        assert me_data["onboarding_complete"] == True, "onboarding_complete should be True after PUT"
        assert me_data["interests"] == test_interests, f"interests should be {test_interests}"
        
        print(f"PASSED: PUT /api/auth/me/onboarding saves interests and sets onboarding_complete=true")
    
    def test_onboarding_with_empty_interests(self, authenticated_session):
        """PUT /api/auth/me/onboarding with empty interests should still work"""
        response = authenticated_session.put(
            f"{BASE_URL}/api/auth/me/onboarding",
            json={"interests": []}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print("PASSED: PUT /api/auth/me/onboarding works with empty interests")


class TestLanguageEndpoint:
    """Test PUT /api/auth/me/language endpoint"""
    
    def test_language_requires_auth(self):
        """PUT /api/auth/me/language without session should return 401"""
        response = requests.put(
            f"{BASE_URL}/api/auth/me/language",
            json={"language": "es"}
        )
        assert response.status_code == 401 or "Session ID required" in response.text
        print("PASSED: PUT /api/auth/me/language requires auth")
    
    def test_language_saves_english(self, authenticated_session):
        """PUT /api/auth/me/language with 'en' should save"""
        response = authenticated_session.put(
            f"{BASE_URL}/api/auth/me/language",
            json={"language": "en"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert data.get("language") == "en"
        
        # Verify
        me_response = authenticated_session.get(f"{BASE_URL}/api/auth/me")
        assert me_response.json()["language"] == "en"
        print("PASSED: PUT /api/auth/me/language saves 'en'")
    
    def test_language_saves_spanish(self, authenticated_session):
        """PUT /api/auth/me/language with 'es' should save"""
        response = authenticated_session.put(
            f"{BASE_URL}/api/auth/me/language",
            json={"language": "es"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert data.get("language") == "es"
        print("PASSED: PUT /api/auth/me/language saves 'es'")
    
    def test_language_saves_yoruba(self, authenticated_session):
        """PUT /api/auth/me/language with 'yo' should save"""
        response = authenticated_session.put(
            f"{BASE_URL}/api/auth/me/language",
            json={"language": "yo"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert data.get("language") == "yo"
        print("PASSED: PUT /api/auth/me/language saves 'yo'")
    
    def test_language_rejects_invalid(self, authenticated_session):
        """PUT /api/auth/me/language with invalid language should return 400"""
        response = authenticated_session.put(
            f"{BASE_URL}/api/auth/me/language",
            json={"language": "fr"}  # French not supported
        )
        assert response.status_code == 400
        print("PASSED: PUT /api/auth/me/language rejects invalid language 'fr'")
    
    def test_language_rejects_empty(self, authenticated_session):
        """PUT /api/auth/me/language with empty language should use default or reject"""
        response = authenticated_session.put(
            f"{BASE_URL}/api/auth/me/language",
            json={"language": ""}
        )
        # Should either reject or default to 'en'
        if response.status_code == 400:
            print("PASSED: PUT /api/auth/me/language rejects empty language")
        else:
            # If it accepts, verify it defaults to 'en'
            me_response = authenticated_session.get(f"{BASE_URL}/api/auth/me")
            assert me_response.json()["language"] in ["en", ""], "Should default to 'en' or empty"
            print("PASSED: PUT /api/auth/me/language handles empty language")


class TestEnrollmentTrendsRegression:
    """Regression test for GET /api/analytics/enrollment-trends"""
    
    def test_enrollment_trends_requires_auth(self):
        """GET /api/analytics/enrollment-trends without session should return 401"""
        response = requests.get(f"{BASE_URL}/api/analytics/enrollment-trends")
        assert response.status_code == 401 or "Session ID required" in response.text
        print("PASSED: GET /api/analytics/enrollment-trends requires auth")
    
    def test_enrollment_trends_returns_array(self, authenticated_session):
        """GET /api/analytics/enrollment-trends should return array of date/enrollment objects"""
        response = authenticated_session.get(f"{BASE_URL}/api/analytics/enrollment-trends?days=7")
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        if len(data) > 0:
            first_item = data[0]
            assert "date" in first_item, "Each item should have 'date' field"
            assert "enrollments" in first_item, "Each item should have 'enrollments' field"
        
        print(f"PASSED: GET /api/analytics/enrollment-trends returns array with {len(data)} items")


class TestSessionRecordsRegression:
    """Regression test for GET /api/session-records"""
    
    def test_session_records_requires_auth(self):
        """GET /api/session-records without session should return 401"""
        response = requests.get(f"{BASE_URL}/api/session-records")
        assert response.status_code == 401 or "Session ID required" in response.text
        print("PASSED: GET /api/session-records requires auth")
    
    def test_session_records_returns_list(self, authenticated_session):
        """GET /api/session-records should return list of ended sessions"""
        response = authenticated_session.get(f"{BASE_URL}/api/session-records")
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        print(f"PASSED: GET /api/session-records returns list with {len(data)} items")


# Fixtures
@pytest.fixture(scope="module")
def authenticated_session():
    """Create an authenticated session using MongoDB directly"""
    from pymongo import MongoClient
    
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    db_name = os.environ.get('DB_NAME', 'test_database')
    client = MongoClient(mongo_url)
    db = client[db_name]
    
    # Create test user
    test_user_id = f"{TEST_PREFIX}user_{uuid.uuid4().hex[:8]}"
    test_session_id = f"{TEST_PREFIX}session_{uuid.uuid4().hex[:8]}"
    
    test_user = {
        "id": test_user_id,
        "email": f"{test_user_id}@test.com",
        "name": "Test User Iter12",
        "picture": "https://example.com/pic.jpg",
        "role": "faculty",  # Faculty to access analytics
        "bio": "",
        "subscription_tier": "elder_circle",
        "onboarding_complete": False,
        "language": "en",
        "interests": [],
        "created_at": datetime.now(timezone.utc)
    }
    
    test_session = {
        "session_id": test_session_id,
        "user_id": test_user_id,
        "session_token": f"token_{uuid.uuid4().hex}",
        "expires_at": datetime(2030, 1, 1, tzinfo=timezone.utc)
    }
    
    db.users.insert_one(test_user)
    db.sessions.insert_one(test_session)
    
    # Create session with header
    session = requests.Session()
    session.headers.update({"X-Session-ID": test_session_id})
    
    yield session
    
    # Cleanup
    db.users.delete_many({"id": {"$regex": f"^{TEST_PREFIX}"}})
    db.sessions.delete_many({"session_id": {"$regex": f"^{TEST_PREFIX}"}})
    client.close()
    print(f"Cleaned up test data with prefix {TEST_PREFIX}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
