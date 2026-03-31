# The Ile Ubuntu - Living Learning Commons
## Product Requirements Document

### Original Problem Statement
Build a "Living Learning Commons" platform called "The Ile Ubuntu" — courses, cohorts, community, archives, and protected knowledge spaces with differentiated access roles and a midnight blue/black/gold design with Ankh branding.

### Architecture
- **Frontend**: React, React Router, Tailwind CSS, Shadcn/UI, @tailwindcss/typography, Phosphor Icons, i18n (EN/ES/YO)
- **Backend**: FastAPI, modular routes, tier_gating.py
- **Database**: MongoDB
- **Integrations**: Emergent Auth, Stripe, Resend, Jitsi Meet, Google APIs

### Implementation Complete (Phases 1-10)

#### Phase 1-4: Foundation + Core
- Modular architecture, RBAC (5 roles), Courses, Enrollment, Live Teaching (Jitsi), File Attachments, Google Import, Cohorts, Spaces, Community, Archives

#### Phase 5: Dashboard + Content
- Cohort Progress Dashboard (leaderboard), Lesson Content Viewer (markdown + embeds), 9 Branded Backgrounds

#### Phase 6: Analytics, Search, Payments
- Analytics Dashboard, Cross-Platform Search, Stripe Subscriptions (Explorer/Scholar/Elder Circle)

#### Phase 7: Tier Gating
- Enforced enrollment limits, cohort/space/live/archive gating, UpgradePrompt modal

#### Phase 8: P2 Features
- Email Notifications (Resend), Session Recording Management, Advanced Analytics (trend chart + CSV export)

#### Phase 9: Onboarding, i18n, Marketing
- Student Onboarding Wizard, Multi-language (EN/ES/YO), Marketing About Page

#### Phase 10: Certificates, Push Notifications, Search, Marketing (Latest - Feb 2026)
- **Course Completion Certificates**: Branded PDF generation via reportlab. Endpoints: /my-certificates, /check/{course_id}, /download/{course_id}. Dashboard "My Certificates" section with download links. CourseDetailPage download button.
- **PWA Push Notifications**: Backend subscription management (VAPID keys, subscribe/unsubscribe/status). Service worker updated with JSON payload parsing and click-to-navigate. Settings page toggle for enable/disable.
- **Advanced Search Results Page**: Full-page /search route with faceted filters (type, sort, access level). SearchBar "View all results" link to /search. Structured results by category.
- **Marketing & Branding Page**: /marketing route (faculty+). Platform one-pager (16 features, brand identity, color palette, quick stats, tier comparison, tech stack). Social media strategy (Instagram/Twitter/LinkedIn copy-ready posts, brand voice guidelines, hashtag bank, 4-week content calendar). Print/Save PDF button.
- **Tests**: 22 backend + all frontend passed (iteration 13, 100% success)

### Subscription Tiers (Enforced)
| Feature | Explorer (Free) | Scholar ($19.99/mo) | Elder Circle ($49.99/mo) |
|---|---|---|---|
| Course enrollment | Max 2 | Unlimited | Unlimited |
| Cohort membership | No | Yes | Yes |
| Knowledge Spaces | Public only | Public + Members | All |
| Live Teaching | No | No | Yes |
| Archives | Public only | Public only | Public + Restricted |
*Faculty/Elder/Admin bypass ALL restrictions*

### Backlog

#### P2 (Remaining)
- JaaS video recording integration (deferred for cost — currently metadata only)

#### P3 (Future)
- Custom AI-generated backgrounds (image gen quota exhausted)

### Key Files
```
/app/backend/
  server.py, database.py, middleware.py, tier_gating.py
  routes/ (19 files: auth, courses, cohorts, community, archives, files, messages, enrollments, live_sessions, google_integration, spaces, analytics, search, subscriptions, email_notifications, session_records, certificates, push_notifications)
/app/frontend/src/
  App.js (React Router, I18nProvider, onboarding logic — 21 routes)
  i18n/ (index.js, en.js, es.js, yo.js)
  lib/ (api.js, backgrounds.js)
  components/ (OnboardingWizard.jsx, UpgradePrompt.jsx, LessonContentViewer.jsx, layout/Sidebar.jsx, layout/AppLayout.jsx, layout/SearchBar.jsx)
  pages/ (19 pages: Login, Dashboard, Courses, CourseDetail, Cohorts, CohortDetail, Spaces, Community, Archives, LiveSessions, LiveRoom, Messages, Settings, Analytics, Subscriptions, SessionRecords, About, SearchResults, Marketing)
```
