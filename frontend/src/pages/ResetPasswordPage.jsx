import React, { useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import BrandMark from '../components/brand/BrandMark';
import { LockKey, Eye, EyeSlash, CheckCircle } from '@phosphor-icons/react';

const API = process.env.REACT_APP_BACKEND_URL || process.env.REACT_APP_API_URL || 'https://ileubuntu-production.up.railway.app';

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') || '';
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [done, setDone] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (password.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }
    if (password !== confirm) {
      setError('Passwords do not match.');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/auth/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, password }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || 'Something went wrong. Please request a new reset link.');
      } else {
        setDone(true);
      }
    } catch (err) {
      setError('Unable to reach the server. Please check your connection and try again.');
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[rgb(var(--ink-deep))] px-8" data-testid="reset-password-page">
      <div className="w-full max-w-sm space-y-8">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto rounded-lg bg-[rgb(var(--gold)/0.1)] border border-[rgb(var(--gold)/0.2)] flex items-center justify-center mb-6">
            <BrandMark className="w-10 h-10 object-contain" />
          </div>
          <h1 className="text-3xl font-light text-[rgb(var(--text-main))] mb-1" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
            Reset Password
          </h1>
          <p className="text-xs tracking-[0.2em] uppercase text-[rgb(var(--gold))]">The Ile Ubuntu</p>
        </div>

        {!token ? (
          <div className="text-center space-y-4">
            <p className="text-sm text-[rgb(var(--text-muted))]">
              This reset link is missing its token. Please use the link from your email, or request a new one.
            </p>
            <Link to="/login" className="text-sm text-[rgb(var(--gold))] hover:underline">Back to sign in</Link>
          </div>
        ) : done ? (
          <div className="text-center space-y-4">
            <CheckCircle size={40} weight="duotone" className="mx-auto text-emerald-400" />
            <p className="text-sm text-[rgb(var(--text-muted))]">
              Your password has been updated. Please sign in with your new password.
            </p>
            <Link to="/login">
              <Button className="w-full bg-[rgb(var(--gold))] text-[rgb(var(--ink-deep))] hover:bg-[rgb(var(--gold-soft))] font-medium py-3">
                Go to Sign In
              </Button>
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs text-[rgb(var(--text-muted))] mb-1.5 uppercase tracking-wider">New Password</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Min 6 characters"
                  required
                  className="w-full px-4 py-2.5 rounded-md bg-[rgb(var(--ink-card-alt))] border border-[rgb(var(--ink-border))] text-[rgb(var(--text-main))] placeholder-[rgb(var(--text-faint))] focus:outline-none focus:border-[rgb(var(--gold)/0.5)] text-sm pr-10 transition-colors"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[rgb(var(--text-faint))] hover:text-[rgb(var(--text-muted))]"
                >
                  {showPassword ? <EyeSlash size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <div>
              <label className="block text-xs text-[rgb(var(--text-muted))] mb-1.5 uppercase tracking-wider">Confirm Password</label>
              <input
                type={showPassword ? 'text' : 'password'}
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                placeholder="Repeat new password"
                required
                className="w-full px-4 py-2.5 rounded-md bg-[rgb(var(--ink-card-alt))] border border-[rgb(var(--ink-border))] text-[rgb(var(--text-main))] placeholder-[rgb(var(--text-faint))] focus:outline-none focus:border-[rgb(var(--gold)/0.5)] text-sm transition-colors"
              />
            </div>

            {error && (
              <p className="text-xs text-red-400 bg-red-400/10 rounded-md px-3 py-2">{error}</p>
            )}

            <Button
              type="submit"
              disabled={loading}
              className="w-full bg-[rgb(var(--gold))] text-[rgb(var(--ink-deep))] hover:bg-[rgb(var(--gold-soft))] font-medium py-3 transition-all duration-200"
            >
              <LockKey size={18} weight="duotone" className="mr-2" /> Update Password
            </Button>

            <p className="text-center text-xs text-[rgb(var(--text-muted))]">
              <Link to="/login" className="text-[rgb(var(--gold))] hover:underline">Back to sign in</Link>
            </p>
          </form>
        )}
      </div>
    </div>
  );
}
