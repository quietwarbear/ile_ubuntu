import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { getCookie, setCookie, apiPost, apiGet } from './lib/api';
import AppLayout from './components/layout/AppLayout';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import CoursesPage from './pages/CoursesPage';
import CourseDetailPage from './pages/CourseDetailPage';
import CohortsPage from './pages/CohortsPage';
import CommunityPage from './pages/CommunityPage';
import ArchivesPage from './pages/ArchivesPage';
import MessagesPage from './pages/MessagesPage';
import SettingsPage from './pages/SettingsPage';
import './App.css';

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

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
      <BrowserRouter>
        <Routes>
          <Route path="*" element={<LoginPage onLogin={handleLogin} />} />
        </Routes>
      </BrowserRouter>
    );
  }

  return (
    <BrowserRouter>
      <AppLayout user={user} onLogout={handleLogout}>
        <Routes>
          <Route path="/dashboard" element={<DashboardPage user={user} />} />
          <Route path="/courses" element={<CoursesPage user={user} />} />
          <Route path="/courses/:courseId" element={<CourseDetailPage user={user} />} />
          <Route path="/cohorts" element={<CohortsPage user={user} />} />
          <Route path="/community" element={<CommunityPage user={user} />} />
          <Route path="/archives" element={<ArchivesPage user={user} />} />
          <Route path="/messages" element={<MessagesPage user={user} />} />
          <Route path="/settings" element={<SettingsPage user={user} />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </AppLayout>
    </BrowserRouter>
  );
}

export default App;
