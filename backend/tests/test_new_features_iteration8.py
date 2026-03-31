"""
Test Suite for Iteration 8 - New Features:
1. Cohort Progress Dashboard (leaderboard + per-course breakdown)
2. Lesson Content Viewer (markdown + embedded media)
3. Branded Virtual Backgrounds (9 total backgrounds)

Tests the following endpoints:
- GET /api/cohorts/{id}/detail - enriched_members with overall_progress and enrollments
- POST /api/cohorts - create cohort (faculty+ only)
- POST /api/cohorts/{id}/courses - link course (faculty+)
- POST /api/cohorts/{id}/join - join as student
- POST /api/courses/{id}/enroll - enroll student in linked course
- POST /api/courses/{id}/lessons/{lid}/complete - mark lesson complete
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
TEST_PREFIX = "ITER8_TEST_"


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
    
    db.users.insert_one({
        "id": user_id,
        "email": f"{user_id}@test.com",
        "name": f"{TEST_PREFIX}Admin User",
        "role": "admin",
        "picture": "https://example.com/admin.jpg",
        "created_at": datetime.now(timezone.utc),
    })
    
    db.sessions.insert_one({
        "session_id": session_id,
        "user_id": user_id,
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=24),
    })
    
    yield {"session_id": session_id, "user_id": user_id, "name": f"{TEST_PREFIX}Admin User"}
    
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
        "name": f"{TEST_PREFIX}Faculty User",
        "role": "faculty",
        "picture": "https://example.com/faculty.jpg",
        "created_at": datetime.now(timezone.utc),
    })
    
    db.sessions.insert_one({
        "session_id": session_id,
        "user_id": user_id,
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=24),
    })
    
    yield {"session_id": session_id, "user_id": user_id, "name": f"{TEST_PREFIX}Faculty User"}
    
    db.users.delete_one({"id": user_id})
    db.sessions.delete_one({"session_id": session_id})


@pytest.fixture(scope="module")
def student_sessions(db):
    """Create multiple student users and sessions for progress testing"""
    students = []
    for i in range(3):
        session_id = f"test_student{i}_{uuid.uuid4().hex[:8]}"
        user_id = f"{TEST_PREFIX}student{i}_{uuid.uuid4().hex[:8]}"
        name = f"{TEST_PREFIX}Student {i+1}"
        
        db.users.insert_one({
            "id": user_id,
            "email": f"{user_id}@test.com",
            "name": name,
            "role": "student",
            "picture": f"https://example.com/student{i}.jpg",
            "created_at": datetime.now(timezone.utc),
        })
        
        db.sessions.insert_one({
            "session_id": session_id,
            "user_id": user_id,
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=24),
        })
        
        students.append({"session_id": session_id, "user_id": user_id, "name": name})
    
    yield students
    
    for student in students:
        db.users.delete_one({"id": student["user_id"]})
        db.sessions.delete_one({"session_id": student["session_id"]})


@pytest.fixture(scope="module")
def api_client():
    """Create requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestCohortProgressDashboard:
    """Test Cohort Progress Dashboard feature - leaderboard and per-course breakdown"""
    
    @pytest.fixture(scope="class")
    def test_courses(self, api_client, faculty_session, db):
        """Create test courses with lessons"""
        courses = []
        
        for i in range(2):
            course_data = {
                "title": f"{TEST_PREFIX}Progress Course {i+1}",
                "description": f"Test course {i+1} for progress dashboard",
                "tags": ["test", "progress"]
            }
            
            api_client.headers.update({"X-Session-ID": faculty_session["session_id"]})
            resp = api_client.post(f"{BASE_URL}/api/courses", json=course_data)
            assert resp.status_code == 200, f"Failed to create course: {resp.text}"
            course = resp.json()
            
            # Activate course
            api_client.put(f"{BASE_URL}/api/courses/{course['id']}", json={"status": "active"})
            
            # Add lessons
            lessons = []
            for j in range(3):
                lesson_data = {
                    "title": f"{TEST_PREFIX}Lesson {j+1}",
                    "description": f"Lesson {j+1} description",
                    "content": f"# Lesson {j+1}\n\nThis is **markdown** content.",
                    "order": j + 1
                }
                resp = api_client.post(f"{BASE_URL}/api/courses/{course['id']}/lessons", json=lesson_data)
                assert resp.status_code == 200, f"Failed to create lesson: {resp.text}"
                lessons.append(resp.json())
            
            courses.append({"id": course["id"], "title": course["title"], "lessons": lessons})
        
        yield courses
        
        # Cleanup
        for course in courses:
            api_client.headers.update({"X-Session-ID": faculty_session["session_id"]})
            api_client.delete(f"{BASE_URL}/api/courses/{course['id']}")
    
    @pytest.fixture(scope="class")
    def test_cohort(self, api_client, faculty_session, test_courses, db):
        """Create test cohort with linked courses"""
        cohort_data = {
            "name": f"{TEST_PREFIX}Progress Dashboard Cohort",
            "description": "Cohort for testing progress dashboard",
            "max_members": 30
        }
        
        api_client.headers.update({"X-Session-ID": faculty_session["session_id"]})
        resp = api_client.post(f"{BASE_URL}/api/cohorts", json=cohort_data)
        assert resp.status_code == 200, f"Failed to create cohort: {resp.text}"
        cohort = resp.json()
        
        # Link courses
        for course in test_courses:
            resp = api_client.post(f"{BASE_URL}/api/cohorts/{cohort['id']}/courses", json={"course_id": course["id"]})
            assert resp.status_code == 200, f"Failed to link course: {resp.text}"
        
        yield cohort
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/cohorts/{cohort['id']}")
    
    def test_cohort_detail_returns_enriched_members_structure(self, api_client, faculty_session, test_cohort):
        """Test GET /api/cohorts/{id}/detail returns enriched_members field"""
        api_client.headers.update({"X-Session-ID": faculty_session["session_id"]})
        
        response = api_client.get(f"{BASE_URL}/api/cohorts/{test_cohort['id']}/detail")
        assert response.status_code == 200, f"Failed to get cohort detail: {response.text}"
        
        data = response.json()
        assert "enriched_members" in data, "Response should contain enriched_members"
        assert "linked_courses" in data, "Response should contain linked_courses"
        assert len(data["linked_courses"]) == 2, f"Should have 2 linked courses, got {len(data['linked_courses'])}"
        
        print(f"✓ GET /api/cohorts/{'{id}'}/detail returns enriched_members and linked_courses")
    
    def test_students_join_cohort(self, api_client, student_sessions, test_cohort):
        """Test POST /api/cohorts/{id}/join - students join cohort"""
        for student in student_sessions:
            api_client.headers.update({"X-Session-ID": student["session_id"]})
            response = api_client.post(f"{BASE_URL}/api/cohorts/{test_cohort['id']}/join", json={})
            assert response.status_code == 200, f"Failed to join cohort: {response.text}"
        
        print(f"✓ POST /api/cohorts/{'{id}'}/join - 3 students joined cohort")
    
    def test_students_enroll_in_courses(self, api_client, student_sessions, test_courses):
        """Test POST /api/courses/{id}/enroll - students enroll in linked courses"""
        for student in student_sessions:
            api_client.headers.update({"X-Session-ID": student["session_id"]})
            for course in test_courses:
                response = api_client.post(f"{BASE_URL}/api/courses/{course['id']}/enroll", json={})
                assert response.status_code == 200, f"Failed to enroll: {response.text}"
        
        print(f"✓ POST /api/courses/{'{id}'}/enroll - all students enrolled in all courses")
    
    def test_complete_lessons_creates_progress(self, api_client, student_sessions, test_courses):
        """Test POST /api/courses/{id}/lessons/{lid}/complete - mark lessons complete"""
        course = test_courses[0]
        
        # Student 0: Complete all 3 lessons (100%)
        api_client.headers.update({"X-Session-ID": student_sessions[0]["session_id"]})
        for lesson in course["lessons"]:
            response = api_client.post(f"{BASE_URL}/api/courses/{course['id']}/lessons/{lesson['id']}/complete", json={})
            assert response.status_code == 200, f"Failed to complete lesson: {response.text}"
        
        # Student 1: Complete 2 lessons (66%)
        api_client.headers.update({"X-Session-ID": student_sessions[1]["session_id"]})
        for lesson in course["lessons"][:2]:
            response = api_client.post(f"{BASE_URL}/api/courses/{course['id']}/lessons/{lesson['id']}/complete", json={})
            assert response.status_code == 200
        
        # Student 2: Complete 1 lesson (33%)
        api_client.headers.update({"X-Session-ID": student_sessions[2]["session_id"]})
        response = api_client.post(f"{BASE_URL}/api/courses/{course['id']}/lessons/{course['lessons'][0]['id']}/complete", json={})
        assert response.status_code == 200
        
        print(f"✓ POST /api/courses/{'{id}'}/lessons/{'{lid}'}/complete - lessons completed with varying progress")
    
    def test_cohort_detail_shows_member_progress(self, api_client, faculty_session, test_cohort, student_sessions):
        """Test GET /api/cohorts/{id}/detail shows member progress data"""
        api_client.headers.update({"X-Session-ID": faculty_session["session_id"]})
        
        response = api_client.get(f"{BASE_URL}/api/cohorts/{test_cohort['id']}/detail")
        assert response.status_code == 200
        
        data = response.json()
        enriched_members = data.get("enriched_members", [])
        
        assert len(enriched_members) == 3, f"Should have 3 members, got {len(enriched_members)}"
        
        for member in enriched_members:
            assert "overall_progress" in member, f"Member {member.get('name')} missing overall_progress"
            assert "enrollments" in member, f"Member {member.get('name')} missing enrollments"
            print(f"  - {member.get('name')}: {member.get('overall_progress')}% overall progress")
        
        print(f"✓ Cohort detail shows overall_progress for all members")
    
    def test_per_course_enrollment_data(self, api_client, faculty_session, test_cohort):
        """Test that enriched_members contains per-course enrollment data"""
        api_client.headers.update({"X-Session-ID": faculty_session["session_id"]})
        
        response = api_client.get(f"{BASE_URL}/api/cohorts/{test_cohort['id']}/detail")
        assert response.status_code == 200
        
        data = response.json()
        enriched_members = data.get("enriched_members", [])
        
        for member in enriched_members:
            enrollments = member.get("enrollments", [])
            assert len(enrollments) == 2, f"Member should have 2 enrollments (one per course), got {len(enrollments)}"
            
            for enrollment in enrollments:
                assert "course_id" in enrollment, "Enrollment should have course_id"
                assert "progress" in enrollment, "Enrollment should have progress"
        
        print(f"✓ Per-course enrollment data present for all members")
    
    def test_leaderboard_sorting(self, api_client, faculty_session, test_cohort):
        """Test that members can be sorted by overall_progress for leaderboard"""
        api_client.headers.update({"X-Session-ID": faculty_session["session_id"]})
        
        response = api_client.get(f"{BASE_URL}/api/cohorts/{test_cohort['id']}/detail")
        assert response.status_code == 200
        
        data = response.json()
        enriched_members = data.get("enriched_members", [])
        
        # Sort by progress (descending)
        sorted_members = sorted(enriched_members, key=lambda m: m["overall_progress"], reverse=True)
        
        # Verify top performer has highest progress
        assert sorted_members[0]["overall_progress"] >= sorted_members[1]["overall_progress"]
        assert sorted_members[1]["overall_progress"] >= sorted_members[2]["overall_progress"]
        
        print(f"✓ Leaderboard sorting works - top performer: {sorted_members[0].get('name')} ({sorted_members[0].get('overall_progress')}%)")


