import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { getCookie, setCookie, apiPost, apiGet } from './lib/api';
import { I18nProvider } from './i18n';
import { initializeRevenueCat, syncRevenueCatUser, logOutRevenueCat } from './lib/revenuecat';
import { applySafeAreaStyles, initializeNativePlugins } from './lib/platform';
import AppLayout from './components/layout/AppLayout';
import BrandMark from './components/brand/BrandMark';
import OnboardingWizard from './components/OnboardingWizard';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import CoursesPage from './pages/CoursesPage';
import CourseDetailPage from './pages/CourseDetailPage';
import CohortsPage from './pages/CohortsPage';
import CommunityPage from './pages/CommunityPage';
import ArchivesPage from './pages/ArchivesPage';
import MessagesPage from './pages/MessagesPage';
import SettingsPage from './pages/SettingsPage';
import LiveSessionsPage from './pages/LiveSessionsPage';
import LiveRoomPage from './pages/LiveRoomPage';
import CohortDetailPage from './pages/CohortDetailPage';
import SpacesPage from './pages/SpacesPage';
import AnalyticsPage from './pages/AnalyticsPage';
import SubscriptionsPage from './pages/SubscriptionsPage';
import SessionRecordsPage from './pages/SessionRecordsPage';
import AboutPage from './pages/AboutPage';
import SearchResultsPage from './pages/SearchResultsPage';
import MarketingPage from './pages/MarketingPage';
import LandingPage from './pages/LandingPage';
import PublicBlogPage from './pages/PublicBlogPage';
import BlogPage from './pages/BlogPage';
import BlogPostPage from './pages/BlogPostPage';
import BlogEditorPage from './pages/BlogEditorPage';
import TeacherDashboardPage from './pages/TeacherDashboardPage';
import PrivacyPolicyPage from './pages/PrivacyPolicyPage';
import TermsPage from './pages/TermsPage';
import './App.css';

