# The Ile Ubuntu - Living Learning Commons
## Product Requirements Document

### Original Problem Statement
Build a "Living Learning Commons" platform called "The Ile Ubuntu" that holds courses, cohorts, community, archives, and protected knowledge spaces in one coherent environment. Supports differentiated access roles (elders, faculty, students, assistants, admin) and features a midnight blue, black, and gold design with Ankh symbol branding.

### User Personas
- **Elder**: Highest governance/oversight role, bypasses all tier restrictions
- **Faculty**: Creates courses, manages cohorts, bypasses all tier restrictions
- **Assistant**: Supports faculty, limited admin capabilities
- **Student**: Learner, access gated by subscription tier
- **Admin**: Platform administration, bypasses all tier restrictions

### Subscription Tiers
| Feature | Explorer (Free) | Scholar ($19.99/mo) | Elder Circle ($49.99/mo) |
|---|---|---|---|
| Course enrollment | Max 2 | Unlimited | Unlimited |
| Cohort membership | No | Yes | Yes |
| Knowledge Spaces | Public only | Public + Members | All |
| Live Teaching | No | No | Yes |
| Archives | Public only | Public only | Public + Restricted |
| Community | Full | Full | Full |
*Faculty/Elder/Admin bypass ALL restrictions*

### Core Architecture
- **Frontend**: React, React Router, Tailwind CSS, Shadcn/UI, @tailwindcss/typography, Phosphor Icons
- **Backend**: FastAPI, modular routes, tier_gating.py middleware
- **Database**: MongoDB
- **Auth**: Emergent Auth
- **Payments**: Stripe via emergentintegrations

### Implementation Status

#### Phase 1-4 (Feb-Mar 2026) — COMPLETE
- Modular backend/frontend architecture, RBAC, Courses, Enrollment, Live Teaching (Jitsi), File Attachments, Google Slides/Docs Import, Cohorts, Spaces, Community, Archives

#### Phase 5 (Mar 2026) — COMPLETE
- Cohort Progress Dashboard, Lesson Content Viewer (markdown + embeds), 9 Branded Backgrounds

#### Phase 6 (Mar 2026) — COMPLETE
- Analytics Dashboard, Cross-Platform Search, Stripe Subscriptions, Course Edit/Delete Controls

#### Phase 7 (Mar 2026) — COMPLETE
- **Subscription Tier Gating**: Enforced enrollment limits (Explorer=2), cohort join (Scholar+), space access (Scholar+), live session join (Elder Circle+), restricted archives (Elder Circle+)
- **Faculty/Elder/Admin bypass**: BYPASS_ROLES in tier_gating.py
- **UpgradePrompt component**: Modal with "View Plans"/"Maybe Later" on tier wall hits
- **parseTierError() utility**: Frontend error format detection
- **18 backend + 16 frontend tests passed (iteration 10, 100%)**

### Prioritized Backlog

#### P2
- Email notifications (course updates, enrollment confirmations)
- Session recording management
- Advanced analytics: time-series charts, CSV export

#### P3
- Custom AI-generated branded backgrounds
- Multi-language support
- Mobile PWA push notifications
- Advanced search with faceted filters

### Key Files
```
/app/backend/
  server.py, database.py, middleware.py, tier_gating.py
  routes/ (auth, courses, cohorts, community, archives, files, messages, enrollments, live_sessions, google_integration, spaces, analytics, search, subscriptions)
/app/frontend/src/
  App.js (React Router — 16 routes)
  lib/ (api.js with parseTierError, backgrounds.js)
  components/ (UpgradePrompt.jsx, LessonContentViewer.jsx, layout/Sidebar.jsx, layout/AppLayout.jsx, layout/SearchBar.jsx)
  pages/ (Login, Dashboard, Courses, CourseDetail, Cohorts, CohortDetail, Spaces, Community, Archives, LiveSessions, LiveRoom, Messages, Settings, Analytics, Subscriptions)
```

### API Endpoints
- Auth: POST /api/auth/profile, GET /api/auth/me, GET /api/auth/users, PUT /api/auth/users/{id}/role
- Courses: GET/POST /api/courses, GET/PUT/DELETE /api/courses/{id}, GET/POST /api/courses/{id}/lessons
- Enrollment: POST /api/courses/{id}/enroll (GATED: Explorer=2 max), POST /api/courses/{id}/unenroll, POST /api/courses/{id}/lessons/{lid}/complete
- Cohorts: GET/POST /api/cohorts, POST /api/cohorts/{id}/join (GATED: Scholar+), POST /api/cohorts/{id}/leave, POST /api/cohorts/{id}/courses, GET /api/cohorts/{id}/detail
- Spaces: GET/POST /api/spaces, POST /api/spaces/{id}/request-access (GATED: Scholar+), POST /api/spaces/{id}/approve/{uid}, POST /api/spaces/{id}/resources
- Live: GET/POST /api/live-sessions, POST /api/live-sessions/{id}/join (GATED: Elder Circle+, host bypasses), PUT /api/live-sessions/{id}/start, PUT /api/live-sessions/{id}/end
- Archives: GET /api/archives (GATED: restricted requires Elder Circle+ or faculty), POST /api/archives, GET/DELETE /api/archives/{id}
- Community: GET/POST /api/community/posts, POST /api/community/posts/{id}/reply, POST /api/community/posts/{id}/like
- Analytics: GET /api/analytics/dashboard (faculty+ only)
- Search: GET /api/search?q=term
- Subscriptions: GET /api/subscriptions/tiers, GET /api/subscriptions/my-subscription, POST /api/subscriptions/checkout, GET /api/subscriptions/checkout/status/{id}, GET /api/subscriptions/transactions
- Webhook: POST /api/webhook/stripe
