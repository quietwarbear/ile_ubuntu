import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import {
  Shield,
  GoogleLogo,
  CheckCircle,
  LinkBreak,
  Plugs,
  Bell,
  BellSlash,
} from '@phosphor-icons/react';
import { apiGet, apiPut, apiPost, apiDelete } from '../lib/api';

export default function SettingsPage({ user }) {
  const [users, setUsers] = useState([]);
  const [loaded, setLoaded] = useState(false);
  const [googleConnected, setGoogleConnected] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(true);
  const [pushEnabled, setPushEnabled] = useState(false);
  const [pushLoading, setPushLoading] = useState(false);
  const [pushSupported] = useState('serviceWorker' in navigator && 'PushManager' in window);
  const [searchParams] = useSearchParams();

  const isAdmin = ['admin', 'elder'].includes(user?.role);
  const isFaculty = ['faculty', 'elder', 'admin'].includes(user?.role);

  useEffect(() => {
    checkGoogleStatus();
    checkPushStatus();
    if (searchParams.get('google_connected') === 'true') {
      setGoogleConnected(true);
    }
  }, [searchParams]); // eslint-disable-line -- mount-only init with searchParams trigger

  const checkPushStatus = async () => {
    if (!pushSupported) return;
    try {
      const data = await apiGet('/api/push/status');
      setPushEnabled(data.subscribed);
    } catch (e) { console.error(e); }
  };

  const handleTogglePush = async () => {
    setPushLoading(true);
    try {
      if (pushEnabled) {
        await apiDelete('/api/push/subscribe');
        setPushEnabled(false);
      } else {
        const permission = await Notification.requestPermission();
        if (permission !== 'granted') {
          alert('Notification permission denied. Please enable notifications in your browser settings.');
          setPushLoading(false);
          return;
        }
        const reg = await navigator.serviceWorker.ready;
        const vapidRes = await apiGet('/api/push/vapid-key');
        if (!vapidRes.public_key) {
          alert('Push notifications are not configured on the server yet.');
          setPushLoading(false);
          return;
        }
        const subscription = await reg.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(vapidRes.public_key),
        });
        await apiPost('/api/push/subscribe', { subscription: subscription.toJSON() });
        setPushEnabled(true);
      }
    } catch (e) { console.error('Push toggle error:', e); }
    finally { setPushLoading(false); }
  };

  function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    const rawData = window.atob(base64);
    return Uint8Array.from([...rawData].map(c => c.charCodeAt(0)));
  }

  const checkGoogleStatus = async () => {
    try {
      const data = await apiGet('/api/google/status');
      setGoogleConnected(data.connected);
    } catch (e) { console.error(e); }
    finally { setGoogleLoading(false); }
  };

  const handleConnectGoogle = async () => {
    try {
      const data = await apiGet('/api/google/auth-url');
      const isNativePlatform = window.Capacitor && typeof window.Capacitor.isNativePlatform === 'function' && window.Capacitor.isNativePlatform();
      if (isNativePlatform) {
        const { Browser } = await import('@capacitor/browser');
        await Browser.open({ url: data.auth_url, presentationStyle: 'fullscreen' });
      } else {
        window.location.href = data.auth_url;
      }
    } catch (e) { alert(e.message); }
  };

  const handleDisconnectGoogle = async () => {
    if (!window.confirm('Disconnect your Google account?')) return;
    try {
      await apiDelete('/api/google/disconnect');
      setGoogleConnected(false);
    } catch (e) { alert(e.message); }
  };

  const loadUsers = async () => {
    try {
      setUsers(await apiGet('/api/auth/users'));
      setLoaded(true);
    } catch (e) { console.error(e); }
  };

  const changeRole = async (userId, role) => {
    try {
      await apiPut(`/api/auth/users/${userId}/role`, { role });
      loadUsers();
    } catch (e) { alert(e.message); }
  };

  const roleColor = (role) => {
    const colors = {
      admin: 'bg-red-500/10 text-red-400 border-red-500/20',
      elder: 'bg-[#D4AF37]/10 text-[#D4AF37] border-[#D4AF37]/20',
      faculty: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
      assistant: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
      student: 'bg-[#94A3B8]/10 text-[#94A3B8] border-[#94A3B8]/20',
    };
    return colors[role] || colors.student;
  };

  return (
    <div className="space-y-6 animate-fade-in-up" data-testid="settings-page">
      <div>
        <h1 className="text-3xl font-light text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>Settings</h1>
        <p className="text-sm text-[#94A3B8]">Profile and platform management</p>
      </div>

      {/* Profile Card */}
      <Card className="bg-[#0F172A] border-[#1E293B]">
        <CardHeader>
          <CardTitle className="text-lg text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
            Your Profile
          </CardTitle>
        </CardHeader>
        <CardContent className="flex items-center gap-4">
          <img src={user?.picture} alt={user?.name} className="w-14 h-14 rounded-full border-2 border-[#D4AF37]/30" />
          <div>
            <p className="text-lg text-[#F8FAFC]">{user?.name}</p>
            <p className="text-sm text-[#94A3B8]">{user?.email}</p>
            <Badge className={`mt-1 text-[10px] ${roleColor(user?.role)}`}>{user?.role}</Badge>
          </div>
        </CardContent>
      </Card>

      {/* Push Notifications */}
      <Card className="bg-[#0F172A] border-[#1E293B]" data-testid="push-notification-card">
        <CardHeader>
          <CardTitle className="text-lg text-[#F8FAFC] flex items-center gap-2" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
            <Bell size={20} weight="duotone" className="text-[#D4AF37]" />
            Push Notifications
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-[#94A3B8] mb-4">
            Get notified about new enrollments, cohort updates, and community activity.
          </p>
          {!pushSupported ? (
            <p className="text-xs text-[#475569]">Push notifications are not supported in this browser.</p>
          ) : (
            <div className="flex items-center justify-between p-3 bg-[#050814] border border-[#1E293B] rounded-md">
              <div className="flex items-center gap-2">
                {pushEnabled ? (
                  <Bell size={18} weight="fill" className="text-emerald-400" />
                ) : (
                  <BellSlash size={18} weight="duotone" className="text-[#94A3B8]" />
                )}
                <span className={`text-sm ${pushEnabled ? 'text-emerald-400' : 'text-[#94A3B8]'}`}>
                  {pushEnabled ? 'Notifications enabled' : 'Notifications disabled'}
                </span>
              </div>
              <Button
                size="sm"
                onClick={handleTogglePush}
                disabled={pushLoading}
                className={pushEnabled
                  ? 'bg-red-500/10 text-red-400 border border-red-500/20 hover:bg-red-500/20 text-xs'
                  : 'bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB] text-xs'}
                data-testid="toggle-push-btn"
              >
                {pushLoading ? 'Processing...' : pushEnabled ? 'Disable' : 'Enable'}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Google Account Connection (Faculty+) */}
      {isFaculty && (
        <Card className="bg-[#0F172A] border-[#1E293B]" data-testid="google-connection-card">
          <CardHeader>
            <CardTitle className="text-lg text-[#F8FAFC] flex items-center gap-2" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
              <Plugs size={20} weight="duotone" className="text-[#D4AF37]" />
              Google Integration
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-[#94A3B8] mb-4">
              Connect your Google account to import Slides and Docs directly into your courses.
            </p>
            {googleLoading ? (
              <div className="flex items-center gap-2 text-sm text-[#94A3B8]">
                <span className="w-4 h-4 border border-[#D4AF37] border-t-transparent rounded-full animate-spin" />
                Checking connection...
              </div>
            ) : googleConnected ? (
              <div className="flex items-center justify-between p-3 bg-[#050814] border border-emerald-500/20 rounded-md">
                <div className="flex items-center gap-2">
                  <CheckCircle size={18} weight="fill" className="text-emerald-400" />
                  <span className="text-sm text-emerald-400">Google account connected</span>
                </div>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={handleDisconnectGoogle}
                  className="text-red-400 hover:text-red-300 text-xs"
                  data-testid="disconnect-google-btn"
                >
                  <LinkBreak size={14} className="mr-1" /> Disconnect
                </Button>
              </div>
            ) : (
              <Button
                onClick={handleConnectGoogle}
                className="bg-white text-[#050814] hover:bg-gray-100 font-medium"
                data-testid="connect-google-btn"
              >
                <GoogleLogo size={18} weight="bold" className="mr-2" />
                Connect Google Account
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      {/* Role Management (Admin/Elder only) */}
      {isAdmin && (
        <Card className="bg-[#0F172A] border-[#1E293B]">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-lg text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
              <Shield size={20} weight="duotone" className="inline mr-2 text-[#D4AF37]" />
              Role Management
            </CardTitle>
            {!loaded && (
              <Button size="sm" onClick={loadUsers} className="bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB] text-xs" data-testid="load-users-btn">
                Load Users
              </Button>
            )}
          </CardHeader>
          <CardContent className="space-y-3">
            {loaded && users.map(u => (
              <div key={u.id} className="flex items-center justify-between p-3 bg-[#050814] border border-[#1E293B] rounded-md" data-testid={`user-row-${u.id}`}>
                <div className="flex items-center gap-3">
                  <img src={u.picture} alt={u.name} className="w-8 h-8 rounded-full" />
                  <div>
                    <p className="text-sm text-[#F8FAFC]">{u.name}</p>
                    <p className="text-[10px] text-[#94A3B8]">{u.email}</p>
                  </div>
                </div>
                <select
                  value={u.role}
                  onChange={(e) => changeRole(u.id, e.target.value)}
                  className="px-2 py-1 text-xs bg-[#0F172A] border border-[#1E293B] text-[#F8FAFC] rounded"
                  data-testid={`role-select-${u.id}`}
                >
                  {['student', 'assistant', 'faculty', 'elder', 'admin'].map(r => (
                    <option key={r} value={r}>{r.charAt(0).toUpperCase() + r.slice(1)}</option>
                  ))}
                </select>
              </div>
            ))}
            {loaded && users.length === 0 && <p className="text-sm text-[#94A3B8] text-center py-4">No users found</p>}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
