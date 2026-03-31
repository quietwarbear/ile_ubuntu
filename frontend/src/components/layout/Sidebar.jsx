import React, { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  House,
  BookOpenText,
  UsersThree,
  Chats,
  Archive,
  Bell,
  GearSix,
  SignOut,
  List,
  X,
  VideoCamera,
  ShieldCheck,
} from '@phosphor-icons/react';
import { clearCookie } from '../../lib/api';

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: House },
  { to: '/courses', label: 'Courses', icon: BookOpenText },
  { to: '/live', label: 'Live Teaching', icon: VideoCamera },
  { to: '/cohorts', label: 'Cohorts', icon: UsersThree },
  { to: '/spaces', label: 'Spaces', icon: ShieldCheck },
  { to: '/community', label: 'Community', icon: Chats },
  { to: '/archives', label: 'Archives', icon: Archive },
  { to: '/messages', label: 'Messages', icon: Bell },
];

export default function Sidebar({ user, onLogout }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const navigate = useNavigate();

  const handleLogout = () => {
    clearCookie('session_id');
    onLogout();
    navigate('/');
  };

  const linkClass = ({ isActive }) =>
    `flex items-center gap-3 px-4 py-3 text-sm font-medium transition-all duration-200 border-l-2 ${
      isActive
        ? 'border-[#D4AF37] text-[#D4AF37] bg-[#D4AF37]/5'
        : 'border-transparent text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#0F172A]'
    }`;

  const sidebarContent = (
    <div className="flex flex-col h-full" data-testid="sidebar">
      {/* Logo */}
      <div className="px-5 py-6 border-b border-[#1E293B]">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-md bg-[#D4AF37]/10 flex items-center justify-center">
            <span className="text-[#D4AF37] font-bold text-lg" style={{ fontFamily: 'Cormorant Garamond, serif' }}>&#9765;</span>
          </div>
          <div>
            <h1 className="text-base font-semibold text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
              The Ile Ubuntu
            </h1>
            <p className="text-[10px] tracking-[0.2em] uppercase text-[#D4AF37]">Living Commons</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-4 space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={linkClass}
            onClick={() => setMobileOpen(false)}
            data-testid={`nav-${item.label.toLowerCase()}`}
          >
            <item.icon size={20} weight="duotone" />
            {item.label}
          </NavLink>
        ))}
      </nav>

      {/* User */}
      <div className="border-t border-[#1E293B] p-4">
        <div className="flex items-center gap-3 mb-3">
          <img
            src={user?.picture}
            alt={user?.name}
            className="w-8 h-8 rounded-full border border-[#D4AF37]/30"
          />
          <div className="flex-1 min-w-0">
            <p className="text-sm text-[#F8FAFC] truncate">{user?.name}</p>
            <p className="text-[10px] tracking-[0.15em] uppercase text-[#D4AF37]">{user?.role}</p>
          </div>
        </div>
        <div className="flex gap-2">
          <NavLink
            to="/settings"
            className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs text-[#94A3B8] hover:text-[#F8FAFC] bg-[#0F172A] rounded border border-[#1E293B] hover:border-[#D4AF37]/30 transition-all"
            data-testid="nav-settings"
          >
            <GearSix size={14} weight="duotone" />
            Settings
          </NavLink>
          <button
            onClick={handleLogout}
            className="flex items-center justify-center gap-1.5 px-3 py-2 text-xs text-[#94A3B8] hover:text-red-400 bg-[#0F172A] rounded border border-[#1E293B] hover:border-red-400/30 transition-all"
            data-testid="logout-button"
          >
            <SignOut size={14} weight="duotone" />
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* Mobile toggle */}
      <button
        className="lg:hidden fixed top-4 left-4 z-50 p-2 bg-[#0F172A] border border-[#1E293B] rounded-md text-[#94A3B8]"
        onClick={() => setMobileOpen(!mobileOpen)}
        data-testid="mobile-menu-toggle"
      >
        {mobileOpen ? <X size={20} /> : <List size={20} />}
      </button>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/60 z-40"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed top-0 left-0 h-screen w-60 bg-[#050814] border-r border-[#1E293B] z-40 transition-transform duration-300 ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        {sidebarContent}
      </aside>
    </>
  );
}
