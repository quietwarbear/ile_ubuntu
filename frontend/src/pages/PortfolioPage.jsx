import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import {
  Backpack, Plus, Check, Trash, Target, NotePencil, Medal, Paperclip,
  LinkSimple, LockSimple, UsersThree, DownloadSimple, CaretDown, CaretUp,
} from '@phosphor-icons/react';
import { apiGet, apiPost, apiPut, apiDelete, apiUpload } from '../lib/api';

// The portfolio is the young person's own — private by default, shared by
// their choice (eval §6.3: "theirs to keep and carry forward").

const inputCls = "w-full px-3 py-1.5 rounded bg-[#050814] border border-[#1E293B] text-xs text-[#F8FAFC] placeholder-[#475569] focus:outline-none focus:border-[#D4AF37]/50";
const goldBtnCls = "bg-[#D4AF37]/15 text-[#D4AF37] border border-[#D4AF37]/30 hover:bg-[#D4AF37]/25";

function VisibilityBadge({ visibility }) {
  const shared = visibility === 'shared';
  return (
    <span className={`inline-flex items-center gap-1 text-[9px] px-1.5 py-0.5 rounded border ${
      shared ? 'text-[#D4AF37] border-[#D4AF37]/30 bg-[#D4AF37]/10' : 'text-[#94A3B8] border-[#334155] bg-[#050814]'
    }`}>
      {shared ? <UsersThree size={10} /> : <LockSimple size={10} />}
      {shared ? 'Shared' : 'Private'}
    </span>
  );
}

