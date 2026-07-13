import React, { useState, useEffect, lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { getCookie, setCookie, apiPost, apiGet } from './lib/api';
import { identifyUser, resetAnalytics } from './lib/analytics';
import { I18nProvider } from './i18n';
import { initializeRevenueCat, syncRevenueCatUser, logOutRevenueCat } from './lib/revenuecat';
import { applySafeAreaStyles, initializeNativePlugins } from './lib/platform';
import AppLayout from './components/layout/AppLayout';
import BrandMark from './components/brand/BrandMark';
// Eager: the anonymous first-paint path (landing + login) and the invite
// redirect that must run on every authenticated boot. Everything else is a
// lazy route chunk — webpack code-splits each import() so first load ships
// the shell instead of all ~30 pages (§11.1 single-chunk fix).
import LoginPage from './pages/LoginPage';
import LandingPage from './pages/LandingPage';
import JoinCoursePage, { PendingInviteRedirect } from './pages/JoinCoursePage';
import InviteLandingPage from './components/InviteLandingPage';
import './App.css';

const OnboardingWizard = lazy(() => import('./components/OnboardingWizard'));
const ResetPasswordPage = lazy(() => import('./pages/ResetPasswordPage'));
const FamilyPage = lazy(() => import('./pages/FamilyPage'));
const LearningCirclePage = lazy(() => import('./pages/LearningCirclePage'));
const CommunityDashboardPage = lazy(() => import('./pages/CommunityDashboardPage'));
const VillagesPage = lazy(() => import('./pages/VillagesPage'));
const VillageDetail = lazy(() => import('./pages/VillagesPage').then(m => ({ default: m.VillageDetail })));
const VillageHomePage = lazy(() => import('./pages/VillageHomePage'));
const VillageHomeGate = lazy(() => import('./pages/VillageHomePage').then(m => ({ default: m.VillageHomeGate })));
const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const CoursesPage = lazy(() => import('./pages/CoursesPage'));
const CourseDetailPage = lazy(() => import('./pages/CourseDetailPage'));
const CoursePlayerPage = lazy(() => import('./pages/CoursePlayerPage'));
const CohortsPage = lazy(() => import('./pages/CohortsPage'));
const CommunityPage = lazy(() => import('./pages/CommunityPage'));
const ArchivesPage = lazy(() => import('./pages/ArchivesPage'));
const MessagesPage = lazy(() => import('./pages/MessagesPage'));
const SettingsPage = lazy(() => import('./pages/SettingsPage'));
const LiveSessionsPage = lazy(() => import('./pages/LiveSessionsPage'));
const LiveRoomPage = lazy(() => import('./pages/LiveRoomPage'));
const CohortDetailPage = lazy(() => import('./pages/CohortDetailPage'));
const SpacesPage = lazy(() => import('./pages/SpacesPage'));
const AnalyticsPage = lazy(() => import('./pages/AnalyticsPage'));
const SubscriptionsPage = lazy(() => import('./pages/SubscriptionsPage'));
const SessionRecordsPage = lazy(() => import('./pages/SessionRecordsPage'));
const AboutPage = lazy(() => import('./pages/AboutPage'));
const SearchResultsPage = lazy(() => import('./pages/SearchResultsPage'));
const MarketingPage = lazy(() => import('./pages/MarketingPage'));
const PublicBlogPage = lazy(() => import('./pages/PublicBlogPage'));
const BlogPage = lazy(() => import('./pages/BlogPage'));
const BlogPostPage = lazy(() => import('./pages/BlogPostPage'));
const BlogEditorPage = lazy(() => import('./pages/BlogEditorPage'));
const TeacherDashboardPage = lazy(() => import('./pages/TeacherDashboardPage'));
const PrivacyPolicyPage = lazy(() => import('./pages/PrivacyPolicyPage'));
const TermsPage = lazy(() => import('./pages/TermsPage'));

// Route-chunk loading state — same brand treatment as the app boot screen.
function PageLoader() {
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

// Ubuntu Markets SSO handoff — redeems a one-time code from a sibling product (Kindred)
// and opens an Ile Ubuntu session. Reached at /sso?code=…
function SSOHandoffPage() {
  const [error, setError] = useState("");
  useEffect(() => {
    const code = new URLSearchParams(window.location.search).get("code");
    if (!code) { setError("Missing sign-in code. Please try again from the other app."); return; }
    (async () => {
      try {
        const res = await apiPost('/api/auth/sso-redeem', { code });
        if (res && res.session_id) {
          setCookie('session_id', res.session_id, 7);
          window.location.replace('/dashboard');
        } else {
          setError("Sign-in failed. Please try again.");
        }
      } catch (e) {
        setError("This sign-in link has expired or was already used. Please try again from the other app.");
      }
    })();
  }, []);
  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94A3B8', padding: 24, textAlign: 'center', background: '#050814' }}>
      <p data-testid="ile-sso-status">{error || 'Signing you in to Ile Ubuntu…'}</p>
    </div>
  );
}

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

  // Google sign-in handler — LoginPage's Google button calls this via onLogin.
  // Native: uses Browser.open (SFSafariViewController) for in-app OAuth.
  // Web: redirects to Google OAuth via backend login-url endpoint.
  const handleGoogleFromLogin = async () => {
    const isNativePlatform = window.Capacitor && window.Capacitor.isNativePlatform();

    if (isNativePlatform) {
      const API = process.env.REACT_APP_BACKEND_URL || 'https://ileubuntu-production.up.railway.app';
      const authUrl = `${API}/api/auth/google/start?redirect_uri=${encodeURIComponent('ileubuntu://auth/google/callback')}`;
      try {
        const { Browser } = await import('@capacitor/browser');
        await Browser.open({ url: authUrl, presentationStyle: 'fullscreen' });
      } catch (e) {
        console.error('Failed to open in-app browser for Google Sign In:', e);
      }
      return;
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

  return (
    <Suspense fallback={<PageLoader />}>
    <Routes>
      <Route path="/invite/:code" element={<InviteLandingPage />} />
      <Route path="/about" element={<AboutPage />} />
      <Route path="/privacy-policy" element={<PrivacyPolicyPage />} />
      <Route path="/terms" element={<TermsPage />} />
      <Route path="/blog" element={<PublicBlogPage onLogin={handleLogin} />} />
      <Route path="/login" element={<LoginPage onLogin={handleGoogleFromLogin} onPasswordLogin={handlePasswordLogin} />} />
      <Route path="/sso" element={<SSOHandoffPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route path="/join/:code" element={<JoinCoursePage />} />
      <Route path="*" element={<LandingPage onLogin={handleLogin} />} />
    </Routes>
    </Suspense>
  );
}

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showOnboarding, setShowOnboarding] = useState(false);

  // Analytics identity follows the user state: identify on login/restore,
  // reset on logout so the next login isn't merged into the old person.
  useEffect(() => {
    if (user?.id) {
      identifyUser(user);
    } else {
      resetAnalytics();
    }
  }, [user?.id]);

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
          <Suspense fallback={<PageLoader />}>
            <OnboardingWizard
              user={user}
              onComplete={() => setShowOnboarding(false)}
            />
          </Suspense>
        )}
        <PendingInviteRedirect />
        <AppLayout user={user} onLogout={handleLogout}>
          <Suspense fallback={<PageLoader />}>
          <Routes>
            {/* Phase 2 (deep migration): home is the village. One village →
                its feed; multiple → picker; none → commons dashboard. */}
            <Route path="/" element={<VillageHomeGate user={user} />} />
            <Route path="/village/:villageId" element={<VillageHomePage user={user} />} />
            <Route path="/dashboard" element={<DashboardPage user={user} />} />
            <Route path="/courses" element={<CoursesPage user={user} />} />
            <Route path="/courses/:courseId" element={<CourseDetailPage user={user} />} />
            <Route path="/courses/:courseId/learn" element={<CoursePlayerPage user={user} />} />
            <Route path="/courses/:courseId/learn/:lessonId" element={<CoursePlayerPage user={user} />} />
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
            <Route path="/join/:code" element={<JoinCoursePage user={user} />} />
            <Route path="/family" element={<FamilyPage user={user} />} />
            <Route path="/learning-circles" element={<LearningCirclePage user={user} />} />
            {/* Old path kept as a redirect — bookmarks and the renamed nav */}
            <Route path="/mentorship" element={<Navigate to="/learning-circles" replace />} />
            <Route path="/community-dashboard" element={<CommunityDashboardPage user={user} />} />
            <Route path="/villages" element={<VillagesPage user={user} />} />
            <Route path="/villages/:villageId" element={<VillageDetail user={user} />} />
            <Route path="/about" element={<AboutPage />} />
            <Route path="/privacy-policy" element={<PrivacyPolicyPage />} />
            <Route path="/terms" element={<TermsPage />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
          </Suspense>
        </AppLayout>
      </BrowserRouter>
    </I18nProvider>
  );
}

export default App;
