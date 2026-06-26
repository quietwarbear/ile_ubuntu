import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Navigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import {
  TreeEvergreen, VideoCamera, Target, Check, Chats, HandHeart,
  MapPin, CalendarBlank, UsersThree, Sparkle, CaretRight,
} from '@phosphor-icons/react';
import { apiGet } from '../lib/api';
import { useI18n } from '../i18n';

const Avatar = ({ person, size = 'w-7 h-7' }) => (
  <img
    src={person?.picture || person?.author_picture || person?.host_picture || `https://ui-avatars.com/api/?name=${encodeURIComponent(person?.name || person?.author_name || person?.host_name || '?')}&background=0F172A&color=D4AF37`}
    alt=""
    className={`${size} rounded-full flex-shrink-0`}
  />
);

const REL_LABELS = { co_learner: 'Co-learner', family: 'Family' };

function fmtWhen(iso) {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    const today = new Date();
    const sameDay = d.toDateString() === today.toDateString();
    const time = d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
    return sameDay ? `Today · ${time}` : `${d.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' })} · ${time}`;
  } catch {
    return iso;
  }
}

// The member's home IS their village (deep migration Phase 2, eval §8).
export default function VillageHomePage({ user }) {
  const { villageId } = useParams();
  const navigate = useNavigate();
  const { t } = useI18n();
  const [home, setHome] = useState(null);
  const [error, setError] = useState('');

  const load = useCallback(() => {
    apiGet(`/api/villages/${villageId}/home`).then(setHome).catch(e => setError(e.message));
  }, [villageId]);
  useEffect(() => { load(); }, [load]);

  if (error) return <p className="text-sm text-red-400 bg-red-400/10 rounded-md px-4 py-3">{error}</p>;
  if (!home) return <p className="text-sm text-[#94A3B8]">{t('village_entering')}</p>;

  const { village, sessions, circle, goals, goals_done, posts, elder_prompt } = home;

  return (
    <div className="space-y-6 animate-fade-in-up max-w-4xl" data-testid="village-home">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <TreeEvergreen size={24} weight="duotone" className="text-[#D4AF37]" />
          <h1 className="text-2xl text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>{village.name}</h1>
        </div>
        <div className="flex flex-wrap gap-3 text-xs text-[#94A3B8]">
          {village.season && <span className="flex items-center gap-1"><CalendarBlank size={12} /> {village.season}</span>}
          {village.place && <span className="flex items-center gap-1"><MapPin size={12} /> {village.place}</span>}
          <span className="flex items-center gap-1"><UsersThree size={12} /> {home.member_count} members</span>
          <button onClick={() => navigate(`/villages/${village.id}`)} className="flex items-center gap-0.5 text-[#D4AF37] hover:underline">
            {t('village_full')} <CaretRight size={10} />
          </button>
        </div>
      </div>

      {/* Elder prompt — static v1; Ubuntu Intelligence takes this slot later */}
      <Card className="bg-gradient-to-r from-[#D4AF37]/10 to-transparent border-[#D4AF37]/30">
        <CardContent className="p-4 flex items-start gap-3">
          <Sparkle size={18} weight="duotone" className="text-[#D4AF37] flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-[10px] tracking-[0.2em] uppercase text-[#D4AF37] mb-1">{t('village_elder_word')}</p>
            <p className="text-sm text-[#F8FAFC] italic" style={{ fontFamily: 'Cormorant Garamond, serif' }}>{elder_prompt}</p>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Today's sessions */}
        <Card className="bg-[#0F172A] border-[#1E293B]">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-[#F8FAFC] flex items-center gap-2" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
              <VideoCamera size={15} weight="duotone" className="text-[#D4AF37]" /> {t('village_sessions')}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1.5">
            {sessions.map(s => (
              <button key={s.id} onClick={() => navigate(s.status === 'live' ? `/live/${s.id}` : '/live')}
                className="w-full flex items-center gap-2.5 p-2 rounded bg-[#050814] border border-[#1E293B] text-left hover:border-[#D4AF37]/25">
                <Avatar person={s} size="w-6 h-6" />
                <span className="flex-1 min-w-0">
                  <span className="block text-xs text-[#F8FAFC] truncate">{s.title}</span>
                  <span className="block text-[10px] text-[#94A3B8]">{s.host_name}{s.scheduled_at ? ` · ${fmtWhen(s.scheduled_at)}` : ''}</span>
                </span>
                {s.status === 'live' && (
                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-red-500/15 text-red-400 border border-red-500/30 uppercase tracking-wider flex-shrink-0">Live</span>
                )}
              </button>
            ))}
            {sessions.length === 0 && <p className="text-xs text-[#475569]">{t('village_no_sessions')}</p>}
          </CardContent>
        </Card>

        {/* My circle */}
        <Card className="bg-[#0F172A] border-[#1E293B]">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-[#F8FAFC] flex items-center gap-2" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
              <HandHeart size={15} weight="duotone" className="text-[#D4AF37]" /> {t('village_circle')}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1.5">
            {circle.map((p, i) => (
              <button key={`${p.id}-${i}`} onClick={() => navigate(p.relationship === 'family' ? '/family' : '/learning-circles')}
                className="w-full flex items-center gap-2.5 p-2 rounded bg-[#050814] border border-[#1E293B] text-left hover:border-[#D4AF37]/25">
                <Avatar person={p} size="w-6 h-6" />
                <span className="flex-1 min-w-0">
                  <span className="block text-xs text-[#F8FAFC] truncate">{p.name}</span>
                  <span className="block text-[10px] text-[#94A3B8]">{REL_LABELS[p.relationship] || p.relationship}{p.in_village ? '' : ' · beyond the village'}</span>
                </span>
              </button>
            ))}
            {circle.length === 0 && <p className="text-xs text-[#475569]">{t('village_no_circle')}</p>}
          </CardContent>
        </Card>
      </div>

      {/* Village goals progress */}
      <Card className="bg-[#0F172A] border-[#D4AF37]/25">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm text-[#F8FAFC] flex items-center gap-2" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
            <Target size={15} weight="duotone" className="text-[#D4AF37]" /> {t('village_goals')}
            {goals.length > 0 && (
              <span className="text-[10px] text-[#94A3B8] font-normal">{goals_done}/{goals.length} carried home</span>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {goals.length > 0 ? (
            <>
              <div className="h-1.5 rounded-full bg-[#050814] border border-[#1E293B] overflow-hidden mb-3">
                <div className="h-full bg-[#D4AF37]/70 transition-all" style={{ width: `${goals.length ? Math.round((goals_done / goals.length) * 100) : 0}%` }} />
              </div>
              <div className="space-y-1">
                {goals.map(g => (
                  <div key={g.id} className="flex items-center gap-2">
                    <span className={`w-3.5 h-3.5 rounded border flex items-center justify-center flex-shrink-0 ${g.done ? 'bg-emerald-500/20 border-emerald-500/50' : 'border-[#334155]'}`}>
                      {g.done && <Check size={10} className="text-emerald-400" />}
                    </span>
                    <span className={`text-xs ${g.done ? 'text-[#475569] line-through' : 'text-[#F8FAFC]'}`}>{g.text}</span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <p className="text-xs text-[#475569]">{t('village_no_goals')}</p>
          )}
        </CardContent>
      </Card>

      {/* Latest from village members */}
      <Card className="bg-[#0F172A] border-[#1E293B]">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm text-[#F8FAFC] flex items-center gap-2" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
            <Chats size={15} weight="duotone" className="text-[#D4AF37]" /> {t('village_voices')}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {posts.map(p => (
            <button key={p.id} onClick={() => navigate('/community')}
              className="w-full p-3 rounded bg-[#050814] border border-[#1E293B] text-left hover:border-[#D4AF37]/25">
              <div className="flex items-center gap-2 mb-1">
                <Avatar person={p} size="w-5 h-5" />
                <span className="text-[10px] text-[#94A3B8]">{p.author_name}</span>
                <span className="text-[9px] px-1.5 rounded bg-[#0F172A] border border-[#1E293B] text-[#475569]">{p.category}</span>
              </div>
              <p className="text-xs text-[#F8FAFC] mb-0.5">{p.title}</p>
              <p className="text-[11px] text-[#94A3B8] line-clamp-2">{p.content}</p>
              <p className="text-[10px] text-[#475569] mt-1">{p.reply_count} replies · {p.like_count} likes</p>
            </button>
          ))}
          {posts.length === 0 && <p className="text-xs text-[#475569]">{t('village_no_posts')}</p>}
        </CardContent>
      </Card>
    </div>
  );
}

// Gate for "/": one village → its feed; multiple → picker; none → commons
// dashboard. DashboardPage stays intact for commons users (plan Phase 2.4).
export function VillageHomeGate({ user }) {
  const [data, setData] = useState(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    apiGet('/api/villages').then(setData).catch(() => setFailed(true));
  }, []);

  if (failed) return <Navigate to="/dashboard" replace />;
  if (!data) return <p className="text-sm text-[#94A3B8]">Loading…</p>;

  const mine = data.mine || [];
  if (mine.length === 0) return <Navigate to="/dashboard" replace />;
  if (mine.length === 1) return <Navigate to={`/village/${mine[0].id}`} replace />;
  return <VillagePicker villages={mine} />;
}

function VillagePicker({ villages }) {
  const navigate = useNavigate();
  const { t } = useI18n();
  return (
    <div className="space-y-6 animate-fade-in-up max-w-3xl" data-testid="village-picker">
      <div>
        <div className="flex items-center gap-2 mb-1">
          <TreeEvergreen size={20} weight="duotone" className="text-[#D4AF37]" />
          <h1 className="text-xl text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>{t('village_pick')}</h1>
        </div>
        <p className="text-xs text-[#94A3B8]">{t('village_pick_sub')}</p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {villages.map(v => (
          <Card key={v.id} className="bg-[#0F172A] border-[#1E293B] hover:border-[#D4AF37]/30 transition-all cursor-pointer"
            onClick={() => navigate(`/village/${v.id}`)} data-testid={`pick-village-${v.id}`}>
            <CardContent className="p-4">
              <p className="text-sm text-[#F8FAFC] mb-1" style={{ fontFamily: 'Cormorant Garamond, serif' }}>{v.name}</p>
              <div className="flex flex-wrap gap-2 text-[10px] text-[#94A3B8]">
                {v.season && <span>{v.season}</span>}
                {v.place && <span>· {v.place}</span>}
                <span>· {(v.members || []).length} members</span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
