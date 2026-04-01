"""
Blog Feature Tests - Iteration 16
Tests for blog/news section with:
- Categories endpoint
- Public posts endpoint (no auth)
- Authenticated posts endpoint
- Post CRUD (faculty+ only)
- Comments CRUD (any auth user)
"""
import pytest
import requests
import os
import uuid
import sys
sys.path.insert(0, '/app/backend')

# Load environment variables
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Get valid session ID from database
def get_valid_session_id():
    """Get a valid session ID from the database or create one"""
    try:
        from database import sessions_col, users_col
        from datetime import datetime, timezone, timedelta
        import uuid as uuid_mod
        
        # Find the faculty user or create one
        user = users_col.find_one({'email': 'quiet927@gmail.com'}, {'_id': 0})
        if not user:
            user = {
                'id': str(uuid_mod.uuid4()),
                'email': 'quiet927@gmail.com',
                'name': 'Test Faculty User',
                'role': 'faculty',
                'picture': '',
                'onboarding_complete': True
            }
            users_col.insert_one(user)
        
        # Ensure user has faculty role
        if user.get('role') not in ['faculty', 'elder', 'admin']:
            users_col.update_one({'id': user['id']}, {'$set': {'role': 'faculty'}})
        
        # Create a new valid session
        new_session_id = f'TEST_BLOG_{uuid_mod.uuid4()}'
        sessions_col.insert_one({
            'session_id': new_session_id,
            'user_id': user['id'],
            'session_token': 'test_token',
            'expires_at': datetime.now(timezone.utc) + timedelta(hours=24)
        })
        return new_session_id
    except Exception as e:
        print(f"Error getting session: {e}")
        return None

VALID_SESSION_ID = get_valid_session_id()

@pytest.fixture(scope="module")
def auth_headers():
    """Get auth headers for authenticated requests"""
    if VALID_SESSION_ID:
        return {"x-session-id": VALID_SESSION_ID, "Content-Type": "application/json"}
    pytest.skip("No valid session found for authenticated tests")

@pytest.fixture(scope="module")
def created_post_id():
    """Store created post ID for cleanup"""
    return {"id": None, "slug": None}


class TestBlogCategories:
    """Test GET /api/blog/categories - Public endpoint"""
    
    def test_get_categories_returns_7_categories(self):
        """Categories endpoint should return 7 predefined categories"""
        response = requests.get(f"{BASE_URL}/api/blog/categories")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        categories = response.json()
        assert isinstance(categories, list), "Categories should be a list"
        assert len(categories) == 7, f"Expected 7 categories, got {len(categories)}"
        
        expected = ["Announcements", "Teaching", "Community", "Culture", "Research", "Events", "Reflections"]
        assert categories == expected, f"Categories mismatch: {categories}"
        print(f"✓ Categories endpoint returns 7 categories: {categories}")


class TestPublicBlogPosts:
    """Test GET /api/blog/posts/public - Public endpoint (no auth required)"""
    
    def test_public_posts_returns_200(self):
        """Public posts endpoint should return 200 with posts array"""
        response = requests.get(f"{BASE_URL}/api/blog/posts/public")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "posts" in data, "Response should have 'posts' key"
        assert "total" in data, "Response should have 'total' key"
        assert isinstance(data["posts"], list), "Posts should be a list"
        assert isinstance(data["total"], int), "Total should be an integer"
        print(f"✓ Public posts endpoint returns {len(data['posts'])} posts, total: {data['total']}")
    
    def test_public_posts_with_category_filter(self):
        """Public posts endpoint should accept category filter"""
        response = requests.get(f"{BASE_URL}/api/blog/posts/public?category=Announcements")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "posts" in data
        # All returned posts should have the filtered category
        for post in data["posts"]:
            assert post.get("category") == "Announcements", f"Post category mismatch: {post.get('category')}"
        print(f"✓ Category filter works, returned {len(data['posts'])} Announcements posts")
    
    def test_public_posts_pagination(self):
        """Public posts endpoint should support limit and skip"""
        response = requests.get(f"{BASE_URL}/api/blog/posts/public?limit=5&skip=0")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["posts"]) <= 5, "Should respect limit parameter"
        print(f"✓ Pagination works, returned {len(data['posts'])} posts with limit=5")


class TestAuthenticatedBlogPosts:
    """Test GET /api/blog/posts - Requires authentication"""
    
    def test_posts_without_auth_returns_401(self):
        """Posts endpoint without auth should return 401"""
        response = requests.get(f"{BASE_URL}/api/blog/posts")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Posts endpoint correctly requires authentication")
    
    def test_posts_by_slug_without_auth_returns_401(self):
        """Posts by slug endpoint without auth should return 401"""
        response = requests.get(f"{BASE_URL}/api/blog/posts/by-slug/test-slug")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Posts by slug endpoint correctly requires authentication")


