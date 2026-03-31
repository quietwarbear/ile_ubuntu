import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { UserCircle, Shield } from '@phosphor-icons/react';
import { apiGet, apiPut } from '../lib/api';

export default function SettingsPage({ user }) {
  const [users, setUsers] = useState([]);
  const [loaded, setLoaded] = useState(false);

  const isAdmin = ['admin', 'elder'].includes(user?.role);

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
