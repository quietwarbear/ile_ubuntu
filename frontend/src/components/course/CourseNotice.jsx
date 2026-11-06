import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '../ui/card';
import { Button } from '../ui/button';
import WysiwygEditor from './WysiwygEditor';
import LessonContentViewer from '../LessonContentViewer';
import { apiGet, apiPut } from '../../lib/api';

// Organizer-written notice at the top of a course page (I7): sharing rules,
// credits, acknowledgments. The server only returns it to this course's staff
// and enrolled students; anyone else gets 404 and sees nothing here.
export function CourseNotice({ courseId, canRead, canEdit }) {
  const [body, setBody] = useState('');
  const [draft, setDraft] = useState('');
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let live = true;
    setBody('');
    if (!canRead) return undefined;
    apiGet(`/api/courses/${courseId}/notice`)
      .then(res => { if (live) setBody(res.body || ''); })
      .catch(() => { /* 404 = no notice */ });
    return () => { live = false; };
  }, [courseId, canRead]);

  const save = async () => {
    setBusy(true); setError('');
    try {
      const res = await apiPut(`/api/courses/${courseId}/notice`, { body: draft });
      setBody(res.body || '');
      setEditing(false);
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  };

  if (!canRead) return null;
  if (!body && !canEdit) return null;

  if (editing) {
    return (
      <Card className="bg-[rgb(var(--ink-card))] border-[rgb(var(--gold)/0.3)]" data-testid="course-notice-editor">
        <CardContent className="p-4 space-y-3">
          <p className="text-xs tracking-[0.15em] uppercase text-[rgb(var(--gold))]">Course notice</p>
          <p className="text-[11px] text-[rgb(var(--text-muted))]">
            Shown at the top of this page to enrolled students and course staff only. Use it for sharing rules, credits and acknowledgments.
          </p>
          <WysiwygEditor value={draft} onChange={setDraft} minHeight={120}
            placeholder="For example: please don't share recordings outside this course. Thanks to everyone who made these sessions possible."
            testId="course-notice-input" />
          {error && <p className="text-xs text-red-400" role="alert">{error}</p>}
          <div className="flex gap-2">
            <Button size="sm" onClick={save} disabled={busy}
              className="bg-[rgb(var(--gold))] text-[rgb(var(--ink-deep))] hover:bg-[rgb(var(--gold-soft))] text-xs"
              data-testid="course-notice-save">{busy ? 'Saving…' : 'Save notice'}</Button>
            <Button size="sm" variant="ghost" onClick={() => setEditing(false)} disabled={busy}
              className="text-xs text-[rgb(var(--text-muted))]">Cancel</Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!body) {
    return (
      <button type="button" onClick={() => { setDraft(''); setEditing(true); }}
        className="text-xs text-[rgb(var(--gold))] hover:underline" data-testid="course-notice-add">
        + Add a course notice (sharing rules, credits, acknowledgments)
      </button>
    );
  }

  return (
    <Card className="bg-[rgb(var(--gold)/0.05)] border-[rgb(var(--gold)/0.3)]" data-testid="course-notice">
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-3">
          <p className="text-[10px] tracking-[0.15em] uppercase text-[rgb(var(--gold))] mb-2">From the course organizers</p>
          {canEdit && (
            <button type="button" onClick={() => { setDraft(body); setEditing(true); }}
              className="text-[11px] text-[rgb(var(--text-muted))] hover:text-[rgb(var(--gold))]"
              data-testid="course-notice-edit">Edit</button>
          )}
        </div>
        <LessonContentViewer content={body} />
      </CardContent>
    </Card>
  );
}

export default CourseNotice;
