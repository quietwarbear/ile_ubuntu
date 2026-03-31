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
- **Frontend**: React with React Router, Tailwind CSS, Shadcn/UI, Phosphor Icons, @tailwindcss/typography
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

### What's Been Implemented (Phase 1b - Course Enrollment - Feb 2026)
- [x] Course enrollment system: students browse and enroll in active courses
- [x] Course detail page with enrollment CTA, curriculum, progress bar
- [x] Lesson completion tracking: students mark lessons complete, progress auto-calculates
- [x] "My Learning" tab on Courses page showing enrolled courses with SVG progress circles
- [x] Faculty can view enrolled students with individual progress on course detail page

### What's Been Implemented (Phase 2 - Live Teaching - Feb 2026)
- [x] Live Teaching system with embedded Jitsi Meet video conferencing (free, no API keys)
- [x] Live session CRUD: create, schedule, start, join, end, delete
- [x] Session state management: scheduled -> live -> ended
- [x] Pre-join screen with background picker before entering Jitsi sessions
- [x] 9 curated branded backgrounds matching Ile Ubuntu aesthetic
- [x] "None" and "Blur" background options

### What's Been Implemented (Phase 3 - File & Google Integration - Feb 2026)
- [x] File upload per lesson with type-specific icons (PDF, DOC, PPT, XLS, Image)
- [x] Google OAuth 2.0 integration for Slides/Docs API access
- [x] Import dialog with Slides and Docs tabs, one-click import

### What's Been Implemented (Phase 4 - Cohorts, Spaces, Community, Archives - Mar 2026)
- [x] Cohort-Course linking: faculty link/unlink courses to cohorts
- [x] Cohort detail page with curriculum, member list, and per-member progress tracking
- [x] Protected Knowledge Spaces with 4 access levels: public, members, faculty+, elders only
- [x] Space discovery: members-only spaces visible to all users (content stripped for non-members)
- [x] Access request/approval flow for members-only spaces
- [x] Resource management within spaces (text, links, embeds)
- [x] Community forums fully functional with posts, replies, likes, categories
- [x] Archives with access-level filtering

### What's Been Implemented (Phase 5 - Progress Dashboard, Content Viewer, Backgrounds - Mar 2026)
- [x] Cohort Progress Dashboard: visual leaderboard with crown/medal icons for top performers
- [x] Per-course breakdown showing individual member progress across linked courses
- [x] Bar chart visualization of progress with gold/silver/bronze color coding
- [x] Lesson Content Viewer with markdown rendering (headings, bold, italic, code blocks, lists, tables)
- [x] Auto-detection and embedding of YouTube, Vimeo, Google Slides, and Google Docs URLs
- [x] Rich text styling using @tailwindcss/typography with custom dark theme prose classes
- [x] 4 new branded virtual backgrounds: Sacred Vault, Midnight Glow, Scholar's Den, Cosmic Dust
- [x] Total 9 curated backgrounds for Live Teaching pre-join screen
- [x] Full test suite: 19 backend + all frontend tests passing (iteration 8)

### Prioritized Backlog

#### P1 (Up Next)
- (none remaining from original P1 list!)

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
  server.py, database.py, middleware.py
  models/ (user.py, course.py, cohort.py)
  routes/ (auth, courses, cohorts, community, archives, files, messages, enrollments, live_sessions, google_integration, spaces)
/app/frontend/src/
  App.js (React Router)
  lib/ (api.js, backgrounds.js)
  components/ (layout/Sidebar.jsx, layout/AppLayout.jsx, LessonContentViewer.jsx)
  pages/ (Login, Dashboard, Courses, CourseDetail, Cohorts, CohortDetail, Spaces, Community, Archives, LiveSessions, LiveRoom, Messages, Settings)
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
