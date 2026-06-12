# Village Deep Migration — Blueprint

*Prepared 2026-06-12 at the end of the foundation session. The next build session
starts here. Foundation already shipped (commit 1427f79): Village entity, members
with relationship roles, collective goals, cohort attachment (cohort.village_id).*

## Goal (eval §6.1 / §8 / §9)

Make the village, not the course, the primitive. Courses, cohorts, live sessions,
and spaces become things *inside* a village. The member's home becomes their
village feed. The dashboard, digest, and attention signals scope to the village.

## Phase 1 — Scope content into villages (backend)

1. `course.village_id`, `live_session.village_id` (nullable — platform-wide
   content remains legal; "commons" content has no village).
2. Set-village endpoints (steward-gated), mirroring cohort attachment.
3. List endpoints accept `?village_id=` filter; course visibility gains a third
   tier: `village` (visible to village members only) alongside listed/unlisted.
4. Enrollment/join rules: village-scoped content joinable by village members
   without invite codes.

## Phase 2 — Village feed as home (frontend)

1. New `VillageHomePage`: today's sessions, my circle (mentor/mentee + family),
   village goals progress, latest community posts from village members, an
   elder prompt slot (static v1, Ubuntu Intelligence later).
2. Routing: if user belongs to exactly one village → `/` lands there; multiple →
   village picker; none → current dashboard (commons view).
3. Sidebar: VILLAGE section pinned on top when user has a village (eval §8 tree).
4. DashboardPage's learner content folds into the village feed over time —
   don't delete it; commons users still need it.

## Phase 3 — Measures go village-wide

1. Community Dashboard: village selector (members = village.members), not just
   cohorts. Keep cohort drill-down inside it.
2. Family digest: include village name + village goal progress in each youth
   section ("Their village completed 2 goals this season").
3. Attention list at village level; mentors of the village surfaced for routing
   ("suggest a mentor check-in" — precursor to eval §7.5 interventions).

## Phase 4 — Migration & cleanup

1. Backfill script: for each existing cohort, offer steward UI to create a
   village from it (cohort name → village name) — do NOT auto-create.
2. `village.member_added` should fire when cohort attached brings new people?
   No — keep membership explicit; attaching a cohort does not auto-add members
   (decided in foundation session; revisit only with Doc).
3. Events to add: `village.session_held`, `village.goal_progress` as needed.

## Hard-won context (do not relearn these)

- Handlers with no `await` are SYNC on purpose (threadpool; PyMongo blocks).
- Every Stripe call in marketplace.py passes `api_key=` per call; never set the
  global. SDK GETs are broken on Railway — use direct `requests` for GETs.
- `ensure_indexes()` in database.py is the only place indexes are made; add
  village_id indexes for courses/live_sessions there.
- Events are faculty-readable: never put sensitive payloads (scores, notes) in
  event meta.
- i18n: add nav keys to en/es/yo or the key name leaks into the UI.
- Frontend lockfiles: yarn 1 pinned via packageManager; do NOT add npm deps
  casually (QR uses qrserver.com image API for this reason).
- Fetch origin/main before committing — multiple Claude channels push here.

## Open loops elsewhere (not this slice)

- Marketplace rehearsal: sandbox webhook destination + secret swap, then re-test
  the $5.07 purchase end-to-end.
- Roll the exposed live key for the Give Lively account; Bitwarden everything.
- Stripe live review pending on Ubuntu Markets Platform; after it clears:
  migrate subscriptions OFF the Give Lively account keys (own slice).
- DIGEST_SECRET / FAMILY_DIGEST_KEY setup if not done.
