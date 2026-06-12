import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import BrandMark from '../components/brand/BrandMark';
import { GraduationCap, SignIn, CheckCircle } from '@phosphor-icons/react';
import { apiGet, apiPost } from '../lib/api';

// Renders both signed-out (public invite landing) and signed-in (inside AppLayout).
export default function JoinCoursePage({ user }) {
  const { code } = useParams();
  const navigate = useNavigate();
  const [invite, setInvite] = useState(null);
  const [error, setError] = useState('');
  const [joining, setJoining] = useState(false);

  useEffect(() => {
    apiGet(`/api/courses/invites/${code}/resolve`)
      .then(setInvite)
      .catch(e => setError(e.message || 'This invite is not valid.'));
  }, [code]);

  const handleJoin = async () => {
    if (!user) {
      // Continue this join after sign-in (App redirects via PendingInviteRedirect)
      localStorage.setItem('pending_invite', code);
      navigate('/login');
      return;
    }
    setJoining(true);
    try {
      const res = await apiPost(`/api/courses/invites/${code}/accept`, {});
      if (res.enrolled) {
        navigate(`/courses/${res.course_id}`);
        return;
      }
      if (res.premium_required) {
        const isNative = window.Capacitor?.isNativePlatform?.();
        if (isNative) {
          setError(`This is a premium course ($${res.premium_price}). Premium courses can be purchased on the web at ile-ubuntu.org.`);
          setJoining(false);
          return;
        }
        const checkout = await apiPost(`/api/marketplace/courses/${res.course_id}/checkout`, {
          success_url: `${window.location.origin}/courses/${res.course_id}`,
          cancel_url: window.location.href,
        });
        if (checkout.url) window.location.href = checkout.url;
        return;
      }
    } catch (e) {
      setError(e.message || 'Could not join the course.');
    }
    setJoining(false);
  };

  return (
    <div className={user ? 'max-w-lg mx-auto py-10' : 'min-h-screen flex items-center justify-center bg-[#050814] px-8'}>
      <div className="w-full max-w-lg space-y-6 text-center">
        {!user && (
          <div className="w-16 h-16 mx-auto rounded-lg bg-[#D4AF37]/10 border border-[#D4AF37]/20 flex items-center justify-center">
            <BrandMark className="w-10 h-10 object-contain" />
          </div>
        )}
        <p className="text-xs tracking-[0.25em] uppercase text-[#D4AF37]">You're invited</p>

        {error ? (
          <p className="text-sm text-red-400 bg-red-400/10 rounded-md px-4 py-3">{error}</p>
        ) : !invite ? (
          <p className="text-sm text-[#94A3B8]">Loading invite…</p>
        ) : (
          <>
            <h1 className="text-3xl font-light text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
              {invite.title}
            </h1>
            <p className="text-sm text-[#94A3B8]">
              {invite.instructor_name && <>Taught by <span className="text-[#F8FAFC]">{invite.instructor_name}</span>. </>}
              {invite.description}
            </p>
            {invite.is_premium && (
              <p className="text-sm text-[#D4AF37]">
                Premium course — ${invite.premium_price} one-time, lifetime access.
              </p>
            )}
            <Button
              onClick={handleJoin}
              disabled={joining}
              className="w-full bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB] font-medium py-3"
              data-testid="join-course-btn"
            >
              {user ? (
                <><GraduationCap size={18} weight="duotone" className="mr-2" />
                  {joining ? 'Joining…' : invite.is_premium ? `Purchase & Join — $${invite.premium_price}` : 'Join Course'}</>
              ) : (
                <><SignIn size={18} weight="duotone" className="mr-2" /> Sign in to Join</>
              )}
            </Button>
            {!user && (
              <p className="text-xs text-[#94A3B8]">
                New here? Signing in will bring you right back to this invitation.
              </p>
            )}
          </>
        )}
      </div>
    </div>
  );
}

// Mount once inside the signed-in Router: finishes an invite that was
// interrupted by the sign-in step.
export function PendingInviteRedirect() {
  const navigate = useNavigate();
  useEffect(() => {
    const pending = localStorage.getItem('pending_invite');
    if (pending) {
      localStorage.removeItem('pending_invite');
      navigate(`/join/${pending}`);
    }
  }, [navigate]);
  return null;
}