function AddItemCard({ onAdded }) {
  const [open, setOpen] = useState(false);
  const [kind, setKind] = useState('work');
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [linkUrl, setLinkUrl] = useState('');
  const [visibility, setVisibility] = useState('private');
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const fileRef = useRef(null);

  const reset = () => {
    setTitle(''); setBody(''); setLinkUrl(''); setFile(null); setVisibility('private');
    if (fileRef.current) fileRef.current.value = '';
  };

  const submit = async () => {
    if (!title.trim()) { setError('Give it a title.'); return; }
    setBusy(true); setError('');
    try {
      let fileId = null;
      if (kind === 'work' && file) {
        const fd = new FormData();
        fd.append('file', file);
        const up = await apiUpload('/api/files/upload', fd);
        fileId = up.file.id;
      }
      await apiPost('/api/portfolio', {
        kind, title, body, link_url: linkUrl, visibility, file_id: fileId,
      });
      reset(); setOpen(false); onAdded();
    } catch (e) { setError(e.message); }
    setBusy(false);
  };

  return (
    <Card className="bg-[#0F172A] border-[#1E293B]" data-testid="add-portfolio-item">
      <CardHeader className="pb-2 cursor-pointer" onClick={() => setOpen(o => !o)}>
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm text-[#F8FAFC] flex items-center gap-2" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
            <Plus size={14} className="text-[#D4AF37]" /> Add to my portfolio
          </CardTitle>
          {open ? <CaretUp size={14} className="text-[#94A3B8]" /> : <CaretDown size={14} className="text-[#94A3B8]" />}
        </div>
      </CardHeader>
      {open && (
        <CardContent className="space-y-3">
          <div className="flex gap-2">
            {[['work', 'Work I made', NotePencil], ['reflection', 'A reflection', Backpack]].map(([k, label, Icon]) => (
              <button
                key={k}
                onClick={() => setKind(k)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs border transition-colors ${
                  kind === k ? 'text-[#D4AF37] border-[#D4AF37]/40 bg-[#D4AF37]/10' : 'text-[#94A3B8] border-[#1E293B] bg-[#050814]'
                }`}
                data-testid={`kind-${k}`}
              >
                <Icon size={13} /> {label}
              </button>
            ))}
          </div>
          <input value={title} onChange={e => setTitle(e.target.value)} placeholder="Title" className={inputCls} data-testid="item-title" />
          <textarea
            value={body} onChange={e => setBody(e.target.value)} rows={3}
            placeholder={kind === 'reflection' ? 'What did this season teach you?' : 'Tell the story of this piece…'}
            className={inputCls}
          />
          {kind === 'work' && (
            <div className="flex flex-col sm:flex-row gap-2">
              <input value={linkUrl} onChange={e => setLinkUrl(e.target.value)} placeholder="Link (optional)" className={inputCls} />
              <input ref={fileRef} type="file" onChange={e => setFile(e.target.files?.[0] || null)}
                className="text-xs text-[#94A3B8] file:mr-2 file:px-3 file:py-1.5 file:rounded file:border file:border-[#D4AF37]/30 file:bg-[#D4AF37]/10 file:text-[#D4AF37] file:text-xs file:cursor-pointer" />
            </div>
          )}
          <label className="flex items-center gap-2 text-xs text-[#94A3B8] cursor-pointer">
            <input type="checkbox" checked={visibility === 'shared'}
              onChange={e => setVisibility(e.target.checked ? 'shared' : 'private')} />
            Share with my facilitators and family
          </label>
          {error && <p className="text-xs text-red-400">{error}</p>}
          <Button size="sm" onClick={submit} disabled={busy} className={goldBtnCls} data-testid="save-item">
            {busy ? 'Saving…' : 'Add to portfolio'}
          </Button>
        </CardContent>
      )}
    </Card>
  );
}

function ItemCard({ item, onChanged }) {
  const Icon = item.kind === 'reflection' ? Backpack : NotePencil;
  const toggleVisibility = async () => {
    try {
      await apiPut(`/api/portfolio/${item.id}`, { visibility: item.visibility === 'shared' ? 'private' : 'shared' });
      onChanged();
    } catch (e) { alert(e.message); }
  };
  const remove = async () => {
    if (!window.confirm('Remove this from your portfolio?')) return;
    try { await apiDelete(`/api/portfolio/${item.id}`); onChanged(); } catch (e) { alert(e.message); }
  };
  return (
    <Card className="bg-[#0F172A] border-[#1E293B]" data-testid={`portfolio-item-${item.id}`}>
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <Icon size={18} weight="duotone" className="text-[#D4AF37] mt-0.5 flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <p className="text-sm text-[#F8FAFC]">{item.title}</p>
              <VisibilityBadge visibility={item.visibility} />
            </div>
            {item.body && <p className="text-xs text-[#94A3B8] mt-1 whitespace-pre-wrap">{item.body}</p>}
            <div className="flex items-center gap-3 mt-2 flex-wrap">
              {item.link_url && (
                <a href={item.link_url} target="_blank" rel="noopener noreferrer"
                  className="flex items-center gap-1 text-[10px] text-[#D4AF37] hover:underline">
                  <LinkSimple size={11} /> {item.link_url.replace(/^https?:\/\//, '').slice(0, 40)}
                </a>
              )}
              {item.file && (
                <a href={`${process.env.REACT_APP_BACKEND_URL || ''}${item.file.download_url}`}
                  target="_blank" rel="noopener noreferrer"
                  className="flex items-center gap-1 text-[10px] text-[#D4AF37] hover:underline">
                  <DownloadSimple size={11} /> {item.file.original_filename}
                </a>
              )}
              <span className="text-[9px] text-[#475569]">{new Date(item.created_at).toLocaleDateString()}</span>
            </div>
          </div>
          <div className="flex items-center gap-1 flex-shrink-0">
            <button onClick={toggleVisibility} className="p-1 text-[#94A3B8] hover:text-[#D4AF37]"
              title={item.visibility === 'shared' ? 'Make private' : 'Share with facilitators & family'}>
              {item.visibility === 'shared' ? <LockSimple size={14} /> : <UsersThree size={14} />}
            </button>
            <button onClick={remove} className="p-1 text-[#94A3B8] hover:text-red-400" title="Remove">
              <Trash size={14} />
            </button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function GoalCard({ goal, onChanged }) {
  const [milestoneInput, setMilestoneInput] = useState('');
  const [completing, setCompleting] = useState(false);
  const [reflection, setReflection] = useState('');
  const done = goal.status === 'completed';

  const addMilestone = async () => {
    if (!milestoneInput.trim()) return;
    try { await apiPost(`/api/portfolio/goals/${goal.id}/milestones`, { text: milestoneInput }); setMilestoneInput(''); onChanged(); }
    catch (e) { alert(e.message); }
  };
  const toggleMilestone = async (mid) => {
    try { await apiPut(`/api/portfolio/goals/${goal.id}/milestones/${mid}/toggle`, {}); onChanged(); }
    catch (e) { alert(e.message); }
  };
  const complete = async () => {
    try { await apiPut(`/api/portfolio/goals/${goal.id}`, { status: 'completed', reflection }); setCompleting(false); onChanged(); }
    catch (e) { alert(e.message); }
  };
  const reopen = async () => {
    try { await apiPut(`/api/portfolio/goals/${goal.id}`, { status: 'active' }); onChanged(); }
    catch (e) { alert(e.message); }
  };
  const remove = async () => {
    if (!window.confirm('Let this goal go? Its milestones go with it.')) return;
    try { await apiDelete(`/api/portfolio/goals/${goal.id}`); onChanged(); } catch (e) { alert(e.message); }
  };

  return (
    <Card className="bg-[#0F172A] border-[#1E293B]" data-testid={`goal-${goal.id}`}>
      <CardContent className="p-4 space-y-3">
        <div className="flex items-start gap-3">
          <Target size={18} weight="duotone" className={done ? 'text-emerald-400 mt-0.5' : 'text-[#D4AF37] mt-0.5'} />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <p className={`text-sm ${done ? 'text-[#475569] line-through' : 'text-[#F8FAFC]'}`}>{goal.title}</p>
              <span className={`text-[9px] px-1.5 py-0.5 rounded border ${
                done ? 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10' : 'text-[#D4AF37] border-[#D4AF37]/30 bg-[#D4AF37]/10'
              }`}>
                {done ? 'Completed' : goal.target_date ? `By ${goal.target_date}` : 'Active'}
              </span>
            </div>
            {goal.why && <p className="text-xs text-[#94A3B8] mt-1 italic">Why: {goal.why}</p>}
            {done && goal.reflection && (
              <p className="text-xs text-[#94A3B8] mt-1 whitespace-pre-wrap">"{goal.reflection}"</p>
            )}
          </div>
          <button onClick={remove} className="p-1 text-[#94A3B8] hover:text-red-400 flex-shrink-0" title="Delete goal">
            <Trash size={14} />
          </button>
        </div>

        {!done && (
          <>
            <div className="space-y-1.5">
              {(goal.milestones || []).map(m => (
                <button key={m.id} onClick={() => toggleMilestone(m.id)}
                  className="w-full flex items-center gap-2 p-2 rounded bg-[#050814] border border-[#1E293B] text-left hover:border-[#D4AF37]/25 transition-colors">
                  <span className={`w-4 h-4 rounded border flex items-center justify-center flex-shrink-0 ${
                    m.done ? 'bg-emerald-500/20 border-emerald-500/50' : 'border-[#334155]'
                  }`}>
                    {m.done && <Check size={11} className="text-emerald-400" />}
                  </span>
                  <span className={`text-xs ${m.done ? 'text-[#475569] line-through' : 'text-[#F8FAFC]'}`}>{m.text}</span>
                </button>
              ))}
            </div>
            <div className="flex gap-2">
              <input value={milestoneInput} onChange={e => setMilestoneInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && addMilestone()}
                placeholder="A step along the way…" className={inputCls} />
              <Button size="sm" onClick={addMilestone} className={`${goldBtnCls} h-8`}><Plus size={13} /></Button>
            </div>
            {completing ? (
              <div className="space-y-2">
                <textarea value={reflection} onChange={e => setReflection(e.target.value)} rows={2}
                  placeholder="What did reaching this goal teach you?" className={inputCls} autoFocus />
                <div className="flex gap-2">
                  <Button size="sm" onClick={complete} className="bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/25">
                    <Check size={13} className="mr-1" /> Mark complete
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => setCompleting(false)} className="text-[#94A3B8]">Cancel</Button>
                </div>
              </div>
            ) : (
              <Button size="sm" onClick={() => setCompleting(true)} className={goldBtnCls} data-testid={`complete-goal-${goal.id}`}>
                <Check size={13} className="mr-1" /> I reached this goal
              </Button>
            )}
          </>
        )}
        {done && (
          <button onClick={reopen} className="text-[10px] text-[#94A3B8] hover:text-[#D4AF37]">Reopen this goal</button>
        )}
      </CardContent>
    </Card>
  );
}

export default function PortfolioPage({ user }) {
  const [tab, setTab] = useState('portfolio');
  const [portfolio, setPortfolio] = useState(null);
  const [goals, setGoals] = useState(null);
  const [goalTitle, setGoalTitle] = useState('');
  const [goalWhy, setGoalWhy] = useState('');
  const [goalDate, setGoalDate] = useState('');
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    apiGet('/api/portfolio').then(setPortfolio).catch(console.error);
    apiGet('/api/portfolio/goals').then(d => setGoals(d.goals)).catch(console.error);
  }, []);
  useEffect(() => { load(); }, [load]);

  const addGoal = async () => {
    if (!goalTitle.trim()) return;
    setBusy(true);
    try {
      await apiPost('/api/portfolio/goals', { title: goalTitle, why: goalWhy, target_date: goalDate });
      setGoalTitle(''); setGoalWhy(''); setGoalDate(''); load();
    } catch (e) { alert(e.message); }
    setBusy(false);
  };

  const activeGoals = (goals || []).filter(g => g.status !== 'completed');
  const doneGoals = (goals || []).filter(g => g.status === 'completed');

  return (
    <div className="space-y-6 animate-fade-in-up max-w-3xl" data-testid="portfolio-page">
      <div>
        <div className="flex items-center gap-2 mb-1">
          <Backpack size={20} weight="duotone" className="text-[#D4AF37]" />
          <h1 className="text-xl text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>My Portfolio</h1>
        </div>
        <p className="text-xs text-[#94A3B8]">Yours to keep and carry forward — your work, your reflections, your goals.</p>
      </div>

      <div className="flex gap-2">
        {[['portfolio', 'Portfolio'], ['goals', 'My Goals']].map(([k, label]) => (
          <button key={k} onClick={() => setTab(k)}
            className={`px-4 py-1.5 rounded text-xs border transition-colors ${
              tab === k ? 'text-[#D4AF37] border-[#D4AF37]/40 bg-[#D4AF37]/10' : 'text-[#94A3B8] border-[#1E293B] bg-[#050814]'
            }`}
            data-testid={`tab-${k}`}>
            {label}
          </button>
        ))}
      </div>

      {tab === 'portfolio' && (
        <div className="space-y-4">
          <AddItemCard onAdded={load} />

          {portfolio?.recognitions?.length > 0 && (
            <div>
              <p className="text-[10px] tracking-[0.15em] uppercase text-[#D4AF37] mb-2 flex items-center gap-1">
                <Medal size={12} /> Recognitions
              </p>
              <div className="grid sm:grid-cols-2 gap-2">
                {portfolio.recognitions.map((r, i) => (
                  <div key={i} className="flex items-center gap-2 p-2.5 rounded border border-[#D4AF37]/25 bg-[#D4AF37]/5">
                    <Medal size={16} weight="duotone" className="text-[#D4AF37] flex-shrink-0" />
                    <div className="min-w-0">
                      <p className="text-xs text-[#F8FAFC] truncate">{r.title}</p>
                      <p className="text-[9px] text-[#94A3B8]">
                        Completed{r.completed_at ? ` · ${new Date(r.completed_at).toLocaleDateString()}` : ''}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="space-y-3">
            {(portfolio?.items || []).map(item => (
              <ItemCard key={item.id} item={item} onChanged={load} />
            ))}
            {portfolio && portfolio.items.length === 0 && (
              <Card className="bg-[#0F172A] border-[#1E293B]">
                <CardContent className="p-6 text-center">
                  <p className="text-sm text-[#94A3B8]">
                    Nothing here yet. Add work you're proud of, or a reflection on where you've been —
                    this collection is yours for life.
                  </p>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      )}

      {tab === 'goals' && (
        <div className="space-y-4">
          <Card className="bg-[#0F172A] border-[#1E293B]">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
                Set a goal
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <input value={goalTitle} onChange={e => setGoalTitle(e.target.value)} placeholder="What are you walking toward?" className={inputCls} data-testid="goal-title" />
              <input value={goalWhy} onChange={e => setGoalWhy(e.target.value)} placeholder="Why does it matter to you? (optional)" className={inputCls} />
              <div className="flex gap-2">
                <input type="date" value={goalDate} onChange={e => setGoalDate(e.target.value)} className={inputCls} />
                <Button size="sm" onClick={addGoal} disabled={busy || !goalTitle.trim()} className={`${goldBtnCls} whitespace-nowrap`} data-testid="save-goal">
                  <Plus size={13} className="mr-1" /> Set goal
                </Button>
              </div>
            </CardContent>
          </Card>

          <div className="space-y-3">
            {activeGoals.map(g => <GoalCard key={g.id} goal={g} onChanged={load} />)}
            {doneGoals.length > 0 && (
              <p className="text-[10px] tracking-[0.15em] uppercase text-[#D4AF37] pt-2">Completed</p>
            )}
            {doneGoals.map(g => <GoalCard key={g.id} goal={g} onChanged={load} />)}
            {goals && goals.length === 0 && (
              <Card className="bg-[#0F172A] border-[#1E293B]">
                <CardContent className="p-6 text-center">
                  <p className="text-sm text-[#94A3B8]">
                    No goals yet. Name one thing you're walking toward — your goals are private to you.
                  </p>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
