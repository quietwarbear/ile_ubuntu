# The Ile Ubuntu - Living Learning Commons
## Product Requirements Document

### Original Problem Statement
Build a "Living Learning Commons" platform called "The Ile Ubuntu" — courses, cohorts, community, archives, and protected knowledge spaces with differentiated access roles and a midnight blue/black/gold design with Ankh branding.

### Architecture
- **Frontend**: React, React Router, Tailwind CSS, Shadcn/UI, @tailwindcss/typography, Phosphor Icons, i18n (EN/ES/YO)
- **Backend**: FastAPI, modular routes, tier_gating.py
- **Database**: MongoDB
- **Integrations**: Emergent Auth, Stripe, Resend, Jitsi Meet, Google APIs

### Implementation Complete (Phases 1-9)

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

#### Phase 9: Onboarding, i18n, Marketing (Latest)
- **Student Onboarding Wizard**: 5-step guided tour (welcome, interests, courses, cohort, complete) with progress dots and skip option
- **Multi-language**: English, Spanish, Yoruba translations with i18n context, language selector in sidebar, preference persisted to backend
- **Marketing About Page**: Public route (/about) with 12 feature cards, 3 tier comparisons, 5 roles, tech stack, social media strategy (Instagram/Twitter/LinkedIn copy, hashtags, elevator pitch)
- **Tests**: 15 backend + all frontend passed (iteration 12)

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

#### P3 (Remaining)
- Custom AI-generated backgrounds (image gen quota exhausted)
- Mobile PWA push notifications
- Advanced search with faceted filters

### Key Files
```
/app/backend/
  server.py, database.py, middleware.py, tier_gating.py
  routes/ (17 files: auth, courses, cohorts, community, archives, files, messages, enrollments, live_sessions, google_integration, spaces, analytics, search, subscriptions, email_notifications, session_records)
/app/frontend/src/
  App.js (React Router, I18nProvider, onboarding logic — 18 routes)
  i18n/ (index.js, en.js, es.js, yo.js)
  lib/ (api.js, backgrounds.js)
  components/ (OnboardingWizard.jsx, UpgradePrompt.jsx, LessonContentViewer.jsx, layout/Sidebar.jsx, layout/AppLayout.jsx, layout/SearchBar.jsx)
  pages/ (17 pages: Login, Dashboard, Courses, CourseDetail, Cohorts, CohortDetail, Spaces, Community, Archives, LiveSessions, LiveRoom, Messages, Settings, Analytics, Subscriptions, SessionRecords, About)
```
