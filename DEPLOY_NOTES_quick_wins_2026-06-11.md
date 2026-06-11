# Ile Ubuntu — §11.2 Perf + Security Quick Wins (2026-06-11)

Implements the 30–60-day backend items from the Product Evaluation brief (§10 Quick Win 1, §11.2 items 1–3, §11.4 quick wins). Changes are uncommitted in the working tree for review.

## What changed

**Event loop / concurrency (§11.2.1)**
- 99 route handlers with no `await` converted from `async def` to `def` — FastAPI now runs them (and `get_current_user`) in its threadpool, so blocking PyMongo calls no longer freeze the event loop.
- Procfile now runs `--workers ${WEB_CONCURRENCY:-2}`.

**Indexes (§11.2.2, §11.2.7)**
- `database.py` gains `ensure_indexes()`, called at startup: ~30 indexes covering sessions (unique + TTL auto-expiry), users, enrollments, courses, posts, blog, quizzes, payments, and more. Each is individually try/excepted so a conflict can't block boot.

**Pagination (§11.2.3)**
- `GET /api/courses` and `GET /api/community/posts` accept `limit` (default 100, max 200) and `skip`. Response shape unchanged (bare array), so the current frontend keeps working; UIs with >100 items will need "load more" later.

**Security**
- CORS: explicit allow-list (prod domains + Capacitor origins + localhost dev), overridable via `CORS_ORIGINS`.
- `/docs`, `/redoc`, `/openapi.json` disabled unless `ENABLE_API_DOCS=true`.
- `tier_gating.py`: removed the `@ubuntu-village.org` wildcard (forgeable — registration doesn't verify email ownership). Admin emails now come from `ADMIN_EMAILS` env (defaults to the three known owner emails). Long-term: set `role: admin` on your user docs and drop the email list.
- Stripe webhook: fail-closed — requires `STRIPE_WEBHOOK_SECRET` and a valid signature; errors return 400 so Stripe retries.
- RevenueCat webhook: fail-closed — requires `REVENUECAT_WEBHOOK_SECRET`; accepts RC's Authorization-header mechanism or HMAC.
- Rate limiting (`rate_limit.py`, no new dependency): login 10/5min, register 10/hr, forgot-password 5/15min, reset 10/15min — per IP, per worker.

**Password reset + email verification (§11.4)**
- `POST /api/auth/forgot-password` → tokenized email via Resend (1h expiry, no account enumeration).
- `POST /api/auth/reset-password` → updates hash, invalidates all sessions.
- `GET /api/auth/verify-email?token=` → marks `email_verified`, redirects to site. Sent on registration; soft (doesn't block login).
- Frontend: "Forgot password?" on LoginPage + new `/reset-password` page (branded, matches login).

## ⚠️ Before deploying — set in Railway

1. `STRIPE_WEBHOOK_SECRET` — REQUIRED now. Without it the Stripe webhook returns 503 and tier upgrades from web checkout stop syncing. (Stripe Dashboard → Webhooks → signing secret.)
2. `REVENUECAT_WEBHOOK_SECRET` — REQUIRED now. Set the same value as the Authorization header configured in RevenueCat → Integrations → Webhooks. Without it, mobile IAP events return 503.
3. `WEB_CONCURRENCY` — optional, default 2. Watch Railway memory after deploy.
4. `ADMIN_EMAILS` — optional; defaults to hodari@/shy@ubuntu-village.org + quiet927@gmail.com.
5. `CORS_ORIGINS` — optional; only if a new web origin needs API access.
6. `PUBLIC_SITE_URL` — optional, default https://www.ile-ubuntu.org (used in reset/verification emails).
7. `ENABLE_API_DOCS` — leave unset in prod; set `true` locally to get /docs back.

Store webhook secrets in the Bitwarden team vault, not in the repo or Desktop.

## Post-deploy smoke test

1. `GET /docs` → 404.
2. Sign in (web + one mobile app) — confirms CORS list is right. If a native app can't reach the API, check the Capacitor origins in `server.py`.
3. "Forgot password?" → email arrives → reset works → old session is logged out.
4. Buy/restore a test subscription on mobile → tier updates (webhook auth OK).
5. 11 rapid failed logins → 429.

## Teacher Marketplace (added later on 2026-06-11)

The Teacher Marketplace UI (built earlier on another channel) had NO backend — now implemented: Stripe Connect Express onboarding, premium pricing, web-only checkout with 15% application fee (destination charges), webhook fulfillment, earnings.

**Before marketplace can take real money:**
1. Enable **Connect** in the Stripe Dashboard (Settings → Connect → enable Express accounts). Without this, "Connect with Stripe" returns a Stripe error.
2. Branding: set platform name/icon under Connect settings (shows on teacher onboarding).
3. Optional env: `MARKETPLACE_FEE_PCT` (default 0.15).
4. Test end-to-end in Stripe **test mode** first: connect a test teacher → set a price → buy with card 4242… on the web → webhook fulfills enrollment.
5. Payouts to teachers are on Stripe's standard schedule; the platform fee stays on the platform account.
6. Mobile: premium purchase is web-only by design (Apple/Google IAP rules). Native apps show a "purchase on the web" message. Do NOT add a Stripe buy button inside the apps before reviewing App Store guideline 3.1.1.

## Not done yet (next from the brief)

- Motor/async driver migration (full §11.2.1) — threadpool + workers covers classroom-scale; revisit with a staging environment.
- Media to S3/R2 + CDN (§11.2.6), text search indexes (§11.2.4), analytics aggregation pipelines (§11.2.5).
- Activity event stream (§10 QW6) — next highest-leverage item; unblocks analytics scaling and Ubuntu Intelligence.
- Role-aware navigation, attendance v0, onboarding role fork, leaderboard reframe (§10 QW2–5).
