import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { getCookie, setCookie, apiPost, apiGet } from './lib/api';
import { I18nProvider } from './i18n';
import AppLayout from './components/layout/AppLayout';
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
import './App.css';

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showOnboarding, setShowOnboarding] = useState(false);

  useEffect(() => {
    checkAuth();
    handleAuthCallback();
  }, []);

  const checkAuth = async () => {
    const sessionId = getCookie('session_id');
    if (sessionId) {
      try {
        const userData = await apiGet('/api/auth/me');
        setUser(userData);
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
    const hash = window.location.hash;
    if (hash && hash.includes('session_id=')) {
      const sessionId = hash.split('session_id=')[1];
      try {
        await apiPost('/api/auth/profile', { session_id: sessionId });
        setCookie('session_id', sessionId, 7);
        window.location.hash = '';
        const userData = await apiGet('/api/auth/me');
        setUser(userData);
        if (!userData.onboarding_complete) {
          setShowOnboarding(true);
        }
      } catch (e) {
        console.error('Auth callback failed:', e);
      }
    }
  };

  const handleLogin = () => {
    const currentUrl = window.location.origin;
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(currentUrl)}`;
  };

  const handleLogout = () => {
    setUser(null);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#050814] flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 mx-auto rounded-lg bg-[#D4AF37]/10 border border-[#D4AF37]/20 flex items-center justify-center mb-4 animate-pulse">
            <span className="text-[#D4AF37] text-2xl" style={{ fontFamily: 'Cormorant Garamond, serif' }}>&#9765;</span>
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
          <Routes>
            <Route path="/about" element={<AboutPage />} />
            <Route path="/blog" element={<PublicBlogPage onLogin={handleLogin} />} />
            <Route path="/login" element={<LoginPage onLogin={handleLogin} />} />
            <Route path="*" element={<LandingPage onLogin={handleLogin} />} />
          </Routes>
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
            <Route path="/about" element={<AboutPage />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </AppLayout>
      </BrowserRouter>
    </I18nProvider>
  );
}

export default App;
