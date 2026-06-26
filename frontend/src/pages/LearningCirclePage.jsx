import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import {
  HandHeart, Plus, Check, Trash, ChatCircle, Target, NotePencil, CaretDown, CaretUp,
} from '@phosphor-icons/react';
import { useNavigate } from 'react-router-dom';
import { apiGet, apiPost, apiPut, apiDelete } from '../lib/api';

const Avatar = ({ person, size = 'w-7 h-7' }) => (
  <img
    src={person?.picture || `https://ui-avatars.com/api/?name=${encodeURIComponent(person?.name || '?')}&background=0F172A&color=D4AF37`}
    alt=""
    className={`${size} rounded-full flex-shrink-0`}
  />
);

// Reciprocal: a circle has two co-learners, neither above the other. "other"
// is simply whichever co-learner isn't me.
function CircleCard({ circle, currentUserId, onEnded }) {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [detail, setDetail] = useState(null);
  const [goalInput, setGoalInput] = useState('');
  const [noteInput, setNoteInput] = useState('');
  const [busy, setBusy] = useState(false);

  const other = circle.co_learner_a?.id === currentUserId ? circle.co_learner_b : circle.co_learner_a;

  const loadDetail = useCallback(() => {
    apiGet(`/api/learning-circles/${circle.id}`).then(setDetail).catch(console.error);
  }, [circle.id]);

  useEffect(() => { if (open && !detail) loadDetail(); }, [open, detail, loadDetail]);

  const addGoal = async () => {
    if (!goalInput.trim()) return;
    setBusy(true);
    try { await apiPost(`/api/learning-circles/${circle.id}/goals`, { text: goalInput }); setGoalInput(''); loadDetail(); }
    catch (e) { alert(e.message); }
    setBusy(false);
  };

  const toggleGoal = async (goalId) => {
    try { await apiPut(`/api/learning-circles/${circle.id}/goals/${goalId}/toggle`, {}); loadDetail(); }
    catch (e) { alert(e.message); }
  };

  const addNote = async () => {
    if (!noteInput.trim()) return;
    setBusy(true);
    try { await apiPost(`/api/learning-circles/${circle.id}/notes`, { text: noteInput }); setNoteInput(''); loadDetail(); }
    catch (e) { alert(e.message); }
    setBusy(false);
  };

  return (
    <Card className="bg-[#0F172A] border-[#1E293B]" data-testid={`circle-${circle.id}`}>
      <CardHeader className="pb-2 cursor-pointer" onClick={() => setOpen(o => !o)}>
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm text-[#F8FAFC] flex items-center gap-2" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
            <Avatar person={other} />
            <span>
              {other?.name}
              <span className="text-[10px] text-[#94A3B8] ml-2">your co-learner</span>
            </span>
          </CardTitle>
          {open ? <CaretUp size={14} className="text-[#94A3B8]" /> : <CaretDown size={14} className="text-[#94A3B8]" />}
        </div>
      </CardHeader>
      {open && (
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <button
              onClick={() => navigate('/messages')}
              className="flex items-center gap-1 text-xs text-[#D4AF37] hover:underline"
            >
              <ChatCircle size={13} /> Message {other?.name?.split(' ')[0]}
            </button>
          </div>

          {/* Shared goals */}
          <div>
            <p className="text-[10px] tracking-[0.15em] uppercase text-[#D4AF37] mb-2 flex items-center gap-1">
              <Target size={12} /> Our goals
            </p>
            <div className="space-y-1.5 mb-2">
              {(detail?.goals || []).map(g => (
                <button
                  key={g.id}
                  onClick={() => toggleGoal(g.id)}
                  className="w-full flex items-center gap-2 p-2 rounded bg-[#050814] border border-[#1E293B] text-left hover:border-[#D4AF37]/25 transition-colors"
                  data-testid={`goal-${g.id}`}
                >
                  <span className={`w-4 h-4 rounded border flex items-center justify-center flex-shrink-0 ${
                    g.done ? 'bg-emerald-500/20 border-emerald-500/50' : 'border-[#334155]'
                  }`}>
                    {g.done && <Check size={11} className="text-emerald-400" />}
                  </span>
                  <span className={`text-xs ${g.done ? 'text-[#475569] line-through' : 'text-[#F8FAFC]'}`}>{g.text}</span>
                </button>
              ))}
              {detail && detail.goals.length === 0 && (
                <p className="text-xs text-[#475569]">No goals yet — set the first one together.</p>
              )}
            </div>
            <div className="flex gap-2">
              <input
                value={goalInput}
                onChange={e => setGoalInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && addGoal()}
                placeholder="A goal we're walking toward…"
                className="flex-1 px-3 py-1.5 rounded bg-[#050814] border border-[#1E293B] text-xs text-[#F8FAFC] placeholder-[#475569] focus:outline-none focus:border-[#D4AF37]/50"
              />
              <Button size="sm" onClick={addGoal} disabled={busy} className="bg-[#D4AF37]/15 text-[#D4AF37] border border-[#D4AF37]/30 hover:bg-[#D4AF37]/25 h-8">
                <Plus size={13} />
              </Button>
            </div>
          </div>

          {/* Shared journal */}
          <div>
            <p className="text-[10px] tracking-[0.15em] uppercase text-[#D4AF37] mb-2 flex items-center gap-1">
              <NotePencil size={12} /> Our journal
              <span className="text-[#475569] normal-case tracking-normal ml-1">(shared with your facilitator)</span>
            </p>
            <div className="flex gap-2 mb-2">
              <input
                value={noteInput}
                onChange={e => setNoteInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && addNote()}
                placeholder="A reflection from this week…"
                className="flex-1 px-3 py-1.5 rounded bg-[#050814] border border-[#1E293B] text-xs text-[#F8FAFC] placeholder-[#475569] focus:outline-none focus:border-[#D4AF37]/50"
              />
              <Button size="sm" onClick={addNote} disabled={busy} className="bg-[#D4AF37]/15 text-[#D4AF37] border border-[#D4AF37]/30 hover:bg-[#D4AF37]/25 h-8">
                <Plus size={13} />
              </Button>
            </div>
            <div className="space-y-1.5 max-h-56 overflow-y-auto">
              {(detail?.notes || []).map(n => (
                <div key={n.id} className="p-2 rounded bg-[#050814] border border-[#1E293B]">
                  <p className="text-xs text-[#F8FAFC]">{n.text}</p>
                  <p className="text-[9px] text-[#475569] mt-1">
                    {n.author_name} · {new Date(n.created_at).toLocaleDateString()}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </CardContent>
      )}
    </Card>
  );
}

export default function LearningCirclePage({ user }) {
  const [data, setData] = useState(null);
  const [users, setUsers] = useState([]);
  const [aId, setAId] = useState('');
  const [bId, setBId] = useState('');
  const [message, setMessage] = useState(null);
  const [busy, setBusy] = useState(false);

  const isFaculty = ['faculty', 'elder', 'admin'].includes(user?.role);

  const load = useCallback(() => {
    apiGet('/api/learning-circles').then(setData).catch(e => setMessage({ type: 'error', text: e.message }));
    if (isFaculty) apiGet('/api/auth/users').then(setUsers).catch(() => {});
  }, [isFaculty]);

  useEffect(() => { load(); }, [load]);

  const handleForm = async () => {
    setBusy(true);
    try {
      const res = await apiPost('/api/learning-circles/form', { co_learner_a_id: aId, co_learner_b_id: bId });
      setMessage({ type: 'success', text: `${res.co_learner_a.name} and ${res.co_learner_b.name} are now walking together.` });
      setAId(''); setBId('');
      load();
    } catch (e) { setMessage({ type: 'error', text: e.message }); }
    setBusy(false);
  };

  const handleEnd = async (circleId) => {
    if (!window.confirm('Close this learning circle? Goals and journal entries are kept.')) return;
    try { await apiDelete(`/api/learning-circles/${circleId}`); load(); }
    catch (e) { setMessage({ type: 'error', text: e.message }); }
  };

  const selectCls = "flex-1 px-3 py-2 rounded-md bg-[#050814] border border-[#1E293B] text-xs text-[#F8FAFC] focus:outline-none focus:border-[#D4AF37]/50";

  return (
    <div className="space-y-6 animate-fade-in-up max-w-3xl" data-testid="learning-circle-page">
      <div>
        <div className="flex items-center gap-2 mb-1">
          <HandHeart size={20} weight="duotone" className="text-[#D4AF37]" />
          <h1 className="text-xl text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>Learning Circles</h1>
        </div>
        <p className="text-xs text-[#94A3B8]">Wisdom flows in every direction — co-learners walking together, one circle at a time.</p>
      </div>

      {message && (
        <div className={`p-3 rounded-md text-sm ${
          message.type === 'success'
            ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-400'
            : 'bg-red-500/10 border border-red-500/30 text-red-400'
        }`}>
          {message.text}
        </div>
      )}

      {/* My circles */}
      {data?.mine?.length > 0 ? (
        <div className="space-y-3">
          {data.mine.map(c => (
            <CircleCard key={c.id} circle={c} currentUserId={user?.id} onEnded={load} />
          ))}
        </div>
      ) : (
        <Card className="bg-[#0F172A] border-[#1E293B]">
          <CardContent className="p-6 text-center">
            <p className="text-sm text-[#94A3B8]">
              No learning circles yet. Circles are formed by your facilitators —
              {user?.intent === 'mentor'
                ? " they know you're here to walk with others, and they'll reach out."
                : ' let them know if you\'d like a co-learner to walk with.'}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Faculty: form + manage circles */}
      {isFaculty && (
        <Card className="bg-[#0F172A] border-[#1E293B]">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
              Form a learning circle
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col sm:flex-row gap-2 mb-2">
              <select value={aId} onChange={e => setAId(e.target.value)} className={selectCls} data-testid="co-learner-a-select">
                <option value="">A co-learner…</option>
                {users.map(u => (
                  <option key={u.id} value={u.id}>{u.name}{u.is_minor ? ' · youth' : ''} ({u.intent || u.role})</option>
                ))}
              </select>
              <select value={bId} onChange={e => setBId(e.target.value)} className={selectCls} data-testid="co-learner-b-select">
                <option value="">Another co-learner…</option>
                {users.map(u => (
                  <option key={u.id} value={u.id}>{u.name}{u.is_minor ? ' · youth' : ''} ({u.intent || u.role})</option>
                ))}
              </select>
              <Button onClick={handleForm} disabled={busy || !aId || !bId} className="bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB]">
                Form
              </Button>
            </div>
            <p className="text-[10px] text-[#475569] mb-3">
              Forming a circle opens a direct message channel between them — including for youth — so pair with care.
            </p>
            {data?.all?.length > 0 && (
              <div className="space-y-1.5">
                <p className="text-[10px] tracking-[0.15em] uppercase text-[#D4AF37]">All circles</p>
                {data.all.map(c => (
                  <div key={c.id} className="flex items-center gap-2 p-2 rounded bg-[#050814] border border-[#1E293B]">
                    <Avatar person={c.co_learner_a} size="w-5 h-5" />
                    <span className="text-xs text-[#F8FAFC]">{c.co_learner_a?.name}</span>
                    <span className="text-[10px] text-[#475569]">walks with</span>
                    <Avatar person={c.co_learner_b} size="w-5 h-5" />
                    <span className="text-xs text-[#F8FAFC] flex-1">{c.co_learner_b?.name}</span>
                    <button onClick={() => handleEnd(c.id)} className="text-[#475569] hover:text-red-400" title="Close circle">
                      <Trash size={13} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
