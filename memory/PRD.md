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

### Prioritized Backlog

#### P0 (Next)
- Google OAuth fix for Google Slides/Docs import (callback loop issue)
- File attachments on courses and lessons

#### P1
- Protected knowledge spaces with membership management
- Cohort-course linking (assign courses to cohorts)
- Enhanced community with categories filtering
- Lesson content viewer (rich text, embedded media)
- Branded virtual backgrounds for Jitsi sessions

#### P2
- Subscription/membership management
- Advanced analytics dashboard
- Search across courses, archives, community
- Email notifications
- Session recording management

### Key Files
```
/app/backend/
├── server.py (FastAPI entry point, mounts routers)
├── database.py (MongoDB connection)
├── middleware.py (Auth middleware)
├── models/ (user.py, course.py, cohort.py)
├── routes/ (auth.py, courses.py, cohorts.py, community.py, archives.py, files.py, messages.py)
/app/frontend/src/
├── App.js (React Router)
├── lib/api.js (API client)
├── components/layout/ (Sidebar.jsx, AppLayout.jsx)
├── pages/ (LoginPage, DashboardPage, CoursesPage, CohortsPage, CommunityPage, ArchivesPage, MessagesPage, SettingsPage)
```

### API Endpoints
- Auth: POST /api/auth/profile, GET /api/auth/me, GET /api/auth/users, PUT /api/auth/users/{id}/role
- Courses: GET/POST /api/courses, GET/PUT/DELETE /api/courses/{id}, GET/POST /api/courses/{id}/lessons
- Enrollment: POST /api/courses/{id}/enroll, POST /api/courses/{id}/unenroll, GET /api/courses/{id}/enrollment, GET /api/courses/{id}/progress, POST /api/courses/{id}/lessons/{lid}/complete, GET /api/courses/{id}/enrollments, GET /api/enrollments/my-courses
- Cohorts: GET/POST /api/cohorts, GET/PUT/DELETE /api/cohorts/{id}, POST /api/cohorts/{id}/join, POST /api/cohorts/{id}/leave
- Community: GET/POST /api/community/posts, GET/DELETE /api/community/posts/{id}, POST /api/community/posts/{id}/reply, POST /api/community/posts/{id}/like
- Archives: GET/POST /api/archives, GET/DELETE /api/archives/{id}
- Files: POST /api/files/upload, GET /api/files, GET /api/files/{id}/download, DELETE /api/files/{id}
- Messages: GET/POST /api/messages, GET /api/notifications, PUT /api/notifications/{id}/read
