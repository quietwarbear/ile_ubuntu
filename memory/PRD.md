# The Ile Ubuntu - Living Learning Commons
## Product Requirements Document

### Original Problem Statement
Build a "Living Learning Commons" platform called "The Ile Ubuntu" that holds courses, cohorts, community, archives, and protected knowledge spaces in one coherent environment. Supports differentiated access roles (elders, faculty, students, assistants, admin) and features a midnight blue, black, and gold design with Ankh symbol branding.

### Subscription Tiers (Enforced)
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
- **Backend**: FastAPI, modular routes + tier_gating.py middleware
- **Database**: MongoDB
- **Auth**: Emergent Auth
- **Payments**: Stripe via emergentintegrations
- **Email**: Resend (transactional emails with branded HTML)

### Implementation Complete

#### Phase 1-4: Foundation + Core Features
- Modular architecture, RBAC (5 roles), Courses, Enrollment, Live Teaching (Jitsi), File Attachments, Google Slides/Docs Import, Cohorts, Spaces, Community, Archives

#### Phase 5: Dashboard + Content
- Cohort Progress Dashboard (leaderboard), Lesson Content Viewer (markdown + embeds), 9 Branded Backgrounds

#### Phase 6: Analytics, Search, Payments
- Analytics Dashboard, Cross-Platform Search, Stripe Subscriptions (3 tiers), Course Edit/Delete Controls

#### Phase 7: Tier Gating
- Enforced enrollment limits, cohort/space/live/archive access gating, UpgradePrompt modal, Faculty/Elder/Admin bypass

#### Phase 8: P2 Features (Latest)
- **Email Notifications**: Resend integration with branded HTML templates. Triggers on enrollment, cohort join. Test endpoint at POST /api/notifications/email/test
- **Session Recording Management**: Metadata for ended sessions — notes, key takeaways, tags, attendee details. CSV export per session. Notes editing for faculty/host
- **Advanced Analytics**: 14-day enrollment trend bar chart, CSV export of course performance data
- Full test suite: 19 backend + 17 frontend tests passed (iteration 11)

### Prioritized Backlog

#### P3
- Custom AI-generated branded backgrounds (when image gen quota resets)
- Multi-language support
- Mobile PWA push notifications
- Advanced search with faceted filters

### Key Files
```
/app/backend/
  server.py, database.py, middleware.py, tier_gating.py
  routes/ (auth, courses, cohorts, community, archives, files, messages, enrollments, live_sessions, google_integration, spaces, analytics, search, subscriptions, email_notifications, session_records)
/app/frontend/src/
  App.js (React Router — 17 routes)
  lib/ (api.js, backgrounds.js)
  components/ (UpgradePrompt.jsx, LessonContentViewer.jsx, layout/Sidebar.jsx, layout/AppLayout.jsx, layout/SearchBar.jsx)
  pages/ (Login, Dashboard, Courses, CourseDetail, Cohorts, CohortDetail, Spaces, Community, Archives, LiveSessions, LiveRoom, Messages, Settings, Analytics, Subscriptions, SessionRecords)
```

### API Endpoints
- Auth: POST /api/auth/profile, GET /api/auth/me, GET /api/auth/users, PUT /api/auth/users/{id}/role
- Courses: CRUD + lessons + enrollment (GATED: Explorer=2 max)
- Cohorts: CRUD + join (GATED: Scholar+) + leave + course linking + detail
- Spaces: CRUD + request-access (GATED: Scholar+) + approve + resources
- Live: CRUD + join (GATED: Elder Circle+) + start + end
- Archives: CRUD (GATED: restricted=Elder Circle+ or faculty)
- Community: posts + replies + likes
- Analytics: GET /api/analytics/dashboard, GET /api/analytics/enrollment-trends, GET /api/analytics/export/csv
- Search: GET /api/search?q=term
- Subscriptions: tiers, my-subscription, checkout, status, transactions
- Email: POST /api/notifications/email/test
- Session Records: GET/PUT /api/session-records, GET /api/session-records/{id}/export
- Webhook: POST /api/webhook/stripe
