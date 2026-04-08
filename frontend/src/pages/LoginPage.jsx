import React, { useState } from 'react';
import { Button } from '../components/ui/button';
import BrandMark from '../components/brand/BrandMark';
import { SignIn, GoogleLogo, EnvelopeSimple, Eye, EyeSlash, UserPlus } from '@phosphor-icons/react';

const API = process.env.REACT_APP_API_URL || '';

export default function LoginPage({ onLogin, onPasswordLogin }) {
  const [mode, setMode] = useState('login'); // 'login' or 'register'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const endpoint = mode === 'register' ? '/api/auth/register' : '/api/auth/login';
      const body = mode === 'register'
        ? { email, password, name }
        : { email, password };

      const res = await fetch(`${API}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.detail || 'Something went wrong');
        setLoading(false);
        return;
      }

      // Success — store session and notify parent
      if (onPasswordLogin) {
        onPasswordLogin(data);
      }
    } catch (err) {
      setError('Network error. Please try again.');
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen flex" data-testid="login-page">
      {/* Left visual panel */}
      <div
        className="hidden lg:flex lg:w-1/2 relative items-end p-12"
        style={{
          backgroundImage:
            'url(https://images.pexels.com/photos/6563056/pexels-photo-6563056.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940)',
          backgroundSize: 'cover',
          backgroundPosition: 'center',
        }}
      >
        <div className="absolute inset-0 bg-[#050814]/75" />
        <div className="relative z-10 max-w-md">
          <p className="text-xs tracking-[0.25em] uppercase text-[#D4AF37] mb-4">
            A Living Learning Commons
          </p>
          <h2
            className="text-4xl font-light text-[#F8FAFC] leading-tight mb-4"
            style={{ fontFamily: 'Cormorant Garamond, serif' }}
          >
            Where Knowledge Lives, <br />
            Community Grows
          </h2>
          <p className="text-sm text-[#94A3B8] leading-relaxed">
            Courses, cohorts, community, and archives — woven into one coherent
            environment for learning that honors tradition and embraces the future.
          </p>
        </div>
      </div>

      {/* Right login panel */}
      <div className="flex-1 flex items-center justify-center bg-[#050814] px-8">
        <div className="w-full max-w-sm space-y-8">
          {/* Logo */}
          <div className="text-center">
            <div className="w-16 h-16 mx-auto rounded-lg bg-[#D4AF37]/10 border border-[#D4AF37]/20 flex items-center justify-center mb-6">
              <BrandMark className="w-10 h-10 object-contain" />
            </div>
            <h1
              className="text-3xl font-light text-[#F8FAFC] mb-1"
              style={{ fontFamily: 'Cormorant Garamond, serif' }}
            >
              The Ile Ubuntu
            </h1>
            <p className="text-xs tracking-[0.2em] uppercase text-[#D4AF37]">
              Living Learning Commons
            </p>
          </div>

          {/* Email/Password Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === 'register' && (
              <div>
                <label className="block text-xs text-[#94A3B8] mb-1.5 uppercase tracking-wider">Name</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Your full name"
                  className="w-full px-4 py-2.5 rounded-md bg-[#0F1629] border border-[#1E293B] text-[#F8FAFC] placeholder-[#475569] focus:outline-none focus:border-[#D4AF37]/50 text-sm transition-colors"
                />
              </div>
            )}

            <div>
              <label className="block text-xs text-[#94A3B8] mb-1.5 uppercase tracking-wider">Email</label>
              <div className="relative">
                <EnvelopeSimple size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#475569]" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  required
                  className="w-full pl-10 pr-4 py-2.5 rounded-md bg-[#0F1629] border border-[#1E293B] text-[#F8FAFC] placeholder-[#475569] focus:outline-none focus:border-[#D4AF37]/50 text-sm transition-colors"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs text-[#94A3B8] mb-1.5 uppercase tracking-wider">Password</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder={mode === 'register' ? 'Min 6 characters' : 'Your password'}
                  required
                  className="w-full px-4 py-2.5 rounded-md bg-[#0F1629] border border-[#1E293B] text-[#F8FAFC] placeholder-[#475569] focus:outline-none focus:border-[#D4AF37]/50 text-sm pr-10 transition-colors"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[#475569] hover:text-[#94A3B8]"
                >
                  {showPassword ? <EyeSlash size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {error && (
              <p className="text-xs text-red-400 bg-red-400/10 rounded-md px-3 py-2">{error}</p>
            )}

            <Button
              type="submit"
              disabled={loading}
              className="w-full bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB] font-medium py-3 transition-all duration-200"
              data-testid="login-button"
            >
              {mode === 'register' ? (
                <><UserPlus size={18} weight="duotone" className="mr-2" /> Create Account</>
              ) : (
                <><SignIn size={18} weight="duotone" className="mr-2" /> Sign In</>
              )}
            </Button>
          </form>

          {/* Divider */}
          <div className="flex items-center gap-3">
            <div className="flex-1 border-t border-[#1E293B]" />
            <span className="text-xs text-[#475569] uppercase tracking-wider">or</span>
            <div className="flex-1 border-t border-[#1E293B]" />
          </div>

          {/* Google OAuth */}
          <Button
            onClick={onLogin}
            variant="outline"
            className="w-full border-[#1E293B] text-[#94A3B8] hover:bg-[#0F1629] hover:text-[#F8FAFC] py-3 transition-all duration-200"
          >
            <GoogleLogo size={18} weight="bold" className="mr-2" />
            Continue with Google
          </Button>

          {/* Toggle mode */}
          <p className="text-center text-xs text-[#94A3B8]">
            {mode === 'login' ? (
              <>Don't have an account?{' '}
                <button onClick={() => { setMode('register'); setError(''); }} className="text-[#D4AF37] hover:underline">
                  Create one
                </button>
              </>
            ) : (
              <>Already have an account?{' '}
                <button onClick={() => { setMode('login'); setError(''); }} className="text-[#D4AF37] hover:underline">
                  Sign in
                </button>
              </>
            )}
          </p>

          {/* Mobile-only tagline */}
          <div className="lg:hidden text-center">
            <p className="text-sm text-[#94A3B8] leading-relaxed">
              Courses, cohorts, community, and archives — woven into one coherent
              environment for transformative learning.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