class TestLessonContentViewer:
    """Test Lesson Content with markdown and embedded media"""
    
    @pytest.fixture(scope="class")
    def test_course(self, api_client, faculty_session, db):
        """Create test course for content testing"""
        course_data = {
            "title": f"{TEST_PREFIX}Rich Content Course",
            "description": "Course with markdown and embedded media lessons",
            "tags": ["markdown", "video"]
        }
        
        api_client.headers.update({"X-Session-ID": faculty_session["session_id"]})
        resp = api_client.post(f"{BASE_URL}/api/courses", json=course_data)
        assert resp.status_code == 200, f"Failed to create course: {resp.text}"
        course = resp.json()
        
        yield course
        
        api_client.delete(f"{BASE_URL}/api/courses/{course['id']}")
    
    def test_create_lesson_with_markdown_content(self, api_client, faculty_session, test_course):
        """Test creating lesson with markdown content"""
        api_client.headers.update({"X-Session-ID": faculty_session["session_id"]})
        
        markdown_content = """# Introduction to Python

This is a **comprehensive** lesson about Python programming.

## Key Concepts

1. Variables and data types
2. Control flow
3. Functions

### Code Example

```python
def hello_world():
    print("Hello, World!")
```

> This is a blockquote with important information.

- List item 1
- List item 2
- List item 3

[Learn more](https://python.org)
"""
        
        lesson_data = {
            "title": f"{TEST_PREFIX}Markdown Lesson",
            "description": "Lesson with rich markdown content",
            "content": markdown_content,
            "order": 1
        }
        
        response = api_client.post(f"{BASE_URL}/api/courses/{test_course['id']}/lessons", json=lesson_data)
        assert response.status_code == 200, f"Failed to create lesson: {response.text}"
        
        lesson = response.json()
        assert lesson["content"] == markdown_content, "Content should be preserved"
        assert "# Introduction" in lesson["content"]
        assert "**comprehensive**" in lesson["content"]
        assert "```python" in lesson["content"]
        
        print(f"✓ Created lesson with markdown content (headings, bold, code blocks, lists, links)")
    
    def test_create_lesson_with_youtube_url(self, api_client, faculty_session, test_course):
        """Test creating lesson with YouTube URL for auto-embed"""
        api_client.headers.update({"X-Session-ID": faculty_session["session_id"]})
        
        content_with_youtube = """# Video Lesson

Watch this introduction video:

https://www.youtube.com/watch?v=dQw4w9WgXcQ

Also check out this short: https://youtu.be/abc123xyz

## Summary

The video covers the basics of our topic.
"""
        
        lesson_data = {
            "title": f"{TEST_PREFIX}YouTube Lesson",
            "description": "Lesson with YouTube video",
            "content": content_with_youtube,
            "order": 2
        }
        
        response = api_client.post(f"{BASE_URL}/api/courses/{test_course['id']}/lessons", json=lesson_data)
        assert response.status_code == 200, f"Failed to create lesson: {response.text}"
        
        lesson = response.json()
        assert "youtube.com" in lesson["content"] or "youtu.be" in lesson["content"]
        
        print(f"✓ Created lesson with YouTube URLs for auto-embed")
    
    def test_create_lesson_with_vimeo_url(self, api_client, faculty_session, test_course):
        """Test creating lesson with Vimeo URL"""
        api_client.headers.update({"X-Session-ID": faculty_session["session_id"]})
        
        content_with_vimeo = """# Vimeo Video Lesson

Check out this Vimeo video:

https://vimeo.com/123456789

Great content for learning!
"""
        
        lesson_data = {
            "title": f"{TEST_PREFIX}Vimeo Lesson",
            "description": "Lesson with Vimeo video",
            "content": content_with_vimeo,
            "order": 3
        }
        
        response = api_client.post(f"{BASE_URL}/api/courses/{test_course['id']}/lessons", json=lesson_data)
        assert response.status_code == 200
        assert "vimeo.com" in response.json()["content"]
        
        print(f"✓ Created lesson with Vimeo URL")
    
    def test_create_lesson_with_google_slides(self, api_client, faculty_session, test_course):
        """Test creating lesson with Google Slides URL"""
        api_client.headers.update({"X-Session-ID": faculty_session["session_id"]})
        
        content_with_slides = """# Presentation Lesson

View the slides:

https://docs.google.com/presentation/d/1abc123xyz/edit

## Discussion Points

After viewing the slides, consider the following...
"""
        
        lesson_data = {
            "title": f"{TEST_PREFIX}Google Slides Lesson",
            "description": "Lesson with Google Slides",
            "content": content_with_slides,
            "order": 4
        }
        
        response = api_client.post(f"{BASE_URL}/api/courses/{test_course['id']}/lessons", json=lesson_data)
        assert response.status_code == 200
        assert "docs.google.com/presentation" in response.json()["content"]
        
        print(f"✓ Created lesson with Google Slides URL")
    
    def test_create_lesson_with_google_docs(self, api_client, faculty_session, test_course):
        """Test creating lesson with Google Docs URL"""
        api_client.headers.update({"X-Session-ID": faculty_session["session_id"]})
        
        content_with_docs = """# Reading Material

Read the document:

https://docs.google.com/document/d/1xyz789abc/edit

Take notes as you read.
"""
        
        lesson_data = {
            "title": f"{TEST_PREFIX}Google Docs Lesson",
            "description": "Lesson with Google Docs",
            "content": content_with_docs,
            "order": 5
        }
        
        response = api_client.post(f"{BASE_URL}/api/courses/{test_course['id']}/lessons", json=lesson_data)
        assert response.status_code == 200
        assert "docs.google.com/document" in response.json()["content"]
        
        print(f"✓ Created lesson with Google Docs URL")
    
    def test_get_lessons_returns_content(self, api_client, faculty_session, test_course):
        """Test GET /api/courses/{id}/lessons returns content field"""
        api_client.headers.update({"X-Session-ID": faculty_session["session_id"]})
        
        response = api_client.get(f"{BASE_URL}/api/courses/{test_course['id']}/lessons")
        assert response.status_code == 200
        
        lessons = response.json()
        assert len(lessons) >= 5, f"Should have at least 5 lessons, got {len(lessons)}"
        
        for lesson in lessons:
            assert "content" in lesson, f"Lesson {lesson.get('title')} missing content field"
            assert lesson["content"], f"Lesson {lesson.get('title')} has empty content"
        
        print(f"✓ GET /api/courses/{'{id}'}/lessons returns content field for all lessons")


