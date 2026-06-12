# Village Deep Migration — Blueprint

*Prepared 2026-06-12 at the end of the foundation session. The next build session
starts here. Foundation already shipped (commit 1427f79): Village entity, members
with relationship roles, collective goals, cohort attachment (cohort.village_id).*

## Goal (eval §6.1 / §8 / §9)

Make the village, not the course, the primitive. Courses, cohorts, live sessions,
and spaces become things *inside* a village. The member's home becomes their
village feed. The dashboard, digest, and attention signals scope to the village.

## Phase 1 — Scope content into villages (backend) ✅ SHIPPED 2026-06-12

*All four items below landed (commit "feat: Phase 1 of village deep migration").
Verified by backend/tests/standalone_test_village_scoping.py (17 checks).
Notes for Phase 2: attach/detach lives on the villages router
(POST/DELETE /api/villages/{id}/courses and /live-sessions); detaching a
village-visibility course resets it to unlisted; village privacy 404s like
drafts; invite codes do not pierce it; village-scoped session join requires
membership (tier gate unchanged).*

1. `course.village_id`, `live_session.village_id` (nullable — platform-wide
   content remains legal; "commons" content has no village).
2. Set-village endpoints (steward-gated), mirroring cohort attachment.
3. List endpoints accept `?village_id=` filter; course visibility gains a third
   tier: `village` (visible to village members only) alongside listed/unlisted.
4. Enrollment/join rules: village-scoped content joinable by village members
   without invite codes.

## Phase 2 — Village feed as home (frontend) ✅ SHIPPED 2026-06-12

*All four items landed. GET /api/villages/{id}/home feeds the whole page
(sessions, circle, goals, member posts, elder prompt — static rotation,
deterministic per village per day). Routes: "/" → VillageHomeGate (one
village → /village/:id, multiple → picker, none → /dashboard); DashboardPage
untouched. Sidebar pins a VILLAGE section on top when the user has one.
15 i18n keys added to en/es/yo. Standalone suite now 22 checks.*

1. New `VillageHomePage`: today's sessions, my circle (mentor/mentee + family),
   village goals progress, latest community posts from village members, an
   elder prompt slot (static v1, Ubuntu Intelligence later).
2. Routing: if user belongs to exactly one village → `/` lands there; multiple →
   village picker; none → current dashboard (commons view).
3. Sidebar: VILLAGE section pinned on top when user has a village (eval §8 tree).
4. DashboardPage's learner content folds into the village feed over time —
   don't delete it; commons users still need it.

## Phase 3 — Measures go village-wide ✅ SHIPPED 2026-06-12

*All three items landed. GET /api/dashboard/village/{id} shares
_compute_dashboard() with the cohort view; access = faculty+ OR that
village's stewards. Response adds village_mentors (mentor/elder roles, for
check-in routing) and cohorts (drill-down chips in the UI; breadcrumb back).
Digest youth sections name the village + goals carried home; villageless
youth get no village line. BONUS FIX: attention-list datetime comparison
500'd on real PyMongo (naive vs aware) — normalized in _compute_dashboard;
this also fixed the pre-existing cohort dashboard. Suite now 32 checks.*

1. Community Dashboard: village selector (members = village.members), not just
   cohorts. Keep cohort drill-down inside it.
2. Family digest: include village name + village goal progress in each youth
   section ("Their village completed 2 goals this season").
3. Attention list at village level; mentors of the village surfaced for routing
   ("suggest a mentor check-in" — precursor to eval §7.5 interventions).

## Phase 4 — Migration & cleanup ✅ SHIPPED 2026-06-12 — MIGRATION COMPLETE

*POST /api/villages/from-cohort (faculty+): founds a village named after the
cohort, attaches it, founder is sole member — membership stays explicit, no
auto-add (honored as decided). VillagesPage offers it per unattached cohort.
Events village.session_held (on village session end) and
village.goal_progress (counts-only meta, both directions) registered and
emitted. Suite: 41 checks. All four phases of the deep migration are done.*

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
