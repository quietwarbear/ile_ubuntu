from fastapi import FastAPI, HTTPException, Depends, Header, Request, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pymongo import MongoClient
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import uuid
import requests
from datetime import datetime, timedelta
import json
import shutil
from pathlib import Path
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="The Ile Ubuntu API", version="1.0.0")

# Create uploads directory
UPLOADS_DIR = Path("uploads")
UPLOADS_DIR.mkdir(exist_ok=True)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for serving uploads
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# MongoDB connection
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = MongoClient(MONGO_URL)
db = client.ile_ubuntu

# Collections
users_collection = db.users
sessions_collection = db.sessions
classes_collection = db.classes
lessons_collection = db.lessons
slides_collection = db.slides
messages_collection = db.messages
notifications_collection = db.notifications
google_tokens_collection = db.google_tokens
files_collection = db.files

# Google OAuth credentials
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
GOOGLE_SCOPES = [
    'https://www.googleapis.com/auth/presentations',
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive.readonly'
]

# Google OAuth flow configuration - ENABLED with new credentials
def create_google_flow():
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["https://8bec313c-42bc-492f-8514-71511295d06c.preview.emergentagent.com/auth/google/callback"]
            }
        },
        scopes=GOOGLE_SCOPES
    )
    flow.redirect_uri = "https://8bec313c-42bc-492f-8514-71511295d06c.preview.emergentagent.com/auth/google/callback"
    return flow

# Pydantic models
class User(BaseModel):
    id: str
    email: str
    name: str
    picture: str
    role: str = "teacher"  # teacher or student
    created_at: datetime

class Session(BaseModel):
    session_id: str
    user_id: str
    session_token: str
    expires_at: datetime

class ClassRoom(BaseModel):
    id: str
    name: str
    description: str
    teacher_id: str
    students: List[str] = []
    created_at: datetime

class Lesson(BaseModel):
    id: str
    title: str
    description: str
    class_id: str
    teacher_id: str
    slides_url: Optional[str] = None
    google_slides_id: Optional[str] = None
    google_docs_id: Optional[str] = None
    audio_url: Optional[str] = None
    video_url: Optional[str] = None
    files: List[str] = []  # File IDs
    created_at: datetime
    updated_at: datetime

class Message(BaseModel):
    id: str
    sender_id: str
    recipient_id: str
    class_id: Optional[str] = None
    message: str
    created_at: datetime

class Notification(BaseModel):
    id: str
    user_id: str
    title: str
    message: str
    type: str  # lesson, message, assignment
    read: bool = False
    created_at: datetime

class LessonFile(BaseModel):
    id: str
    filename: str
    original_filename: str
    file_path: str
    file_size: int
    mime_type: str
    lesson_id: Optional[str] = None
    class_id: Optional[str] = None
    uploaded_by: str
    uploaded_at: datetime

# Authentication helper
async def get_current_user(x_session_id: Optional[str] = Header(None)):
    if not x_session_id:
        raise HTTPException(status_code=401, detail="Session ID required")
    
    session = sessions_collection.find_one({"session_id": x_session_id})
    if not session or session["expires_at"] < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    user = users_collection.find_one({"id": session["user_id"]})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user

# Root endpoint
@app.get("/")
async def root():
    return {"message": "The Ile Ubuntu API is running"}

# Authentication endpoints
@app.post("/api/auth/profile")
async def create_profile(request: Request):
    data = await request.json()
    session_id = data.get("session_id")
    
    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID required")
    
    # Call Emergent auth API
    headers = {"X-Session-ID": session_id}
    response = requests.get(
        "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
        headers=headers
    )
    
    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    auth_data = response.json()
    
    # Check if user exists
    existing_user = users_collection.find_one({"email": auth_data["email"]})
    
    if not existing_user:
        # Create new user
        user_data = {
            "id": str(uuid.uuid4()),
            "email": auth_data["email"],
            "name": auth_data["name"],
            "picture": auth_data["picture"],
            "role": "teacher",  # Default role
            "created_at": datetime.utcnow()
        }
        users_collection.insert_one(user_data)
        user_id = user_data["id"]
    else:
        user_id = existing_user["id"]
    
    # Create session
    session_data = {
        "session_id": session_id,
        "user_id": user_id,
        "session_token": auth_data["session_token"],
        "expires_at": datetime.utcnow() + timedelta(days=7)
    }
    sessions_collection.insert_one(session_data)
    
    return {"success": True, "user_id": user_id, "session_token": auth_data["session_token"]}

