// A visitor picks Scholar or Elder Circle on the landing page, then has to
// make an account before Stripe can bill them. Remember the choice so
// /subscriptions opens on it instead of dropping them on a dashboard with no
// memory of why they signed up.
//
// Every tier button on the landing page used to call the same onLogin
// handler, so the tier a visitor chose was discarded at the login door.
//
// Wrapped because private mode and blocked site data make localStorage throw.

const KEY = 'ileUbuntuPendingTier';
const PAID_TIERS = ['scholar', 'elder_circle'];

export const rememberPendingTier = (tierId, period = 'monthly') => {
  if (!PAID_TIERS.includes(tierId)) return;
  try {
    localStorage.setItem(KEY, JSON.stringify({ tierId, period }));
  } catch (e) {
    /* the tier just won't be preselected */
  }
};

export const takePendingTier = () => {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;
    localStorage.removeItem(KEY);
    const parsed = JSON.parse(raw);
    if (!PAID_TIERS.includes(parsed?.tierId)) return null;
    return {
      tierId: parsed.tierId,
      period: parsed.period === 'annual' ? 'annual' : 'monthly',
    };
  } catch (e) {
    return null;
  }
};

// Read without consuming — App uses this to decide where to land someone
// straight after sign-in.
export const hasPendingTier = () => {
  try {
    return Boolean(localStorage.getItem(KEY));
  } catch (e) {
    return false;
  }
};
