# Course purchases in the native apps

Native one-time course purchases use Apple/Google billing via RevenueCat. The website retains Stripe Checkout and Connect payouts. A course purchase never grants or requires a membership subscription.

## Access and identity

- Each course has a centrally managed `iap` mapping: `entitlement_id`, `ios_product_id`, `android_product_id`, `enabled`.
- `PUT /api/courses/{id}/purchase-options` is admin-only, validates identifiers, and prevents mapping a product or entitlement already assigned to another course.
- The native app waits for RevenueCat configuration, logs in with the authenticated Ile Ubuntu `users.id`, checks the SDK account, and fetches a **NON_SUBSCRIPTION** product directly. The current membership offering is unchanged.
- The button uses the store's localized price. Completion, restore, and already-owned responses ask `POST /api/courses/{id}/confirm-purchase` to confirm access. That request accepts no caller-supplied receipt, product, or user ID.
- The backend reads the current RevenueCat subscriber using `REVENUECAT_COURSE_API_KEY`, or the already configured `REVENUECAT_SECRET_KEY`. It requires the mapped perpetual entitlement plus its matching non-refunded one-time store purchase.
- Sandbox receipts are denied except for explicit IDs in `REVENUECAT_SANDBOX_USER_IDS`. Those test IDs can see configured course products before public `enabled` is turned on.
- A per-user database lease serializes verification across app requests and webhook deliveries. Unique indexes prevent duplicate managed enrollments and event records.

## Refunds, restores, and transfers

The authenticated RevenueCat webhook reconciles course `NON_RENEWING_PURCHASE`, `CANCELLATION`, `EXPIRATION`, `UNCANCELLATION`, and `TRANSFER` events against the current provider state. Course events and unknown products cannot downgrade memberships.

Store revocation only marks enrollments owned by this integration. It preserves progress, completed lessons, and organizer access-date overrides. Restore removes the integration's revocation flag. Web purchases and imported enrollments are never revoked by RevenueCat; a web purchase after a store refund converts the retained enrollment to independent Stripe access.

The common course/file access rule rejects revoked grants, and quiz reads and course notices enforce the same paid access boundary. Existing completion records are preserved.

## Accounting

`course_iap_events` records authenticated store events, reported currency/price/commission/tax, course, and instructor, separately from Stripe transactions. `payout_status` starts as `not_scheduled`: these records do not claim that Stripe paid an educator. Apple/Google settle proceeds to the developer business. Educator settlement for third-party course sales needs a separately approved payout process before those courses are enabled.

## Block Pedagogy configuration

- Course: `eaac1aff-b044-4cdf-9ad1-6d30091046b8`
- RevenueCat project: `3082956e`
- Entitlement: `course_block_pedagogy` (`entl8891899e44`)
- iOS: `com.ileubuntu.course.blockpedagogy` (`prod239953687a`)
- Android: `ile_ubuntu_block_pedagogy` (`proddb245f49b7`)
- Requested US price: USD 3.00, one time. Store prices must be configured and verified separately from `premium_price`, which controls Stripe.

## Build and release

Run `npm run build:native` in `frontend`: it validates the production API URL and both public RevenueCat SDK keys, builds the frontend, and syncs Capacitor. Server secrets must never enter frontend environment files. iOS/Android binaries must be rebuilt; a website deployment cannot update installed frontend assets.

Before enabling a course for production purchases:

1. Complete both store products' localization, pricing, availability, and review information. The Apple product is non-consumable; the Google one-time product must remain non-consumable in RevenueCat.
2. Confirm Apple server notifications and Google RTDN reach RevenueCat; confirm the existing authenticated RevenueCat webhook reaches Railway. One-time refund notifications require platform server notifications.
3. Apply the mapping with `enabled: false`, and allow only specific sandbox tester user IDs.
4. On actual store test builds, verify purchase, cancellation, pending approval, restore/reinstall, existing web access without a second charge, refund revocation, and account transfer. Verify course access on the website using the same account.
5. For third-party instructors, approve settlement reporting and the payout process before selling their courses natively.
6. Submit the binaries/products for review, verify their availability, then set `enabled: true`. Until then the app shows purchase unavailability and offers restoration; the website continues selling through Stripe.

References: [RevenueCat non-subscriptions](https://www.revenuecat.com/docs/platform-resources/non-subscriptions), [customer model](https://www.revenuecat.com/docs/api-v1/customer-info-model), [webhook events](https://www.revenuecat.com/docs/integrations/webhooks/event-types-and-fields).
