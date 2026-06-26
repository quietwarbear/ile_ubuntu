import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';

// Public web fallback for https://ile-ubuntu.org/invite/:code
//
// On Android with verified App Links, the OS opens the app directly and this
// component never renders. Same for iOS with Universal Links once AASA is
// published. For everything else (desktop, browser-shared link, app not
// installed), this page tries the custom-scheme deep link
// (ileubuntu://invite/:code) and falls back to a "get the app" prompt.

const PLAY_STORE_URL =
  'https://play.google.com/store/apps/details?id=com.ubuntumarket.ileubuntu';
// App Store ID: fill in once Apple's listing URL is finalized.
const APP_STORE_URL = 'https://apps.apple.com/app/ile-ubuntu/';

export default function InviteLandingPage() {
  const { code } = useParams();
  const [attempted, setAttempted] = useState(false);

  useEffect(() => {
    if (!code) return;
    const t = setTimeout(() => {
      window.location.href = `ileubuntu://invite/${code}`;
      setAttempted(true);
    }, 250);
    return () => clearTimeout(t);
  }, [code]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-amber-50 to-orange-50 px-6 py-16">
      <div className="w-full max-w-md rounded-2xl bg-white shadow-xl p-8 text-center">
        <p className="text-xs uppercase tracking-[0.2em] text-orange-700 mb-2">Ile Ubuntu</p>
        <h1 className="text-3xl font-semibold text-slate-900 mb-3">You're invited</h1>
        <p className="text-slate-600 mb-6">
          Open the Ile Ubuntu app to accept your invite
          {code ? ` (code: ${code.toUpperCase()})` : ''}.
        </p>

        {code && (
          <div className="mb-6">
            <a
              href={`ileubuntu://invite/${code}`}
              className="inline-block w-full rounded-full bg-orange-700 px-6 py-3 text-white font-semibold hover:bg-orange-800 transition"
            >
              Open in app
            </a>
            {attempted && (
              <p className="mt-3 text-xs text-slate-500">
                Didn't open? Install the app below, then tap this link again.
              </p>
            )}
          </div>
        )}

        <div className="space-y-3">
          <a
            href={PLAY_STORE_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="block w-full rounded-full border border-slate-300 px-6 py-3 text-slate-900 font-medium hover:bg-slate-50 transition"
          >
            Get it on Google Play
          </a>
          <a
            href={APP_STORE_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="block w-full rounded-full border border-slate-300 px-6 py-3 text-slate-900 font-medium hover:bg-slate-50 transition"
          >
            Download on the App Store
          </a>
        </div>
      </div>
    </div>
  );
}
