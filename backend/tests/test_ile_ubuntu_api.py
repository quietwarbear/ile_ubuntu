"""
Backend API Tests for The Ile Ubuntu - Living Learning Commons
Tests: Auth, Courses CRUD, Cohorts CRUD, Community, Archives, Messages, RBAC
"""
import pytest
import requests
import os
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient
import uuid

# Use public URL for testing
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "http://localhost:8001"

# MongoDB connection for test data setup
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'test_database')

client = MongoClient(MONGO_URL)
db = client[DB_NAME]


class TestSetup:
    """Setup test users and sessions directly in MongoDB"""
    
    @pytest.fixture(scope="class")
    def test_users(self):
        """Create test users with different roles"""
        users = {
            "admin": {
                "id": f"TEST_admin_{uuid.uuid4().hex[:8]}",
                "email": "test_admin@ileubuntu.test",
                "name": "Test Admin",
                "picture": "https://ui-avatars.com/api/?name=Test+Admin",
                "role": "admin",
                "bio": "Test admin user",
                "created_at": datetime.now(timezone.utc),
            },
            "faculty": {
                "id": f"TEST_faculty_{uuid.uuid4().hex[:8]}",
                "email": "test_faculty@ileubuntu.test",
                "name": "Test Faculty",
                "picture": "https://ui-avatars.com/api/?name=Test+Faculty",
                "role": "faculty",
                "bio": "Test faculty user",
                "created_at": datetime.now(timezone.utc),
            },
            "student": {
                "id": f"TEST_student_{uuid.uuid4().hex[:8]}",
                "email": "test_student@ileubuntu.test",
                "name": "Test Student",
                "picture": "https://ui-avatars.com/api/?name=Test+Student",
                "role": "student",
                "bio": "Test student user",
                "created_at": datetime.now(timezone.utc),
            },
        }
        
        # Insert users into MongoDB
        for role, user in users.items():
            db.users.delete_many({"email": user["email"]})  # Clean up first
            db.users.insert_one(user.copy())
        
        yield users
        
        # Cleanup after tests
        for role, user in users.items():
            db.users.delete_many({"email": user["email"]})
    
    @pytest.fixture(scope="class")
    def sessions(self, test_users):
        """Create sessions for test users"""
        sessions = {}
        for role, user in test_users.items():
            session_id = f"TEST_session_{role}_{uuid.uuid4().hex[:8]}"
            session_data = {
                "session_id": session_id,
                "user_id": user["id"],
                "session_token": f"test_token_{role}",
                "expires_at": datetime.now(timezone.utc) + timedelta(days=1),
            }
            db.sessions.delete_many({"user_id": user["id"]})  # Clean up first
            db.sessions.insert_one(session_data.copy())
            sessions[role] = session_id
        
        yield sessions
        
        # Cleanup after tests
        for role, session_id in sessions.items():
            db.sessions.delete_many({"session_id": session_id})


