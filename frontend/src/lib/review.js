/**
 * Native in-app review prompt (iOS SKStoreReviewController / Android
 * In-App Review) — asked at a moment of accomplishment, never at launch.
 *
 * Rules (Apple 5.6.1 / Play guidance both punish over-asking):
 * - Native apps only; no-op on web/PWA.
 * - At most once per person per app version.
 * - Only after a real milestone (completed goal, third lesson finished).
 * - The OS itself decides whether to actually show the dialog; calling is
 *   a request, not a guarantee — so failures are silently ignored.
 */
import { Capacitor } from "@capacitor/core";

const PROMPTED_KEY = "review_prompted_version";
const LESSONS_KEY = "review_lessons_completed";

async function appVersion() {
  try {
    const { App } = await import("@capacitor/app");
    const info = await App.getInfo();
    return info.version || "unknown";
  } catch (e) {
    return "unknown";
  }
}

export async function maybeRequestReview() {
  if (!Capacitor.isNativePlatform()) return;
  try {
    const version = await appVersion();
    if (localStorage.getItem(PROMPTED_KEY) === version) return;
    localStorage.setItem(PROMPTED_KEY, version);
    // Let the celebration moment land before the system dialog appears.
    setTimeout(async () => {
      try {
        const { InAppReview } = await import("@capacitor-community/in-app-review");
        await InAppReview.requestReview();
      } catch (e) { /* the OS declined or plugin unavailable — never surface */ }
    }, 1200);
  } catch (e) { /* never let a review ask break a milestone */ }
}

/** Count lesson completions; ask on the third (a real habit, not a fluke). */
export function trackLessonCompletedForReview() {
  if (!Capacitor.isNativePlatform()) return;
  try {
    const n = (parseInt(localStorage.getItem(LESSONS_KEY) || "0", 10) || 0) + 1;
    localStorage.setItem(LESSONS_KEY, String(n));
    if (n === 3) maybeRequestReview();
  } catch (e) { /* storage unavailable */ }
}
