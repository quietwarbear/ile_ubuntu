import requests
import sys
import json
import io
import os
from datetime import datetime

class IleUbuntuAPITester:
    def __init__(self, base_url="https://8bec313c-42bc-492f-8514-71511295d06c.preview.emergentagent.com"):
        self.base_url = base_url
        self.session_id = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.created_class_id = None
        self.created_lesson_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None, files=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        test_headers = {}
        
        if headers:
            test_headers.update(headers)
        
        if self.session_id and 'X-Session-ID' not in test_headers:
            test_headers['X-Session-ID'] = self.session_id

        # Don't set Content-Type for file uploads
        if not files and 'Content-Type' not in test_headers:
            test_headers['Content-Type'] = 'application/json'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        print(f"   Method: {method}")
        print(f"   Headers: {test_headers}")
        if data and not files:
            print(f"   Data: {json.dumps(data, indent=2)}")
        elif files:
            print(f"   Files: {list(files.keys()) if files else 'None'}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers)
            elif method == 'POST':
                if files:
                    response = requests.post(url, files=files, data=data, headers=test_headers)
                else:
                    response = requests.post(url, json=data, headers=test_headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers)

            print(f"   Response Status: {response.status_code}")
            
            try:
                response_data = response.json()
                print(f"   Response Data: {json.dumps(response_data, indent=2)}")
            except:
                print(f"   Response Text: {response.text}")
                response_data = {}

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")

            return success, response_data

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test root endpoint"""
        success, response = self.run_test(
            "Root Endpoint",
            "GET",
            "",
            200
        )
        # Check if the response contains "The Ile Ubuntu"
        if success and response.get("message"):
            if "The Ile Ubuntu" in response["message"]:
                print("✅ App name correctly updated to 'The Ile Ubuntu'")
            else:
                print(f"⚠️  App name in response: {response['message']}")
        return success

    def test_auth_me_without_session(self):
        """Test /api/auth/me without session (should fail)"""
        success, response = self.run_test(
            "Auth Me Without Session",
            "GET",
            "api/auth/me",
            401
        )
        return success

    def test_create_profile_without_session(self):
        """Test creating profile without session_id (should fail)"""
        success, response = self.run_test(
            "Create Profile Without Session",
            "POST",
            "api/auth/profile",
            400,
            data={}
        )
        return success

    def test_create_profile_with_invalid_session(self):
        """Test creating profile with invalid session_id"""
        success, response = self.run_test(
            "Create Profile With Invalid Session",
            "POST",
            "api/auth/profile",
            401,
            data={"session_id": "invalid_session_123"}
        )
        return success

    def test_classes_without_auth(self):
        """Test getting classes without authentication"""
        success, response = self.run_test(
            "Get Classes Without Auth",
            "GET",
            "api/classes",
            401
        )
        return success

    def test_lessons_without_auth(self):
        """Test getting lessons without authentication"""
        success, response = self.run_test(
            "Get Lessons Without Auth",
            "GET",
            "api/lessons",
            401
        )
        return success

    def test_messages_without_auth(self):
        """Test getting messages without authentication"""
        success, response = self.run_test(
            "Get Messages Without Auth",
            "GET",
            "api/messages",
            401
        )
        return success

    def test_notifications_without_auth(self):
        """Test getting notifications without authentication"""
        success, response = self.run_test(
            "Get Notifications Without Auth",
            "GET",
            "api/notifications",
            401
        )
        return success

    def test_google_auth_url_without_auth(self):
        """Test Google auth URL without authentication"""
        success, response = self.run_test(
            "Google Auth URL Without Auth",
            "GET",
            "api/google/auth-url",
            401
        )
        return success

    def test_google_auth_url_with_mock_session(self):
        """Test Google auth URL with mock session to check error handling"""
        # This will fail with 401 but we want to see what the response would be
        # if we had a valid session - testing the error handling logic
        success, response = self.run_test(
            "Google Auth URL With Mock Session (Expected to fail but shows error handling)",
            "GET",
            "api/google/auth-url",
            401,  # We expect 401 since we don't have valid session
            headers={"X-Session-ID": "mock_session_for_testing"}
        )
        return success

    def test_google_oauth_callback_without_auth(self):
        """Test Google OAuth callback without authentication"""
        success, response = self.run_test(
            "Google OAuth Callback Without Auth",
            "POST",
            "api/google/callback",
            401,
            data={"code": "test_code", "state": "test_state"}
        )
        return success

    def test_google_import_slides_without_auth(self):
        """Test Google import slides without authentication"""
        success, response = self.run_test(
            "Google Import Slides Without Auth",
            "POST",
            "api/google/import-slides",
            401,
            data={"slides_id": "test_slides_id", "lesson_id": "test_lesson_id"}
        )
        return success

    def test_google_import_docs_without_auth(self):
        """Test Google import docs without authentication"""
        success, response = self.run_test(
            "Google Import Docs Without Auth",
            "POST",
            "api/google/import-docs",
            401,
            data={"docs_id": "test_docs_id", "lesson_id": "test_lesson_id"}
        )
        return success

    def test_google_slides_content_without_auth(self):
        """Test Google slides content without authentication"""
        success, response = self.run_test(
            "Google Slides Content Without Auth",
            "GET",
            "api/google/slides/test_slides_id",
            401
        )
        return success

    def test_google_slides_without_auth(self):
        """Test Google slides without authentication"""
        success, response = self.run_test(
            "Google Slides Without Auth",
            "GET",
            "api/google/slides",
            401
        )
        return success

    def test_google_docs_without_auth(self):
        """Test Google docs without authentication"""
        success, response = self.run_test(
            "Google Docs Without Auth",
            "GET",
            "api/google/docs",
            401
        )
        return success

    def test_create_class_without_auth(self):
        """Test creating class without authentication"""
        success, response = self.run_test(
            "Create Class Without Auth",
            "POST",
            "api/classes",
            401,
            data={"name": "Test Class", "description": "Test Description"}
        )
        return success

    def test_create_lesson_without_auth(self):
        """Test creating lesson without authentication"""
        success, response = self.run_test(
            "Create Lesson Without Auth",
            "POST",
            "api/lessons",
            401,
            data={"title": "Test Lesson", "description": "Test Description", "class_id": "test_id"}
        )
        return success

    def test_send_message_without_auth(self):
        """Test sending message without authentication"""
        success, response = self.run_test(
            "Send Message Without Auth",
            "POST",
            "api/messages",
            401,
            data={"recipient_id": "test_id", "message": "Test message"}
        )
        return success

    def create_test_file(self, filename, content, content_type):
        """Create a test file for upload"""
        if content_type == 'text/plain':
            return io.BytesIO(content.encode('utf-8'))
        elif content_type == 'application/pdf':
            # Create a minimal PDF-like content
            pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000074 00000 n \n0000000120 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n179\n%%EOF"
            return io.BytesIO(pdf_content)
        else:
            # For other types, create simple content
            return io.BytesIO(content.encode('utf-8'))

    def test_file_upload_without_auth(self):
        """Test file upload without authentication"""
        test_file = self.create_test_file("test.txt", "Test content", "text/plain")
        files = {'file': ('test.txt', test_file, 'text/plain')}
        
        success, response = self.run_test(
            "File Upload Without Auth",
            "POST",
            "api/files/upload",
            401,
            files=files
        )
        return success

    def test_file_upload_invalid_type_without_auth(self):
        """Test file upload with invalid type without authentication"""
        test_file = self.create_test_file("test.exe", "Invalid content", "application/x-executable")
        files = {'file': ('test.exe', test_file, 'application/x-executable')}
        
        success, response = self.run_test(
            "File Upload Invalid Type Without Auth",
            "POST",
            "api/files/upload",
            401,  # Should fail with 401 before checking file type
            files=files
        )
        return success

    def test_get_files_without_auth(self):
        """Test getting files without authentication"""
        success, response = self.run_test(
            "Get Files Without Auth",
            "GET",
            "api/files",
            401
        )
        return success

    def test_download_file_without_auth(self):
        """Test downloading file without authentication"""
        success, response = self.run_test(
            "Download File Without Auth",
            "GET",
            "api/files/test_file_id/download",
            401
        )
        return success

    def test_delete_file_without_auth(self):
        """Test deleting file without authentication"""
        success, response = self.run_test(
            "Delete File Without Auth",
            "DELETE",
            "api/files/test_file_id",
            401
        )
        return success

    def test_file_upload_allowed_types_simulation(self):
        """Test file upload validation for allowed types (simulation without auth)"""
        allowed_types = [
            ('test.pdf', 'application/pdf'),
            ('test.doc', 'application/msword'),
            ('test.docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
            ('test.ppt', 'application/vnd.ms-powerpoint'),
            ('test.pptx', 'application/vnd.openxmlformats-officedocument.presentationml.presentation'),
            ('test.jpg', 'image/jpeg'),
            ('test.png', 'image/png'),
            ('test.gif', 'image/gif'),
            ('test.txt', 'text/plain'),
            ('test.xls', 'application/vnd.ms-excel'),
            ('test.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        ]
        
        print(f"\n📁 TESTING FILE TYPE VALIDATION (WITHOUT AUTH - EXPECT 401)")
        print("-" * 60)
        
        all_passed = True
        for filename, content_type in allowed_types:
            test_file = self.create_test_file(filename, f"Test content for {filename}", content_type)
            files = {'file': (filename, test_file, content_type)}
            
            success, response = self.run_test(
                f"File Upload {filename} ({content_type})",
                "POST",
                "api/files/upload",
                401,  # Expect 401 without auth
                files=files
            )
            if not success:
                all_passed = False
        
        return all_passed

    def test_file_upload_disallowed_types_simulation(self):
        """Test file upload validation for disallowed types (simulation without auth)"""
        disallowed_types = [
            ('test.exe', 'application/x-executable'),
            ('test.bat', 'application/x-bat'),
            ('test.sh', 'application/x-sh'),
            ('test.zip', 'application/zip'),
            ('test.rar', 'application/x-rar-compressed')
        ]
        
        print(f"\n🚫 TESTING DISALLOWED FILE TYPES (WITHOUT AUTH - EXPECT 401)")
        print("-" * 60)
        
        all_passed = True
        for filename, content_type in disallowed_types:
            test_file = self.create_test_file(filename, f"Test content for {filename}", content_type)
            files = {'file': (filename, test_file, content_type)}
            
            success, response = self.run_test(
                f"File Upload {filename} ({content_type}) - Should be blocked",
                "POST",
                "api/files/upload",
                401,  # Expect 401 without auth (would be 400 with auth due to file type)
                files=files
            )
            if not success:
                all_passed = False
        
        return all_passed

    def print_summary(self):
        """Print test summary"""
        print(f"\n" + "="*60)
        print(f"📊 TEST SUMMARY")
        print(f"="*60)
        print(f"Total Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if self.tests_passed == self.tests_run:
            print(f"🎉 All tests passed!")
            return 0
        else:
            print(f"⚠️  Some tests failed. Check the logs above for details.")
            return 1

def main():
    print("🚀 Starting The Ile Ubuntu API Tests...")
    print("="*60)
    
    tester = IleUbuntuAPITester()
    
    # Test basic endpoints
    print("\n📋 TESTING BASIC ENDPOINTS")
    print("-" * 40)
    tester.test_root_endpoint()
    
    # Test authentication endpoints
    print("\n🔐 TESTING AUTHENTICATION ENDPOINTS")
    print("-" * 40)
    tester.test_auth_me_without_session()
    tester.test_create_profile_without_session()
    tester.test_create_profile_with_invalid_session()
    
    # Test protected endpoints without authentication
    print("\n🛡️  TESTING PROTECTED ENDPOINTS (WITHOUT AUTH)")
    print("-" * 40)
    tester.test_classes_without_auth()
    tester.test_lessons_without_auth()
    tester.test_messages_without_auth()
    tester.test_notifications_without_auth()
    tester.test_create_class_without_auth()
    tester.test_create_lesson_without_auth()
    tester.test_send_message_without_auth()
    
    # Test Google integration endpoints without authentication
    print("\n🔗 TESTING GOOGLE INTEGRATION ENDPOINTS (WITHOUT AUTH)")
    print("-" * 40)
    tester.test_google_auth_url_without_auth()
    tester.test_google_auth_url_with_mock_session()
    tester.test_google_slides_without_auth()
    tester.test_google_docs_without_auth()
    tester.test_google_oauth_callback_without_auth()
    tester.test_google_import_slides_without_auth()
    tester.test_google_import_docs_without_auth()
    tester.test_google_slides_content_without_auth()
    
    # Test file upload endpoints without authentication
    print("\n📁 TESTING FILE UPLOAD ENDPOINTS (WITHOUT AUTH)")
    print("-" * 40)
    tester.test_file_upload_without_auth()
    tester.test_file_upload_invalid_type_without_auth()
    tester.test_get_files_without_auth()
    tester.test_download_file_without_auth()
    tester.test_delete_file_without_auth()
    
    # Test file type validation
    tester.test_file_upload_allowed_types_simulation()
    tester.test_file_upload_disallowed_types_simulation()
    
    return tester.print_summary()

if __name__ == "__main__":
    sys.exit(main())