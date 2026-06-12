import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import {
  UsersThree, Compass, HandsClapping, Handshake, Sparkle, Heart, HandHeart, Bell,
  ArrowLeft,
} from '@phosphor-icons/react';
import { apiGet } from '../lib/api';

const DIMENSIONS = [
  { key: 'belonging', label: 'Belonging', icon: UsersThree, blurb: 'How regularly each person shows up' },
  { key: 'participation', label: 'Participation', icon: Compass, blurb: 'Lessons, sessions, and quizzes engaged' },
  { key: 'contribution', label: 'Contribution', icon: HandsClapping, blurb: 'What each person gives to the community' },
  { key: 'collaboration', label: 'Collaboration', icon: Handshake, blurb: 'Responding, joining, building together' },
  { key: 'leadership', label: 'Leadership', icon: Sparkle, blurb: 'Initiating, mentoring, carrying others' },
  { key: 'wellness', label: 'Wellness', icon: Heart, blurb: 'Arrives with SEL check-ins' },
];

const ScoreRing = ({ score }) => (
  <div className="relative w-12 h-12 flex-shrink-0">
    <svg className="w-12 h-12 -rotate-90" viewBox="0 0 40 40">
      <circle cx="20" cy="20" r="16" fill="none" stroke="#1E293B" strokeWidth="3" />
      {score !== null && (
        <circle cx="20" cy="20" r="16" fill="none" stroke="#D4AF37" strokeWidth="3"
          strokeDasharray={`${(score || 0) * 1.005} 100.5`} strokeLinecap="round" />
      )}
    </svg>
    <div className="absolute inset-0 flex items-center justify-center">
      <span className="text-[11px] font-semibold text-[#F8FAFC]">{score === null ? '—' : score}</span>
    </div>
  </div>
);

