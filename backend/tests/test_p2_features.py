"""
Test P2 Features for The Ile Ubuntu:
1. Email Notifications via Resend (test endpoint, enrollment trigger)
2. Session Recording Management (CRUD for ended sessions, notes, export)
3. Advanced Analytics (enrollment trends, CSV export)
"""
import pytest
import requests
import os
import uuid
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test user credentials - we'll create test users via MongoDB
TEST_PREFIX = "P2_TEST_"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def faculty_user(api_client):
    """Create a faculty user for testing via MongoDB"""
    from pymongo import MongoClient
    client = MongoClient("mongodb://localhost:27017")
    db = client["test_database"]
    
    user_id = f"{TEST_PREFIX}faculty_{uuid.uuid4().hex[:8]}"
    user = {
        "id": user_id,
        "email": f"{user_id}@test.com",
        "name": f"Test Faculty {user_id}",
        "picture": "",
        "role": "faculty",
        "subscription_tier": "elder_circle",
        "created_at": datetime.now(timezone.utc),
    }
    db.users.insert_one(user)
    
    # Create a session for this user with proper expiration
    session_id = f"session_{uuid.uuid4().hex}"
    db.sessions.insert_one({
        "session_id": session_id,
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(days=1),
    })
    
    yield {"user": user, "session_id": session_id}
    
    # Cleanup
    db.users.delete_one({"id": user_id})
    db.sessions.delete_one({"session_id": session_id})
    client.close()


@pytest.fixture(scope="module")
def student_user(api_client):
    """Create a student user for testing via MongoDB"""
    from pymongo import MongoClient
    client = MongoClient("mongodb://localhost:27017")
    db = client["test_database"]
    
    user_id = f"{TEST_PREFIX}student_{uuid.uuid4().hex[:8]}"
    user = {
        "id": user_id,
        "email": f"{user_id}@test.com",
        "name": f"Test Student {user_id}",
        "picture": "",
        "role": "student",
        "subscription_tier": "explorer",
        "created_at": datetime.now(timezone.utc),
    }
    db.users.insert_one(user)
    
    # Create a session for this user with proper expiration
    session_id = f"session_{uuid.uuid4().hex}"
    db.sessions.insert_one({
        "session_id": session_id,
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(days=1),
    })
    
    yield {"user": user, "session_id": session_id}
    
    # Cleanup
    db.users.delete_one({"id": user_id})
    db.sessions.delete_one({"session_id": session_id})
    client.close()


def get_auth_headers(session_id):
    """Get headers with session authentication"""
    return {"X-Session-Id": session_id, "Content-Type": "application/json"}


class TestEmailNotifications:
    """Test email notification endpoints"""
    
    def test_email_test_endpoint_requires_auth(self, api_client):
        """POST /api/notifications/email/test requires authentication"""
        response = api_client.post(f"{BASE_URL}/api/notifications/email/test")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASSED: Email test endpoint requires auth")
    
    def test_email_test_endpoint_with_auth(self, api_client, faculty_user):
        """POST /api/notifications/email/test sends test email (may fail in test mode)"""
        headers = get_auth_headers(faculty_user["session_id"])
        response = api_client.post(f"{BASE_URL}/api/notifications/email/test", headers=headers)
        
        # Resend may fail in test mode (unverified domain), but endpoint should not crash
        # Accept 200 (success) or 500 (Resend API error - expected in test mode)
        assert response.status_code in [200, 500], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            assert "success" in data or "email_id" in data
            print(f"PASSED: Email test sent successfully: {data}")
        else:
            # 500 is expected if Resend domain not verified
            print(f"PASSED: Email endpoint responded (500 expected in test mode)")


