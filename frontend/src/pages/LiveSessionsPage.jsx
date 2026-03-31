import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Badge } from '../components/ui/badge';
import {
  VideoCameraSlash,
  VideoCamera,
  Plus,
  Play,
  Stop,
  Trash,
  Users,
  Calendar,
  Circle,
} from '@phosphor-icons/react';
import { apiGet, apiPost, apiPut, apiDelete, parseTierError } from '../lib/api';
import UpgradePrompt from '../components/UpgradePrompt';

export default function LiveSessionsPage({ user }) {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState([]);
  const [courses, setCourses] = useState([]);
  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState({ title: '', description: '', course_id: '', scheduled_at: '' });
  const [activeFilter, setActiveFilter] = useState('all');

  const isFaculty = ['faculty', 'elder', 'admin'].includes(user?.role);

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      const [sessionsData, coursesData] = await Promise.all([
        apiGet('/api/live-sessions'),
        isFaculty ? apiGet('/api/courses') : Promise.resolve([]),
      ]);
      setSessions(sessionsData);
      setCourses(coursesData);
    } catch (e) { console.error(e); }
  };

  const handleCreate = async () => {
    try {
      await apiPost('/api/live-sessions', {
        title: form.title,
        description: form.description,
        course_id: form.course_id || undefined,
        scheduled_at: form.scheduled_at || undefined,
      });
      setForm({ title: '', description: '', course_id: '', scheduled_at: '' });
      setCreateOpen(false);
      loadData();
    } catch (e) { alert(e.message); }
  };

  const handleStart = async (id) => {
    try {
      const result = await apiPut(`/api/live-sessions/${id}/start`, {});
      if (result.success) {
        navigate(`/live/${id}`);
      }
    } catch (e) { alert(e.message); }
  };

  const handleEnd = async (id, e) => {
    e.stopPropagation();
    if (!window.confirm('End this live session?')) return;
    try { await apiPut(`/api/live-sessions/${id}/end`, {}); loadData(); }
    catch (e) { alert(e.message); }
  };

  const handleDelete = async (id, e) => {
    e.stopPropagation();
    if (!window.confirm('Delete this session?')) return;
    try { await apiDelete(`/api/live-sessions/${id}`); loadData(); }
    catch (e) { alert(e.message); }
  };

  const [upgradePrompt, setUpgradePrompt] = useState(null);

  const handleJoin = async (id) => {
    try {
      await apiPost(`/api/live-sessions/${id}/join`, {});
      navigate(`/live/${id}`);
    } catch (e) {
      const tierErr = parseTierError(e.message);
      if (tierErr) setUpgradePrompt({ feature: 'live_session', requiredTier: 'elder_circle' });
      else alert(e.message);
    }
  };

  const filteredSessions = sessions.filter(s => {
    if (activeFilter === 'all') return true;
    return s.status === activeFilter;
  });

  const statusConfig = {
    scheduled: { color: 'bg-blue-500/10 text-blue-400 border-blue-500/20', label: 'Scheduled' },
    live: { color: 'bg-red-500/10 text-red-400 border-red-500/20', label: 'Live Now' },
    ended: { color: 'bg-[#94A3B8]/10 text-[#94A3B8] border-[#94A3B8]/20', label: 'Ended' },
  };

  return (
    <div className="space-y-6 animate-fade-in-up" data-testid="live-sessions-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-light text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
            Live Teaching
          </h1>
          <p className="text-sm text-[#94A3B8]">Real-time sessions and virtual classrooms</p>
        </div>
        {isFaculty && (
          <Dialog open={createOpen} onOpenChange={setCreateOpen}>
            <DialogTrigger asChild>
              <Button className="bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB]" data-testid="create-session-btn">
                <Plus size={16} weight="bold" className="mr-1.5" /> New Session
              </Button>
            </DialogTrigger>
            <DialogContent className="bg-[#0F172A] border-[#1E293B]">
              <DialogHeader>
                <DialogTitle className="text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>Schedule Live Session</DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <Input
                  placeholder="Session Title"
                  value={form.title}
                  onChange={e => setForm({ ...form, title: e.target.value })}
                  className="bg-[#050814] border-[#1E293B] text-[#F8FAFC]"
                  data-testid="session-title-input"
                />
                <Textarea
                  placeholder="Description (optional)"
                  value={form.description}
                  onChange={e => setForm({ ...form, description: e.target.value })}
                  className="bg-[#050814] border-[#1E293B] text-[#F8FAFC]"
                  data-testid="session-desc-input"
                />
                {courses.length > 0 && (
                  <select
                    value={form.course_id}
                    onChange={e => setForm({ ...form, course_id: e.target.value })}
                    className="w-full p-2 rounded-md bg-[#050814] border border-[#1E293B] text-[#F8FAFC] text-sm"
                    data-testid="session-course-select"
                  >
                    <option value="">No linked course</option>
                    {courses.map(c => <option key={c.id} value={c.id}>{c.title}</option>)}
                  </select>
                )}
                <div>
                  <label className="text-xs text-[#94A3B8] mb-1 block">Schedule for (optional)</label>
                  <Input
                    type="datetime-local"
                    value={form.scheduled_at}
                    onChange={e => setForm({ ...form, scheduled_at: e.target.value })}
                    className="bg-[#050814] border-[#1E293B] text-[#F8FAFC]"
                    data-testid="session-schedule-input"
                  />
                </div>
                <Button
                  onClick={handleCreate}
                  className="w-full bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB]"
                  data-testid="submit-session-btn"
                >
                  Schedule Session
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        )}
      </div>

      {/* Filters */}
      <div className="flex gap-1 p-1 bg-[#0F172A] border border-[#1E293B] rounded-md w-fit">
        {[
          { key: 'all', label: 'All' },
          { key: 'live', label: 'Live Now' },
          { key: 'scheduled', label: 'Upcoming' },
          { key: 'ended', label: 'Past' },
        ].map(f => (
          <button
            key={f.key}
            onClick={() => setActiveFilter(f.key)}
            className={`px-4 py-2 text-xs font-medium rounded transition-all ${
              activeFilter === f.key ? 'bg-[#D4AF37] text-[#050814]' : 'text-[#94A3B8] hover:text-[#F8FAFC]'
            }`}
            data-testid={`filter-${f.key}`}
          >
            {f.key === 'live' && <Circle size={8} weight="fill" className="inline mr-1 text-red-400" />}
            {f.label}
          </button>
        ))}
      </div>

      {/* Sessions List */}
      {filteredSessions.length === 0 ? (
        <Card className="bg-[#0F172A] border-[#1E293B]">
          <CardContent className="p-10 text-center">
            <VideoCamera size={48} weight="duotone" className="text-[#D4AF37] mx-auto mb-4" />
            <h3 className="text-lg text-[#F8FAFC] mb-2" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
              {activeFilter === 'live' ? 'No live sessions right now' : 'No sessions found'}
            </h3>
            <p className="text-sm text-[#94A3B8]">
              {isFaculty ? 'Schedule a session to start teaching live.' : 'Check back later for upcoming sessions.'}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {filteredSessions.map(session => {
            const isHost = session.host_id === user?.id;
            const config = statusConfig[session.status] || statusConfig.scheduled;

            return (
              <Card
                key={session.id}
                className={`bg-[#0F172A] border-[#1E293B] transition-all ${
                  session.status === 'live' ? 'border-l-2 border-l-red-500 hover:border-red-500/50' : 'hover:border-[#D4AF37]/30'
                }`}
                data-testid={`session-card-${session.id}`}
              >
                <CardContent className="p-5">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        {session.status === 'live' && (
                          <span className="flex items-center gap-1">
                            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                          </span>
                        )}
                        <h3
                          className="text-base text-[#F8FAFC]"
                          style={{ fontFamily: 'Cormorant Garamond, serif' }}
                        >
                          {session.title}
                        </h3>
                        <Badge className={`text-[10px] ${config.color}`}>{config.label}</Badge>
                      </div>

                      {session.description && (
                        <p className="text-xs text-[#94A3B8] mb-2">{session.description}</p>
                      )}

                      <div className="flex items-center gap-4 text-xs text-[#94A3B8]">
                        <span className="flex items-center gap-1">
                          <img src={session.host_picture || `https://ui-avatars.com/api/?name=${session.host_name}&background=0F172A&color=D4AF37&size=16`} alt="" className="w-4 h-4 rounded-full" />
                          {session.host_name}
                        </span>
                        {session.course_title && (
                          <span className="flex items-center gap-1 text-[#D4AF37]">
                            {session.course_title}
                          </span>
                        )}
                        <span className="flex items-center gap-1">
                          <Users size={12} /> {session.participants?.length || 0}
                        </span>
                        {session.scheduled_at && (
                          <span className="flex items-center gap-1">
                            <Calendar size={12} /> {new Date(session.scheduled_at).toLocaleString()}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2 flex-shrink-0">
                      {session.status === 'scheduled' && isHost && (
                        <Button
                          size="sm"
                          onClick={() => handleStart(session.id)}
                          className="bg-red-500 text-white hover:bg-red-600 text-xs"
                          data-testid={`start-session-${session.id}`}
                        >
                          <Play size={14} weight="fill" className="mr-1" /> Go Live
                        </Button>
                      )}
                      {session.status === 'live' && !isHost && (
                        <Button
                          size="sm"
                          onClick={() => handleJoin(session.id)}
                          className="bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB] text-xs"
                          data-testid={`join-session-${session.id}`}
                        >
                          <VideoCamera size={14} weight="duotone" className="mr-1" /> Join
                        </Button>
                      )}
                      {session.status === 'live' && isHost && (
                        <>
                          <Button
                            size="sm"
                            onClick={() => navigate(`/live/${session.id}`)}
                            className="bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB] text-xs"
                            data-testid={`rejoin-session-${session.id}`}
                          >
                            <VideoCamera size={14} className="mr-1" /> Rejoin
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={(e) => handleEnd(session.id, e)}
                            className="text-red-400 hover:text-red-300 text-xs"
                            data-testid={`end-session-${session.id}`}
                          >
                            <Stop size={14} className="mr-1" /> End
                          </Button>
                        </>
                      )}
                      {(session.status === 'scheduled' || session.status === 'ended') && isHost && (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={(e) => handleDelete(session.id, e)}
                          className="text-red-400 hover:text-red-300 h-8 w-8 p-0"
                          data-testid={`delete-session-${session.id}`}
                        >
                          <Trash size={14} />
                        </Button>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {upgradePrompt && (
        <UpgradePrompt
          feature={upgradePrompt.feature}
          requiredTier={upgradePrompt.requiredTier}
          onClose={() => setUpgradePrompt(null)}
        />
      )}
    </div>
  );
}