class TestBrandedBackgrounds:
    """Test branded virtual backgrounds configuration"""
    
    def test_backgrounds_file_has_9_backgrounds(self):
        """Verify backgrounds.js has 9 branded backgrounds"""
        expected_backgrounds = [
            ("blu-gold-abstract", "Blue & Gold Abstract"),
            ("gold-ornate", "Gold Ornate"),
            ("dark-metallic", "Dark Metallic"),
            ("vintage-study", "Vintage Study"),
            ("ice-gold-veins", "Ice & Gold"),
            ("sacred-vault", "Sacred Vault"),
            ("midnight-glow", "Midnight Glow"),
            ("scholars-den", "Scholar's Den"),
            ("cosmic-dust", "Cosmic Dust"),
        ]
        
        backgrounds_path = "/app/frontend/src/lib/backgrounds.js"
        with open(backgrounds_path, 'r') as f:
            content = f.read()
        
        for bg_id, bg_name in expected_backgrounds:
            assert bg_id in content, f"Background ID '{bg_id}' not found"
            assert bg_name in content, f"Background name '{bg_name}' not found"
        
        # Count background objects
        import re
        bg_count = len(re.findall(r"id:\s*'[^']+'", content))
        assert bg_count == 9, f"Expected 9 backgrounds, found {bg_count}"
        
        print(f"✓ backgrounds.js contains all 9 branded backgrounds")
        print(f"  Original 5: Blue & Gold Abstract, Gold Ornate, Dark Metallic, Vintage Study, Ice & Gold")
        print(f"  New 4: Sacred Vault, Midnight Glow, Scholar's Den, Cosmic Dust")
    
    def test_new_backgrounds_have_correct_names(self):
        """Verify the 4 new backgrounds have correct names"""
        new_backgrounds = [
            "Sacred Vault",
            "Midnight Glow",
            "Scholar's Den",
            "Cosmic Dust"
        ]
        
        backgrounds_path = "/app/frontend/src/lib/backgrounds.js"
        with open(backgrounds_path, 'r') as f:
            content = f.read()
        
        for bg_name in new_backgrounds:
            assert bg_name in content, f"New background '{bg_name}' not found"
        
        print(f"✓ All 4 new backgrounds have correct names")


