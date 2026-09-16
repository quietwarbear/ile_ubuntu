import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import {
  TreeEvergreen, Plus, Check, MapPin, CalendarBlank, UsersThree, Target, ArrowLeft,
} from '@phosphor-icons/react';
import { apiGet, apiPost, apiPut } from '../lib/api';

const ROLE_LABELS = {
  youth: 'Young People', educator: 'Educators', mentor: 'Mentors',
  elder: 'Elders', family: 'Family',
};
const ROLE_ORDER = ['elder', 'educator', 'mentor', 'youth', 'family'];

const Avatar = ({ person, size = 'w-7 h-7' }) => (
  <img
    src={person?.picture || `https://ui-avatars.com/api/?name=${encodeURIComponent(person?.name || '?')}&background=0F172A&color=D4AF37`}
    alt=""
    className={`${size} rounded-full flex-shrink-0`}
  />
);

export function VillageDetail({ user }) {
  const { villageId } = useParams();
  const navigate = useNavigate();
  const [v, setV] = useState(null);
  const [error, setError] = useState('');
  const [users, setUsers] = useState([]);
  const [memberId, setMemberId] = useState('');
  const [memberRole, setMemberRole] = useState('youth');
  const [goalInput, setGoalInput] = useState('');
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    apiGet(`/api/villages/${villageId}`).then(setV).catch(e => setError(e.message));
  }, [villageId]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    if (v?.can_steward) apiGet('/api/auth/users').then(setUsers).catch(() => {});
  }, [v?.can_steward]);

  if (error) return <p className="text-sm text-red-400 bg-red-400/10 rounded-md px-4 py-3">{error}</p>;
  if (!v) return <p className="text-sm text-[rgb(var(--text-muted))]">Entering the village…</p>;

  const grouped = ROLE_ORDER.map(r => ({
    role: r,
    people: (v.members || []).filter(m => m.village_role === r),
  })).filter(g => g.people.length > 0);

  const doneGoals = (v.goals || []).filter(g => g.done).length;

  return (
    <div className="space-y-6 animate-fade-in-up max-w-3xl" data-testid="village-detail">
      <button onClick={() => navigate('/villages')} className="flex items-center gap-2 text-sm text-[rgb(var(--text-muted))] hover:text-[rgb(var(--gold))]">
        <ArrowLeft size={16} /> All villages
      </button>

      <div>
        <div className="flex items-center gap-2 mb-1">
          <TreeEvergreen size={22} weight="duotone" className="text-[rgb(var(--gold))]" />
          <h1 className="text-2xl text-[rgb(var(--text-main))]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>{v.name}</h1>
        </div>
        <div className="flex flex-wrap gap-3 text-xs text-[rgb(var(--text-muted))]">
          {v.season && <span className="flex items-center gap-1"><CalendarBlank size={12} /> {v.season}</span>}
          {v.place && <span className="flex items-center gap-1"><MapPin size={12} /> {v.place}</span>}
          <span className="flex items-center gap-1"><UsersThree size={12} /> {(v.members || []).length} members</span>
        </div>
        {v.description && <p className="text-sm text-[rgb(var(--text-muted))] mt-2">{v.description}</p>}
      </div>

      {/* Village goals — collective by definition */}
      <Card className="bg-[rgb(var(--ink-card))] border-[rgb(var(--gold)/0.25)]">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm text-[rgb(var(--text-main))] flex items-center gap-2" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
            <Target size={15} weight="duotone" className="text-[rgb(var(--gold))]" /> Our goals this season
            {v.goals?.length > 0 && (
              <span className="text-[10px] text-[rgb(var(--text-muted))] font-normal">{doneGoals}/{v.goals.length} carried home</span>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-1.5">
          {(v.goals || []).map(g => (
            <button
              key={g.id}
              onClick={() => v.can_steward && apiPut(`/api/villages/${v.id}/goals/${g.id}/toggle`, {}).then(load)}
              disabled={!v.can_steward}
              className="w-full flex items-center gap-2 p-2 rounded bg-[rgb(var(--ink-deep))] border border-[rgb(var(--ink-border))] text-left disabled:cursor-default hover:border-[rgb(var(--gold)/0.25)]"
            >
              <span className={`w-4 h-4 rounded border flex items-center justify-center flex-shrink-0 ${
                g.done ? 'bg-emerald-500/20 border-emerald-500/50' : 'border-[rgb(var(--ink-border-strong))]'
              }`}>
                {g.done && <Check size={11} className="text-emerald-400" />}
              </span>
              <span className={`text-xs ${g.done ? 'text-[rgb(var(--text-faint))] line-through' : 'text-[rgb(var(--text-main))]'}`}>{g.text}</span>
            </button>
          ))}
          {(!v.goals || v.goals.length === 0) && (
            <p className="text-xs text-[rgb(var(--text-faint))]">No goals named yet this season.</p>
          )}
          {v.can_steward && (
            <div className="flex gap-2 pt-1">
              <input
                value={goalInput}
                onChange={e => setGoalInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && goalInput.trim() && apiPost(`/api/villages/${v.id}/goals`, { text: goalInput }).then(() => { setGoalInput(''); load(); })}
                placeholder="A goal the village walks toward together…"
                className="flex-1 px-3 py-1.5 rounded bg-[rgb(var(--ink-deep))] border border-[rgb(var(--ink-border))] text-xs text-[rgb(var(--text-main))] placeholder-[rgb(var(--text-faint))] focus:outline-none focus:border-[rgb(var(--gold)/0.5)]"
              />
              <Button
                size="sm"
                onClick={() => goalInput.trim() && apiPost(`/api/villages/${v.id}/goals`, { text: goalInput }).then(() => { setGoalInput(''); load(); })}
                className="bg-[rgb(var(--gold)/0.15)] text-[rgb(var(--gold))] border border-[rgb(var(--gold)/0.3)] hover:bg-[rgb(var(--gold)/0.25)] h-8"
              >
                <Plus size={13} />
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* The web of relationships */}
      <div className="space-y-3">
        {grouped.map(g => (
          <div key={g.role}>
            <p className="text-[10px] tracking-[0.15em] uppercase text-[rgb(var(--gold))] mb-1.5">{ROLE_LABELS[g.role]}</p>
            <div className="flex flex-wrap gap-2">
              {g.people.map(m => (
                <span key={m.user_id} className="flex items-center gap-1.5 text-xs text-[rgb(var(--text-main))] bg-[rgb(var(--ink-card))] border border-[rgb(var(--ink-border))] rounded-full pl-1 pr-3 py-1">
                  <Avatar person={m} size="w-5 h-5" /> {m.name}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Steward: welcome a member */}
      {v.can_steward && (
        <Card className="bg-[rgb(var(--ink-card))] border-[rgb(var(--ink-border))]">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-[rgb(var(--text-main))]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
              Welcome someone into the village
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col sm:flex-row gap-2">
              <select value={memberId} onChange={e => setMemberId(e.target.value)}
                className="flex-1 px-3 py-2 rounded-md bg-[rgb(var(--ink-deep))] border border-[rgb(var(--ink-border))] text-xs text-[rgb(var(--text-main))] focus:outline-none focus:border-[rgb(var(--gold)/0.5)]">
                <option value="">Who…</option>
                {users.filter(u => !(v.members || []).some(m => m.user_id === u.id)).map(u => (
                  <option key={u.id} value={u.id}>{u.name}{u.is_minor ? ' · youth' : ''}</option>
                ))}
              </select>
              <select value={memberRole} onChange={e => setMemberRole(e.target.value)}
                className="px-3 py-2 rounded-md bg-[rgb(var(--ink-deep))] border border-[rgb(var(--ink-border))] text-xs text-[rgb(var(--text-main))] focus:outline-none focus:border-[rgb(var(--gold)/0.5)]">
                {Object.entries(ROLE_LABELS).map(([k, lbl]) => <option key={k} value={k}>{lbl}</option>)}
              </select>
              <Button
                onClick={async () => {
                  setBusy(true);
                  try { await apiPost(`/api/villages/${v.id}/members`, { user_id: memberId, village_role: memberRole }); setMemberId(''); load(); }
                  catch (e) { alert(e.message); }
                  setBusy(false);
                }}
                disabled={busy || !memberId}
                className="bg-[rgb(var(--gold))] text-[rgb(var(--ink-deep))] hover:bg-[rgb(var(--gold-soft))]"
              >
                Welcome
              </Button>
            </div>
            <p className="text-[10px] text-[rgb(var(--text-faint))] mt-2">
              A village role describes how someone belongs — it grants no platform permissions.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Linked cohorts */}
      {v.cohorts?.length > 0 && (
        <div>
          <p className="text-[10px] tracking-[0.15em] uppercase text-[rgb(var(--gold))] mb-1.5">Cohorts in this village</p>
          <div className="flex flex-wrap gap-2">
            {v.cohorts.map(c => (
              <button key={c.id} onClick={() => navigate(`/cohorts/${c.id}`)}
                className="text-xs text-[rgb(var(--text-main))] bg-[rgb(var(--ink-card))] border border-[rgb(var(--ink-border))] rounded-md px-3 py-1.5 hover:border-[rgb(var(--gold)/0.3)]">
                {c.name} <span className="text-[rgb(var(--text-faint))]">· {c.member_count}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function VillagesPage({ user }) {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ name: '', season: '', place: '', description: '' });
  const [busy, setBusy] = useState(false);
  const [looseCohorts, setLooseCohorts] = useState([]);

  const isFaculty = ['faculty', 'elder', 'admin'].includes(user?.role);
  const load = useCallback(() => { apiGet('/api/villages').then(setData).catch(console.error); }, []);
  useEffect(() => { load(); }, [load]);

  // Phase 4 backfill: cohorts not yet inside any village — offered, never
  // auto-created. Founding one does NOT auto-add the cohort's members.
  useEffect(() => {
    if (isFaculty) {
      apiGet('/api/cohorts').then(cs => setLooseCohorts((cs || []).filter(c => !c.village_id))).catch(() => {});
    }
  }, [isFaculty]);

  const villages = data ? (isFaculty ? (data.all || []) : data.mine) : [];

  return (
    <div className="space-y-6 animate-fade-in-up max-w-3xl" data-testid="villages-page">
      <div className="flex items-end justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <TreeEvergreen size={20} weight="duotone" className="text-[rgb(var(--gold))]" />
            <h1 className="text-xl text-[rgb(var(--text-main))]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>Villages</h1>
          </div>
          <p className="text-xs text-[rgb(var(--text-muted))]">Bounded communities with a season, a place, and shared goals.</p>
        </div>
        {isFaculty && (
          <Button onClick={() => setCreating(c => !c)} className="bg-[rgb(var(--gold))] text-[rgb(var(--ink-deep))] hover:bg-[rgb(var(--gold-soft))]">
            <Plus size={14} className="mr-1" /> Found a village
          </Button>
        )}
      </div>

      {creating && (
        <Card className="bg-[rgb(var(--ink-card))] border-[rgb(var(--gold)/0.25)]">
          <CardContent className="p-4 space-y-2">
            {[
              { k: 'name', ph: 'Village name (e.g. Oakland Saturday Academy)' },
              { k: 'season', ph: 'Season (e.g. Fall 2026)' },
              { k: 'place', ph: 'Place (e.g. Oakland, CA)' },
              { k: 'description', ph: 'What this village is for…' },
            ].map(f => (
              <input key={f.k} value={form[f.k]} onChange={e => setForm(s => ({ ...s, [f.k]: e.target.value }))}
                placeholder={f.ph}
                className="w-full px-3 py-2 rounded bg-[rgb(var(--ink-deep))] border border-[rgb(var(--ink-border))] text-xs text-[rgb(var(--text-main))] placeholder-[rgb(var(--text-faint))] focus:outline-none focus:border-[rgb(var(--gold)/0.5)]" />
            ))}
            <Button
              onClick={async () => {
                setBusy(true);
                try {
                  const v = await apiPost('/api/villages', form);
                  navigate(`/villages/${v.id}`);
                } catch (e) { alert(e.message); setBusy(false); }
              }}
              disabled={busy || !form.name.trim()}
              className="bg-[rgb(var(--gold))] text-[rgb(var(--ink-deep))] hover:bg-[rgb(var(--gold-soft))] w-full"
            >
              Found this village
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Backfill: found a village from a cohort that has none */}
      {isFaculty && looseCohorts.length > 0 && (
        <Card className="bg-[rgb(var(--ink-card))] border-[rgb(var(--ink-border))]" data-testid="cohort-backfill">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-[rgb(var(--text-main))]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
              Cohorts not yet in a village
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {looseCohorts.map(c => (
                <div key={c.id} className="flex items-center justify-between gap-2 p-2 rounded bg-[rgb(var(--ink-deep))] border border-[rgb(var(--ink-border))]">
                  <span className="text-xs text-[rgb(var(--text-main))] min-w-0 truncate">
                    {c.name} <span className="text-[rgb(var(--text-faint))]">· {(c.members || []).length} members</span>
                  </span>
                  <Button
                    size="sm"
                    disabled={busy}
                    onClick={async () => {
                      setBusy(true);
                      try {
                        const v = await apiPost('/api/villages/from-cohort', { cohort_id: c.id });
                        navigate(`/villages/${v.id}`);
                      } catch (e) { alert(e.message); setBusy(false); }
                    }}
                    className="bg-[rgb(var(--gold)/0.15)] text-[rgb(var(--gold))] border border-[rgb(var(--gold)/0.3)] hover:bg-[rgb(var(--gold)/0.25)] h-7 text-xs flex-shrink-0"
                  >
                    Found a village from it
                  </Button>
                </div>
              ))}
            </div>
            <p className="text-[10px] text-[rgb(var(--text-faint))] mt-2">
              The cohort is attached; its people are not auto-added — welcome each member with a role.
            </p>
          </CardContent>
        </Card>
      )}

      {villages.length === 0 ? (
        <Card className="bg-[rgb(var(--ink-card))] border-[rgb(var(--ink-border))]">
          <CardContent className="p-6 text-center">
            <p className="text-sm text-[rgb(var(--text-muted))]">
              {isFaculty ? 'No villages yet — found the first one.' : "You haven't been welcomed into a village yet — your facilitators will bring you in."}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {villages.map(v => (
            <Card key={v.id} className="bg-[rgb(var(--ink-card))] border-[rgb(var(--ink-border))] hover:border-[rgb(var(--gold)/0.3)] transition-all cursor-pointer"
              onClick={() => navigate(`/villages/${v.id}`)} data-testid={`village-${v.id}`}>
              <CardContent className="p-4">
                <p className="text-sm text-[rgb(var(--text-main))] mb-1" style={{ fontFamily: 'Cormorant Garamond, serif' }}>{v.name}</p>
                <div className="flex flex-wrap gap-2 text-[10px] text-[rgb(var(--text-muted))]">
                  {v.season && <span>{v.season}</span>}
                  {v.place && <span>· {v.place}</span>}
                  <span>· {(v.members || []).length} members</span>
                  {v.goals?.length > 0 && <span>· {v.goals.filter(g => g.done).length}/{v.goals.length} goals</span>}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