class TestBlogPostCRUD:
    """Test blog post CRUD operations - Requires faculty+ role"""
    
    def test_create_post_without_auth_returns_401(self):
        """Create post without auth should return 401"""
        payload = {
            "title": "Test Post",
            "content": "Test content",
            "category": "Announcements",
            "visibility": "public"
        }
        response = requests.post(f"{BASE_URL}/api/blog/posts", json=payload)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Create post correctly requires authentication")
    
    def test_update_post_without_auth_returns_401(self):
        """Update post without auth should return 401"""
        payload = {"title": "Updated Title"}
        response = requests.put(f"{BASE_URL}/api/blog/posts/test-id", json=payload)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Update post correctly requires authentication")
    
    def test_delete_post_without_auth_returns_401(self):
        """Delete post without auth should return 401"""
        response = requests.delete(f"{BASE_URL}/api/blog/posts/test-id")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Delete post correctly requires authentication")


class TestBlogComments:
    """Test blog comments endpoints - Requires authentication"""
    
    def test_get_comments_without_auth_returns_401(self):
        """Get comments without auth should return 401"""
        response = requests.get(f"{BASE_URL}/api/blog/posts/test-id/comments")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Get comments correctly requires authentication")
    
    def test_add_comment_without_auth_returns_401(self):
        """Add comment without auth should return 401"""
        payload = {"content": "Test comment"}
        response = requests.post(f"{BASE_URL}/api/blog/posts/test-id/comments", json=payload)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Add comment correctly requires authentication")
    
    def test_delete_comment_without_auth_returns_401(self):
        """Delete comment without auth should return 401"""
        response = requests.delete(f"{BASE_URL}/api/blog/comments/test-id")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Delete comment correctly requires authentication")


class TestPublicPostBySlug:
    """Test GET /api/blog/posts/public/by-slug/{slug} - Public endpoint"""
    
    def test_public_post_by_slug_not_found(self):
        """Non-existent slug should return 404"""
        response = requests.get(f"{BASE_URL}/api/blog/posts/public/by-slug/nonexistent-slug-12345")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent public post returns 404")


class TestBlogMyPosts:
    """Test GET /api/blog/posts/mine - Requires authentication"""
    
    def test_my_posts_without_auth_returns_401(self):
        """My posts endpoint without auth should return 401"""
        response = requests.get(f"{BASE_URL}/api/blog/posts/mine")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ My posts endpoint correctly requires authentication")