export default function CommunityDashboardPage({ user }) {
  // Phase 3 (deep migration): the village, not just the cohort, is a scope.
  // scope = "village:<id>" | "cohort:<id>"; cohort drill-down stays inside.
  const [villages, setVillages] = useState([]);
  const [cohorts, setCohorts] = useState([]);
  const [scope, setScope] = useState('');
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    Promise.all([
      apiGet('/api/villages').catch(() => ({ mine: [] })),
      apiGet('/api/cohorts').catch(() => []),
    ]).then(([vData, cs]) => {
      const vs = vData.all || vData.mine || [];
      setVillages(vs);
      setCohorts(cs);
      // Villages first: the village is the primitive.
      if (vs.length > 0) setScope(`village:${vs[0].id}`);
      else if (cs.length > 0) setScope(`cohort:${cs[0].id}`);
    }).catch(e => setError(e.message));
  }, []);

  const load = useCallback(() => {
    if (!scope) return;
    const [kind, id] = scope.split(':');
    setLoading(true);
    setError('');
    apiGet(kind === 'village' ? `/api/dashboard/village/${id}` : `/api/dashboard/community/${id}`)
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [scope]);

  useEffect(() => { load(); }, [load]);

  const isVillageScope = scope.startsWith('village:');
  const parentVillage = isVillageScope ? null
    : villages.find(v => (v.cohort_ids || []).includes(scope.split(':')[1]));

  return (
    <div className="space-y-6 animate-fade-in-up" data-testid="community-dashboard-page">
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <UsersThree size={20} weight="duotone" className="text-[#D4AF37]" />
            <h1 className="text-xl text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
              Community Dashboard
            </h1>
          </div>
          <p className="text-xs text-[#94A3B8]">
            Measuring what Ubuntu values — last {data?.window_days || 30} days, individual and village together.
          </p>
        </div>
        <select
          value={scope}
          onChange={e => setScope(e.target.value)}
          className="px-3 py-2 rounded-md bg-[#0F172A] border border-[#1E293B] text-xs text-[#F8FAFC] focus:outline-none focus:border-[#D4AF37]/50"
          data-testid="dashboard-scope-select"
        >
          {villages.length === 0 && cohorts.length === 0 && <option value="">Nothing to measure yet</option>}
          {villages.length > 0 && (
            <optgroup label="Villages">
              {villages.map(v => <option key={v.id} value={`village:${v.id}`}>{v.name}</option>)}
            </optgroup>
          )}
          {cohorts.length > 0 && (
            <optgroup label="Cohorts">
              {cohorts.map(c => <option key={c.id} value={`cohort:${c.id}`}>{c.name}</option>)}
            </optgroup>
          )}
        </select>
      </div>

      {/* Drill-down breadcrumb: back from a cohort to its village */}
      {parentVillage && (
        <button onClick={() => setScope(`village:${parentVillage.id}`)}
          className="flex items-center gap-1.5 text-xs text-[#94A3B8] hover:text-[#D4AF37]" data-testid="back-to-village">
          <ArrowLeft size={13} /> Back to {parentVillage.name}
        </button>
      )}

      {error && <p className="text-sm text-red-400 bg-red-400/10 rounded-md px-4 py-3">{error}</p>}
      {loading && <p className="text-sm text-[#94A3B8]">Listening to the village…</p>}

      {data && data.dimensions && (
        <>
          {/* May need you this week */}
          {data.attention?.length > 0 && (
            <Card className="bg-[#0F172A] border-amber-500/30">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-amber-400 flex items-center gap-2" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
                  <Bell size={15} weight="duotone" /> These young people may need you this week
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {data.attention.map(a => (
                    <span key={a.id} className="flex items-center gap-1.5 text-xs text-[#F8FAFC] bg-[#050814] border border-[#1E293B] rounded-full px-2.5 py-1.5">
                      <img src={a.picture || `https://ui-avatars.com/api/?name=${encodeURIComponent(a.name)}&background=0F172A&color=D4AF37`} alt="" className="w-5 h-5 rounded-full" />
                      {a.name}
                      <span className="text-[9px] text-[#94A3B8]">
                        {a.last_seen ? `quiet since ${new Date(a.last_seen).toLocaleDateString()}` : 'not yet active'}
                      </span>
                    </span>
                  ))}
                </div>
                <p className="text-[10px] text-[#94A3B8] mt-2 italic">
                  An invitation, not a verdict — a check-in, a call, a word of welcome.
                </p>
                {/* Mentors of the village, ready to carry an attention name
                    (precursor to eval §7.5 interventions) */}
                {data.village_mentors?.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-[#1E293B]">
                    <p className="text-[10px] tracking-[0.15em] uppercase text-[#D4AF37] mb-1.5 flex items-center gap-1">
                      <HandHeart size={11} weight="duotone" /> Suggest a mentor check-in
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {data.village_mentors.map(m => (
                        <span key={m.id} className="flex items-center gap-1.5 text-xs text-[#F8FAFC] bg-[#050814] border border-[#D4AF37]/20 rounded-full px-2.5 py-1">
                          <img src={m.picture || `https://ui-avatars.com/api/?name=${encodeURIComponent(m.name)}&background=0F172A&color=D4AF37`} alt="" className="w-4 h-4 rounded-full" />
                          {m.name}
                        </span>
                      ))}
                    </div>
                    <p className="text-[10px] text-[#475569] mt-1.5 italic">
                      These members hold mentor or elder roles here — a quiet name above could be theirs to reach.
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Village scope: cohort drill-down stays one click away */}
          {data.cohorts?.length > 0 && (
            <div className="flex flex-wrap items-center gap-2" data-testid="cohort-drilldown">
              <span className="text-[10px] tracking-[0.15em] uppercase text-[#475569]">Drill into a cohort:</span>
              {data.cohorts.map(c => (
                <button key={c.id} onClick={() => setScope(`cohort:${c.id}`)}
                  className="text-xs text-[#F8FAFC] bg-[#0F172A] border border-[#1E293B] rounded-md px-3 py-1.5 hover:border-[#D4AF37]/30">
                  {c.name} <span className="text-[#475569]">· {c.member_count}</span>
                </button>
              ))}
            </div>
          )}

          {/* Village dimensions */}
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
            {DIMENSIONS.map(d => {
              const dim = data.dimensions[d.key];
              return (
                <Card key={d.key} className="bg-[#0F172A] border-[#1E293B]">
                  <CardContent className="p-4 flex items-center gap-3">
                    <ScoreRing score={dim?.score ?? null} />
                    <div className="min-w-0">
                      <p className="text-sm text-[#F8FAFC] flex items-center gap-1.5">
                        <d.icon size={14} weight="duotone" className="text-[#D4AF37]" /> {d.label}
                      </p>
                      <p className="text-[10px] text-[#94A3B8] leading-snug mt-0.5">{dim?.note || d.blurb}</p>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>

          {/* Member signals — alphabetical, never ranked */}
          <Card className="bg-[#0F172A] border-[#1E293B]">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
                Each member's signals
              </CardTitle>
            </CardHeader>
            <CardContent className="overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr className="text-[9px] uppercase tracking-wider text-[#94A3B8]">
                    <th className="pb-2 pr-3 font-normal">Member</th>
                    <th className="pb-2 px-2 font-normal text-center">Active days</th>
                    {['belonging', 'participation', 'contribution', 'collaboration', 'leadership', 'wellness'].map(k => (
                      <th key={k} className="pb-2 px-2 font-normal text-center capitalize">{k}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.members.map(m => (
                    <tr key={m.id} className="border-t border-[#1E293B]" data-testid={`dash-member-${m.id}`}>
                      <td className="py-2 pr-3">
                        <span className="flex items-center gap-2 text-xs text-[#F8FAFC]">
                          <img src={m.picture || `https://ui-avatars.com/api/?name=${encodeURIComponent(m.name)}&background=0F172A&color=D4AF37`} alt="" className="w-6 h-6 rounded-full" />
                          {m.name}
                          {m.is_mentor && <HandHeart size={12} className="text-[#D4AF37]" title="Mentor" />}
                        </span>
                      </td>
                      <td className="py-2 px-2 text-center text-xs text-[#94A3B8]">{m.active_days}</td>
                      {['belonging', 'participation', 'contribution', 'collaboration', 'leadership', 'wellness'].map(k => {
                        const s = m.scores[k];
                        return (
                          <td key={k} className="py-2 px-2">
                            {s === null || s === undefined ? (
                              <p className="text-center text-[10px] text-[#475569]">—</p>
                            ) : (
                              <div className="w-14 h-1.5 bg-[#0A1128] rounded-full overflow-hidden mx-auto">
                                <div className="h-full bg-[#D4AF37] rounded-full" style={{ width: `${Math.max(s, 2)}%` }} />
                              </div>
                            )}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="text-[10px] text-[#475569] mt-3 italic">
                Signals are absolute, not comparative — this table has no first place.
              </p>
            </CardContent>
          </Card>
        </>
      )}

      {data && !data.dimensions && (
        <p className="text-sm text-[#94A3B8]">{data.message}</p>
      )}
    </div>
  );
}
