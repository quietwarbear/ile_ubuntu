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
    <Card className="bg-[rgb(var(--ink-card))] border-[rgb(var(--ink-border))]" data-testid={`circle-${circle.id}`}>
      <CardHeader className="pb-2 cursor-pointer" onClick={() => setOpen(o => !o)}>
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm text-[rgb(var(--text-main))] flex items-center gap-2" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
            <Avatar person={other} />
            <span>
              {other?.name}
              <span className="text-[10px] text-[rgb(var(--text-muted))] ml-2">your co-learner</span>
            </span>
          </CardTitle>
          {open ? <CaretUp size={14} className="text-[rgb(var(--text-muted))]" /> : <CaretDown size={14} className="text-[rgb(var(--text-muted))]" />}
        </div>
      </CardHeader>
      {open && (
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <button
              onClick={() => navigate('/messages')}
              className="flex items-center gap-1 text-xs text-[rgb(var(--gold))] hover:underline"
            >
              <ChatCircle size={13} /> Message {other?.name?.split(' ')[0]}
            </button>
          </div>

          {/* Shared goals */}
          <div>
            <p className="text-[10px] tracking-[0.15em] uppercase text-[rgb(var(--gold))] mb-2 flex items-center gap-1">
              <Target size={12} /> Our goals
            </p>
            <div className="space-y-1.5 mb-2">
              {(detail?.goals || []).map(g => (
                <button
                  key={g.id}
                  onClick={() => toggleGoal(g.id)}
                  className="w-full flex items-center gap-2 p-2 rounded bg-[rgb(var(--ink-deep))] border border-[rgb(var(--ink-border))] text-left hover:border-[rgb(var(--gold)/0.25)] transition-colors"
                  data-testid={`goal-${g.id}`}
                >
                  <span className={`w-4 h-4 rounded border flex items-center justify-center flex-shrink-0 ${
                    g.done ? 'bg-emerald-500/20 border-emerald-500/50' : 'border-[rgb(var(--ink-border-strong))]'
                  }`}>
                    {g.done && <Check size={11} className="text-emerald-400" />}
                  </span>
                  <span className={`text-xs ${g.done ? 'text-[rgb(var(--text-faint))] line-through' : 'text-[rgb(var(--text-main))]'}`}>{g.text}</span>
                </button>
              ))}
              {detail && detail.goals.length === 0 && (
                <p className="text-xs text-[rgb(var(--text-faint))]">No goals yet — set the first one together.</p>
              )}
            </div>
            <div className="flex gap-2">
              <input
                value={goalInput}
                onChange={e => setGoalInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && addGoal()}
                placeholder="A goal we're walking toward…"
                className="flex-1 px-3 py-1.5 rounded bg-[rgb(var(--ink-deep))] border border-[rgb(var(--ink-border))] text-xs text-[rgb(var(--text-main))] placeholder-[rgb(var(--text-faint))] focus:outline-none focus:border-[rgb(var(--gold)/0.5)]"
              />
              <Button size="sm" onClick={addGoal} disabled={busy} className="bg-[rgb(var(--gold)/0.15)] text-[rgb(var(--gold))] border border-[rgb(var(--gold)/0.3)] hover:bg-[rgb(var(--gold)/0.25)] h-8">
                <Plus size={13} />
              </Button>
            </div>
          </div>

          {/* Shared journal */}
          <div>
            <p className="text-[10px] tracking-[0.15em] uppercase text-[rgb(var(--gold))] mb-2 flex items-center gap-1">
              <NotePencil size={12} /> Our journal
              <span className="text-[rgb(var(--text-faint))] normal-case tracking-normal ml-1">(shared with your facilitator)</span>
            </p>
            <div className="flex gap-2 mb-2">
              <input
                value={noteInput}
                onChange={e => setNoteInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && addNote()}
                placeholder="A reflection from this week…"
                className="flex-1 px-3 py-1.5 rounded bg-[rgb(var(--ink-deep))] border border-[rgb(var(--ink-border))] text-xs text-[rgb(var(--text-main))] placeholder-[rgb(var(--text-faint))] focus:outline-none focus:border-[rgb(var(--gold)/0.5)]"
              />
              <Button size="sm" onClick={addNote} disabled={busy} className="bg-[rgb(var(--gold)/0.15)] text-[rgb(var(--gold))] border border-[rgb(var(--gold)/0.3)] hover:bg-[rgb(var(--gold)/0.25)] h-8">
                <Plus size={13} />
              </Button>
            </div>
            <div className="space-y-1.5 max-h-56 overflow-y-auto">
              {(detail?.notes || []).map(n => (
                <div key={n.id} className="p-2 rounded bg-[rgb(var(--ink-deep))] border border-[rgb(var(--ink-border))]">
                  <p className="text-xs text-[rgb(var(--text-main))]">{n.text}</p>
                  <p className="text-[9px] text-[rgb(var(--text-faint))] mt-1">
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

  const selectCls = "flex-1 px-3 py-2 rounded-md bg-[rgb(var(--ink-deep))] border border-[rgb(var(--ink-border))] text-xs text-[rgb(var(--text-main))] focus:outline-none focus:border-[rgb(var(--gold)/0.5)]";

  return (
    <div className="space-y-6 animate-fade-in-up max-w-3xl" data-testid="learning-circle-page">
      <div>
        <div className="flex items-center gap-2 mb-1">
          <HandHeart size={20} weight="duotone" className="text-[rgb(var(--gold))]" />
          <h1 className="text-xl text-[rgb(var(--text-main))]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>Learning Circles</h1>
        </div>
        <p className="text-xs text-[rgb(var(--text-muted))]">Wisdom flows in every direction — co-learners walking together, one circle at a time.</p>
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
        <Card className="bg-[rgb(var(--ink-card))] border-[rgb(var(--ink-border))]">
          <CardContent className="p-6 text-center">
            <p className="text-sm text-[rgb(var(--text-muted))]">
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
        <Card className="bg-[rgb(var(--ink-card))] border-[rgb(var(--ink-border))]">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-[rgb(var(--text-main))]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
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
              <Button onClick={handleForm} disabled={busy || !aId || !bId} className="bg-[rgb(var(--gold))] text-[rgb(var(--ink-deep))] hover:bg-[rgb(var(--gold-soft))]">
                Form
              </Button>
            </div>
            <p className="text-[10px] text-[rgb(var(--text-faint))] mb-3">
              Forming a circle opens a direct message channel between them — including for youth — so pair with care.
            </p>
            {data?.all?.length > 0 && (
              <div className="space-y-1.5">
                <p className="text-[10px] tracking-[0.15em] uppercase text-[rgb(var(--gold))]">All circles</p>
                {data.all.map(c => (
                  <div key={c.id} className="flex items-center gap-2 p-2 rounded bg-[rgb(var(--ink-deep))] border border-[rgb(var(--ink-border))]">
                    <Avatar person={c.co_learner_a} size="w-5 h-5" />
                    <span className="text-xs text-[rgb(var(--text-main))]">{c.co_learner_a?.name}</span>
                    <span className="text-[10px] text-[rgb(var(--text-faint))]">walks with</span>
                    <Avatar person={c.co_learner_b} size="w-5 h-5" />
                    <span className="text-xs text-[rgb(var(--text-main))] flex-1">{c.co_learner_b?.name}</span>
                    <button onClick={() => handleEnd(c.id)} className="text-[rgb(var(--text-faint))] hover:text-red-400" title="Close circle">
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