// Unauthenticated routes. This sits INSIDE <BrowserRouter> so it can use
// useNavigate() — which is required because Capacitor's iOS webview does NOT
// reliably navigate via `window.location.href = '/login'`. Apple rejected
// iOS 1.0 (Guideline 2.1 App Completeness) because every "Sign In / Begin
// Your Journey / Join" button was unresponsive due to that bug.
function PublicRoutes({ handlePasswordLogin }) {
  const navigate = useNavigate();

  // Entry point from Landing/Blog "Sign In" buttons. Always route to the
  // LoginPage first — on BOTH web and native — so the user can choose between
  // email/password, Google, or Apple. Previously web skipped LoginPage and
  // went straight to Google OAuth, which hid the Apple option.
  const handleLogin = () => {
    navigate('/login');
  };

  // Called from the LoginPage "Continue with Google" button. On web, redirects
  // to the backend's Google OAuth start URL. On native, runs the Capacitor
  // GoogleAuth plugin and POSTs the idToken to /api/auth/google/session.
  const handleGoogleFromLogin = async () => {
    const isNativePlatform = window.Capacitor && window.Capacitor.isNativePlatform();
    const isAndroid = isNativePlatform && window.Capacitor.getPlatform() === 'android';
    const isIOS = isNativePlatform && window.Capacitor.getPlatform() === 'ios';
    console.log("[DEBUG] Platform:", window.Capacitor?.getPlatform?.(), "isNative:", isNativePlatform, "isIOS:", isIOS, "isAndroid:", isAndroid);
    if (isIOS) {
      // iOS native: use server-side OAuth flow via /api/auth/google/start
      // (GoogleAuth Capacitor plugin needs CocoaPods, not available with SPM)
      const API = process.env.REACT_APP_BACKEND_URL || 'https://ileubuntu-production.up.railway.app';
      const redirectUri = 'ileubuntu://auth/google/callback';
      window.location.href = `${API}/api/auth/google/start?redirect_uri=${encodeURIComponent(redirectUri)}`;
      return;
    }

    if (isAndroid) {
      // Android native: run the Capacitor GoogleAuth flow
      return handleGoogleLogin();
    }

    // Web: use backend's Google OAuth redirect flow
    try {
      const redirectUri = `${window.location.origin}/`;
      const data = await apiGet(`/api/auth/google/login-url?redirect_uri=${encodeURIComponent(redirectUri)}`);
      if (data.auth_url) {
        window.location.href = data.auth_url;
      }
    } catch (e) {
      console.error('Failed to get login URL:', e);
    }
  };

  // All native Google sign-in goes through server-side OAuth flow.
  // The Capacitor GoogleAuth plugin requires CocoaPods (not SPM) so
  // we bypass it entirely and use our backend's /api/auth/google/start.
  const handleGoogleLogin = async () => {
    if (!(window.Capacitor && window.Capacitor.isNativePlatform())) {
      return handleLogin();
    }
    const API = process.env.REACT_APP_BACKEND_URL || 'https://ileubuntu-production.up.railway.app';
    const redirectUri = 'ileubuntu://auth/google/callback';
    console.log('[IleUbuntu] Starting server-side Google OAuth for native');
    window.location.href = `${API}/api/auth/google/start?redirect_uri=${encodeURIComponent(redirectUri)}`;
  };

  return (
    <Routes>
      <Route path="/about" element={<AboutPage />} />
      <Route path="/privacy-policy" element={<PrivacyPolicyPage />} />
      <Route path="/terms" element={<TermsPage />} />
      <Route path="/blog" element={<PublicBlogPage onLogin={handleLogin} />} />
      <Route path="/login" element={<LoginPage onLogin={handleGoogleFromLogin} onPasswordLogin={handlePasswordLogin} />} />
      <Route path="*" element={<LandingPage onLogin={handleLogin} />} />
    </Routes>
  );
}

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showOnboarding, setShowOnboarding] = useState(false);

  useEffect(() => {
    // Initialize native platform (Capacitor plugins, safe areas)
    applySafeAreaStyles();
    initializeNativePlugins();
    initializeRevenueCat();

    checkAuth();
    handleAuthCallback();
  }, []);

  const checkAuth = async () => {
    const sessionId = getCookie('session_id');
    if (sessionId) {
      try {
        const userData = await apiGet('/api/auth/me');
        setUser(userData);
        // Sync RevenueCat with authenticated user
        syncRevenueCatUser(userData.id);
        if (!userData.onboarding_complete) {
          setShowOnboarding(true);
        }
      } catch (e) {
        console.error('Auth check failed:', e);
      }
    }
    setLoading(false);
  };

  const handleAuthCallback = async () => {
    const params = new URLSearchParams(window.location.search);

    // Handle Apple OAuth callback with ?session_id= or ?apple_error= parameters
    const appleSessionId = params.get('session_id');
    const appleError = params.get('apple_error');
    if (appleSessionId) {
      try {
        setCookie('session_id', appleSessionId, 7);
        // Clean up URL params
        window.history.replaceState({}, '', '/');
        const userData = await apiGet('/api/auth/me');
        setUser(userData);
        syncRevenueCatUser(userData.id);
        if (!userData.onboarding_complete) {
          setShowOnboarding(true);
        }
        return;
      } catch (e) {
        console.error('Apple auth callback failed:', e);
      }
    }
    if (appleError) {
      console.error('Apple Sign In error:', appleError);
      // Clean up URL params
      window.history.replaceState({}, '', '/');
      return;
    }

    // Handle Google OAuth callback with ?code= parameter
    const code = params.get('code');
    if (code) {
      try {
        const redirectUri = `${window.location.origin}/`;
        const result = await apiPost('/api/auth/google/callback', {
          code,
          redirect_uri: redirectUri,
        });
        if (result.session_id) {
          setCookie('session_id', result.session_id, 7);
          // Clean up URL params
          window.history.replaceState({}, '', '/');
          const userData = await apiGet('/api/auth/me');
          setUser(userData);
          syncRevenueCatUser(userData.id);
          if (!userData.onboarding_complete) {
            setShowOnboarding(true);
          }
        }
      } catch (e) {
        console.error('Auth callback failed:', e);
      }
    }

    // Legacy: handle hash-based session_id (backward compat)
    const hash = window.location.hash;
    if (hash && hash.includes('session_id=')) {
      const sessionId = hash.split('session_id=')[1];
      try {
        await apiPost('/api/auth/profile', { session_id: sessionId });
        setCookie('session_id', sessionId, 7);
        window.location.hash = '';
        const userData = await apiGet('/api/auth/me');
        setUser(userData);
        syncRevenueCatUser(userData.id);
        if (!userData.onboarding_complete) {
          setShowOnboarding(true);
        }
      } catch (e) {
        console.error('Legacy auth callback failed:', e);
      }
    }
  };

  const handlePasswordLogin = async (data) => {
    // Called by LoginPage after successful email/password login or register
    if (data.session_id) {
      setCookie('session_id', data.session_id, 7);
      try {
        const userData = await apiGet('/api/auth/me');
        setUser(userData);
        syncRevenueCatUser(userData.id);
        if (!userData.onboarding_complete) {
          setShowOnboarding(true);
        }
      } catch (e) {
      }
    } else {
    }
  };

  const handleLogout = () => {
    logOutRevenueCat();
    setUser(null);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#050814] flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 mx-auto rounded-lg bg-[#D4AF37]/10 border border-[#D4AF37]/20 flex items-center justify-center mb-4 animate-pulse">
            <BrandMark className="w-8 h-8 object-contain" />
          </div>
          <p className="text-xs tracking-[0.2em] uppercase text-[#94A3B8]">Loading...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <I18nProvider defaultLang="en">
        <BrowserRouter>
          <PublicRoutes handlePasswordLogin={handlePasswordLogin} />
        </BrowserRouter>
      </I18nProvider>
    );
  }

  return (
    <I18nProvider defaultLang={user.language || 'en'}>
      <BrowserRouter>
        {showOnboarding && (
          <OnboardingWizard
            user={user}
            onComplete={() => setShowOnboarding(false)}
          />
        )}
        <AppLayout user={user} onLogout={handleLogout}>
          <Routes>
            <Route path="/dashboard" element={<DashboardPage user={user} />} />
            <Route path="/courses" element={<CoursesPage user={user} />} />
            <Route path="/courses/:courseId" element={<CourseDetailPage user={user} />} />
            <Route path="/live" element={<LiveSessionsPage user={user} />} />
            <Route path="/live/:sessionId" element={<LiveRoomPage user={user} />} />
            <Route path="/cohorts" element={<CohortsPage user={user} />} />
            <Route path="/cohorts/:cohortId" element={<CohortDetailPage user={user} />} />
            <Route path="/spaces" element={<SpacesPage user={user} />} />
            <Route path="/analytics" element={<AnalyticsPage user={user} />} />
            <Route path="/subscriptions" element={<SubscriptionsPage user={user} />} />
            <Route path="/session-records" element={<SessionRecordsPage user={user} />} />
            <Route path="/community" element={<CommunityPage user={user} />} />
            <Route path="/archives" element={<ArchivesPage user={user} />} />
            <Route path="/messages" element={<MessagesPage user={user} />} />
            <Route path="/settings" element={<SettingsPage user={user} />} />
            <Route path="/search" element={<SearchResultsPage user={user} />} />
            <Route path="/marketing" element={<MarketingPage />} />
            <Route path="/blog" element={<BlogPage user={user} />} />
            <Route path="/blog/new" element={<BlogEditorPage user={user} />} />
            <Route path="/blog/edit/:postId" element={<BlogEditorPage user={user} />} />
            <Route path="/blog/:slug" element={<BlogPostPage user={user} />} />
            <Route path="/teacher-dashboard" element={<TeacherDashboardPage user={user} />} />
            <Route path="/about" element={<AboutPage />} />
            <Route path="/privacy-policy" element={<PrivacyPolicyPage />} />
            <Route path="/terms" element={<TermsPage />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </AppLayout>
      </BrowserRouter>
    </I18nProvider>
  );
}

export default App;
