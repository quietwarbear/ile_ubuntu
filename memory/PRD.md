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

#### Phase 10: Certificates, Push Notifications, Search, Marketing (Feb 2026)
- Course Completion Certificates (branded PDF via reportlab)
- PWA Push Notifications (VAPID subscription management + Settings toggle)
- Advanced Search Results Page with faceted filters
- Marketing & Branding Page (one-pager + social media strategy + content calendar)

#### Phase 11: Code Quality Refactoring (Feb 2026)
- **CourseDetailPage split**: 811→240 lines. Extracted CourseHeader, LessonCard, EnrolledStudents, GoogleImportDialog
- **React hook deps**: Fixed stale closure risks, added useCallback for data loaders
- **Empty catches**: All now log errors via console.error
- **Array index keys**: Replaced with stable IDs (lesson.id, file.id, etc.)
- **useMemo**: Added for leaderboard sort (CohortDetailPage) and nav filter (Sidebar)
- **Backend search.py**: Refactored into 5 service functions (_search_courses, etc.)
- **Service worker**: Rewrote with network-first for navigation, stale-while-revalidate for assets (fixed blank deploy)
- **ESLint**: Fixed incompatibility (ESLint 9 + CRA 5), added eslint-plugin-react-hooks@4.6.2
- Tests: iteration_14.json — 22 backend + all frontend = 100% pass rate

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
  App.js (21 routes)
  i18n/ (en.js, es.js, yo.js)
  components/
    course/ (CourseHeader, LessonCard, EnrolledStudents, GoogleImportDialog)
    layout/ (Sidebar, AppLayout, SearchBar)
    OnboardingWizard, UpgradePrompt, LessonContentViewer
  pages/ (19 pages)
```

### Backlog
- P2: JaaS video recording (deferred for cost — metadata only)
- P3: Custom AI backgrounds (image gen quota exhausted)
