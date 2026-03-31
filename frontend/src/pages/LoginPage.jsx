import React from 'react';
import { Button } from '../components/ui/button';
import { SignIn } from '@phosphor-icons/react';

export default function LoginPage({ onLogin }) {
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
        <div className="w-full max-w-sm space-y-10">
          {/* Logo */}
          <div className="text-center">
            <div className="w-16 h-16 mx-auto rounded-lg bg-[#D4AF37]/10 border border-[#D4AF37]/20 flex items-center justify-center mb-6">
              <span
                className="text-[#D4AF37] text-3xl"
                style={{ fontFamily: 'Cormorant Garamond, serif' }}
              >
                &#9765;
              </span>
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

          {/* CTA */}
          <div className="space-y-4">
            <Button
              onClick={onLogin}
              className="w-full bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB] font-medium py-3 transition-all duration-200"
              data-testid="login-button"
            >
              <SignIn size={18} weight="duotone" className="mr-2" />
              Sign In to Continue
            </Button>
            <p className="text-center text-xs text-[#94A3B8]">
              Secure sign-in powered by Google OAuth
            </p>
          </div>

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
