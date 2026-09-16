import React, { useState, useMemo, useEffect } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import BrandMark from '../brand/BrandMark';
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
  ChartBar,
  Sparkle,
  FilmSlate,
  GlobeSimple,
  Megaphone,
  Newspaper,
  ChalkboardTeacher,
  HouseLine,
  HandHeart,
  TreeEvergreen,
  Backpack,
  Compass,
  Sun,
  Moon,
} from '@phosphor-icons/react';
import { clearCookie, clearOfflineCache, apiPut, apiGet } from '../../lib/api';
import { useI18n } from '../../i18n';
import SearchBar from './SearchBar';

// Role-aware, mode-based navigation (product eval §8): each persona sees a
// small, coherent menu instead of one flat 14-item list.
const navSections = [
  {
    labelKey: 'nav_learn',
    items: [
      { to: '/dashboard', labelKey: 'dashboard', icon: House },
      { to: '/courses', labelKey: 'courses', icon: BookOpenText },
      { to: '/live', labelKey: 'live_teaching', icon: VideoCamera },
      { to: '/cohorts', labelKey: 'cohorts', icon: UsersThree },
      { to: '/archives', labelKey: 'archives', icon: Archive },
    ],
  },
  {
    labelKey: 'nav_grow',
    items: [
      { to: '/portfolio', labelKey: 'portfolio', icon: Backpack },
    ],
  },
  {
    labelKey: 'nav_belong',
    items: [
      { to: '/villages', labelKey: 'villages', icon: TreeEvergreen },
      { to: '/community', labelKey: 'community', icon: Chats },
      { to: '/learning-circles', labelKey: 'learning_circles', icon: HandHeart },
      { to: '/spaces', labelKey: 'spaces', icon: ShieldCheck },
      { to: '/blog', labelKey: 'blog', icon: Newspaper },
      { to: '/messages', labelKey: 'messages', icon: Bell },
    ],
  },
  {
    labelKey: 'nav_family',
    familyOnly: true, // family-intent accounts and minors
    items: [
      { to: '/family', labelKey: 'family_my', icon: HouseLine },
    ],
  },
  {
    labelKey: 'nav_facilitate',
    facultyOnly: true,
    items: [
      { to: '/community-dashboard', labelKey: 'community_dashboard', icon: UsersThree },
      { to: '/teacher-dashboard', labelKey: 'teacher_dashboard', icon: ChalkboardTeacher },
      { to: '/session-records', labelKey: 'session_records', icon: FilmSlate },
      { to: '/analytics', labelKey: 'analytics', icon: ChartBar },
      { to: '/marketing', labelKey: 'marketing', icon: Megaphone },
    ],
  },
  {
    labelKey: 'nav_account',
    items: [
      { to: '/subscriptions', labelKey: 'membership', icon: Sparkle },
    ],
  },
];

const FACULTY_ROLES = ['admin', 'elder', 'faculty'];