class TestCohortCRUD:
    """Test basic cohort CRUD operations"""
    
    def test_create_cohort_requires_faculty(self, api_client, db):
        """Test POST /api/cohorts requires faculty role"""
        # Create student session
        session_id = f"test_student_nofac_{uuid.uuid4().hex[:8]}"
        user_id = f"{TEST_PREFIX}student_nofac_{uuid.uuid4().hex[:8]}"
        
        db.users.insert_one({
            "id": user_id,
            "email": f"{user_id}@test.com",
            "name": "Test Student NoFac",
            "role": "student",
            "picture": "",
            "created_at": datetime.now(timezone.utc),
        })
        
        db.sessions.insert_one({
            "session_id": session_id,
            "user_id": user_id,
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=24),
        })
        
        try:
            api_client.headers.update({"X-Session-ID": session_id})
            
            cohort_data = {
                "name": f"{TEST_PREFIX}Student Cohort",
                "description": "Should fail"
            }
            response = api_client.post(f"{BASE_URL}/api/cohorts", json=cohort_data)
            assert response.status_code == 403, f"Expected 403, got {response.status_code}"
            
            print(f"✓ POST /api/cohorts correctly requires faculty+ role")
        finally:
            db.users.delete_one({"id": user_id})
            db.sessions.delete_one({"session_id": session_id})
    
    def test_create_cohort_success(self, api_client, faculty_session, db):
        """Test POST /api/cohorts creates cohort"""
        api_client.headers.update({"X-Session-ID": faculty_session["session_id"]})
        
        cohort_data = {
            "name": f"{TEST_PREFIX}Test Cohort CRUD",
            "description": "Test cohort for CRUD operations",
            "max_members": 25
        }
        response = api_client.post(f"{BASE_URL}/api/cohorts", json=cohort_data)
        assert response.status_code == 200, f"Failed to create cohort: {response.text}"
        
        cohort = response.json()
        assert cohort["name"] == cohort_data["name"]
        assert cohort["max_members"] == 25
        assert "id" in cohort
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/cohorts/{cohort['id']}")
        
        print(f"✓ POST /api/cohorts creates cohort successfully")
    
    def test_link_course_to_cohort(self, api_client, faculty_session, db):
        """Test POST /api/cohorts/{id}/courses links course"""
        api_client.headers.update({"X-Session-ID": faculty_session["session_id"]})
        
        # Create course
        course_data = {
            "title": f"{TEST_PREFIX}Link Test Course",
            "description": "Course for linking test"
        }
        resp = api_client.post(f"{BASE_URL}/api/courses", json=course_data)
        assert resp.status_code == 200
        course_id = resp.json().get("id")
        
        # Create cohort
        cohort_data = {
            "name": f"{TEST_PREFIX}Link Test Cohort",
            "description": "Cohort for linking test"
        }
        resp = api_client.post(f"{BASE_URL}/api/cohorts", json=cohort_data)
        assert resp.status_code == 200
        cohort_id = resp.json().get("id")
        
        # Link course
        response = api_client.post(f"{BASE_URL}/api/cohorts/{cohort_id}/courses", json={"course_id": course_id})
        assert response.status_code == 200, f"Failed to link course: {response.text}"
        
        # Verify link
        resp = api_client.get(f"{BASE_URL}/api/cohorts/{cohort_id}/detail")
        detail = resp.json()
        assert len(detail.get("linked_courses", [])) == 1
        assert detail["linked_courses"][0]["id"] == course_id
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/cohorts/{cohort_id}")
        api_client.delete(f"{BASE_URL}/api/courses/{course_id}")
        
        print(f"✓ POST /api/cohorts/{'{id}'}/courses links course successfully")