class TestHealthCheck(TestSetup):
    """Test API health and root endpoint"""
    
    def test_root_endpoint(self):
        """GET / returns API v2.0 message"""
        # Test internal endpoint since external returns frontend HTML
        response = requests.get("http://localhost:8001/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "v2.0" in data["message"]
        print(f"✓ Root endpoint returns: {data['message']}")


class TestAuthEndpoints(TestSetup):
    """Test authentication endpoints"""
    
    def test_get_me_without_session(self):
        """GET /api/auth/me without session returns 401"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 401
        print("✓ /api/auth/me without session returns 401")
    
    def test_get_me_with_valid_session(self, test_users, sessions):
        """GET /api/auth/me with valid session returns user data"""
        headers = {"X-Session-ID": sessions["faculty"]}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_users["faculty"]["email"]
        assert data["role"] == "faculty"
        print(f"✓ /api/auth/me returns user: {data['name']} ({data['role']})")
    
    def test_list_users_as_faculty(self, test_users, sessions):
        """GET /api/auth/users as faculty returns user list"""
        headers = {"X-Session-ID": sessions["faculty"]}
        response = requests.get(f"{BASE_URL}/api/auth/users", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ /api/auth/users returns {len(data)} users")
    
    def test_list_users_as_student_forbidden(self, test_users, sessions):
        """GET /api/auth/users as student returns 403"""
        headers = {"X-Session-ID": sessions["student"]}
        response = requests.get(f"{BASE_URL}/api/auth/users", headers=headers)
        assert response.status_code == 403
        print("✓ /api/auth/users as student returns 403 (RBAC working)")
    
    def test_update_role_as_admin(self, test_users, sessions):
        """PUT /api/auth/users/{id}/role as admin succeeds"""
        headers = {"X-Session-ID": sessions["admin"]}
        # Update student to assistant
        response = requests.put(
            f"{BASE_URL}/api/auth/users/{test_users['student']['id']}/role",
            headers=headers,
            json={"role": "assistant"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        print("✓ Admin can update user roles")
        
        # Revert back to student
        requests.put(
            f"{BASE_URL}/api/auth/users/{test_users['student']['id']}/role",
            headers=headers,
            json={"role": "student"}
        )
    
    def test_update_role_as_faculty_forbidden(self, test_users, sessions):
        """PUT /api/auth/users/{id}/role as faculty returns 403"""
        headers = {"X-Session-ID": sessions["faculty"]}
        response = requests.put(
            f"{BASE_URL}/api/auth/users/{test_users['student']['id']}/role",
            headers=headers,
            json={"role": "assistant"}
        )
        assert response.status_code == 403
        print("✓ Faculty cannot update roles (RBAC working)")


class TestCoursesCRUD(TestSetup):
    """Test Courses CRUD operations"""
    
    @pytest.fixture(scope="class")
    def created_course_id(self, test_users, sessions):
        """Create a test course and return its ID"""
        headers = {"X-Session-ID": sessions["faculty"]}
        response = requests.post(
            f"{BASE_URL}/api/courses",
            headers=headers,
            json={
                "title": "TEST_Course_Introduction to Ubuntu Philosophy",
                "description": "Learn the foundations of Ubuntu philosophy",
                "tags": ["philosophy", "ubuntu", "test"]
            }
        )
        assert response.status_code == 200
        data = response.json()
        course_id = data["id"]
        print(f"✓ Created test course: {data['title']}")
        
        yield course_id
        
        # Cleanup
        try:
            requests.delete(f"{BASE_URL}/api/courses/{course_id}", headers=headers)
        except:
            pass
    
    def test_create_course_as_faculty(self, test_users, sessions):
        """POST /api/courses as faculty succeeds"""
        headers = {"X-Session-ID": sessions["faculty"]}
        response = requests.post(
            f"{BASE_URL}/api/courses",
            headers=headers,
            json={
                "title": "TEST_Course_Faculty Created",
                "description": "A course created by faculty",
                "tags": ["test"]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "TEST_Course_Faculty Created"
        assert data["status"] == "draft"
        assert data["instructor_id"] == test_users["faculty"]["id"]
        print(f"✓ Faculty can create courses: {data['title']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/courses/{data['id']}", headers=headers)
    
    def test_create_course_as_student_forbidden(self, test_users, sessions):
        """POST /api/courses as student returns 403 (RBAC)"""
        headers = {"X-Session-ID": sessions["student"]}
        response = requests.post(
            f"{BASE_URL}/api/courses",
            headers=headers,
            json={
                "title": "TEST_Course_Student Attempt",
                "description": "Should fail"
            }
        )
        assert response.status_code == 403
        print("✓ Students cannot create courses (RBAC working)")
    
    def test_list_courses(self, test_users, sessions, created_course_id):
        """GET /api/courses returns course list"""
        headers = {"X-Session-ID": sessions["faculty"]}
        response = requests.get(f"{BASE_URL}/api/courses", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/courses returns {len(data)} courses")
    
    def test_get_course_by_id(self, test_users, sessions, created_course_id):
        """GET /api/courses/{id} returns course details"""
        headers = {"X-Session-ID": sessions["faculty"]}
        response = requests.get(f"{BASE_URL}/api/courses/{created_course_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created_course_id
        print(f"✓ GET /api/courses/{created_course_id} returns course details")
    
    def test_update_course(self, test_users, sessions, created_course_id):
        """PUT /api/courses/{id} updates course"""
        headers = {"X-Session-ID": sessions["faculty"]}
        response = requests.put(
            f"{BASE_URL}/api/courses/{created_course_id}",
            headers=headers,
            json={"title": "TEST_Course_Updated Title", "status": "active"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "TEST_Course_Updated Title"
        assert data["status"] == "active"
        print(f"✓ PUT /api/courses/{created_course_id} updates course")
    
    def test_delete_course(self, test_users, sessions):
        """DELETE /api/courses/{id} deletes course"""
        # Create a course to delete
        headers = {"X-Session-ID": sessions["faculty"]}
        create_response = requests.post(
            f"{BASE_URL}/api/courses",
            headers=headers,
            json={"title": "TEST_Course_To Delete", "description": "Will be deleted"}
        )
        course_id = create_response.json()["id"]
        
        # Delete it
        response = requests.delete(f"{BASE_URL}/api/courses/{course_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        print(f"✓ DELETE /api/courses/{course_id} deletes course")
        
        # Verify deletion
        get_response = requests.get(f"{BASE_URL}/api/courses/{course_id}", headers=headers)
        assert get_response.status_code == 404


class TestCohortsCRUD(TestSetup):
    """Test Cohorts CRUD operations"""
    
    @pytest.fixture(scope="class")
    def created_cohort_id(self, test_users, sessions):
        """Create a test cohort and return its ID"""
        headers = {"X-Session-ID": sessions["faculty"]}
        response = requests.post(
            f"{BASE_URL}/api/cohorts",
            headers=headers,
            json={
                "name": "TEST_Cohort_Spring 2026",
                "description": "Spring cohort for testing",
                "max_members": 25
            }
        )
        assert response.status_code == 200
        data = response.json()
        cohort_id = data["id"]
        print(f"✓ Created test cohort: {data['name']}")
        
        yield cohort_id
        
        # Cleanup
        try:
            requests.delete(f"{BASE_URL}/api/cohorts/{cohort_id}", headers=headers)
        except:
            pass
    
    def test_create_cohort_as_faculty(self, test_users, sessions):
        """POST /api/cohorts as faculty succeeds"""
        headers = {"X-Session-ID": sessions["faculty"]}
        response = requests.post(
            f"{BASE_URL}/api/cohorts",
            headers=headers,
            json={
                "name": "TEST_Cohort_Faculty Created",
                "description": "A cohort created by faculty",
                "max_members": 20
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "TEST_Cohort_Faculty Created"
        assert data["status"] == "upcoming"
        print(f"✓ Faculty can create cohorts: {data['name']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/cohorts/{data['id']}", headers=headers)
    
    def test_create_cohort_as_student_forbidden(self, test_users, sessions):
        """POST /api/cohorts as student returns 403"""
        headers = {"X-Session-ID": sessions["student"]}
        response = requests.post(
            f"{BASE_URL}/api/cohorts",
            headers=headers,
            json={"name": "TEST_Cohort_Student Attempt", "description": "Should fail"}
        )
        assert response.status_code == 403
        print("✓ Students cannot create cohorts (RBAC working)")
    
    def test_list_cohorts(self, test_users, sessions, created_cohort_id):
        """GET /api/cohorts returns cohort list"""
        headers = {"X-Session-ID": sessions["faculty"]}
        response = requests.get(f"{BASE_URL}/api/cohorts", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/cohorts returns {len(data)} cohorts")
    
    def test_join_cohort(self, test_users, sessions, created_cohort_id):
        """POST /api/cohorts/{id}/join adds user to cohort"""
        headers = {"X-Session-ID": sessions["student"]}
        response = requests.post(f"{BASE_URL}/api/cohorts/{created_cohort_id}/join", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        print(f"✓ Student joined cohort {created_cohort_id}")
    
    def test_join_cohort_already_member(self, test_users, sessions, created_cohort_id):
        """POST /api/cohorts/{id}/join when already member returns 400"""
        headers = {"X-Session-ID": sessions["student"]}
        response = requests.post(f"{BASE_URL}/api/cohorts/{created_cohort_id}/join", headers=headers)
        assert response.status_code == 400
        print("✓ Cannot join cohort twice")
    
    def test_leave_cohort(self, test_users, sessions, created_cohort_id):
        """POST /api/cohorts/{id}/leave removes user from cohort"""
        headers = {"X-Session-ID": sessions["student"]}
        response = requests.post(f"{BASE_URL}/api/cohorts/{created_cohort_id}/leave", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        print(f"✓ Student left cohort {created_cohort_id}")
    
    def test_delete_cohort(self, test_users, sessions):
        """DELETE /api/cohorts/{id} deletes cohort"""
        headers = {"X-Session-ID": sessions["faculty"]}
        # Create a cohort to delete
        create_response = requests.post(
            f"{BASE_URL}/api/cohorts",
            headers=headers,
            json={"name": "TEST_Cohort_To Delete", "description": "Will be deleted"}
        )
        cohort_id = create_response.json()["id"]
        
        # Delete it
        response = requests.delete(f"{BASE_URL}/api/cohorts/{cohort_id}", headers=headers)
        assert response.status_code == 200
        print(f"✓ DELETE /api/cohorts/{cohort_id} deletes cohort")


class TestCommunity(TestSetup):
    """Test Community posts, replies, and likes"""
    
    @pytest.fixture(scope="class")
    def created_post_id(self, test_users, sessions):
        """Create a test post and return its ID"""
        headers = {"X-Session-ID": sessions["faculty"]}
        response = requests.post(
            f"{BASE_URL}/api/community/posts",
            headers=headers,
            json={
                "title": "TEST_Post_Welcome to the Community",
                "content": "This is a test post for the community forum.",
                "category": "announcements"
            }
        )
        assert response.status_code == 200
        data = response.json()
        post_id = data["id"]
        print(f"✓ Created test post: {data['title']}")
        
        yield post_id
        
        # Cleanup
        try:
            requests.delete(f"{BASE_URL}/api/community/posts/{post_id}", headers=headers)
        except:
            pass
    
    def test_create_post(self, test_users, sessions):
        """POST /api/community/posts creates a post"""
        headers = {"X-Session-ID": sessions["student"]}
        response = requests.post(
            f"{BASE_URL}/api/community/posts",
            headers=headers,
            json={
                "title": "TEST_Post_Student Question",
                "content": "I have a question about the course material.",
                "category": "questions"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "TEST_Post_Student Question"
        assert data["author_id"] == test_users["student"]["id"]
        print(f"✓ Student can create posts: {data['title']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/community/posts/{data['id']}", headers=headers)
    
    def test_list_posts(self, test_users, sessions, created_post_id):
        """GET /api/community/posts returns post list"""
        headers = {"X-Session-ID": sessions["faculty"]}
        response = requests.get(f"{BASE_URL}/api/community/posts", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/community/posts returns {len(data)} posts")
    
    def test_reply_to_post(self, test_users, sessions, created_post_id):
        """POST /api/community/posts/{id}/reply adds a reply"""
        headers = {"X-Session-ID": sessions["student"]}
        response = requests.post(
            f"{BASE_URL}/api/community/posts/{created_post_id}/reply",
            headers=headers,
            json={"content": "This is a test reply from a student."}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "This is a test reply from a student."
        print(f"✓ Student replied to post {created_post_id}")
    
    def test_like_post(self, test_users, sessions, created_post_id):
        """POST /api/community/posts/{id}/like toggles like"""
        headers = {"X-Session-ID": sessions["student"]}
        # Like the post
        response = requests.post(f"{BASE_URL}/api/community/posts/{created_post_id}/like", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["liked"] == True
        print(f"✓ Student liked post {created_post_id}")
        
        # Unlike the post
        response = requests.post(f"{BASE_URL}/api/community/posts/{created_post_id}/like", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["liked"] == False
        print(f"✓ Student unliked post {created_post_id}")
    
    def test_delete_post_by_author(self, test_users, sessions):
        """DELETE /api/community/posts/{id} by author succeeds"""
        headers = {"X-Session-ID": sessions["student"]}
        # Create a post
        create_response = requests.post(
            f"{BASE_URL}/api/community/posts",
            headers=headers,
            json={"title": "TEST_Post_To Delete", "content": "Will be deleted", "category": "general"}
        )
        post_id = create_response.json()["id"]
        
        # Delete it
        response = requests.delete(f"{BASE_URL}/api/community/posts/{post_id}", headers=headers)
        assert response.status_code == 200
        print(f"✓ Author can delete their own post")


class TestArchives(TestSetup):
    """Test Archives management"""
    
    @pytest.fixture(scope="class")
    def created_archive_id(self, test_users, sessions):
        """Create a test archive and return its ID"""
        headers = {"X-Session-ID": sessions["faculty"]}
        response = requests.post(
            f"{BASE_URL}/api/archives",
            headers=headers,
            json={
                "title": "TEST_Archive_Historical Documents",
                "description": "Collection of historical documents",
                "type": "document",
                "tags": ["history", "test"],
                "access_level": "public"
            }
        )
        assert response.status_code == 200
        data = response.json()
        archive_id = data["id"]
        print(f"✓ Created test archive: {data['title']}")
        
        yield archive_id
        
        # Cleanup (admin only)
        try:
            admin_headers = {"X-Session-ID": sessions["admin"]}
            requests.delete(f"{BASE_URL}/api/archives/{archive_id}", headers=admin_headers)
        except:
            pass
    
    def test_create_archive_as_faculty(self, test_users, sessions):
        """POST /api/archives as faculty succeeds"""
        headers = {"X-Session-ID": sessions["faculty"]}
        response = requests.post(
            f"{BASE_URL}/api/archives",
            headers=headers,
            json={
                "title": "TEST_Archive_Faculty Created",
                "description": "An archive created by faculty",
                "type": "resource",
                "access_level": "public"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "TEST_Archive_Faculty Created"
        print(f"✓ Faculty can create archives: {data['title']}")
        
        # Cleanup (admin only)
        admin_headers = {"X-Session-ID": sessions["admin"]}
        requests.delete(f"{BASE_URL}/api/archives/{data['id']}", headers=admin_headers)
    
    def test_create_archive_as_student_forbidden(self, test_users, sessions):
        """POST /api/archives as student returns 403"""
        headers = {"X-Session-ID": sessions["student"]}
        response = requests.post(
            f"{BASE_URL}/api/archives",
            headers=headers,
            json={"title": "TEST_Archive_Student Attempt", "description": "Should fail"}
        )
        assert response.status_code == 403
        print("✓ Students cannot create archives (RBAC working)")
    
    def test_list_archives(self, test_users, sessions, created_archive_id):
        """GET /api/archives returns archive list"""
        headers = {"X-Session-ID": sessions["faculty"]}
        response = requests.get(f"{BASE_URL}/api/archives", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/archives returns {len(data)} archives")
    
    def test_delete_archive_as_admin(self, test_users, sessions):
        """DELETE /api/archives/{id} as admin succeeds"""
        # Create an archive first
        faculty_headers = {"X-Session-ID": sessions["faculty"]}
        create_response = requests.post(
            f"{BASE_URL}/api/archives",
            headers=faculty_headers,
            json={"title": "TEST_Archive_To Delete", "description": "Will be deleted", "access_level": "public"}
        )
        archive_id = create_response.json()["id"]
        
        # Delete as admin
        admin_headers = {"X-Session-ID": sessions["admin"]}
        response = requests.delete(f"{BASE_URL}/api/archives/{archive_id}", headers=admin_headers)
        assert response.status_code == 200
        print(f"✓ Admin can delete archives")
    
    def test_delete_archive_as_faculty_forbidden(self, test_users, sessions, created_archive_id):
        """DELETE /api/archives/{id} as faculty returns 403"""
        headers = {"X-Session-ID": sessions["faculty"]}
        response = requests.delete(f"{BASE_URL}/api/archives/{created_archive_id}", headers=headers)
        assert response.status_code == 403
        print("✓ Faculty cannot delete archives (only admin)")


class TestMessages(TestSetup):
    """Test Messages and Notifications"""
    
    def test_send_message(self, test_users, sessions):
        """POST /api/messages sends a message"""
        headers = {"X-Session-ID": sessions["faculty"]}
        response = requests.post(
            f"{BASE_URL}/api/messages",
            headers=headers,
            json={
                "recipient_id": test_users["student"]["id"],
                "message": "TEST_Message: Welcome to the course!"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "TEST_Message: Welcome to the course!"
        assert data["sender_id"] == test_users["faculty"]["id"]
        assert data["recipient_id"] == test_users["student"]["id"]
        print(f"✓ Faculty sent message to student")
    
    def test_get_messages(self, test_users, sessions):
        """GET /api/messages returns message list"""
        headers = {"X-Session-ID": sessions["student"]}
        response = requests.get(f"{BASE_URL}/api/messages", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/messages returns {len(data)} messages")
    
    def test_get_notifications(self, test_users, sessions):
        """GET /api/notifications returns notification list"""
        headers = {"X-Session-ID": sessions["student"]}
        response = requests.get(f"{BASE_URL}/api/notifications", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should have at least one notification from the message sent above
        print(f"✓ GET /api/notifications returns {len(data)} notifications")


class TestRBAC(TestSetup):
    """Test Role-Based Access Control comprehensively"""
    
    def test_student_cannot_create_course(self, test_users, sessions):
        """Students cannot create courses"""
        headers = {"X-Session-ID": sessions["student"]}
        response = requests.post(
            f"{BASE_URL}/api/courses",
            headers=headers,
            json={"title": "TEST_RBAC_Student Course", "description": "Should fail"}
        )
        assert response.status_code == 403
        print("✓ RBAC: Students cannot create courses")
    
    def test_student_cannot_create_cohort(self, test_users, sessions):
        """Students cannot create cohorts"""
        headers = {"X-Session-ID": sessions["student"]}
        response = requests.post(
            f"{BASE_URL}/api/cohorts",
            headers=headers,
            json={"name": "TEST_RBAC_Student Cohort", "description": "Should fail"}
        )
        assert response.status_code == 403
        print("✓ RBAC: Students cannot create cohorts")
    
    def test_student_cannot_create_archive(self, test_users, sessions):
        """Students cannot create archives"""
        headers = {"X-Session-ID": sessions["student"]}
        response = requests.post(
            f"{BASE_URL}/api/archives",
            headers=headers,
            json={"title": "TEST_RBAC_Student Archive", "description": "Should fail"}
        )
        assert response.status_code == 403
        print("✓ RBAC: Students cannot create archives")
    
    def test_faculty_can_create_course(self, test_users, sessions):
        """Faculty can create courses"""
        headers = {"X-Session-ID": sessions["faculty"]}
        response = requests.post(
            f"{BASE_URL}/api/courses",
            headers=headers,
            json={"title": "TEST_RBAC_Faculty Course", "description": "Should succeed"}
        )
        assert response.status_code == 200
        data = response.json()
        print("✓ RBAC: Faculty can create courses")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/courses/{data['id']}", headers=headers)
    
    def test_admin_can_create_course(self, test_users, sessions):
        """Admin can create courses"""
        headers = {"X-Session-ID": sessions["admin"]}
        response = requests.post(
            f"{BASE_URL}/api/courses",
            headers=headers,
            json={"title": "TEST_RBAC_Admin Course", "description": "Should succeed"}
        )
        assert response.status_code == 200
        data = response.json()
        print("✓ RBAC: Admin can create courses")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/courses/{data['id']}", headers=headers)


class TestCleanup:
    """Cleanup test data after all tests"""
    
    def test_cleanup_test_data(self):
        """Remove all TEST_ prefixed data"""
        # Clean up courses
        deleted_courses = db.courses.delete_many({"title": {"$regex": "^TEST_"}})
        print(f"Cleaned up {deleted_courses.deleted_count} test courses")
        
        # Clean up cohorts
        deleted_cohorts = db.cohorts.delete_many({"name": {"$regex": "^TEST_"}})
        print(f"Cleaned up {deleted_cohorts.deleted_count} test cohorts")
        
        # Clean up posts
        deleted_posts = db.community_posts.delete_many({"title": {"$regex": "^TEST_"}})
        print(f"Cleaned up {deleted_posts.deleted_count} test posts")
        
        # Clean up archives
        deleted_archives = db.archives.delete_many({"title": {"$regex": "^TEST_"}})
        print(f"Cleaned up {deleted_archives.deleted_count} test archives")
        
        # Clean up messages
        deleted_messages = db.messages.delete_many({"message": {"$regex": "^TEST_"}})
        print(f"Cleaned up {deleted_messages.deleted_count} test messages")
        
        # Clean up test users
        deleted_users = db.users.delete_many({"email": {"$regex": "@ileubuntu.test$"}})
        print(f"Cleaned up {deleted_users.deleted_count} test users")
        
        # Clean up test sessions
        deleted_sessions = db.sessions.delete_many({"session_id": {"$regex": "^TEST_"}})
        print(f"Cleaned up {deleted_sessions.deleted_count} test sessions")
        
        print("✓ All test data cleaned up")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