export default function Sidebar({ user, onLogout }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [myVillages, setMyVillages] = useState([]);
  const [guideEnabled, setGuideEnabled] = useState(false);
  const [theme, setTheme] = useState(() => {
    try { return localStorage.getItem('ile-theme') === 'light' ? 'light' : 'dark'; } catch (e) { return 'dark'; }
  });
  const navigate = useNavigate();
  const { t, lang, setLang, LANG_NAMES } = useI18n();

  // Phase 2 (deep migration): when the user belongs to a village, a VILLAGE
  // section is pinned above everything else (eval §8 tree).
  useEffect(() => {
    apiGet('/api/villages').then(d => setMyVillages(d.mine || [])).catch(() => {});
  }, []);

  // Show the Help entry only when the Village Guide is actually available
  // (same env-gate as the floating widget: no ANTHROPIC_API_KEY, no guide).
  useEffect(() => {
    apiGet('/api/guide/status').then(d => setGuideEnabled(!!d.enabled)).catch(() => {});
  }, []);

  const applyTheme = (next) => {
    setTheme(next);
    try { localStorage.setItem('ile-theme', next); } catch (e) { /* private mode */ }
    // index.html applies this same attribute before first paint on reload.
    if (next === 'light') document.documentElement.setAttribute('data-theme', 'light');
    else document.documentElement.removeAttribute('data-theme');
  };

  const openGuide = () => {
    setMobileOpen(false);
    window.dispatchEvent(new Event('open-village-guide'));
  };

  const handleLogout = () => {
    clearCookie('session_id');
    clearOfflineCache();
    onLogout();
    navigate('/');
  };

  const handleLangChange = async (newLang) => {
    setLang(newLang);
    try { await apiPut('/api/auth/me/language', { language: newLang }); } catch (e) { console.error('Language update failed:', e); }
  };

  const visibleSections = useMemo(() => {
    const isFaculty = FACULTY_ROLES.includes(user?.role);
    const isFamily = user?.intent === 'family' || user?.is_minor;
    const sections = navSections
      .filter(section => !section.facultyOnly || isFaculty)
      .filter(section => !section.familyOnly || isFamily)
      .map(section => ({
        ...section,
        items: section.items.filter(item => !item.facultyOnly || isFaculty),
      }))
      .filter(section => section.items.length > 0);
    if (myVillages.length > 0) {
      sections.unshift({
        labelKey: 'nav_village',
        items: [{
          // One village → straight to its feed; several → the picker at "/"
          to: myVillages.length === 1 ? `/village/${myVillages[0].id}` : '/',
          end: myVillages.length !== 1,
          labelKey: 'village_home',
          icon: TreeEvergreen,
        }],
      });
    }
    return sections;
  }, [user?.role, user?.intent, user?.is_minor, myVillages]);

  const linkClass = ({ isActive }) =>
    `flex items-center gap-3 px-4 py-3 text-sm font-medium transition-all duration-200 border-l-2 ${
      isActive
        ? 'border-[rgb(var(--gold))] text-[rgb(var(--gold))] bg-[rgb(var(--gold)/0.05)]'
        : 'border-transparent text-[rgb(var(--text-muted))] hover:text-[rgb(var(--text-main))] hover:bg-[rgb(var(--ink-card))]'
    }`;

  const sidebarContent = (
    <div className="flex flex-col h-full" data-testid="sidebar">
      {/* Logo */}
      <div className="px-5 py-6 border-b border-[rgb(var(--ink-border))]">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-md bg-[rgb(var(--gold)/0.1)] flex items-center justify-center">
            <BrandMark className="w-6 h-6 object-contain" />
          </div>
          <div>
            <h1 className="text-base font-semibold text-[rgb(var(--text-main))]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
              The Ile Ubuntu
            </h1>
            <p className="text-[10px] tracking-[0.2em] uppercase text-[rgb(var(--gold))]">Living Commons</p>
          </div>
        </div>
      </div>

      {/* Search */}
      <div className="px-3 py-2 border-b border-[rgb(var(--ink-border))]">
        <SearchBar />
      </div>

      {/* Nav */}
      <nav className="flex-1 py-2 overflow-y-auto">
        {visibleSections.map((section) => (
          <div key={section.labelKey} className="mb-2">
            <p className="px-4 pt-3 pb-1 text-[9px] tracking-[0.25em] uppercase text-[rgb(var(--text-faint))]">
              {t(section.labelKey)}
            </p>
            <div className="space-y-0.5">
              {section.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  className={linkClass}
                  onClick={() => setMobileOpen(false)}
                  data-testid={`nav-${item.labelKey}`}
                >
                  <item.icon size={20} weight="duotone" />
                  {t(item.labelKey)}
                </NavLink>
              ))}
            </div>
          </div>
        ))}
        {guideEnabled && (
          <div className="mb-2">
            <p className="px-4 pt-3 pb-1 text-[9px] tracking-[0.25em] uppercase text-[rgb(var(--text-faint))]">
              {t('nav_help')}
            </p>
            <button
              onClick={openGuide}
              className="w-full flex items-center gap-3 px-4 py-3 text-sm font-medium transition-all duration-200 border-l-2 border-transparent text-[rgb(var(--text-muted))] hover:text-[rgb(var(--text-main))] hover:bg-[rgb(var(--ink-card))]"
              data-testid="nav-village-guide"
            >
              <Compass size={20} weight="duotone" />
              {t('village_guide')}
            </button>
          </div>
        )}
      </nav>

      {/* Theme */}
      <div className="px-4 py-2 border-t border-[rgb(var(--ink-border))]">
        <div className="flex gap-1" data-testid="theme-selector">
          {[['dark', Moon, 'theme_dark'], ['light', Sun, 'theme_light']].map(([mode, Icon, key]) => (
            <button
              key={mode}
              onClick={() => applyTheme(mode)}
              className={`flex-1 flex items-center justify-center gap-1.5 py-1 rounded text-[9px] transition-all ${
                theme === mode
                  ? 'bg-[rgb(var(--gold)/0.1)] text-[rgb(var(--gold))] border border-[rgb(var(--gold)/0.3)]'
                  : 'text-[rgb(var(--text-faint))] border border-[rgb(var(--ink-border))] hover:text-[rgb(var(--text-muted))]'
              }`}
              data-testid={`theme-${mode}`}
            >
              <Icon size={12} weight="duotone" />
              {t(key)}
            </button>
          ))}
        </div>
      </div>

      {/* Language Selector */}
      <div className="px-4 py-2 border-t border-[rgb(var(--ink-border))]">
        <div className="flex items-center gap-2">
          <GlobeSimple size={14} weight="duotone" className="text-[rgb(var(--text-muted))] flex-shrink-0" />
          <div className="flex gap-1 flex-1" data-testid="language-selector">
            {Object.entries(LANG_NAMES).map(([code, name]) => (
              <button
                key={code}
                onClick={() => handleLangChange(code)}
                className={`flex-1 py-1 rounded text-[9px] transition-all ${
                  lang === code
                    ? 'bg-[rgb(var(--gold)/0.1)] text-[rgb(var(--gold))] border border-[rgb(var(--gold)/0.3)]'
                    : 'text-[rgb(var(--text-faint))] border border-[rgb(var(--ink-border))] hover:text-[rgb(var(--text-muted))]'
                }`}
                data-testid={`lang-${code}`}
              >
                {name}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* User */}
      <div className="border-t border-[rgb(var(--ink-border))] p-4">
        <div className="flex items-center gap-3 mb-3">
          <img
            src={user?.picture}
            alt={user?.name}
            className="w-8 h-8 rounded-full border border-[rgb(var(--gold)/0.3)]"
          />
          <div className="flex-1 min-w-0">
            <p className="text-sm text-[rgb(var(--text-main))] truncate">{user?.name}</p>
            <p className="text-[10px] tracking-[0.15em] uppercase text-[rgb(var(--gold))]">{user?.role}</p>
          </div>
        </div>
        <div className="flex gap-2">
          <NavLink
            to="/settings"
            className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs text-[rgb(var(--text-muted))] hover:text-[rgb(var(--text-main))] bg-[rgb(var(--ink-card))] rounded border border-[rgb(var(--ink-border))] hover:border-[rgb(var(--gold)/0.3)] transition-all"
            data-testid="nav-settings"
          >
            <GearSix size={14} weight="duotone" />
            {t('settings')}
          </NavLink>
          <button
            onClick={handleLogout}
            className="flex items-center justify-center gap-1.5 px-3 py-2 text-xs text-[rgb(var(--text-muted))] hover:text-red-400 bg-[rgb(var(--ink-card))] rounded border border-[rgb(var(--ink-border))] hover:border-red-400/30 transition-all"
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
        className="lg:hidden fixed left-4 z-50 p-2 bg-[rgb(var(--ink-card))] border border-[rgb(var(--ink-border))] rounded-md text-[rgb(var(--text-muted))]"
        style={{ top: 'calc(var(--safe-area-top, 0px) + 12px)' }}
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
        className={`fixed top-0 left-0 h-screen w-60 bg-[rgb(var(--ink-deep))] border-r border-[rgb(var(--ink-border))] z-40 transition-transform duration-300 ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        {sidebarContent}
      </aside>
    </>
  );
}
