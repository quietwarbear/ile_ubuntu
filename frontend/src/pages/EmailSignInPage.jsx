import React, { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import BrandMark from '../components/brand/BrandMark';
import { apiPost, setCookie } from '../lib/api';

// Landing page for an emailed sign-in link (/signin-link?token=…).
// The link is used up only when the person presses a button, never on page
// load, so mail scanners that open links first can't spend it.
// On a phone the session can go to the installed app instead, through the
// ileubuntu:// callback the app already handles for Google sign-in.

export const APP_CALLBACK = 'ileubuntu://auth/email/callback';

export function isPhoneBrowser(nav = typeof navigator !== 'undefined' ? navigator : {}, win = typeof window !== 'undefined' ? window : {}) {
  try {
    if (win.Capacitor?.isNativePlatform?.()) return false;   // already inside the app
  } catch (e) { /* not native */ }
  return /iPhone|iPad|iPod|Android/i.test(nav.userAgent || '');
}

export function appCallbackUrl(sessionId) {
  return `${APP_CALLBACK}?session_id=${encodeURIComponent(sessionId)}`;
}

export default function EmailSignInPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') || '';
  const fromApp = searchParams.get('app') === '1';
  const [state, setState] = useState(token ? 'checking' : 'unknown');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [email, setEmail] = useState('');
  const [info, setInfo] = useState('');
  const phone = isPhoneBrowser();

  useEffect(() => {
    if (!token) return;
    apiPost('/api/auth/email-link/status', { token })
      .then(res => setState(res.state || 'unknown'))
      .catch(() => setState('valid'));   // let the button try; redeem has the final word
  }, [token]);

  const signIn = async (target) => {
    setBusy(true); setError('');
    try {
      const res = await apiPost('/api/auth/email-link/redeem', { token });
      if (target === 'app') {
        window.location.href = appCallbackUrl(res.session_id);
        setState('handed_to_app');
      } else {
        setCookie('session_id', res.session_id, 7);
        window.location.replace('/dashboard');
      }
    } catch (err) {
      setError(err.message);
      setState('used_or_expired');
    } finally { setBusy(false); }
  };

  const requestNew = async (e) => {
    e.preventDefault();
    setBusy(true); setError('');
    try {
      const res = await apiPost('/api/auth/email-link', { email, app: fromApp });
      setInfo(res.message);
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  };

  const usable = state === 'valid' || state === 'checking';
  const gold = 'bg-[rgb(var(--gold))] text-[rgb(var(--ink-deep))] hover:bg-[rgb(var(--gold-soft))]';

  return (
    <div className="min-h-screen flex items-center justify-center bg-[rgb(var(--ink-deep))] px-6" data-testid="email-signin-page">
      <div className="w-full max-w-sm space-y-6 text-center">
        <div className="w-14 h-14 mx-auto rounded-lg bg-[rgb(var(--gold)/0.1)] border border-[rgb(var(--gold)/0.2)] flex items-center justify-center">
          <BrandMark className="w-9 h-9 object-contain" />
        </div>
        <h1 className="text-2xl font-light text-[rgb(var(--text-main))]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
          Sign in to The Ile Ubuntu
        </h1>

        {state === 'handed_to_app' && (
          <p className="text-sm text-[rgb(var(--text-muted))]" data-testid="handed-to-app">
            Opening the app… If nothing happens, the app may not be installed on this phone.
          </p>
        )}

        {usable && (
          <div className="space-y-3" data-testid="signin-actions">
            {phone && (fromApp ? (
              <>
                <Button onClick={() => signIn('app')} disabled={busy} className={`w-full ${gold}`} data-testid="signin-app">
                  Open in the Ile Ubuntu app
                </Button>
                <Button onClick={() => signIn('web')} disabled={busy} variant="outline" className="w-full" data-testid="signin-web">
                  Sign in here in the browser
                </Button>
              </>
            ) : (
              <>
                <Button onClick={() => signIn('web')} disabled={busy} className={`w-full ${gold}`} data-testid="signin-web">
                  Sign in
                </Button>
                <Button onClick={() => signIn('app')} disabled={busy} variant="outline" className="w-full" data-testid="signin-app">
                  Open in the Ile Ubuntu app instead
                </Button>
              </>
            ))}
            {!phone && (
              <Button onClick={() => signIn('web')} disabled={busy} className={`w-full ${gold}`} data-testid="signin-web">
                Sign in
              </Button>
            )}
            <p className="text-xs text-[rgb(var(--text-faint))]">This link works once.</p>
          </div>
        )}

        {!usable && state !== 'handed_to_app' && (
          <form onSubmit={requestNew} className="space-y-3 text-left" data-testid="request-new-link">
            <p className="text-sm text-[rgb(var(--text-muted))] text-center">
              {state === 'expired' ? 'This sign-in link has expired.'
                : state === 'used' ? 'This sign-in link was already used.'
                : 'This sign-in link has expired or was already used.'}{' '}
              Enter your email and we'll send a new one.
            </p>
            <input type="email" required value={email} onChange={e => setEmail(e.target.value)}
              placeholder="you@example.com" aria-label="Email"
              className="w-full px-4 py-2.5 rounded-md bg-[rgb(var(--ink-card-alt))] border border-[rgb(var(--ink-border))] text-[rgb(var(--text-main))] text-sm" />
            <Button type="submit" disabled={busy || !email.trim()} className={`w-full ${gold}`} data-testid="request-new-link-button">
              Email me a new link
            </Button>
          </form>
        )}

        {error && state !== 'used_or_expired' && <p className="text-xs text-red-400" role="alert">{error}</p>}
        {info && <p className="text-xs text-emerald-400" data-testid="request-new-link-info">{info}</p>}

        <Link to="/login" className="block text-xs text-[rgb(var(--gold))] hover:underline">Other ways to sign in</Link>
      </div>
    </div>
  );
}
