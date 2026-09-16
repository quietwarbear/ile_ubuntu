import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { apiGet, apiPost, apiDelete, apiUpload } from '../../lib/api';

const when = (v) => {
  if (!v) return '';
  const d = new Date(v);
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleString(undefined, {
    month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
  });
};

const kb = (bytes) => (!bytes ? '' : `${Math.max(1, Math.round(bytes / 1024))} KB`);

/**
 * Work handed in against a lesson. Students see only their own; teachers see
 * the class. Files are fetched through the submission's own download-link
 * endpoint, which checks who is asking — /api/files/{id}/download does not.
 */
export function LessonSubmissions({ courseId, lessonId, user, isInstructor }) {
  const base = `/api/courses/${courseId}/lessons/${lessonId}/submissions`;
  const fileRef = useRef(null);

  const [mine, setMine] = useState(null);
  const [all, setAll] = useState([]);
  const [note, setNote] = useState('');
  const [links, setLinks] = useState('');
  const [picked, setPicked] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [open, setOpen] = useState(false);

  const load = useCallback(async () => {
    try {
      if (isInstructor) {
        const res = await apiGet(base);
        setAll(res.submissions || []);
      } else {
        const res = await apiGet(`${base}/mine`);
        setMine(res.submission || null);
      }
    } catch (e) { setError(e.message); }
  }, [base, isInstructor]);

  useEffect(() => { if (open) load(); }, [open, load]);

  const download = async (submissionId, file) => {
    setError('');
    try {
      const res = await apiGet(`${base}/${submissionId}/download-link/${file.id}`);
      window.open(res.url, '_blank', 'noopener');
    } catch (e) { setError(e.message); }
  };

  const submit = async () => {
    setBusy(true); setError('');
    try {
      const fileIds = [];
      for (const f of picked) {
        const form = new FormData();
        form.append('file', f);
        // Deliberately no lesson_id/course_id: those fields put a file into
        // the course-wide listing, which has no enrolment check.
        const up = await apiUpload('/api/files/upload', form);
        fileIds.push(up.file.id);
      }
      const existing = (mine?.files || []).map(f => f.id);
      await apiPost(base, {
        note,
        links: links.split('\n').map(s => s.trim()).filter(Boolean),
        file_ids: [...existing, ...fileIds],
      });
      setPicked([]); setNote(''); setLinks('');
      if (fileRef.current) fileRef.current.value = '';
      await load();
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  };

  const withdraw = async (submission) => {
    if (!window.confirm('Withdraw this work? The files are deleted and cannot be recovered.')) return;
    setBusy(true); setError('');
    try {
      await apiDelete(`${base}/${submission.id}`);
      await load();
      setMine(null);
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  };

  const Attachments = ({ submission }) => (
    <>
      {(submission.files || []).map(f => (
        <button key={f.id} onClick={() => download(submission.id, f)}
          className="mr-2 mt-1 inline-flex items-center gap-1 rounded border border-[rgb(var(--ink-border))] bg-[rgb(var(--ink-card))] px-2 py-1 text-[11px] text-[rgb(var(--text-softer))] hover:border-[rgb(var(--gold)/0.4)]"
          data-testid={`download-${f.id}`}>
          {f.original_filename} <span className="text-[rgb(var(--text-dim))]">{kb(f.file_size)}</span>
        </button>
      ))}
      {(submission.links || []).map((url, i) => (
        <a key={i} href={url} target="_blank" rel="noopener noreferrer"
          className="mr-2 mt-1 inline-block max-w-full truncate rounded border border-[rgb(var(--ink-border))] bg-[rgb(var(--ink-card))] px-2 py-1 text-[11px] text-[rgb(var(--gold))] hover:underline">
          {url}
        </a>
      ))}
    </>
  );

  return (
    <div className="mt-4 rounded border border-[rgb(var(--ink-border))] bg-[rgb(var(--ink-deep))] p-3" data-testid="lesson-submissions">
      <button onClick={() => setOpen(v => !v)}
        className="flex w-full items-center justify-between text-left"
        data-testid="toggle-submissions">
        <span className="text-xs font-medium tracking-wide text-[rgb(var(--gold))]">
          {isInstructor ? 'Submitted Work' : 'Your Work'}
        </span>
        <span className="text-[10px] text-[rgb(var(--text-muted))]">{open ? 'Hide' : 'Show'}</span>
      </button>

      {open && (
        <div className="mt-3 space-y-3">
          {isInstructor ? (
            all.length === 0 ? (
              <p className="text-xs text-[rgb(var(--text-muted))]">Nothing handed in yet.</p>
            ) : all.map(s => (
              <div key={s.id} className="rounded border border-[rgb(var(--ink-border))] bg-[rgb(var(--ink-card))] p-3"
                data-testid={`submission-${s.id}`}>
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <span className="text-sm text-[rgb(var(--text-main))]">{s.student_name}</span>
                  <span className="text-[10px] text-[rgb(var(--text-muted))]">
                    {when(s.updated_at || s.submitted_at)}
                  </span>
                </div>
                {s.student_email && (
                  <p className="text-[10px] text-[rgb(var(--text-dim))] break-all">{s.student_email}</p>
                )}
                {s.note && <p className="mt-2 whitespace-pre-wrap text-xs text-[rgb(var(--text-softer))]">{s.note}</p>}
                <div className="mt-1"><Attachments submission={s} /></div>
              </div>
            ))
          ) : (
            <>
              {mine && (
                <div className="rounded border border-[rgb(var(--ink-border))] bg-[rgb(var(--ink-card))] p-3" data-testid="my-submission">
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <span className="text-xs text-emerald-400">Handed in</span>
                    <span className="text-[10px] text-[rgb(var(--text-muted))]">
                      {when(mine.updated_at || mine.submitted_at)}
                    </span>
                  </div>
                  {mine.note && <p className="mt-2 whitespace-pre-wrap text-xs text-[rgb(var(--text-softer))]">{mine.note}</p>}
                  <div className="mt-1"><Attachments submission={mine} /></div>
                  <Button onClick={() => withdraw(mine)} disabled={busy} size="sm" variant="ghost"
                    className="mt-2 text-[rgb(var(--text-muted))] hover:text-red-400 text-[11px]"
                    data-testid="withdraw-submission">
                    Withdraw
                  </Button>
                </div>
              )}

              <div className="space-y-2">
                <input ref={fileRef} type="file" multiple
                  onChange={e => setPicked(Array.from(e.target.files || []))}
                  className="block w-full text-[11px] text-[rgb(var(--text-muted))] file:mr-2 file:rounded file:border-0 file:bg-[rgb(var(--gold))] file:px-3 file:py-1 file:text-[11px] file:text-[rgb(var(--ink-deep))]"
                  data-testid="submission-files" />
                <textarea value={links} onChange={e => setLinks(e.target.value)} rows={2}
                  placeholder="Links, one per line — a Google Doc, a Drive file…"
                  className="w-full rounded-md border border-[rgb(var(--ink-border))] bg-[rgb(var(--ink-card))] p-2 text-xs text-[rgb(var(--text-main))] focus:border-[rgb(var(--gold)/0.5)] focus:outline-none"
                  data-testid="submission-links" />
                <textarea value={note} onChange={e => setNote(e.target.value)} rows={2}
                  placeholder="Anything you want your teacher to know (optional)"
                  className="w-full rounded-md border border-[rgb(var(--ink-border))] bg-[rgb(var(--ink-card))] p-2 text-xs text-[rgb(var(--text-main))] focus:border-[rgb(var(--gold)/0.5)] focus:outline-none"
                  data-testid="submission-note" />
                <Button onClick={submit} size="sm"
                  disabled={busy || (!picked.length && !links.trim() && !note.trim())}
                  className="bg-[rgb(var(--gold))] text-[rgb(var(--ink-deep))] hover:bg-[rgb(var(--gold-soft))] text-xs"
                  data-testid="submit-work">
                  {busy ? 'Sending…' : mine ? 'Add to my work' : 'Hand in work'}
                </Button>
                {mine && (
                  <p className="text-[10px] text-[rgb(var(--text-dim))]">
                    Adding keeps what you already handed in. To replace a file, withdraw first.
                  </p>
                )}
              </div>
            </>
          )}
          {error && <p className="text-[11px] text-red-400" data-testid="submission-error">{error}</p>}
        </div>
      )}
    </div>
  );
}
