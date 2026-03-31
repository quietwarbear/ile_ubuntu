"""
Test suite for Cohorts, Spaces, Community, and Archives features.
Tests: Cohort CRUD + course linking, Spaces CRUD + access control + resources,
Community posts/replies/likes, Archives CRUD with access levels.
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
TEST_PREFIX = "COHORT_SPACE_TEST_"


@pytest.fixture(scope="module")
def db():
    """Get MongoDB database connection"""
    client = MongoClient(MONGO_URL)
    database = client[DB_NAME]
    yield database
    client.close()


@pytest.fixture(scope="module")
def admin_session(db):
    """Create admin user and session"""
    session_id = f"test_admin_{uuid.uuid4().hex[:8]}"
    user_id = f"{TEST_PREFIX}admin_{uuid.uuid4().hex[:8]}"
    
    # Create admin user
    db.users.insert_one({
        "id": user_id,
        "email": f"{user_id}@test.com",
        "name": "Test Admin",
        "role": "admin",
        "picture": "",
        "created_at": datetime.now(timezone.utc),
    })
    
    # Create session
    db.sessions.insert_one({
        "session_id": session_id,
        "user_id": user_id,
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=24),
    })
    
    yield {"session_id": session_id, "user_id": user_id}
    
    # Cleanup
    db.users.delete_one({"id": user_id})
    db.sessions.delete_one({"session_id": session_id})


@pytest.fixture(scope="module")
def faculty_session(db):
    """Create faculty user and session"""
    session_id = f"test_faculty_{uuid.uuid4().hex[:8]}"
    user_id = f"{TEST_PREFIX}faculty_{uuid.uuid4().hex[:8]}"
    
    db.users.insert_one({
        "id": user_id,
        "email": f"{user_id}@test.com",
        "name": "Test Faculty",
        "role": "faculty",
        "picture": "",
        "created_at": datetime.now(timezone.utc),
    })
    
    db.sessions.insert_one({
        "session_id": session_id,
        "user_id": user_id,
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=24),
    })
    
    yield {"session_id": session_id, "user_id": user_id}
    
    db.users.delete_one({"id": user_id})
    db.sessions.delete_one({"session_id": session_id})


@pytest.fixture(scope="module")
def student_session(db):
    """Create student user and session"""
    session_id = f"test_student_{uuid.uuid4().hex[:8]}"
    user_id = f"{TEST_PREFIX}student_{uuid.uuid4().hex[:8]}"
    
    db.users.insert_one({
        "id": user_id,
        "email": f"{user_id}@test.com",
        "name": "Test Student",
        "role": "student",
        "picture": "",
        "created_at": datetime.now(timezone.utc),
    })
    
    db.sessions.insert_one({
        "session_id": session_id,
        "user_id": user_id,
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=24),
    })
    
    yield {"session_id": session_id, "user_id": user_id}
    
    db.users.delete_one({"id": user_id})
    db.sessions.delete_one({"session_id": session_id})


# ============ COHORTS TESTS ============

class TestCohortsCRUD:
    """Test Cohort CRUD operations"""
    
    def test_create_cohort_requires_auth(self):
        """POST /api/cohorts requires authentication"""
        response = requests.post(f"{BASE_URL}/api/cohorts", json={"name": "Test"})
        assert response.status_code == 401
        print("PASSED: Create cohort requires auth")
    
    def test_create_cohort_requires_faculty(self, student_session):
        """POST /api/cohorts requires faculty+ role"""
        response = requests.post(
            f"{BASE_URL}/api/cohorts",
            json={"name": "Test Cohort"},
            headers={"X-Session-ID": student_session["session_id"]}
        )
        assert response.status_code == 403
        print("PASSED: Create cohort requires faculty+ role")
    
    def test_create_cohort_success(self, faculty_session, db):
        """POST /api/cohorts creates cohort successfully"""
        cohort_name = f"{TEST_PREFIX}Cohort_{uuid.uuid4().hex[:6]}"
        response = requests.post(
            f"{BASE_URL}/api/cohorts",
            json={
                "name": cohort_name,
                "description": "Test cohort description",
                "max_members": 25
            },
            headers={"X-Session-ID": faculty_session["session_id"]}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["name"] == cohort_name
        assert data["description"] == "Test cohort description"
        assert data["max_members"] == 25
        assert data["instructor_id"] == faculty_session["user_id"]
        assert "id" in data
        
        # Cleanup
        db.cohorts.delete_one({"id": data["id"]})
        print("PASSED: Create cohort success")
    
    def test_list_cohorts(self, faculty_session):
        """GET /api/cohorts lists cohorts"""
        response = requests.get(
            f"{BASE_URL}/api/cohorts",
            headers={"X-Session-ID": faculty_session["session_id"]}
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        print("PASSED: List cohorts")
    
    def test_get_cohort_detail(self, faculty_session, db):
        """GET /api/cohorts/{id}/detail returns enriched data"""
        # Create cohort first
        cohort_name = f"{TEST_PREFIX}DetailCohort_{uuid.uuid4().hex[:6]}"
        create_resp = requests.post(
            f"{BASE_URL}/api/cohorts",
            json={"name": cohort_name, "description": "Detail test"},
            headers={"X-Session-ID": faculty_session["session_id"]}
        )
        assert create_resp.status_code == 200, f"Create failed: {create_resp.text}"
        cohort_id = create_resp.json()["id"]
        
        # Get detail
        response = requests.get(
            f"{BASE_URL}/api/cohorts/{cohort_id}/detail",
            headers={"X-Session-ID": faculty_session["session_id"]}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == cohort_name
        assert "linked_courses" in data
        assert "enriched_members" in data
        
        # Cleanup
        db.cohorts.delete_one({"id": cohort_id})
        print("PASSED: Get cohort detail with enriched data")


class TestCohortMembership:
    """Test cohort join/leave functionality"""
    
    def test_join_cohort(self, faculty_session, student_session, db):
        """POST /api/cohorts/{id}/join adds user to cohort"""
        # Create cohort
        cohort_name = f"{TEST_PREFIX}JoinCohort_{uuid.uuid4().hex[:6]}"
        create_resp = requests.post(
            f"{BASE_URL}/api/cohorts",
            json={"name": cohort_name},
            headers={"X-Session-ID": faculty_session["session_id"]}
        )
        assert create_resp.status_code == 200, f"Create failed: {create_resp.text}"
        cohort_id = create_resp.json()["id"]
        
        # Student joins
        response = requests.post(
            f"{BASE_URL}/api/cohorts/{cohort_id}/join",
            json={},
            headers={"X-Session-ID": student_session["session_id"]}
        )
        assert response.status_code == 200
        assert response.json()["success"] == True
        
        # Verify membership
        cohort = db.cohorts.find_one({"id": cohort_id})
        assert student_session["user_id"] in cohort["members"]
        
        # Cleanup
        db.cohorts.delete_one({"id": cohort_id})
        print("PASSED: Join cohort")
    
    def test_leave_cohort(self, faculty_session, student_session, db):
        """POST /api/cohorts/{id}/leave removes user from cohort"""
        # Create cohort and add student
        cohort_name = f"{TEST_PREFIX}LeaveCohort_{uuid.uuid4().hex[:6]}"
        create_resp = requests.post(
            f"{BASE_URL}/api/cohorts",
            json={"name": cohort_name},
            headers={"X-Session-ID": faculty_session["session_id"]}
        )
        assert create_resp.status_code == 200
        cohort_id = create_resp.json()["id"]
        
        # Join first
        requests.post(
            f"{BASE_URL}/api/cohorts/{cohort_id}/join",
            json={},
            headers={"X-Session-ID": student_session["session_id"]}
        )
        
        # Leave
        response = requests.post(
            f"{BASE_URL}/api/cohorts/{cohort_id}/leave",
            json={},
            headers={"X-Session-ID": student_session["session_id"]}
        )
        assert response.status_code == 200
        assert response.json()["success"] == True
        
        # Verify removal
        cohort = db.cohorts.find_one({"id": cohort_id})
        assert student_session["user_id"] not in cohort.get("members", [])
        
        # Cleanup
        db.cohorts.delete_one({"id": cohort_id})
        print("PASSED: Leave cohort")


class TestCohortCourseLinking:
    """Test cohort-course linking functionality"""
    
    def test_link_course_to_cohort(self, faculty_session, db):
        """POST /api/cohorts/{id}/courses links course to cohort"""
        # Create cohort
        cohort_name = f"{TEST_PREFIX}LinkCohort_{uuid.uuid4().hex[:6]}"
        create_resp = requests.post(
            f"{BASE_URL}/api/cohorts",
            json={"name": cohort_name},
            headers={"X-Session-ID": faculty_session["session_id"]}
        )
        assert create_resp.status_code == 200
        cohort_id = create_resp.json()["id"]
        
        # Create a test course
        course_id = f"{TEST_PREFIX}course_{uuid.uuid4().hex[:6]}"
        db.courses.insert_one({
            "id": course_id,
            "title": "Test Course",
            "description": "Test",
            "instructor_id": faculty_session["user_id"],
            "instructor_name": "Test Faculty",
            "status": "active",
            "lessons": [],
            "enrolled_count": 0,
            "created_at": datetime.now(timezone.utc),
        })
        
        # Link course
        response = requests.post(
            f"{BASE_URL}/api/cohorts/{cohort_id}/courses",
            json={"course_id": course_id},
            headers={"X-Session-ID": faculty_session["session_id"]}
        )
        assert response.status_code == 200
        assert response.json()["success"] == True
        
        # Verify link
        cohort = db.cohorts.find_one({"id": cohort_id})
        assert course_id in cohort["course_ids"]
        
        # Cleanup
        db.cohorts.delete_one({"id": cohort_id})
        db.courses.delete_one({"id": course_id})
        print("PASSED: Link course to cohort")
    
    def test_unlink_course_from_cohort(self, faculty_session, db):
        """DELETE /api/cohorts/{id}/courses/{course_id} unlinks course"""
        # Create cohort with linked course
        cohort_name = f"{TEST_PREFIX}UnlinkCohort_{uuid.uuid4().hex[:6]}"
        course_id = f"{TEST_PREFIX}course_{uuid.uuid4().hex[:6]}"
        
        db.courses.insert_one({
            "id": course_id,
            "title": "Test Course",
            "status": "active",
            "instructor_id": faculty_session["user_id"],
            "instructor_name": "Test Faculty",
            "lessons": [],
            "created_at": datetime.now(timezone.utc),
        })
        
        create_resp = requests.post(
            f"{BASE_URL}/api/cohorts",
            json={"name": cohort_name, "course_ids": [course_id]},
            headers={"X-Session-ID": faculty_session["session_id"]}
        )
        assert create_resp.status_code == 200
        cohort_id = create_resp.json()["id"]
        
        # Link course first
        requests.post(
            f"{BASE_URL}/api/cohorts/{cohort_id}/courses",
            json={"course_id": course_id},
            headers={"X-Session-ID": faculty_session["session_id"]}
        )
        
        # Unlink course
        response = requests.delete(
            f"{BASE_URL}/api/cohorts/{cohort_id}/courses/{course_id}",
            headers={"X-Session-ID": faculty_session["session_id"]}
        )
        assert response.status_code == 200
        assert response.json()["success"] == True
        
        # Verify unlink
        cohort = db.cohorts.find_one({"id": cohort_id})
        assert course_id not in cohort.get("course_ids", [])
        
        # Cleanup
        db.cohorts.delete_one({"id": cohort_id})
        db.courses.delete_one({"id": course_id})
        print("PASSED: Unlink course from cohort")


# ============ SPACES TESTS ============

class TestSpacesCRUD:
    """Test Knowledge Spaces CRUD operations"""
    
    def test_create_space_requires_auth(self):
        """POST /api/spaces requires authentication"""
        response = requests.post(f"{BASE_URL}/api/spaces", json={"name": "Test"})
        assert response.status_code == 401
        print("PASSED: Create space requires auth")
    
    def test_create_space_requires_faculty(self, student_session):
        """POST /api/spaces requires faculty+ role"""
        response = requests.post(
            f"{BASE_URL}/api/spaces",
            json={"name": "Test Space"},
            headers={"X-Session-ID": student_session["session_id"]}
        )
        assert response.status_code == 403
        print("PASSED: Create space requires faculty+ role")
    
    def test_create_space_success(self, faculty_session, db):
        """POST /api/spaces creates space successfully"""
        space_name = f"{TEST_PREFIX}Space_{uuid.uuid4().hex[:6]}"
        response = requests.post(
            f"{BASE_URL}/api/spaces",
            json={
                "name": space_name,
                "description": "Test space description",
                "access_level": "members",
                "content": "Initial content"
            },
            headers={"X-Session-ID": faculty_session["session_id"]}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["name"] == space_name
        assert data["access_level"] == "members"
        assert data["owner_id"] == faculty_session["user_id"]
        assert faculty_session["user_id"] in data["members"]
        
        # Cleanup
        db.spaces.delete_one({"id": data["id"]})
        print("PASSED: Create space success")
    
    def test_list_spaces_shows_members_only_for_discovery(self, faculty_session, student_session, db):
        """GET /api/spaces shows members-only spaces to all users for discovery"""
        # Create members-only space
        space_name = f"{TEST_PREFIX}MembersSpace_{uuid.uuid4().hex[:6]}"
        create_resp = requests.post(
            f"{BASE_URL}/api/spaces",
            json={"name": space_name, "access_level": "members", "content": "Secret content"},
            headers={"X-Session-ID": faculty_session["session_id"]}
        )
        assert create_resp.status_code == 200
        space_id = create_resp.json()["id"]
        
        # Student should see the space (for discovery) but without content
        response = requests.get(
            f"{BASE_URL}/api/spaces",
            headers={"X-Session-ID": student_session["session_id"]}
        )
        assert response.status_code == 200
        spaces = response.json()
        space = next((s for s in spaces if s["id"] == space_id), None)
        assert space is not None, "Members-only space should be visible for discovery"
        assert space["content"] == "", "Content should be stripped for non-members"
        
        # Cleanup
        db.spaces.delete_one({"id": space_id})
        print("PASSED: List spaces shows members-only for discovery")
    
    def test_delete_space_owner_only(self, faculty_session, student_session, db):
        """DELETE /api/spaces/{id} only allowed for owner"""
        # Create space
        space_name = f"{TEST_PREFIX}DeleteSpace_{uuid.uuid4().hex[:6]}"
        create_resp = requests.post(
            f"{BASE_URL}/api/spaces",
            json={"name": space_name},
            headers={"X-Session-ID": faculty_session["session_id"]}
        )
        assert create_resp.status_code == 200
        space_id = create_resp.json()["id"]
        
        # Student cannot delete
        response = requests.delete(
            f"{BASE_URL}/api/spaces/{space_id}",
            headers={"X-Session-ID": student_session["session_id"]}
        )
        assert response.status_code == 403
        
        # Owner can delete
        response = requests.delete(
            f"{BASE_URL}/api/spaces/{space_id}",
            headers={"X-Session-ID": faculty_session["session_id"]}
        )
        assert response.status_code == 200
        print("PASSED: Delete space owner only")


class TestSpacesAccessControl:
    """Test space access request/approval flow"""
    
    def test_request_access(self, faculty_session, student_session, db):
        """POST /api/spaces/{id}/request-access creates access request"""
        # Create members-only space
        space_name = f"{TEST_PREFIX}AccessSpace_{uuid.uuid4().hex[:6]}"
        create_resp = requests.post(
            f"{BASE_URL}/api/spaces",
            json={"name": space_name, "access_level": "members"},
            headers={"X-Session-ID": faculty_session["session_id"]}
        )
        assert create_resp.status_code == 200
        space_id = create_resp.json()["id"]
        
        # Student requests access
        response = requests.post(
            f"{BASE_URL}/api/spaces/{space_id}/request-access",
            json={},
            headers={"X-Session-ID": student_session["session_id"]}
        )
        assert response.status_code == 200
        assert response.json()["success"] == True
        
        # Verify pending request
        space = db.spaces.find_one({"id": space_id})
        pending_user_ids = [r["user_id"] for r in space.get("pending_requests", [])]
        assert student_session["user_id"] in pending_user_ids
        
        # Cleanup
        db.spaces.delete_one({"id": space_id})
        print("PASSED: Request access to space")
    
    def test_approve_access(self, faculty_session, student_session, db):
        """POST /api/spaces/{id}/approve/{user_id} approves access request"""
        # Create space and request access
        space_name = f"{TEST_PREFIX}ApproveSpace_{uuid.uuid4().hex[:6]}"
        create_resp = requests.post(
            f"{BASE_URL}/api/spaces",
            json={"name": space_name, "access_level": "members"},
            headers={"X-Session-ID": faculty_session["session_id"]}
        )
        assert create_resp.status_code == 200
        space_id = create_resp.json()["id"]
        
        # Request access
        requests.post(
            f"{BASE_URL}/api/spaces/{space_id}/request-access",
            json={},
            headers={"X-Session-ID": student_session["session_id"]}
        )
        
        # Approve access
        response = requests.post(
            f"{BASE_URL}/api/spaces/{space_id}/approve/{student_session['user_id']}",
            json={},
            headers={"X-Session-ID": faculty_session["session_id"]}
        )
        assert response.status_code == 200
        assert response.json()["success"] == True
        
        # Verify membership
        space = db.spaces.find_one({"id": space_id})
        assert student_session["user_id"] in space["members"]
        
        # Cleanup
        db.spaces.delete_one({"id": space_id})
        print("PASSED: Approve access to space")


class TestSpacesResources:
    """Test space resources functionality"""
    
    def test_add_resource_to_space(self, faculty_session, db):
        """POST /api/spaces/{id}/resources adds resource"""
        # Create space
        space_name = f"{TEST_PREFIX}ResourceSpace_{uuid.uuid4().hex[:6]}"
        create_resp = requests.post(
            f"{BASE_URL}/api/spaces",
            json={"name": space_name, "access_level": "public"},
            headers={"X-Session-ID": faculty_session["session_id"]}
        )
        assert create_resp.status_code == 200
        space_id = create_resp.json()["id"]
        
        # Add resource
        response = requests.post(
            f"{BASE_URL}/api/spaces/{space_id}/resources",
            json={
                "title": "Test Resource",
                "type": "text",
                "content": "Resource content"
            },
            headers={"X-Session-ID": faculty_session["session_id"]}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Resource"
        assert data["type"] == "text"
        assert "id" in data
        
        # Verify resource added
        space = db.spaces.find_one({"id": space_id})
        assert len(space["resources"]) == 1
        
        # Cleanup
        db.spaces.delete_one({"id": space_id})
        print("PASSED: Add resource to space")


# ============ COMMUNITY TESTS ============

class TestCommunityPosts:
    """Test Community posts functionality"""
    
    def test_create_post_requires_auth(self):
        """POST /api/community/posts requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/community/posts",
            json={"title": "Test", "content": "Test"}
        )
        assert response.status_code == 401
        print("PASSED: Create post requires auth")
    
    def test_create_post_success(self, student_session, db):
        """POST /api/community/posts creates post successfully"""
        post_title = f"{TEST_PREFIX}Post_{uuid.uuid4().hex[:6]}"
        response = requests.post(
            f"{BASE_URL}/api/community/posts",
            json={
                "title": post_title,
                "content": "Test post content",
                "category": "general"
            },
            headers={"X-Session-ID": student_session["session_id"]}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["title"] == post_title
        assert data["content"] == "Test post content"
        assert data["author_id"] == student_session["user_id"]
        assert "id" in data
        
        # Cleanup
        db.community_posts.delete_one({"id": data["id"]})
        print("PASSED: Create post success")
    
    def test_list_posts(self, student_session):
        """GET /api/community/posts lists posts"""
        response = requests.get(
            f"{BASE_URL}/api/community/posts",
            headers={"X-Session-ID": student_session["session_id"]}
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        print("PASSED: List posts")


class TestCommunityReplies:
    """Test Community replies functionality"""
    
    def test_reply_to_post(self, student_session, faculty_session, db):
        """POST /api/community/posts/{id}/reply adds reply"""
        # Create post
        post_title = f"{TEST_PREFIX}ReplyPost_{uuid.uuid4().hex[:6]}"
        create_resp = requests.post(
            f"{BASE_URL}/api/community/posts",
            json={"title": post_title, "content": "Original post"},
            headers={"X-Session-ID": student_session["session_id"]}
        )
        assert create_resp.status_code == 200
        post_id = create_resp.json()["id"]
        
        # Reply to post
        response = requests.post(
            f"{BASE_URL}/api/community/posts/{post_id}/reply",
            json={"content": "This is a reply"},
            headers={"X-Session-ID": faculty_session["session_id"]}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "This is a reply"
        assert data["author_id"] == faculty_session["user_id"]
        
        # Verify reply added
        post = db.community_posts.find_one({"id": post_id})
        assert len(post["replies"]) == 1
        
        # Cleanup
        db.community_posts.delete_one({"id": post_id})
        print("PASSED: Reply to post")


class TestCommunityLikes:
    """Test Community likes functionality"""
    
    def test_like_post_toggle(self, student_session, faculty_session, db):
        """POST /api/community/posts/{id}/like toggles like"""
        # Create post
        post_title = f"{TEST_PREFIX}LikePost_{uuid.uuid4().hex[:6]}"
        create_resp = requests.post(
            f"{BASE_URL}/api/community/posts",
            json={"title": post_title, "content": "Likeable post"},
            headers={"X-Session-ID": student_session["session_id"]}
        )
        assert create_resp.status_code == 200
        post_id = create_resp.json()["id"]
        
        # Like post
        response = requests.post(
            f"{BASE_URL}/api/community/posts/{post_id}/like",
            json={},
            headers={"X-Session-ID": faculty_session["session_id"]}
        )
        assert response.status_code == 200
        assert response.json()["liked"] == True
        
        # Unlike post (toggle)
        response = requests.post(
            f"{BASE_URL}/api/community/posts/{post_id}/like",
            json={},
            headers={"X-Session-ID": faculty_session["session_id"]}
        )
        assert response.status_code == 200
        assert response.json()["liked"] == False
        
        # Cleanup
        db.community_posts.delete_one({"id": post_id})
        print("PASSED: Like post toggle")


# ============ ARCHIVES TESTS ============

class TestArchivesCRUD:
    """Test Archives CRUD operations"""
    
    def test_create_archive_requires_auth(self):
        """POST /api/archives requires authentication"""
        response = requests.post(f"{BASE_URL}/api/archives", json={"title": "Test"})
        assert response.status_code == 401
        print("PASSED: Create archive requires auth")
    
    def test_create_archive_requires_faculty(self, student_session):
        """POST /api/archives requires faculty+ role"""
        response = requests.post(
            f"{BASE_URL}/api/archives",
            json={"title": "Test Archive"},
            headers={"X-Session-ID": student_session["session_id"]}
        )
        assert response.status_code == 403
        print("PASSED: Create archive requires faculty+ role")
    
    def test_create_archive_success(self, faculty_session, db):
        """POST /api/archives creates archive successfully"""
        archive_title = f"{TEST_PREFIX}Archive_{uuid.uuid4().hex[:6]}"
        response = requests.post(
            f"{BASE_URL}/api/archives",
            json={
                "title": archive_title,
                "description": "Test archive description",
                "type": "document",
                "access_level": "public",
                "tags": ["test", "archive"]
            },
            headers={"X-Session-ID": faculty_session["session_id"]}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["title"] == archive_title
        assert data["type"] == "document"
        assert data["access_level"] == "public"
        assert data["archived_by"] == faculty_session["user_id"]
        
        # Cleanup
        db.archives.delete_one({"id": data["id"]})
        print("PASSED: Create archive success")
    
    def test_list_archives_filtered_for_students(self, faculty_session, student_session, db):
        """GET /api/archives filters restricted archives for students"""
        # Create public archive
        public_title = f"{TEST_PREFIX}PublicArchive_{uuid.uuid4().hex[:6]}"
        public_resp = requests.post(
            f"{BASE_URL}/api/archives",
            json={"title": public_title, "access_level": "public"},
            headers={"X-Session-ID": faculty_session["session_id"]}
        )
        assert public_resp.status_code == 200
        public_id = public_resp.json()["id"]
        
        # Create restricted archive
        restricted_title = f"{TEST_PREFIX}RestrictedArchive_{uuid.uuid4().hex[:6]}"
        restricted_resp = requests.post(
            f"{BASE_URL}/api/archives",
            json={"title": restricted_title, "access_level": "restricted"},
            headers={"X-Session-ID": faculty_session["session_id"]}
        )
        assert restricted_resp.status_code == 200
        restricted_id = restricted_resp.json()["id"]
        
        # Student should only see public
        response = requests.get(
            f"{BASE_URL}/api/archives",
            headers={"X-Session-ID": student_session["session_id"]}
        )
        assert response.status_code == 200
        archives = response.json()
        archive_ids = [a["id"] for a in archives]
        assert public_id in archive_ids
        assert restricted_id not in archive_ids
        
        # Faculty should see both
        response = requests.get(
            f"{BASE_URL}/api/archives",
            headers={"X-Session-ID": faculty_session["session_id"]}
        )
        archives = response.json()
        archive_ids = [a["id"] for a in archives]
        assert public_id in archive_ids
        assert restricted_id in archive_ids
        
        # Cleanup
        db.archives.delete_one({"id": public_id})
        db.archives.delete_one({"id": restricted_id})
        print("PASSED: List archives filtered for students")
    
    def test_delete_archive_admin_only(self, faculty_session, admin_session, db):
        """DELETE /api/archives/{id} requires admin role"""
        # Create archive
        archive_title = f"{TEST_PREFIX}DeleteArchive_{uuid.uuid4().hex[:6]}"
        create_resp = requests.post(
            f"{BASE_URL}/api/archives",
            json={"title": archive_title},
            headers={"X-Session-ID": faculty_session["session_id"]}
        )
        assert create_resp.status_code == 200
        archive_id = create_resp.json()["id"]
        
        # Faculty cannot delete
        response = requests.delete(
            f"{BASE_URL}/api/archives/{archive_id}",
            headers={"X-Session-ID": faculty_session["session_id"]}
        )
        assert response.status_code == 403
        
        # Admin can delete
        response = requests.delete(
            f"{BASE_URL}/api/archives/{archive_id}",
            headers={"X-Session-ID": admin_session["session_id"]}
        )
        assert response.status_code == 200
        print("PASSED: Delete archive admin only")


# ============ CLEANUP ============

class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_data(self, db):
        """Clean up all test data with TEST_PREFIX"""
        # Clean up cohorts
        result = db.cohorts.delete_many({"name": {"$regex": f"^{TEST_PREFIX}"}})
        print(f"Cleaned up {result.deleted_count} test cohorts")
        
        # Clean up spaces
        result = db.spaces.delete_many({"name": {"$regex": f"^{TEST_PREFIX}"}})
        print(f"Cleaned up {result.deleted_count} test spaces")
        
        # Clean up posts
        result = db.community_posts.delete_many({"title": {"$regex": f"^{TEST_PREFIX}"}})
        print(f"Cleaned up {result.deleted_count} test posts")
        
        # Clean up archives
        result = db.archives.delete_many({"title": {"$regex": f"^{TEST_PREFIX}"}})
        print(f"Cleaned up {result.deleted_count} test archives")
        
        # Clean up courses
        result = db.courses.delete_many({"id": {"$regex": f"^{TEST_PREFIX}"}})
        print(f"Cleaned up {result.deleted_count} test courses")
        
        print("PASSED: Cleanup test data")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
