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
- Course Completion Certificates (branded PDF), Push Notifications (VAPID), Advanced Search, Marketing Page

#### Phase 11: Code Quality Refactoring
- CourseDetailPage 811→240 lines, service worker rewrite, backend search refactored, ESLint fix

#### Phase 12: Public Landing Page
- Mission-driven hero, philosophy, features (9 animated cards), testimonials carousel, How It Works, CTA

#### Phase 13: Blog & News Section (Latest - Feb 2026)
- **Backend**: 12 endpoints in `/api/blog/` — CRUD for posts, comments, categories, public + auth endpoints
- **Publishing**: Faculty, Elders, Admins can create/edit/delete posts. Students can comment only
- **Visibility**: Authors choose "public" (SEO-visible, no auth) or "members" (auth required)
- **Content**: Markdown with images/embeds, 7 categories, tags, cover images, auto-generated excerpts/slugs
- **Comments**: Any auth user can comment. Author/admin can delete comments. Cascade delete on post removal
- **Public blog**: `/blog` accessible without login. Category filters, "Sign in to see all content" CTA
- **Landing integration**: "Latest from the Commons" section on landing page showing 3 recent public posts
- **Sidebar**: Blog nav item with Newspaper icon for all authenticated users
- **Tests**: iteration_16.json — 25 backend + all frontend = 100% pass rate

### Key Files
```
/app/backend/
  server.py, database.py, middleware.py, tier_gating.py
  routes/ (20 route files including blog.py)
/app/frontend/src/
  App.js (26 routes)
  pages/ (24 pages: Landing, Login, Dashboard, Courses, CourseDetail, Cohorts, CohortDetail,
          Spaces, Community, Archives, LiveSessions, LiveRoom, Messages, Settings, Analytics,
          Subscriptions, SessionRecords, About, SearchResults, Marketing, Blog, BlogPost,
          BlogEditor, PublicBlog)
  components/
    course/ (CourseHeader, LessonCard, EnrolledStudents, GoogleImportDialog)
    layout/ (Sidebar, AppLayout, SearchBar)
```

### Backlog
- P2: JaaS video recording (deferred for cost — metadata only)
- P3: Custom AI backgrounds (image gen quota exhausted)
