# The Ile Ubuntu - Living Learning Commons
## Product Requirements Document

### Original Problem Statement
Build a "Living Learning Commons" platform called "The Ile Ubuntu" that holds courses, cohorts, community, archives, and protected knowledge spaces in one coherent environment. Supports differentiated access roles (elders, faculty, students, assistants, admin) and features a midnight blue, black, and gold design with Ankh symbol branding.

### User Personas
- **Elder**: Highest governance/oversight role, can manage all content and users
- **Faculty**: Creates courses, manages cohorts, moderates community, views analytics
- **Assistant**: Supports faculty, limited admin capabilities
- **Student**: Learner, enrolls in cohorts/courses, participates in community
- **Admin**: Platform administration, full system access

### Design System
- **Colors**: Midnight blue (#050814), Navy (#0A1128), Card (#0F172A), Gold (#D4AF37)
- **Typography**: Cormorant Garamond (headings), Outfit (body)
- **Theme**: Jewel & Luxury archetype, dark mode
- **Icons**: Phosphor Icons (duotone weight)
- **Layout**: Fixed sidebar navigation (desktop) with search bar, responsive mobile hamburger

### Core Architecture
- **Frontend**: React with React Router, Tailwind CSS, Shadcn/UI, @tailwindcss/typography, Phosphor Icons
- **Backend**: FastAPI (Python), modular route structure
- **Database**: MongoDB
- **Auth**: Emergent Auth (Google OAuth)
- **Payments**: Stripe via emergentintegrations library

### What's Been Implemented

#### Phase 1 — Foundation (Feb 2026)
- [x] Modular backend routes + RBAC (5 roles: admin, elder, faculty, assistant, student)
- [x] Courses CRUD with lessons, Cohorts CRUD, Community forums, Archives
- [x] Messages/notifications, File uploads, Settings with role management
- [x] Premium UI: login page, sidebar nav, dashboard

#### Phase 2 — Course Enrollment & Live Teaching (Feb 2026)
- [x] Course enrollment, progress tracking, "My Learning" view
- [x] Live Teaching via Jitsi Meet (no API keys) with pre-join background picker
- [x] 9 curated branded backgrounds (incl. Sacred Vault, Midnight Glow, Scholar's Den, Cosmic Dust)

#### Phase 3 — Files & Google Integration (Feb 2026)
- [x] File attachments per lesson with type-specific icons
- [x] Google OAuth for Slides/Docs import into lessons

#### Phase 4 — Cohorts, Spaces, Community, Archives (Mar 2026)
- [x] Cohort-Course linking + cohort detail with member progress
- [x] Protected Knowledge Spaces (public/members/faculty/elder access levels)
- [x] Access request/approval flow, resource management
- [x] Community forums (posts, replies, likes), Archives with access filtering

#### Phase 5 — Progress Dashboard & Content Viewer (Mar 2026)
- [x] Cohort Progress Dashboard: leaderboard with crown/medal icons, per-course breakdown
- [x] Lesson Content Viewer: markdown rendering + YouTube/Vimeo/Google Slides auto-embeds
- [x] @tailwindcss/typography integration for rich content

#### Phase 6 — Analytics, Search, Subscriptions, Course Controls (Mar 2026)
- [x] Advanced Analytics Dashboard (faculty+ only): platform overview, enrollment trends, course performance rankings, cohort comparisons, community activity with top contributors
- [x] Cross-Platform Search: real-time debounced search across courses, community, archives, cohorts, spaces with dropdown results
- [x] Stripe Membership Tiers: Explorer (free), Scholar ($19.99/mo), Elder Circle ($49.99/mo) with Stripe checkout, payment status polling, transaction history
- [x] Edit/Delete Course Controls: full RBAC for faculty/course owners (edit, delete, publish)
- [x] Full test suite: 27 backend + all frontend tests passed (iteration 9)

### Prioritized Backlog

#### P2
- Email notifications (course updates, enrollment confirmations)
- Session recording management
- Advanced analytics: time-series enrollment charts, export to CSV

#### P3
- Custom AI-generated branded backgrounds (when image gen quota resets)
- Multi-language support
- Mobile PWA enhancements (push notifications)
- Advanced search with faceted filters

### Key Files
```
/app/backend/
  server.py, database.py, middleware.py
  routes/ (auth, courses, cohorts, community, archives, files, messages, enrollments, live_sessions, google_integration, spaces, analytics, search, subscriptions)
/app/frontend/src/
  App.js (React Router — 14 routes)
  lib/ (api.js, backgrounds.js)
  components/ (layout/Sidebar.jsx, layout/AppLayout.jsx, layout/SearchBar.jsx, LessonContentViewer.jsx)
  pages/ (Login, Dashboard, Courses, CourseDetail, Cohorts, CohortDetail, Spaces, Community, Archives, LiveSessions, LiveRoom, Messages, Settings, Analytics, Subscriptions)
```

### API Endpoints
- Auth: POST /api/auth/profile, GET /api/auth/me, GET /api/auth/users, PUT /api/auth/users/{id}/role
- Courses: GET/POST /api/courses, GET/PUT/DELETE /api/courses/{id}, GET/POST /api/courses/{id}/lessons
- Enrollment: POST /api/courses/{id}/enroll, POST /api/courses/{id}/unenroll, POST /api/courses/{id}/lessons/{lid}/complete, GET /api/enrollments/my-courses
- Cohorts: GET/POST /api/cohorts, GET/PUT/DELETE /api/cohorts/{id}, POST /api/cohorts/{id}/join, POST /api/cohorts/{id}/leave, POST /api/cohorts/{id}/courses, GET /api/cohorts/{id}/detail
- Spaces: GET/POST /api/spaces, GET/PUT/DELETE /api/spaces/{id}, POST /api/spaces/{id}/request-access, POST /api/spaces/{id}/approve/{uid}, POST /api/spaces/{id}/resources
- Community: GET/POST /api/community/posts, DELETE /api/community/posts/{id}, POST /api/community/posts/{id}/reply, POST /api/community/posts/{id}/like
- Archives: GET/POST /api/archives, GET/DELETE /api/archives/{id}
- Files: POST /api/files/upload, GET /api/files, GET /api/files/{id}/download, DELETE /api/files/{id}
- Messages: GET/POST /api/messages, GET /api/notifications, PUT /api/notifications/{id}/read
- Live: GET/POST /api/live-sessions, PUT /api/live-sessions/{id}/start, PUT /api/live-sessions/{id}/end
- Analytics: GET /api/analytics/dashboard (faculty+ only)
- Search: GET /api/search?q=term
- Subscriptions: GET /api/subscriptions/tiers, GET /api/subscriptions/my-subscription, POST /api/subscriptions/checkout, GET /api/subscriptions/checkout/status/{id}, GET /api/subscriptions/transactions
- Webhook: POST /api/webhook/stripe