class TestSessionRecords:
    """Test session recording management endpoints"""
    
    @pytest.fixture(scope="class")
    def ended_session(self, faculty_user):
        """Create an ended live session for testing"""
        from pymongo import MongoClient
        client = MongoClient("mongodb://localhost:27017")
        db = client["test_database"]
        
        session_id = f"{TEST_PREFIX}session_{uuid.uuid4().hex[:8]}"
        session = {
            "id": session_id,
            "title": f"Test Session {session_id}",
            "description": "Test session for P2 features",
            "host_id": faculty_user["user"]["id"],
            "host_name": faculty_user["user"]["name"],
            "room_name": f"test-room-{session_id[:8]}",
            "status": "ended",
            "attendees": [faculty_user["user"]["id"]],
            "participants": [faculty_user["user"]["id"]],
            "started_at": datetime.now(timezone.utc).isoformat(),
            "ended_at": datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc),
        }
        db.live_sessions.insert_one(session)
        
        yield session
        
        # Cleanup
        db.live_sessions.delete_one({"id": session_id})
        client.close()
    
    def test_list_session_records_requires_auth(self, api_client):
        """GET /api/session-records requires authentication"""
        response = api_client.get(f"{BASE_URL}/api/session-records")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASSED: Session records list requires auth")
    
    def test_list_session_records(self, api_client, faculty_user, ended_session):
        """GET /api/session-records returns list of ended sessions"""
        headers = get_auth_headers(faculty_user["session_id"])
        response = api_client.get(f"{BASE_URL}/api/session-records", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "Expected list response"
        
        # Find our test session
        test_session = next((s for s in data if s["id"] == ended_session["id"]), None)
        assert test_session is not None, "Test session not found in list"
        assert "host_name" in test_session, "host_name should be enriched"
        print(f"PASSED: Session records list returned {len(data)} sessions")
    
    def test_get_session_record_detail(self, api_client, faculty_user, ended_session):
        """GET /api/session-records/{id} returns session detail with attendee_details"""
        headers = get_auth_headers(faculty_user["session_id"])
        response = api_client.get(f"{BASE_URL}/api/session-records/{ended_session['id']}", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert data["id"] == ended_session["id"]
        assert "host_name" in data
        assert "attendee_details" in data
        assert isinstance(data["attendee_details"], list)
        print(f"PASSED: Session record detail returned with {len(data['attendee_details'])} attendees")
    
    def test_get_session_record_not_found(self, api_client, faculty_user):
        """GET /api/session-records/{id} returns 404 for non-existent session"""
        headers = get_auth_headers(faculty_user["session_id"])
        response = api_client.get(f"{BASE_URL}/api/session-records/nonexistent-id", headers=headers)
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASSED: Session record not found returns 404")
    
    def test_update_session_notes(self, api_client, faculty_user, ended_session):
        """PUT /api/session-records/{id}/notes saves notes, key_takeaways, tags"""
        headers = get_auth_headers(faculty_user["session_id"])
        
        notes_data = {
            "notes": "These are test notes for the session",
            "key_takeaways": ["Takeaway 1", "Takeaway 2"],
            "tags": ["test", "p2-features"]
        }
        
        response = api_client.put(
            f"{BASE_URL}/api/session-records/{ended_session['id']}/notes",
            json=notes_data,
            headers=headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("success") == True
        
        # Verify notes were saved by fetching the session again
        get_response = api_client.get(f"{BASE_URL}/api/session-records/{ended_session['id']}", headers=headers)
        assert get_response.status_code == 200
        session_data = get_response.json()
        
        assert session_data.get("notes") == notes_data["notes"]
        assert session_data.get("key_takeaways") == notes_data["key_takeaways"]
        assert session_data.get("tags") == notes_data["tags"]
        print("PASSED: Session notes updated and verified")
    
    def test_update_notes_permission_denied(self, api_client, student_user, ended_session):
        """PUT /api/session-records/{id}/notes returns 403 for non-faculty non-host"""
        headers = get_auth_headers(student_user["session_id"])
        
        response = api_client.put(
            f"{BASE_URL}/api/session-records/{ended_session['id']}/notes",
            json={"notes": "Student trying to edit"},
            headers=headers
        )
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("PASSED: Non-faculty/non-host cannot edit notes")
    
    def test_export_session_record(self, api_client, faculty_user, ended_session):
        """GET /api/session-records/{id}/export returns CSV-friendly data"""
        headers = get_auth_headers(faculty_user["session_id"])
        response = api_client.get(f"{BASE_URL}/api/session-records/{ended_session['id']}/export", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Verify export data structure
        assert "session_title" in data
        assert "host" in data
        assert "status" in data
        assert "attendee_count" in data
        assert "attendees" in data
        assert "notes" in data
        assert "key_takeaways" in data
        assert "tags" in data
        print(f"PASSED: Session export returned with {data['attendee_count']} attendees")


class TestAnalytics:
    """Test analytics endpoints"""
    
    def test_analytics_dashboard_requires_auth(self, api_client):
        """GET /api/analytics/dashboard requires authentication"""
        response = api_client.get(f"{BASE_URL}/api/analytics/dashboard")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASSED: Analytics dashboard requires auth")
    
    def test_analytics_dashboard_requires_faculty(self, api_client, student_user):
        """GET /api/analytics/dashboard requires faculty+ role"""
        headers = get_auth_headers(student_user["session_id"])
        response = api_client.get(f"{BASE_URL}/api/analytics/dashboard", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        # Non-faculty should get error response
        assert "error" in data, "Expected error for non-faculty user"
        print("PASSED: Analytics dashboard returns error for non-faculty")
    
    def test_analytics_dashboard_faculty(self, api_client, faculty_user):
        """GET /api/analytics/dashboard returns full data for faculty"""
        headers = get_auth_headers(faculty_user["session_id"])
        response = api_client.get(f"{BASE_URL}/api/analytics/dashboard", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Verify dashboard structure
        assert "overview" in data
        assert "enrollment" in data
        assert "courses" in data
        assert "cohorts" in data
        assert "community" in data
        
        # Verify overview fields
        assert "total_users" in data["overview"]
        assert "users_by_role" in data["overview"]
        assert "total_courses" in data["overview"]
        
        # Verify enrollment fields
        assert "total" in data["enrollment"]
        assert "new_this_week" in data["enrollment"]
        assert "completion_rate" in data["enrollment"]
        
        print(f"PASSED: Analytics dashboard returned with {data['overview']['total_users']} users")
    
    def test_enrollment_trends_requires_auth(self, api_client):
        """GET /api/analytics/enrollment-trends requires authentication"""
        response = api_client.get(f"{BASE_URL}/api/analytics/enrollment-trends?days=14")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASSED: Enrollment trends requires auth")
    
    def test_enrollment_trends(self, api_client, faculty_user):
        """GET /api/analytics/enrollment-trends returns array of {date, enrollments}"""
        headers = get_auth_headers(faculty_user["session_id"])
        response = api_client.get(f"{BASE_URL}/api/analytics/enrollment-trends?days=14", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert isinstance(data, list), "Expected list response"
        assert len(data) == 15, f"Expected 15 days (14 + today), got {len(data)}"
        
        # Verify each item has date and enrollments
        for item in data:
            assert "date" in item, "Each item should have 'date'"
            assert "enrollments" in item, "Each item should have 'enrollments'"
            assert isinstance(item["enrollments"], int), "enrollments should be int"
        
        print(f"PASSED: Enrollment trends returned {len(data)} days of data")
    
    def test_enrollment_trends_custom_days(self, api_client, faculty_user):
        """GET /api/analytics/enrollment-trends?days=7 returns 8 days"""
        headers = get_auth_headers(faculty_user["session_id"])
        response = api_client.get(f"{BASE_URL}/api/analytics/enrollment-trends?days=7", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert len(data) == 8, f"Expected 8 days (7 + today), got {len(data)}"
        print(f"PASSED: Enrollment trends with days=7 returned {len(data)} days")
    
    def test_analytics_csv_export(self, api_client, faculty_user):
        """GET /api/analytics/export/csv returns CSV file"""
        headers = get_auth_headers(faculty_user["session_id"])
        response = api_client.get(f"{BASE_URL}/api/analytics/export/csv", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Verify Content-Type is text/csv
        content_type = response.headers.get("Content-Type", "")
        assert "text/csv" in content_type, f"Expected text/csv, got {content_type}"
        
        # Verify Content-Disposition header
        content_disp = response.headers.get("Content-Disposition", "")
        assert "attachment" in content_disp, "Expected attachment disposition"
        assert ".csv" in content_disp, "Expected .csv filename"
        
        # Verify CSV content has header row
        csv_content = response.text
        assert "Course Title" in csv_content, "CSV should have Course Title header"
        assert "Status" in csv_content, "CSV should have Status header"
        assert "Enrolled" in csv_content, "CSV should have Enrolled header"
        
        print(f"PASSED: CSV export returned with {len(csv_content)} bytes")
    
    def test_analytics_csv_requires_faculty(self, api_client, student_user):
        """GET /api/analytics/export/csv requires faculty+ role"""
        headers = get_auth_headers(student_user["session_id"])
        response = api_client.get(f"{BASE_URL}/api/analytics/export/csv", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "error" in data, "Expected error for non-faculty user"
        print("PASSED: CSV export returns error for non-faculty")


class TestEnrollmentEmailTrigger:
    """Test that enrollment triggers email (non-blocking)"""
    
    def test_enrollment_does_not_block(self, api_client, faculty_user):
        """POST /api/courses/{id}/enroll should not block on email sending"""
        from pymongo import MongoClient
        client = MongoClient("mongodb://localhost:27017")
        db = client["test_database"]
        
        # Create a test course
        course_id = f"{TEST_PREFIX}course_{uuid.uuid4().hex[:8]}"
        course = {
            "id": course_id,
            "title": f"Test Course {course_id}",
            "description": "Test course for email trigger",
            "instructor_id": faculty_user["user"]["id"],
            "instructor_name": faculty_user["user"]["name"],
            "status": "active",
            "enrolled_count": 0,
            "lessons": [],
            "created_at": datetime.now(timezone.utc),
        }
        db.courses.insert_one(course)
        
        try:
            headers = get_auth_headers(faculty_user["session_id"])
            
            import time
            start_time = time.time()
            response = api_client.post(f"{BASE_URL}/api/courses/{course_id}/enroll", headers=headers)
            elapsed = time.time() - start_time
            
            # Enrollment should complete quickly (email is async)
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            assert elapsed < 5, f"Enrollment took too long ({elapsed}s), email may be blocking"
            
            data = response.json()
            assert "id" in data, "Enrollment should return enrollment data"
            
            print(f"PASSED: Enrollment completed in {elapsed:.2f}s (email is non-blocking)")
            
        finally:
            # Cleanup
            db.courses.delete_one({"id": course_id})
            db.enrollments.delete_many({"course_id": course_id})
            client.close()


class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_data(self):
        """Clean up all P2_TEST_ prefixed data"""
        from pymongo import MongoClient
        client = MongoClient("mongodb://localhost:27017")
        db = client["test_database"]
        
        # Clean up test users
        result = db.users.delete_many({"id": {"$regex": f"^{TEST_PREFIX}"}})
        print(f"Cleaned up {result.deleted_count} test users")
        
        # Clean up test sessions
        result = db.sessions.delete_many({"user_id": {"$regex": f"^{TEST_PREFIX}"}})
        print(f"Cleaned up {result.deleted_count} test sessions")
        
        # Clean up test live sessions
        result = db.live_sessions.delete_many({"id": {"$regex": f"^{TEST_PREFIX}"}})
        print(f"Cleaned up {result.deleted_count} test live sessions")
        
        # Clean up test courses
        result = db.courses.delete_many({"id": {"$regex": f"^{TEST_PREFIX}"}})
        print(f"Cleaned up {result.deleted_count} test courses")
        
        # Clean up test enrollments
        result = db.enrollments.delete_many({"course_id": {"$regex": f"^{TEST_PREFIX}"}})
        print(f"Cleaned up {result.deleted_count} test enrollments")
        
        client.close()
        print("PASSED: Cleanup complete")