class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_data(self, db):
        """Clean up any remaining test data"""
        # Clean up users
        result = db.users.delete_many({"id": {"$regex": f"^{TEST_PREFIX}"}})
        print(f"  Cleaned up {result.deleted_count} test users")
        
        # Clean up sessions
        result = db.sessions.delete_many({"session_id": {"$regex": "^test_"}})
        print(f"  Cleaned up {result.deleted_count} test sessions")
        
        # Clean up cohorts
        result = db.cohorts.delete_many({"name": {"$regex": f"^{TEST_PREFIX}"}})
        print(f"  Cleaned up {result.deleted_count} test cohorts")
        
        # Clean up courses
        result = db.courses.delete_many({"title": {"$regex": f"^{TEST_PREFIX}"}})
        print(f"  Cleaned up {result.deleted_count} test courses")
        
        # Clean up lessons
        result = db.lessons.delete_many({"title": {"$regex": f"^{TEST_PREFIX}"}})
        print(f"  Cleaned up {result.deleted_count} test lessons")
        
        # Clean up enrollments for test users
        result = db.enrollments.delete_many({"user_id": {"$regex": f"^{TEST_PREFIX}"}})
        print(f"  Cleaned up {result.deleted_count} test enrollments")
        
        print(f"✓ Test data cleanup complete")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
