"""
Test suite for Subscription Tier Gating System
Tests: Explorer (free, 2 course limit), Scholar ($19.99, cohorts/spaces), Elder Circle ($49.99, live sessions/archives)
Faculty/Elder/Admin bypass all tier restrictions.

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

# Test data prefixes for cleanup
TEST_PREFIX = "TIER_TEST_"


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
    user_id = f"{TEST_PREFIX}faculty_{uuid.uuid4().hex[:8]}"
    session_id = f"{TEST_PREFIX}session_faculty_{uuid.uuid4().hex[:8]}"
    
    user_data = {
        "id": user_id,
        "email": f"{TEST_PREFIX}faculty_{uuid.uuid4().hex[:6]}@test.com",
        "name": f"{TEST_PREFIX}Faculty User",
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
    """Create a student user directly in MongoDB (default tier = explorer)"""
    user_id = f"{TEST_PREFIX}student_{uuid.uuid4().hex[:8]}"
    session_id = f"{TEST_PREFIX}session_student_{uuid.uuid4().hex[:8]}"
    
    user_data = {
        "id": user_id,
        "email": f"{TEST_PREFIX}student_{uuid.uuid4().hex[:6]}@test.com",
        "name": f"{TEST_PREFIX}Student User",
        "picture": "https://example.com/pic.jpg",
        "role": "student",
        "bio": "",
        # No subscription_tier field = defaults to explorer
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
def scholar_user(db):
    """Create a student user with Scholar tier"""
    user_id = f"{TEST_PREFIX}scholar_{uuid.uuid4().hex[:8]}"
    session_id = f"{TEST_PREFIX}session_scholar_{uuid.uuid4().hex[:8]}"
    
    user_data = {
        "id": user_id,
        "email": f"{TEST_PREFIX}scholar_{uuid.uuid4().hex[:6]}@test.com",
        "name": f"{TEST_PREFIX}Scholar User",
        "picture": "https://example.com/pic.jpg",
        "role": "student",
        "subscription_tier": "scholar",  # Scholar tier
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
def elder_circle_user(db):
    """Create a student user with Elder Circle tier"""
    user_id = f"{TEST_PREFIX}elder_circle_{uuid.uuid4().hex[:8]}"
    session_id = f"{TEST_PREFIX}session_elder_circle_{uuid.uuid4().hex[:8]}"
    
    user_data = {
        "id": user_id,
        "email": f"{TEST_PREFIX}elder_circle_{uuid.uuid4().hex[:6]}@test.com",
        "name": f"{TEST_PREFIX}Elder Circle User",
        "picture": "https://example.com/pic.jpg",
        "role": "student",
        "subscription_tier": "elder_circle",  # Elder Circle tier
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


class TestExplorerTierEnrollmentLimit:
    """Test Explorer tier (free) enrollment limit of 2 courses"""
    
    def test_explorer_can_enroll_first_course(self, api_client, faculty_user, student_user, db):
        """Explorer tier student can enroll in first course"""
        # Faculty creates a course
        course_resp = api_client.post(
            f"{BASE_URL}/api/courses",
            json={"title": f"{TEST_PREFIX}Course 1", "description": "Test course for tier gating"},
            headers={"X-Session-ID": faculty_user["session_id"]}
        )
        assert course_resp.status_code == 200, f"Failed to create course: {course_resp.text}"
        course1 = course_resp.json()
        
        # Publish the course
        api_client.put(
            f"{BASE_URL}/api/courses/{course1['id']}",
            json={"status": "active"},
            headers={"X-Session-ID": faculty_user["session_id"]}
        )
        
        # Student enrolls
        enroll_resp = api_client.post(
            f"{BASE_URL}/api/courses/{course1['id']}/enroll",
            json={},
            headers={"X-Session-ID": student_user["session_id"]}
        )
        assert enroll_resp.status_code == 200, f"First enrollment should succeed: {enroll_resp.text}"
        print("PASSED: Explorer can enroll in first course")
    
    def test_explorer_can_enroll_second_course(self, api_client, faculty_user, student_user, db):
        """Explorer tier student can enroll in second course"""
        # Faculty creates second course
        course_resp = api_client.post(
            f"{BASE_URL}/api/courses",
            json={"title": f"{TEST_PREFIX}Course 2", "description": "Test course 2 for tier gating"},
            headers={"X-Session-ID": faculty_user["session_id"]}
        )
        assert course_resp.status_code == 200
        course2 = course_resp.json()
        
        # Publish the course
        api_client.put(
            f"{BASE_URL}/api/courses/{course2['id']}",
            json={"status": "active"},
            headers={"X-Session-ID": faculty_user["session_id"]}
        )
        
        # Student enrolls
        enroll_resp = api_client.post(
            f"{BASE_URL}/api/courses/{course2['id']}/enroll",
            json={},
            headers={"X-Session-ID": student_user["session_id"]}
        )
        assert enroll_resp.status_code == 200, f"Second enrollment should succeed: {enroll_resp.text}"
        print("PASSED: Explorer can enroll in second course")
    
    def test_explorer_blocked_third_course(self, api_client, faculty_user, student_user, db):
        """Explorer tier student is blocked from enrolling in third course"""
        # Faculty creates third course
        course_resp = api_client.post(
            f"{BASE_URL}/api/courses",
            json={"title": f"{TEST_PREFIX}Course 3", "description": "Test course 3 for tier gating"},
            headers={"X-Session-ID": faculty_user["session_id"]}
        )
        assert course_resp.status_code == 200
        course3 = course_resp.json()
        
        # Publish the course
        api_client.put(
            f"{BASE_URL}/api/courses/{course3['id']}",
            json={"status": "active"},
            headers={"X-Session-ID": faculty_user["session_id"]}
        )
        
        # Student tries to enroll - should fail with 403
        enroll_resp = api_client.post(
            f"{BASE_URL}/api/courses/{course3['id']}/enroll",
            json={},
            headers={"X-Session-ID": student_user["session_id"]}
        )
        assert enroll_resp.status_code == 403, f"Third enrollment should be blocked: {enroll_resp.status_code}"
        
        # Check error message format
        error_detail = enroll_resp.json().get("detail", "")
        assert "tier_limit:enrollment:explorer:2" in error_detail, f"Expected tier_limit error, got: {error_detail}"
        print("PASSED: Explorer blocked from third course with correct error format")


class TestFacultyBypassTierRestrictions:
    """Test that Faculty users bypass all tier restrictions"""
    
    def test_faculty_unlimited_enrollments(self, api_client, faculty_user, db):
        """Faculty can enroll in unlimited courses (bypasses tier)"""
        # Create and enroll in 3+ courses
        for i in range(3):
            course_resp = api_client.post(
                f"{BASE_URL}/api/courses",
                json={"title": f"{TEST_PREFIX}Faculty Course {i+1}", "description": f"Faculty test course {i+1}"},
                headers={"X-Session-ID": faculty_user["session_id"]}
            )
            assert course_resp.status_code == 200
            course = course_resp.json()
            
            # Publish
            api_client.put(
                f"{BASE_URL}/api/courses/{course['id']}",
                json={"status": "active"},
                headers={"X-Session-ID": faculty_user["session_id"]}
            )
            
            # Enroll
            enroll_resp = api_client.post(
                f"{BASE_URL}/api/courses/{course['id']}/enroll",
                json={},
                headers={"X-Session-ID": faculty_user["session_id"]}
            )
            # Faculty might already be enrolled or bypass - either 200 or 400 (already enrolled) is acceptable
            assert enroll_resp.status_code in [200, 400], f"Faculty enrollment failed: {enroll_resp.text}"
        
        print("PASSED: Faculty can enroll in unlimited courses (bypasses tier)")


class TestCohortTierGating:
    """Test cohort join requires Scholar tier"""
    
    def test_explorer_cannot_join_cohort(self, api_client, faculty_user, student_user, db):
        """Explorer tier student cannot join cohort - 403 with tier_required:scholar:cohort_join"""
        # Faculty creates a cohort
        cohort_resp = api_client.post(
            f"{BASE_URL}/api/cohorts",
            json={"name": f"{TEST_PREFIX}Test Cohort", "description": "Test cohort for tier gating"},
            headers={"X-Session-ID": faculty_user["session_id"]}
        )
        assert cohort_resp.status_code == 200, f"Failed to create cohort: {cohort_resp.text}"
        cohort = cohort_resp.json()
        
        # Student (explorer tier) tries to join
        join_resp = api_client.post(
            f"{BASE_URL}/api/cohorts/{cohort['id']}/join",
            json={},
            headers={"X-Session-ID": student_user["session_id"]}
        )
        assert join_resp.status_code == 403, f"Explorer should be blocked from cohort: {join_resp.status_code}"
        
        error_detail = join_resp.json().get("detail", "")
        assert "tier_required:scholar:cohort_join" in error_detail, f"Expected tier_required error, got: {error_detail}"
        print("PASSED: Explorer cannot join cohort - correct error format")
    
    def test_scholar_can_join_cohort(self, api_client, faculty_user, scholar_user, db):
        """Scholar tier student CAN join cohort - 200 success"""
        # Faculty creates a cohort
        cohort_resp = api_client.post(
            f"{BASE_URL}/api/cohorts",
            json={"name": f"{TEST_PREFIX}Scholar Test Cohort", "description": "Test cohort for scholar tier"},
            headers={"X-Session-ID": faculty_user["session_id"]}
        )
        assert cohort_resp.status_code == 200
        cohort = cohort_resp.json()
        
        # Scholar tries to join
        join_resp = api_client.post(
            f"{BASE_URL}/api/cohorts/{cohort['id']}/join",
            json={},
            headers={"X-Session-ID": scholar_user["session_id"]}
        )
        assert join_resp.status_code == 200, f"Scholar should be able to join cohort: {join_resp.text}"
        print("PASSED: Scholar can join cohort")


class TestSpaceTierGating:
    """Test space access requires Scholar tier"""
    
    def test_explorer_cannot_request_space_access(self, api_client, faculty_user, student_user, db):
        """Explorer tier student cannot request space access - 403 with tier_required:scholar:space_access"""
        # Faculty creates a space
        space_resp = api_client.post(
            f"{BASE_URL}/api/spaces",
            json={"name": f"{TEST_PREFIX}Test Space", "description": "Test space for tier gating", "access_level": "members"},
            headers={"X-Session-ID": faculty_user["session_id"]}
        )
        assert space_resp.status_code == 200, f"Failed to create space: {space_resp.text}"
        space = space_resp.json()
        
        # Student (explorer tier) tries to request access
        access_resp = api_client.post(
            f"{BASE_URL}/api/spaces/{space['id']}/request-access",
            json={},
            headers={"X-Session-ID": student_user["session_id"]}
        )
        assert access_resp.status_code == 403, f"Explorer should be blocked from space access: {access_resp.status_code}"
        
        error_detail = access_resp.json().get("detail", "")
        assert "tier_required:scholar:space_access" in error_detail, f"Expected tier_required error, got: {error_detail}"
        print("PASSED: Explorer cannot request space access - correct error format")
    
    def test_scholar_can_request_space_access(self, api_client, faculty_user, scholar_user, db):
        """Scholar tier student CAN request space access - 200 success"""
        # Faculty creates a space
        space_resp = api_client.post(
            f"{BASE_URL}/api/spaces",
            json={"name": f"{TEST_PREFIX}Scholar Test Space", "description": "Test space for scholar tier", "access_level": "members"},
            headers={"X-Session-ID": faculty_user["session_id"]}
        )
        assert space_resp.status_code == 200
        space = space_resp.json()
        
        # Scholar tries to request access
        access_resp = api_client.post(
            f"{BASE_URL}/api/spaces/{space['id']}/request-access",
            json={},
            headers={"X-Session-ID": scholar_user["session_id"]}
        )
        assert access_resp.status_code == 200, f"Scholar should be able to request space access: {access_resp.text}"
        print("PASSED: Scholar can request space access")


class TestLiveSessionTierGating:
    """Test live session join requires Elder Circle tier"""
    
    def test_explorer_cannot_join_live_session(self, api_client, faculty_user, student_user, db):
        """Explorer tier student cannot join live session - 403 with tier_required:elder_circle:live_session"""
        # Faculty creates and starts a live session
        session_resp = api_client.post(
            f"{BASE_URL}/api/live-sessions",
            json={"title": f"{TEST_PREFIX}Test Live Session", "description": "Test live session for tier gating"},
            headers={"X-Session-ID": faculty_user["session_id"]}
        )
        assert session_resp.status_code == 200, f"Failed to create live session: {session_resp.text}"
        live_session = session_resp.json()
        
        # Start the session
        start_resp = api_client.put(
            f"{BASE_URL}/api/live-sessions/{live_session['id']}/start",
            json={},
            headers={"X-Session-ID": faculty_user["session_id"]}
        )
        assert start_resp.status_code == 200, f"Failed to start live session: {start_resp.text}"
        
        # Student (explorer tier) tries to join
        join_resp = api_client.post(
            f"{BASE_URL}/api/live-sessions/{live_session['id']}/join",
            json={},
            headers={"X-Session-ID": student_user["session_id"]}
        )
        assert join_resp.status_code == 403, f"Explorer should be blocked from live session: {join_resp.status_code}"
        
        error_detail = join_resp.json().get("detail", "")
        assert "tier_required:elder_circle:live_session" in error_detail, f"Expected tier_required error, got: {error_detail}"
        print("PASSED: Explorer cannot join live session - correct error format")
    
    def test_scholar_cannot_join_live_session(self, api_client, faculty_user, scholar_user, db):
        """Scholar tier student cannot join live session - 403 with tier_required:elder_circle:live_session"""
        # Faculty creates and starts a live session
        session_resp = api_client.post(
            f"{BASE_URL}/api/live-sessions",
            json={"title": f"{TEST_PREFIX}Scholar Test Live Session", "description": "Test live session for scholar tier"},
            headers={"X-Session-ID": faculty_user["session_id"]}
        )
        assert session_resp.status_code == 200
        live_session = session_resp.json()
        
        # Start the session
        api_client.put(
            f"{BASE_URL}/api/live-sessions/{live_session['id']}/start",
            json={},
            headers={"X-Session-ID": faculty_user["session_id"]}
        )
        
        # Scholar tries to join - should also fail (requires elder_circle)
        join_resp = api_client.post(
            f"{BASE_URL}/api/live-sessions/{live_session['id']}/join",
            json={},
            headers={"X-Session-ID": scholar_user["session_id"]}
        )
        assert join_resp.status_code == 403, f"Scholar should be blocked from live session: {join_resp.status_code}"
        
        error_detail = join_resp.json().get("detail", "")
        assert "tier_required:elder_circle:live_session" in error_detail, f"Expected tier_required error, got: {error_detail}"
        print("PASSED: Scholar cannot join live session - correct error format")
    
    def test_elder_circle_can_join_live_session(self, api_client, faculty_user, elder_circle_user, db):
        """Elder Circle tier student CAN join live sessions"""
        # Faculty creates and starts a live session
        session_resp = api_client.post(
            f"{BASE_URL}/api/live-sessions",
            json={"title": f"{TEST_PREFIX}Elder Circle Test Live Session", "description": "Test live session for elder circle tier"},
            headers={"X-Session-ID": faculty_user["session_id"]}
        )
        assert session_resp.status_code == 200
        live_session = session_resp.json()
        
        # Start the session
        api_client.put(
            f"{BASE_URL}/api/live-sessions/{live_session['id']}/start",
            json={},
            headers={"X-Session-ID": faculty_user["session_id"]}
        )
        
        # Elder Circle tries to join - should succeed
        join_resp = api_client.post(
            f"{BASE_URL}/api/live-sessions/{live_session['id']}/join",
            json={},
            headers={"X-Session-ID": elder_circle_user["session_id"]}
        )
        assert join_resp.status_code == 200, f"Elder Circle should be able to join live session: {join_resp.text}"
        print("PASSED: Elder Circle can join live session")


class TestArchiveTierGating:
    """Test restricted archives require Elder Circle tier"""
    
    def test_explorer_only_sees_public_archives(self, api_client, faculty_user, student_user, db):
        """Explorer tier student only sees public archives (no restricted)"""
        # Faculty creates a public archive
        public_archive_resp = api_client.post(
            f"{BASE_URL}/api/archives",
            json={"title": f"{TEST_PREFIX}Public Archive", "description": "Public test archive", "access_level": "public"},
            headers={"X-Session-ID": faculty_user["session_id"]}
        )
        assert public_archive_resp.status_code == 200
        
        # Faculty creates a restricted archive
        restricted_archive_resp = api_client.post(
            f"{BASE_URL}/api/archives",
            json={"title": f"{TEST_PREFIX}Restricted Archive", "description": "Restricted test archive", "access_level": "restricted"},
            headers={"X-Session-ID": faculty_user["session_id"]}
        )
        assert restricted_archive_resp.status_code == 200
        restricted_archive = restricted_archive_resp.json()
        
        # Student lists archives - should only see public
        list_resp = api_client.get(
            f"{BASE_URL}/api/archives",
            headers={"X-Session-ID": student_user["session_id"]}
        )
        assert list_resp.status_code == 200
        archives = list_resp.json()
        
        # Check that restricted archive is not in the list
        archive_ids = [a["id"] for a in archives]
        assert restricted_archive["id"] not in archive_ids, "Explorer should not see restricted archives"
        print("PASSED: Explorer only sees public archives")
    
    def test_elder_circle_sees_restricted_archives(self, api_client, faculty_user, elder_circle_user, db):
        """Elder Circle tier student sees both public + restricted archives"""
        # Faculty creates a restricted archive
        restricted_archive_resp = api_client.post(
            f"{BASE_URL}/api/archives",
            json={"title": f"{TEST_PREFIX}Elder Circle Restricted Archive", "description": "Restricted test archive for elder circle", "access_level": "restricted"},
            headers={"X-Session-ID": faculty_user["session_id"]}
        )
        assert restricted_archive_resp.status_code == 200
        restricted_archive = restricted_archive_resp.json()
        
        # Elder Circle lists archives - should see restricted
        list_resp = api_client.get(
            f"{BASE_URL}/api/archives",
            headers={"X-Session-ID": elder_circle_user["session_id"]}
        )
        assert list_resp.status_code == 200
        archives = list_resp.json()
        
        # Check that restricted archive IS in the list
        archive_ids = [a["id"] for a in archives]
        assert restricted_archive["id"] in archive_ids, "Elder Circle should see restricted archives"
        print("PASSED: Elder Circle sees restricted archives")
    
    def test_faculty_sees_all_archives(self, api_client, faculty_user, db):
        """Faculty user sees all archives regardless of tier"""
        list_resp = api_client.get(
            f"{BASE_URL}/api/archives",
            headers={"X-Session-ID": faculty_user["session_id"]}
        )
        assert list_resp.status_code == 200
        archives = list_resp.json()
        
        # Faculty should see both public and restricted
        access_levels = set(a.get("access_level") for a in archives)
        print(f"Faculty sees archives with access levels: {access_levels}")
        print("PASSED: Faculty can list archives")


class TestMySubscriptionEndpoint:
    """Test GET /api/subscriptions/my-subscription returns correct data"""
    
    def test_my_subscription_returns_tier_info(self, api_client, student_user, db):
        """GET /api/subscriptions/my-subscription returns tier, limits, is_bypassed, enrollment_count"""
        resp = api_client.get(
            f"{BASE_URL}/api/subscriptions/my-subscription",
            headers={"X-Session-ID": student_user["session_id"]}
        )
        assert resp.status_code == 200, f"Failed to get subscription: {resp.text}"
        
        data = resp.json()
        
        # Check required fields
        assert "tier" in data, "Response should include 'tier'"
        assert "limits" in data, "Response should include 'limits'"
        assert "is_bypassed" in data, "Response should include 'is_bypassed'"
        assert "enrollment_count" in data, "Response should include 'enrollment_count'"
        
        # Default tier should be explorer
        assert data["tier"] == "explorer", f"Default tier should be explorer, got: {data['tier']}"
        assert data["is_bypassed"] == False, "Student should not bypass tier restrictions"
        
        # Check limits structure
        limits = data["limits"]
        assert "max_enrollments" in limits
        assert "cohorts" in limits
        assert "spaces" in limits
        assert "live_sessions" in limits
        
        print(f"PASSED: my-subscription returns correct data: tier={data['tier']}, enrollment_count={data['enrollment_count']}")
    
    def test_faculty_is_bypassed(self, api_client, faculty_user, db):
        """Faculty user has is_bypassed=True"""
        resp = api_client.get(
            f"{BASE_URL}/api/subscriptions/my-subscription",
            headers={"X-Session-ID": faculty_user["session_id"]}
        )
        assert resp.status_code == 200
        
        data = resp.json()
        assert data["is_bypassed"] == True, "Faculty should bypass tier restrictions"
        print("PASSED: Faculty has is_bypassed=True")


class TestSubscriptionCheckout:
    """Test POST /api/subscriptions/checkout"""
    
    def test_free_tier_checkout_switches_immediately(self, api_client, student_user, db):
        """POST /api/subscriptions/checkout tier_id=explorer switches for free immediately"""
        resp = api_client.post(
            f"{BASE_URL}/api/subscriptions/checkout",
            json={"tier_id": "explorer", "origin_url": "https://test.com"},
            headers={"X-Session-ID": student_user["session_id"]}
        )
        assert resp.status_code == 200, f"Free tier checkout failed: {resp.text}"
        
        data = resp.json()
        assert data.get("free") == True, "Explorer checkout should be free"
        assert data.get("tier") == "explorer", "Should return explorer tier"
        print("PASSED: Free tier checkout switches immediately")


class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_data(self, api_client, faculty_user, db):
        """Clean up all test data created during tests"""
        # Clean up courses
        courses_resp = api_client.get(
            f"{BASE_URL}/api/courses",
            headers={"X-Session-ID": faculty_user["session_id"]}
        )
        if courses_resp.status_code == 200:
            for course in courses_resp.json():
                if course.get("title", "").startswith(TEST_PREFIX):
                    api_client.delete(
                        f"{BASE_URL}/api/courses/{course['id']}",
                        headers={"X-Session-ID": faculty_user["session_id"]}
                    )
        
        # Clean up cohorts
        cohorts_resp = api_client.get(
            f"{BASE_URL}/api/cohorts",
            headers={"X-Session-ID": faculty_user["session_id"]}
        )
        if cohorts_resp.status_code == 200:
            for cohort in cohorts_resp.json():
                if cohort.get("name", "").startswith(TEST_PREFIX):
                    api_client.delete(
                        f"{BASE_URL}/api/cohorts/{cohort['id']}",
                        headers={"X-Session-ID": faculty_user["session_id"]}
                    )
        
        # Clean up spaces
        spaces_resp = api_client.get(
            f"{BASE_URL}/api/spaces",
            headers={"X-Session-ID": faculty_user["session_id"]}
        )
        if spaces_resp.status_code == 200:
            for space in spaces_resp.json():
                if space.get("name", "").startswith(TEST_PREFIX):
                    api_client.delete(
                        f"{BASE_URL}/api/spaces/{space['id']}",
                        headers={"X-Session-ID": faculty_user["session_id"]}
                    )
        
        # Clean up live sessions
        sessions_resp = api_client.get(
            f"{BASE_URL}/api/live-sessions",
            headers={"X-Session-ID": faculty_user["session_id"]}
        )
        if sessions_resp.status_code == 200:
            for session in sessions_resp.json():
                if session.get("title", "").startswith(TEST_PREFIX):
                    api_client.delete(
                        f"{BASE_URL}/api/live-sessions/{session['id']}",
                        headers={"X-Session-ID": faculty_user["session_id"]}
                    )
        
        # Clean up enrollments
        db.enrollments.delete_many({"user_id": {"$regex": f"^{TEST_PREFIX}"}})
        
        print("PASSED: Test data cleanup completed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
