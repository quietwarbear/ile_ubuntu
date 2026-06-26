import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import {
  House, GraduationCap, UsersThree, LinkSimple, Trash, ArrowsClockwise,
  BookOpenText, VideoCamera, Chats, PencilSimple, Trophy,
} from '@phosphor-icons/react';
import { apiGet, apiPost, apiDelete } from '../lib/api';

const Avatar = ({ person, size = 'w-9 h-9' }) => (
  <img
    src={person.picture || `https://ui-avatars.com/api/?name=${encodeURIComponent(person.name || '?')}&background=0F172A&color=D4AF37`}
    alt=""
    className={`${size} rounded-full flex-shrink-0`}
  />
);

function YouthCard({ youth, onUnlink }) {
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    apiGet(`/api/family/youth/${youth.id}/summary`).then(setSummary).catch(e => setError(e.message));
  }, [youth.id]);

  const week = summary?.this_week;
  const showedUp = week && (week.lessons_completed || week.live_sessions_joined || week.posts_and_replies || week.quizzes_attempted);

  return (
    <Card className="bg-[#0F172A] border-[#1E293B]" data-testid={`youth-card-${youth.id}`}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm text-[#F8FAFC] flex items-center gap-2" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
            <Avatar person={youth} size="w-7 h-7" /> {youth.name}
          </CardTitle>
          <button
            onClick={() => onUnlink(youth.id)}
            className="text-[#475569] hover:text-red-400 transition-colors"
            title="Remove this family link"
            data-testid={`unlink-${youth.id}`}
          >
            <Trash size={14} />
          </button>
        </div>
      </CardHeader>
      <CardContent>
        {error ? (
          <p className="text-xs text-red-400">{error}</p>
        ) : !summary ? (
          <p className="text-xs text-[#94A3B8]">Loading…</p>
        ) : (
          <div className="space-y-3">
            {/* This week, warmly */}
            <div>
              <p className="text-[10px] tracking-[0.15em] uppercase text-[#D4AF37] mb-1.5">This week</p>
              {showedUp ? (
                <div className="flex flex-wrap gap-2">
                  {week.lessons_completed > 0 && (
                    <span className="flex items-center gap-1 text-[10px] text-[#F8FAFC] bg-[#050814] border border-[#1E293B] rounded-full px-2 py-1">
                      <BookOpenText size={11} className="text-[#D4AF37]" /> {week.lessons_completed} lesson{week.lessons_completed !== 1 ? 's' : ''} completed
                    </span>
                  )}
                  {week.live_sessions_joined > 0 && (
                    <span className="flex items-center gap-1 text-[10px] text-[#F8FAFC] bg-[#050814] border border-[#1E293B] rounded-full px-2 py-1">
                      <VideoCamera size={11} className="text-[#D4AF37]" /> joined {week.live_sessions_joined} live session{week.live_sessions_joined !== 1 ? 's' : ''}
                    </span>
                  )}
                  {week.posts_and_replies > 0 && (
                    <span className="flex items-center gap-1 text-[10px] text-[#F8FAFC] bg-[#050814] border border-[#1E293B] rounded-full px-2 py-1">
                      <Chats size={11} className="text-[#D4AF37]" /> {week.posts_and_replies} community contribution{week.posts_and_replies !== 1 ? 's' : ''}
                    </span>
                  )}
                  {week.quizzes_attempted > 0 && (
                    <span className="flex items-center gap-1 text-[10px] text-[#F8FAFC] bg-[#050814] border border-[#1E293B] rounded-full px-2 py-1">
                      <PencilSimple size={11} className="text-[#D4AF37]" /> {week.quizzes_attempted} quiz{week.quizzes_attempted !== 1 ? 'zes' : ''} tried
                    </span>
                  )}
                  {week.courses_completed > 0 && (
                    <span className="flex items-center gap-1 text-[10px] text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 rounded-full px-2 py-1">
                      <Trophy size={11} /> finished {week.courses_completed} course{week.courses_completed !== 1 ? 's' : ''}!
                    </span>
                  )}
                </div>
              ) : (
                <p className="text-xs text-[#94A3B8]">A quiet week so far — a little encouragement goes a long way.</p>
              )}
            </div>

            {/* Learning journey */}
            <div>
              <p className="text-[10px] tracking-[0.15em] uppercase text-[#D4AF37] mb-1.5">Learning journey</p>
              {summary.enrollments.length === 0 ? (
                <p className="text-xs text-[#94A3B8]">Not enrolled in any courses yet.</p>
              ) : (
                <div className="space-y-1.5">
                  {summary.enrollments.map((e, i) => (
                    <div key={i} className="flex items-center gap-2">
                      <span className="text-xs text-[#F8FAFC] truncate flex-1">{e.course_title}</span>
                      <div className="w-24 h-2 bg-[#0A1128] rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${e.completed ? 'bg-emerald-400' : 'bg-[#D4AF37]'}`}
                          style={{ width: `${Math.max(e.progress, 2)}%` }}
                        />
                      </div>
                      <span className={`text-[10px] w-8 text-right ${e.completed ? 'text-emerald-400' : 'text-[#94A3B8]'}`}>{e.progress}%</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function FamilyPage({ user }) {
  const [family, setFamily] = useState(null);
  const [codeInput, setCodeInput] = useState('');
  const [message, setMessage] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    apiGet('/api/family').then(setFamily).catch(e => setMessage({ type: 'error', text: e.message }));
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleLink = async () => {
    if (!codeInput.trim()) return;
    setBusy(true);
    try {
      const res = await apiPost('/api/family/link', { code: codeInput.trim() });
      setMessage({ type: 'success', text: `Linked with ${res.youth?.name || 'your young person'}.` });
      setCodeInput('');
      load();
    } catch (e) {
      setMessage({ type: 'error', text: e.message });
    }
    setBusy(false);
  };

  const handleUnlink = async (otherId) => {
    if (!window.confirm('Remove this family link?')) return;
    try { await apiDelete(`/api/family/link/${otherId}`); load(); }
    catch (e) { setMessage({ type: 'error', text: e.message }); }
  };

  const handleGenerateCode = async () => {
    setBusy(true);
    try { await apiPost('/api/family/code', {}); load(); }
    catch (e) { setMessage({ type: 'error', text: e.message }); }
    setBusy(false);
  };

  const isFamilyIntent = user?.intent === 'family';

  return (
    <div className="space-y-6 animate-fade-in-up max-w-3xl" data-testid="family-page">
      <div>
        <div className="flex items-center gap-2 mb-1">
          <House size={20} weight="duotone" className="text-[#D4AF37]" />
          <h1 className="text-xl text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>Family</h1>
        </div>
        <p className="text-xs text-[#94A3B8]">
          The village around each learner — linked with care, shared with dignity.
        </p>
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

      {/* Guardian side: link + youth cards */}
      <Card className="bg-[#0F172A] border-[#1E293B]">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm text-[#F8FAFC] flex items-center gap-2" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
            <LinkSimple size={16} weight="duotone" className="text-[#D4AF37]" /> Link a young person
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-[#94A3B8] mb-3">
            Ask your young person for their family code (they'll find it on this page when signed in), then enter it here.
          </p>
          <div className="flex gap-2">
            <input
              value={codeInput}
              onChange={e => setCodeInput(e.target.value.toUpperCase())}
              placeholder="e.g. K7XQ2A"
              className="flex-1 px-3 py-2 rounded-md bg-[#050814] border border-[#1E293B] text-sm text-[#F8FAFC] placeholder-[#475569] focus:outline-none focus:border-[#D4AF37]/50 tracking-[0.2em] uppercase"
              data-testid="family-code-input"
            />
            <Button onClick={handleLink} disabled={busy || !codeInput.trim()} className="bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB]">
              Link
            </Button>
          </div>
        </CardContent>
      </Card>

      {family?.youth?.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-xs tracking-[0.15em] uppercase text-[#D4AF37] flex items-center gap-2">
              <GraduationCap size={14} weight="duotone" /> My young people
            </h2>
            <button
              onClick={async () => {
                setBusy(true);
                try {
                  const res = await apiPost('/api/family/digest/preview', {});
                  setMessage({ type: 'success', text: res.message });
                } catch (e) { setMessage({ type: 'error', text: e.message }); }
                setBusy(false);
              }}
              disabled={busy}
              className="text-[10px] text-[#94A3B8] hover:text-[#D4AF37] transition-colors"
              data-testid="digest-preview-btn"
            >
              Email me this week's digest →
            </button>
          </div>
          {family.youth.map(y => (
            <YouthCard key={y.id} youth={y} onUnlink={handleUnlink} />
          ))}
        </div>
      )}

      {/* Youth side: my code + my guardians (hidden for family-intent accounts) */}
      {!isFamilyIntent && (
        <Card className="bg-[#0F172A] border-[#1E293B]">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-[#F8FAFC] flex items-center gap-2" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
              <UsersThree size={16} weight="duotone" className="text-[#D4AF37]" /> My family code
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-[#94A3B8] mb-3">
              Share this code with a parent, guardian, or elder so they can follow and encourage your journey.
              They'll see your progress and participation — never your private messages.
            </p>
            <div className="flex items-center gap-3">
              {family?.family_code ? (
                <span className="px-4 py-2 rounded-md bg-[#050814] border border-[#D4AF37]/30 text-lg tracking-[0.3em] text-[#D4AF37] font-medium" data-testid="my-family-code">
                  {family.family_code}
                </span>
              ) : (
                <span className="text-xs text-[#475569]">No code yet</span>
              )}
              <button
                onClick={handleGenerateCode}
                disabled={busy}
                className="flex items-center gap-1 text-xs text-[#94A3B8] hover:text-[#D4AF37] transition-colors"
                data-testid="generate-family-code"
              >
                <ArrowsClockwise size={13} /> {family?.family_code ? 'New code' : 'Create code'}
              </button>
            </div>

            {family?.guardians?.length > 0 && (
              <div className="mt-4">
                <p className="text-[10px] tracking-[0.15em] uppercase text-[#D4AF37] mb-2">My family</p>
                <div className="space-y-1.5">
                  {family.guardians.map(g => (
                    <div key={g.id} className="flex items-center gap-2 p-2 rounded bg-[#050814] border border-[#1E293B]">
                      <Avatar person={g} size="w-6 h-6" />
                      <span className="text-xs text-[#F8FAFC] flex-1">{g.name}</span>
                      <button onClick={() => handleUnlink(g.id)} className="text-[#475569] hover:text-red-400" title="Remove">
                        <Trash size={13} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
