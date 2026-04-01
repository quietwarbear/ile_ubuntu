# The Ile Ubuntu - Living Learning Commons
## Product Requirements Document

### Original Problem Statement
Build a "Living Learning Commons" platform called "The Ile Ubuntu" — courses, cohorts, community, archives, and protected knowledge spaces with differentiated access roles and a midnight blue/black/gold design with Ankh branding.

### Architecture
- **Frontend**: React, React Router, Tailwind CSS, Shadcn/UI, Phosphor Icons, i18n (EN/ES/YO), PWA
- **Backend**: FastAPI, modular routes, middleware (Auth + Tier Gating)
- **Database**: MongoDB
- **Integrations**: Emergent Auth, Stripe, Resend, Jitsi Meet, Google APIs

### Phases Complete

#### Phase 1-9: Foundation through Onboarding
- Modular architecture, RBAC (5 roles), Courses, Enrollment, Live Teaching (Jitsi), Cohorts, Spaces, Community, Archives
- Analytics Dashboard with CSV export, Stripe Subscriptions (Explorer/Scholar/Elder Circle), Tier Gating
- Email Notifications (Resend), Session Records, i18n (EN/ES/YO), Guided Onboarding Wizard

#### Phase 10: Certificates, Push Notifications, Search, Marketing
- Course Completion Certificates (branded PDF via reportlab)
- PWA Push Notifications (VAPID subscription management + Settings toggle)
- Advanced Search Results Page with faceted filters
- Marketing & Branding Page (one-pager + social media strategy + content calendar)

#### Phase 11: Code Quality Refactoring
- CourseDetailPage split: 811→240 lines via 4 sub-components (CourseHeader, LessonCard, EnrolledStudents, GoogleImportDialog)
- React hook deps fixed, empty catches now log errors, array index keys → stable IDs, useMemo for expensive computations
- Backend search.py refactored into 5 service functions
- Service worker rewritten (network-first for navigation) — fixed blank deploy screen
- ESLint incompatibility resolved

#### Phase 12: Public Landing Page (Latest - Feb 2026)
- Mission-driven hero: "I am because we are" philosophy, Ubuntu imagery, stats (16+ features, 5 roles, 3 languages)
- Philosophy section: 3 pillars (Governance Roles, Intergenerational, Free to Start) + African proverb
- Feature showcase: 9 animated feature cards (scroll-triggered IntersectionObserver)
- Testimonials: 4 placeholder testimonials with auto-rotating carousel (6s interval, manual prev/next)
- How It Works: 4-step journey (Sign In → Explore → Join Cohort → Grow Role)
- Final CTA: "Get Started — It's Free" with reassurance copy
- Footer with About/Sign In links
- Route: / for unauthenticated, /login still available
- Tests: iteration_15.json — 22 backend + all frontend = 100% pass rate

### Subscription Tiers (Enforced)
| Feature | Explorer (Free) | Scholar ($19.99/mo) | Elder Circle ($49.99/mo) |
|---|---|---|---|
| Courses | Max 2 | Unlimited | Unlimited |
| Cohorts | No | Yes | Yes |
| Spaces | Public only | Public + Members | All |
| Live Teaching | No | No | Yes |
| Archives | Public only | Public only | All |

### Key Files
```
/app/backend/
  server.py, database.py, middleware.py, tier_gating.py
  routes/ (19 route files)
/app/frontend/src/
  App.js (22 routes)
  i18n/ (en.js, es.js, yo.js)
  components/
    course/ (CourseHeader, LessonCard, EnrolledStudents, GoogleImportDialog)
    layout/ (Sidebar, AppLayout, SearchBar)
    OnboardingWizard, UpgradePrompt, LessonContentViewer
  pages/ (20 pages: Landing, Login, Dashboard, Courses, CourseDetail, Cohorts, CohortDetail, Spaces, Community, Archives, LiveSessions, LiveRoom, Messages, Settings, Analytics, Subscriptions, SessionRecords, About, SearchResults, Marketing)
```

### Backlog
- P2: JaaS video recording (deferred for cost — metadata only)
- P3: Custom AI backgrounds (image gen quota exhausted)