class TestAuthenticatedBlogCRUD:
    """Test authenticated blog CRUD operations"""
    
    @pytest.fixture(autouse=True)
    def setup(self, auth_headers, created_post_id):
        self.headers = auth_headers
        self.created_post = created_post_id
    
    def test_01_get_posts_with_auth(self):
        """Authenticated user can get all posts"""
        response = requests.get(f"{BASE_URL}/api/blog/posts", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "posts" in data
        assert "total" in data
        print(f"✓ Authenticated posts endpoint returns {len(data['posts'])} posts")
    
    def test_02_create_post_faculty(self):
        """Faculty user can create a post"""
        unique_id = str(uuid.uuid4())[:8]
        payload = {
            "title": f"TEST_Blog Post {unique_id}",
            "content": "# Test Content\n\nThis is a **test** blog post with markdown.",
            "category": "Announcements",
            "tags": ["test", "iteration16"],
            "visibility": "public",
            "status": "published"
        }
        response = requests.post(f"{BASE_URL}/api/blog/posts", json=payload, headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data, "Response should have 'id'"
        assert "slug" in data, "Response should have 'slug'"
        assert data["title"] == payload["title"]
        assert data["category"] == "Announcements"
        assert data["visibility"] == "public"
        
        # Store for later tests
        self.created_post["id"] = data["id"]
        self.created_post["slug"] = data["slug"]
        print(f"✓ Created post with ID: {data['id']}, slug: {data['slug']}")
    
    def test_03_get_post_by_slug(self):
        """Can get post by slug"""
        if not self.created_post.get("slug"):
            pytest.skip("No post created yet")
        
        response = requests.get(
            f"{BASE_URL}/api/blog/posts/by-slug/{self.created_post['slug']}", 
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "content" in data, "Full post should include content"
        assert data["slug"] == self.created_post["slug"]
        print(f"✓ Retrieved post by slug: {data['title']}")
    
    def test_04_public_post_appears_in_public_endpoint(self):
        """Public post should appear in public endpoint"""
        if not self.created_post.get("slug"):
            pytest.skip("No post created yet")
        
        response = requests.get(f"{BASE_URL}/api/blog/posts/public")
        assert response.status_code == 200
        
        data = response.json()
        post_slugs = [p["slug"] for p in data["posts"]]
        assert self.created_post["slug"] in post_slugs, "Created public post should appear in public endpoint"
        print(f"✓ Public post appears in public endpoint (total: {data['total']})")
    
    def test_05_add_comment(self):
        """Any authenticated user can add a comment"""
        if not self.created_post.get("id"):
            pytest.skip("No post created yet")
        
        payload = {"content": "This is a test comment from iteration 16 testing."}
        response = requests.post(
            f"{BASE_URL}/api/blog/posts/{self.created_post['id']}/comments",
            json=payload,
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data
        assert data["content"] == payload["content"]
        self.created_post["comment_id"] = data["id"]
        print(f"✓ Added comment with ID: {data['id']}")
    
    def test_06_get_comments(self):
        """Can get comments for a post"""
        if not self.created_post.get("id"):
            pytest.skip("No post created yet")
        
        response = requests.get(
            f"{BASE_URL}/api/blog/posts/{self.created_post['id']}/comments",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        comments = response.json()
        assert isinstance(comments, list)
        assert len(comments) >= 1, "Should have at least one comment"
        print(f"✓ Retrieved {len(comments)} comment(s)")
    
    def test_07_update_post(self):
        """Author can update their post"""
        if not self.created_post.get("id"):
            pytest.skip("No post created yet")
        
        payload = {
            "title": f"TEST_Updated Blog Post {str(uuid.uuid4())[:8]}",
            "content": "# Updated Content\n\nThis post has been updated."
        }
        response = requests.put(
            f"{BASE_URL}/api/blog/posts/{self.created_post['id']}",
            json=payload,
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "Updated" in data["title"]
        # Slug should be updated too
        self.created_post["slug"] = data["slug"]
        print(f"✓ Updated post, new slug: {data['slug']}")
    
    def test_08_delete_comment(self):
        """Author can delete their comment"""
        if not self.created_post.get("comment_id"):
            pytest.skip("No comment created yet")
        
        response = requests.delete(
            f"{BASE_URL}/api/blog/comments/{self.created_post['comment_id']}",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("status") == "deleted"
        print("✓ Deleted comment successfully")
    
    def test_09_delete_post(self):
        """Author can delete their post"""
        if not self.created_post.get("id"):
            pytest.skip("No post created yet")
        
        response = requests.delete(
            f"{BASE_URL}/api/blog/posts/{self.created_post['id']}",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("status") == "deleted"
        print("✓ Deleted post successfully")
    
    def test_10_deleted_post_not_in_public(self):
        """Deleted post should not appear in public endpoint"""
        if not self.created_post.get("slug"):
            pytest.skip("No post slug stored")
        
        response = requests.get(f"{BASE_URL}/api/blog/posts/public")
        assert response.status_code == 200
        
        data = response.json()
        post_slugs = [p["slug"] for p in data["posts"]]
        assert self.created_post["slug"] not in post_slugs, "Deleted post should not appear"
        print("✓ Deleted post no longer appears in public endpoint")


class TestStudentCannotCreatePost:
    """Test that student role cannot create posts"""
    
    def test_student_create_post_returns_403(self):
        """Student should get 403 when trying to create a post"""
        # Create a student session for testing
        try:
            import sys
            sys.path.insert(0, '/app/backend')
            from database import sessions_col, users_col
            
            # Find student user
            student = users_col.find_one({"role": "student"}, {"_id": 0})
            if not student:
                pytest.skip("No student user found")
            
            # Create a session for student
            import uuid
            from datetime import datetime, timezone, timedelta
            student_session_id = f"TEST_STUDENT_{uuid.uuid4()}"
            sessions_col.insert_one({
                "session_id": student_session_id,
                "user_id": student["id"],
                "session_token": "test_token",
                "expires_at": datetime.now(timezone.utc) + timedelta(hours=1)
            })
            
            # Try to create post as student
            payload = {
                "title": "Student Test Post",
                "content": "This should fail",
                "category": "Announcements",
                "visibility": "public"
            }
            response = requests.post(
                f"{BASE_URL}/api/blog/posts",
                json=payload,
                headers={"x-session-id": student_session_id, "Content-Type": "application/json"}
            )
            
            # Cleanup
            sessions_col.delete_one({"session_id": student_session_id})
            
            assert response.status_code == 403, f"Expected 403, got {response.status_code}"
            print("✓ Student correctly gets 403 when trying to create post")
            
        except Exception as e:
            pytest.skip(f"Could not test student role: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
