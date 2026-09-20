import { rememberPendingTier, takePendingTier, hasPendingTier } from './pendingTier';

describe('the tier a visitor picks on the landing page', () => {
  beforeEach(() => {
    try { localStorage.clear(); } catch (e) { /* not available */ }
  });

  it('survives the trip through sign-in', () => {
    rememberPendingTier('scholar', 'annual');
    expect(takePendingTier()).toEqual({ tierId: 'scholar', period: 'annual' });
  });

  it('defaults to monthly, which is what the landing page prices', () => {
    rememberPendingTier('elder_circle');
    expect(takePendingTier()).toEqual({ tierId: 'elder_circle', period: 'monthly' });
  });

  it('is consumed once, so a later visit is not hijacked by a stale choice', () => {
    rememberPendingTier('scholar');
    expect(takePendingTier()).not.toBeNull();
    expect(takePendingTier()).toBeNull();
  });

  it('never remembers the free tier — explorer needs no checkout', () => {
    rememberPendingTier('explorer');
    expect(hasPendingTier()).toBe(false);
    expect(takePendingTier()).toBeNull();
  });

  it('rejects a tier id that is not a real paid tier', () => {
    localStorage.setItem('ileUbuntuPendingTier', JSON.stringify({ tierId: 'admin', period: 'annual' }));
    expect(takePendingTier()).toBeNull();
  });

  it('treats an unrecognised period as monthly rather than billing a year', () => {
    localStorage.setItem('ileUbuntuPendingTier', JSON.stringify({ tierId: 'scholar', period: 'decade' }));
    expect(takePendingTier()).toEqual({ tierId: 'scholar', period: 'monthly' });
  });

  it('survives corrupted storage without throwing', () => {
    localStorage.setItem('ileUbuntuPendingTier', '{not json');
    expect(takePendingTier()).toBeNull();
  });

  it('hasPendingTier does not consume the choice', () => {
    rememberPendingTier('scholar');
    expect(hasPendingTier()).toBe(true);
    expect(hasPendingTier()).toBe(true);
    expect(takePendingTier()).not.toBeNull();
  });
});
