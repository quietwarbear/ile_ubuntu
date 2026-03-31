# The Ile Ubuntu - Living Learning Commons
## Product Requirements Document

### Original Problem Statement
Build a "Living Learning Commons" platform called "The Ile Ubuntu" that holds courses, cohorts, community, archives, and protected knowledge spaces in one coherent environment. Supports differentiated access roles (elders, faculty, students, assistants, admin) and features a midnight blue, black, and gold design with Ankh symbol branding.

### User Personas
- **Elder**: Highest governance/oversight role, can manage all content and users
- **Faculty**: Creates courses, manages cohorts, moderates community
- **Assistant**: Supports faculty, limited admin capabilities
- **Student**: Learner, enrolls in cohorts/courses, participates in community
- **Admin**: Platform administration, full system access

### Design System
- **Colors**: Midnight blue (#050814), Navy (#0A1128), Card (#0F172A), Gold (#D4AF37)
- **Typography**: Cormorant Garamond (headings), Outfit (body)
- **Theme**: Jewel & Luxury archetype, dark mode
- **Icons**: Phosphor Icons (duotone weight)
- **Layout**: Fixed sidebar navigation (desktop), responsive mobile hamburger

### Core Architecture
- **Frontend**: React with React Router, Tailwind CSS, Shadcn/UI, Phosphor Icons
- **Backend**: FastAPI (Python), modular route structure
- **Database**: MongoDB
- **Auth**: Emergent Auth (Google OAuth)

### What's Been Implemented (Phase 1 - Feb 2026)
- [x] Complete backend restructure: modular routes (auth, courses, cohorts, community, archives, files, messages)
- [x] RBAC system with 5 roles: admin, elder, faculty, assistant, student
- [x] Role hierarchy with permission checking
- [x] Courses CRUD with lesson sub-routes
- [x] Cohorts CRUD with join/leave functionality
- [x] Community forums with posts, replies, likes
- [x] Archives with access levels (public/restricted)
- [x] Messages and notifications system
- [x] File upload/download system
- [x] Frontend restructure: React Router with page components
- [x] Premium login page with split-panel design
- [x] Sidebar navigation with role-based display
- [x] Dashboard with stats and quick actions
- [x] All pages: Courses, Cohorts, Community, Archives, Messages, Settings
- [x] Settings page with role management (admin/elder only)
- [x] Full test suite: 39 backend + 9 frontend tests passing

### What's Been Implemented (Phase 1b - Course Enrollment - Feb 2026)
- [x] Course enrollment system: students browse and enroll in active courses
- [x] Course detail page (/courses/:courseId) with enrollment CTA, curriculum, progress bar
- [x] Lesson completion tracking: students mark lessons complete, progress auto-calculates
- [x] "My Learning" tab on Courses page showing enrolled courses with SVG progress circles
- [x] "My Learning" section on Dashboard with enrolled courses and progress
- [x] Faculty can view enrolled students with individual progress on course detail page
- [x] Course search/filter on browse view
- [x] Enrolled count tracking on courses (increments/decrements properly)
- [x] Full test suite: 18 enrollment backend + 12 enrollment frontend tests passing

### What's Been Implemented (Phase 2 - Live Teaching with Jitsi Meet - Feb 2026)
- [x] Live Teaching system with embedded Jitsi Meet video conferencing (free, no API keys)
- [x] Live session CRUD: create, schedule, start, join, end, delete
- [x] Session state management: scheduled -> live -> ended
- [x] Course-linked sessions (optional)
- [x] Immersive live room page (/live/:sessionId) with hidden sidebar, full-screen Jitsi embed
- [x] Session filters: All, Live Now, Upcoming, Past
- [x] RBAC: Only faculty+ can create/start sessions, students can only join live sessions
- [x] "Live Teaching" nav item in sidebar with VideoCamera icon
- [x] Full test suite: 19 backend + 19 frontend tests passing

### What's Been Implemented (Phase 2b - Branded Virtual Backgrounds - Feb 2026)
- [x] Pre-join screen with background picker before entering Jitsi sessions
- [x] 5 curated branded backgrounds matching Ile Ubuntu aesthetic
- [x] "None" and "Blur" background options
- [x] Visual selection state with gold border and checkmark overlay
- [x] Background auto-applied to Jitsi via executeCommand API on join
- [x] Full test suite: 19 backend regression + 20 frontend tests passing

### What's Been Implemented (Phase 3a - File Attachments - Feb 2026)
- [x] File upload per lesson with type-specific icons (PDF, DOC, PPT, XLS, Image)
- [x] Expandable lesson cards showing content text and attached materials
- [x] Faculty can attach files, students can download materials
- [x] File size display, hover-to-reveal download/delete controls
- [x] "Add Lesson" button directly on course detail page for faculty
- [x] Full test suite: 17 backend + all frontend tests passing

### What's Been Implemented (Phase 3b - Google OAuth & Import - Feb 2026)
- [x] Google OAuth 2.0 integration for Slides/Docs API access (connect/disconnect in Settings)
- [x] "Import from Google" button on lesson expanded views (when Google connected)
- [x] Import dialog with Slides and Docs tabs, lists user's files, one-click import
- [x] Imported Google Slides show as embeddable resources on lessons
- [x] Imported Google Docs extract content directly into lesson text
- [x] Token refresh mechanism for long-lived Google access
- [x] Full test suite: 25 backend + all frontend tests passing

### What's Been Implemented (Phase 4 - Cohorts, Spaces, Community, Archives - Mar 2026)
- [x] Cohort-Course linking: faculty link/unlink courses to cohorts
- [x] Cohort detail page with curriculum, member list, and per-member progress tracking
- [x] Protected Knowledge Spaces with 4 access levels: public, members, faculty+, elders only
- [x] Space discovery: members-only spaces visible to all users (content stripped for non-members)
- [x] Access request/approval flow for members-only spaces
- [x] Resource management within spaces (text, links, embeds)
- [x] Community forums fully functional with posts, replies, likes, categories
- [x] Archives with access-level filtering (public visible to all, restricted to faculty+)
- [x] Sidebar navigation updated with all sections
- [x] Fixed spaces visibility bug (non-members can now discover and request access)
- [x] Fixed archives delete button condition (admin-only properly)
- [x] Full test suite: 28 backend + 23 frontend tests passing (iteration 7)

### Prioritized Backlog

#### P0 (Next)
- (none - all P0s completed!)

#### P1 (Up Next)
- Lesson content viewer (rich text, embedded media)
- Custom AI-generated backgrounds (when image gen quota resets)

#### P2
- Edit/Delete course controls RBAC validation for faculty/elders
- Subscription/membership management
- Advanced analytics dashboard
- Search across courses, archives, community
- Email notifications
- Session recording management

### Key Files
```
/app/backend/
  server.py (FastAPI entry point, mounts routers)
  database.py (MongoDB connection)
  middleware.py (Auth middleware)
  models/ (user.py, course.py, cohort.py)
  routes/ (auth.py, courses.py, cohorts.py, community.py, archives.py, files.py, messages.py, enrollments.py, live_sessions.py, google_integration.py, spaces.py)
/app/frontend/src/
  App.js (React Router)
  lib/api.js (API client)
  components/layout/ (Sidebar.jsx, AppLayout.jsx)
  pages/ (LoginPage, DashboardPage, CoursesPage, CourseDetailPage, CohortsPage, CohortDetailPage, SpacesPage, CommunityPage, ArchivesPage, LiveSessionsPage, LiveRoomPage, MessagesPage, SettingsPage)
```

### API Endpoints
- Auth: POST /api/auth/profile, GET /api/auth/me, GET /api/auth/users, PUT /api/auth/users/{id}/role
- Courses: GET/POST /api/courses, GET/PUT/DELETE /api/courses/{id}, GET/POST /api/courses/{id}/lessons
- Enrollment: POST /api/courses/{id}/enroll, POST /api/courses/{id}/unenroll, GET /api/courses/{id}/enrollment, GET /api/courses/{id}/progress, POST /api/courses/{id}/lessons/{lid}/complete, GET /api/courses/{id}/enrollments, GET /api/enrollments/my-courses
- Cohorts: GET/POST /api/cohorts, GET/PUT/DELETE /api/cohorts/{id}, POST /api/cohorts/{id}/join, POST /api/cohorts/{id}/leave, POST /api/cohorts/{id}/courses, DELETE /api/cohorts/{id}/courses/{cid}, GET /api/cohorts/{id}/detail
- Spaces: GET/POST /api/spaces, GET/PUT/DELETE /api/spaces/{id}, POST /api/spaces/{id}/request-access, POST /api/spaces/{id}/approve/{uid}, POST /api/spaces/{id}/deny/{uid}, POST /api/spaces/{id}/resources
- Community: GET/POST /api/community/posts, GET/DELETE /api/community/posts/{id}, POST /api/community/posts/{id}/reply, POST /api/community/posts/{id}/like
- Archives: GET/POST /api/archives, GET/DELETE /api/archives/{id}
- Files: POST /api/files/upload, GET /api/files, GET /api/files/{id}/download, DELETE /api/files/{id}
- Messages: GET/POST /api/messages, GET /api/notifications, PUT /api/notifications/{id}/read
- Live: GET/POST /api/live-sessions, PUT /api/live-sessions/{id}/start, PUT /api/live-sessions/{id}/end, DELETE /api/live-sessions/{id}