@app.get("/api/auth/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "name": current_user["name"],
        "picture": current_user["picture"],
        "role": current_user["role"]
    }

# Classroom endpoints
@app.post("/api/classes")
async def create_class(class_data: dict, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can create classes")
    
    new_class = {
        "id": str(uuid.uuid4()),
        "name": class_data["name"],
        "description": class_data.get("description", ""),
        "teacher_id": current_user["id"],
        "students": [],
        "created_at": datetime.utcnow()
    }
    
    classes_collection.insert_one(new_class)
    return new_class

@app.get("/api/classes")
async def get_classes(current_user: dict = Depends(get_current_user)):
    if current_user["role"] == "teacher":
        classes = list(classes_collection.find({"teacher_id": current_user["id"]}))
    else:
        classes = list(classes_collection.find({"students": current_user["id"]}))
    
    # Remove MongoDB _id field
    for class_item in classes:
        class_item.pop("_id", None)
    
    return classes

@app.get("/api/classes/{class_id}")
async def get_class(class_id: str, current_user: dict = Depends(get_current_user)):
    class_data = classes_collection.find_one({"id": class_id})
    if not class_data:
        raise HTTPException(status_code=404, detail="Class not found")
    
    # Check if user has access
    if (current_user["role"] == "teacher" and class_data["teacher_id"] != current_user["id"]) or \
       (current_user["role"] == "student" and current_user["id"] not in class_data["students"]):
        raise HTTPException(status_code=403, detail="Access denied")
    
    class_data.pop("_id", None)
    return class_data

# Lesson endpoints
@app.post("/api/lessons")
async def create_lesson(lesson_data: dict, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can create lessons")
    
    # Verify class ownership
    class_data = classes_collection.find_one({"id": lesson_data["class_id"]})
    if not class_data or class_data["teacher_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    new_lesson = {
        "id": str(uuid.uuid4()),
        "title": lesson_data["title"],
        "description": lesson_data.get("description", ""),
        "class_id": lesson_data["class_id"],
        "teacher_id": current_user["id"],
        "slides_url": lesson_data.get("slides_url"),
        "google_slides_id": lesson_data.get("google_slides_id"),
        "google_docs_id": lesson_data.get("google_docs_id"),
        "audio_url": lesson_data.get("audio_url"),
        "video_url": lesson_data.get("video_url"),
        "files": [],  # Initialize empty files list
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    lessons_collection.insert_one(new_lesson)
    
    # Create notification for students
    if class_data["students"]:
        for student_id in class_data["students"]:
            notification = {
                "id": str(uuid.uuid4()),
                "user_id": student_id,
                "title": "New Lesson Available",
                "message": f"New lesson '{new_lesson['title']}' has been added to {class_data['name']}",
                "type": "lesson",
                "read": False,
                "created_at": datetime.utcnow()
            }
            notifications_collection.insert_one(notification)
    
    new_lesson.pop("_id", None)
    return new_lesson

@app.get("/api/lessons")
async def get_lessons(class_id: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    query = {}
    if class_id:
        # Verify access to class
        class_data = classes_collection.find_one({"id": class_id})
        if not class_data:
            raise HTTPException(status_code=404, detail="Class not found")
        
        if (current_user["role"] == "teacher" and class_data["teacher_id"] != current_user["id"]) or \
           (current_user["role"] == "student" and current_user["id"] not in class_data["students"]):
            raise HTTPException(status_code=403, detail="Access denied")
        
        query["class_id"] = class_id
    else:
        if current_user["role"] == "teacher":
            query["teacher_id"] = current_user["id"]
        else:
            # Get student's classes
            student_classes = classes_collection.find({"students": current_user["id"]})
            class_ids = [c["id"] for c in student_classes]
            query["class_id"] = {"$in": class_ids}
    
    lessons = list(lessons_collection.find(query).sort("created_at", -1))
    
    for lesson in lessons:
        lesson.pop("_id", None)
    
    return lessons

# Google integration endpoints
@app.get("/api/google/auth-url")
async def get_google_auth_url(current_user: dict = Depends(get_current_user)):
    """Get Google OAuth authorization URL"""
    try:
        client_id = GOOGLE_CLIENT_ID
        redirect_uri = "https://8bec313c-42bc-492f-8514-71511295d06c.preview.emergentagent.com/auth/google/callback"
        
        # Build the OAuth URL with proper encoding
        auth_url = (
            f"https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={client_id}&"
            f"redirect_uri={redirect_uri}&"
            f"response_type=code&"
            f"scope=https://www.googleapis.com/auth/presentations%20https://www.googleapis.com/auth/documents%20https://www.googleapis.com/auth/drive.readonly&"
            f"access_type=offline&"
            f"prompt=consent&"
            f"include_granted_scopes=true"
        )
        
        return {"auth_url": auth_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create auth URL: {str(e)}")

@app.get("/auth/google/callback")
async def google_oauth_callback_get(request: Request):
    """Handle Google OAuth callback - GET request"""
    try:
        # Log the callback for debugging
        print(f"OAuth callback received: {request.url}")
        print(f"Query params: {dict(request.query_params)}")
        
        # Get the authorization code from query parameters
        authorization_code = request.query_params.get("code")
        error = request.query_params.get("error")
        
        if error:
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head><title>OAuth Error</title></head>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                <h2>🔱 The Ile Ubuntu</h2>
                <p style="color: red;">OAuth Error: {error}</p>
                <p>Please close this window and try again.</p>
            </body>
            </html>
            """
            from fastapi.responses import HTMLResponse
            return HTMLResponse(content=html_content)
        
        if not authorization_code:
            html_content = """
            <!DOCTYPE html>
            <html>
            <head><title>OAuth Error</title></head>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                <h2>🔱 The Ile Ubuntu</h2>
                <p style="color: red;">No authorization code received</p>
                <p>Please close this window and try again.</p>
            </body>
            </html>
            """
            from fastapi.responses import HTMLResponse
            return HTMLResponse(content=html_content)
        
        # Create a simple success page that redirects to the main app
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Google OAuth Success - The Ile Ubuntu</title>
            <style>
                body {{ 
                    font-family: Arial, sans-serif; 
                    text-align: center; 
                    padding: 50px; 
                    background: linear-gradient(135deg, #0f172a, #1e293b);
                    color: white;
                }}
                .ankh {{ color: #d97706; font-size: 48px; }}
                .success {{ color: #10b981; }}
            </style>
        </head>
        <body>
            <div class="ankh">🔱</div>
            <h2>The Ile Ubuntu</h2>
            <p class="success">✅ Google Authentication Successful!</p>
            <p>Completing connection...</p>
            
            <script>
                // Store the auth code and redirect to main app
                localStorage.setItem('google_auth_code', '{authorization_code}');
                setTimeout(function() {{
                    window.location.href = 'https://8bec313c-42bc-492f-8514-71511295d06c.preview.emergentagent.com/?google_connected=true';
                }}, 2000);
            </script>
        </body>
        </html>
        """
        
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        print(f"OAuth callback error: {str(e)}")
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head><title>OAuth Error</title></head>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h2>🔱 The Ile Ubuntu</h2>
            <p style="color: red;">OAuth callback error: {str(e)}</p>
            <p>Please close this window and try again.</p>
        </body>
        </html>
        """
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=html_content)

@app.post("/api/google/complete-auth")
async def complete_google_auth(request: Request, current_user: dict = Depends(get_current_user)):
    """Complete Google OAuth with authorization code"""
    try:
        data = await request.json()
        authorization_code = data.get("code")
        
        if not authorization_code:
            raise HTTPException(status_code=400, detail="Authorization code required")
        
        flow = create_google_flow()
        flow.fetch_token(code=authorization_code)
        
        credentials = flow.credentials
        
        # Store Google credentials
        token_data = {
            "user_id": current_user["id"],
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes,
            "created_at": datetime.utcnow(),
            "expires_at": credentials.expiry
        }
        
        # Update or insert Google token
        google_tokens_collection.replace_one(
            {"user_id": current_user["id"]},
            token_data,
            upsert=True
        )
        
        return {"success": True, "message": "Google account connected successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OAuth completion failed: {str(e)}")

@app.get("/api/google/slides")
async def list_google_slides(current_user: dict = Depends(get_current_user)):
    """List user's Google Slides presentations"""
    try:
        # Get user's Google credentials
        token_data = google_tokens_collection.find_one({"user_id": current_user["id"]})
        if not token_data:
            raise HTTPException(status_code=401, detail="Google account not connected")
        
        # Create credentials object
        credentials = Credentials(
            token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            token_uri=token_data["token_uri"],
            client_id=token_data["client_id"],
            client_secret=token_data["client_secret"],
            scopes=token_data["scopes"]
        )
        
        # Refresh credentials if needed
        if credentials.expired:
            credentials.refresh(GoogleRequest())
            # Update stored credentials
            google_tokens_collection.update_one(
                {"user_id": current_user["id"]},
                {"$set": {
                    "access_token": credentials.token,
                    "expires_at": credentials.expiry
                }}
            )
        
        # Build Drive service to list presentations
        drive_service = build('drive', 'v3', credentials=credentials)
        
        # Search for Google Slides presentations
        results = drive_service.files().list(
            q="mimeType='application/vnd.google-apps.presentation'",
            pageSize=50,
            fields="nextPageToken, files(id, name, createdTime, modifiedTime, thumbnailLink)"
        ).execute()
        
        presentations = results.get('files', [])
        
        return {"presentations": presentations}
        
    except HttpError as error:
        raise HTTPException(status_code=400, detail=f"Google API error: {error}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list slides: {str(e)}")

@app.get("/api/google/docs")
async def list_google_docs(current_user: dict = Depends(get_current_user)):
    """List user's Google Docs documents"""
    try:
        # Get user's Google credentials
        token_data = google_tokens_collection.find_one({"user_id": current_user["id"]})
        if not token_data:
            raise HTTPException(status_code=401, detail="Google account not connected")
        
        # Create credentials object
        credentials = Credentials(
            token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            token_uri=token_data["token_uri"],
            client_id=token_data["client_id"],
            client_secret=token_data["client_secret"],
            scopes=token_data["scopes"]
        )
        
        # Refresh credentials if needed
        if credentials.expired:
            credentials.refresh(GoogleRequest())
            # Update stored credentials
            google_tokens_collection.update_one(
                {"user_id": current_user["id"]},
                {"$set": {
                    "access_token": credentials.token,
                    "expires_at": credentials.expiry
                }}
            )
        
        # Build Drive service to list documents
        drive_service = build('drive', 'v3', credentials=credentials)
        
        # Search for Google Docs documents
        results = drive_service.files().list(
            q="mimeType='application/vnd.google-apps.document'",
            pageSize=50,
            fields="nextPageToken, files(id, name, createdTime, modifiedTime, thumbnailLink)"
        ).execute()
        
        documents = results.get('files', [])
        
        return {"documents": documents}
        
    except HttpError as error:
        raise HTTPException(status_code=400, detail=f"Google API error: {error}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list docs: {str(e)}")

@app.post("/api/google/import-slides")
async def import_google_slides(data: dict, current_user: dict = Depends(get_current_user)):
    """Import Google Slides presentation - DISABLED"""
    raise HTTPException(
        status_code=501, 
        detail="Google Slides import is temporarily disabled. Please configure Google Cloud Console first."
    )

@app.post("/api/google/import-docs")
async def import_google_docs(data: dict, current_user: dict = Depends(get_current_user)):
    """Import Google Docs document - DISABLED"""
    raise HTTPException(
        status_code=501, 
        detail="Google Docs import is temporarily disabled. Please configure Google Cloud Console first."
    )

@app.get("/api/google/slides/{slides_id}")
async def get_slides_content(slides_id: str, current_user: dict = Depends(get_current_user)):
    """Get Google Slides content - DISABLED"""
    raise HTTPException(
        status_code=501, 
        detail="Google Slides content access is temporarily disabled. Please configure Google Cloud Console first."
    )

@app.get("/api/test-google-config")
async def test_google_config():
    """Test Google OAuth configuration"""
    return {
        "client_id": GOOGLE_CLIENT_ID,
        "project_id": os.environ.get('GOOGLE_PROJECT_ID'),
        "redirect_uri": "https://8bec313c-42bc-492f-8514-71511295d06c.preview.emergentagent.com/auth/google/callback",
        "test_auth_url": f"https://accounts.google.com/o/oauth2/v2/auth?client_id={GOOGLE_CLIENT_ID}&redirect_uri=https://8bec313c-42bc-492f-8514-71511295d06c.preview.emergentagent.com/auth/google/callback&response_type=code&scope=https://www.googleapis.com/auth/presentations&access_type=offline&prompt=consent"
    }

# Messaging endpoints
@app.post("/api/messages")
async def send_message(message_data: dict, current_user: dict = Depends(get_current_user)):
    new_message = {
        "id": str(uuid.uuid4()),
        "sender_id": current_user["id"],
        "recipient_id": message_data["recipient_id"],
        "class_id": message_data.get("class_id"),
        "message": message_data["message"],
        "created_at": datetime.utcnow()
    }
    
    messages_collection.insert_one(new_message)
    
    # Create notification
    notification = {
        "id": str(uuid.uuid4()),
        "user_id": message_data["recipient_id"],
        "title": "New Message",
        "message": f"You have a new message from {current_user['name']}",
        "type": "message",
        "read": False,
        "created_at": datetime.utcnow()
    }
    notifications_collection.insert_one(notification)
    
    new_message.pop("_id", None)
    return new_message

@app.get("/api/messages")
async def get_messages(recipient_id: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    query = {
        "$or": [
            {"sender_id": current_user["id"]},
            {"recipient_id": current_user["id"]}
        ]
    }
    
    if recipient_id:
        query = {
            "$or": [
                {"sender_id": current_user["id"], "recipient_id": recipient_id},
                {"sender_id": recipient_id, "recipient_id": current_user["id"]}
            ]
        }
    
    messages = list(messages_collection.find(query).sort("created_at", -1))
    
    for message in messages:
        message.pop("_id", None)
    
    return messages

# Notifications endpoints
@app.get("/api/notifications")
async def get_notifications(current_user: dict = Depends(get_current_user)):
    notifications = list(notifications_collection.find({"user_id": current_user["id"]}).sort("created_at", -1))
    
    for notification in notifications:
        notification.pop("_id", None)
    
    return notifications

@app.put("/api/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, current_user: dict = Depends(get_current_user)):
    result = notifications_collection.update_one(
        {"id": notification_id, "user_id": current_user["id"]},
        {"$set": {"read": True}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    
# File upload endpoints
@app.post("/api/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    lesson_id: Optional[str] = Form(None),
    class_id: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """Upload a file for lesson plans"""
    try:
        # Validate file type
        allowed_types = {
            'application/pdf': '.pdf',
            'application/msword': '.doc',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
            'application/vnd.ms-powerpoint': '.ppt',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation': '.pptx',
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'text/plain': '.txt',
            'application/vnd.ms-excel': '.xls',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx'
        }
        
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="File type not allowed")
        
        # Generate unique filename
        file_id = str(uuid.uuid4())
        extension = allowed_types[file.content_type]
        filename = f"{file_id}{extension}"
        file_path = UPLOADS_DIR / filename
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Save file metadata to database
        file_data = {
            "id": file_id,
            "filename": filename,
            "original_filename": file.filename,
            "file_path": str(file_path),
            "file_size": file_size,
            "mime_type": file.content_type,
            "lesson_id": lesson_id,
            "class_id": class_id,
            "uploaded_by": current_user["id"],
            "uploaded_at": datetime.utcnow()
        }
        
        files_collection.insert_one(file_data)
        
        # Update lesson if lesson_id provided
        if lesson_id:
            lessons_collection.update_one(
                {"id": lesson_id, "teacher_id": current_user["id"]},
                {"$addToSet": {"files": file_id}}
            )
        
        file_data.pop("_id", None)
        return {
            "success": True,
            "file": file_data,
            "download_url": f"/api/files/{file_id}/download"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")

@app.get("/api/files/{file_id}/download")
async def download_file(file_id: str, current_user: dict = Depends(get_current_user)):
    """Download a file"""
    try:
        file_data = files_collection.find_one({"id": file_id})
        if not file_data:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Check permissions (file owner or lesson access)
        if file_data["uploaded_by"] != current_user["id"]:
            # Check if user has access to the lesson/class
            if file_data.get("lesson_id"):
                lesson = lessons_collection.find_one({"id": file_data["lesson_id"]})
                if not lesson:
                    raise HTTPException(status_code=403, detail="Access denied")
                
                # Check if user is teacher or student in the class
                class_data = classes_collection.find_one({"id": lesson["class_id"]})
                if not class_data:
                    raise HTTPException(status_code=403, detail="Access denied")
                
                if (current_user["role"] == "teacher" and class_data["teacher_id"] != current_user["id"]) or \
                   (current_user["role"] == "student" and current_user["id"] not in class_data["students"]):
                    raise HTTPException(status_code=403, detail="Access denied")
        
        file_path = Path(file_data["file_path"])
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found on disk")
        
        return FileResponse(
            path=file_path,
            filename=file_data["original_filename"],
            media_type=file_data["mime_type"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File download failed: {str(e)}")

@app.get("/api/files")
async def get_files(
    lesson_id: Optional[str] = None,
    class_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get files for a lesson or class"""
    try:
        query = {}
        
        if lesson_id:
            query["lesson_id"] = lesson_id
            # Verify access to lesson
            lesson = lessons_collection.find_one({"id": lesson_id})
            if not lesson:
                raise HTTPException(status_code=404, detail="Lesson not found")
            
            class_data = classes_collection.find_one({"id": lesson["class_id"]})
            if not class_data:
                raise HTTPException(status_code=404, detail="Class not found")
            
            if (current_user["role"] == "teacher" and class_data["teacher_id"] != current_user["id"]) or \
               (current_user["role"] == "student" and current_user["id"] not in class_data["students"]):
                raise HTTPException(status_code=403, detail="Access denied")
        
        elif class_id:
            query["class_id"] = class_id
            # Verify access to class
            class_data = classes_collection.find_one({"id": class_id})
            if not class_data:
                raise HTTPException(status_code=404, detail="Class not found")
            
            if (current_user["role"] == "teacher" and class_data["teacher_id"] != current_user["id"]) or \
               (current_user["role"] == "student" and current_user["id"] not in class_data["students"]):
                raise HTTPException(status_code=403, detail="Access denied")
        
        else:
            # Get user's files
            query["uploaded_by"] = current_user["id"]
        
        files = list(files_collection.find(query).sort("uploaded_at", -1))
        
        for file_data in files:
            file_data.pop("_id", None)
            file_data["download_url"] = f"/api/files/{file_data['id']}/download"
        
        return {"files": files}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get files: {str(e)}")

@app.delete("/api/files/{file_id}")
async def delete_file(file_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a file"""
    try:
        file_data = files_collection.find_one({"id": file_id})
        if not file_data:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Check if user owns the file
        if file_data["uploaded_by"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Delete file from disk
        file_path = Path(file_data["file_path"])
        if file_path.exists():
            file_path.unlink()
        
        # Remove from database
        files_collection.delete_one({"id": file_id})
        
        # Remove from lesson if associated
        if file_data.get("lesson_id"):
            lessons_collection.update_one(
                {"id": file_data["lesson_id"]},
                {"$pull": {"files": file_id}}
            )
        
        return {"success": True, "message": "File deleted successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)