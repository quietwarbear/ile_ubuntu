import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '../ui/card';
import { Button } from '../ui/button';
import { apiGet, apiPost } from '../../lib/api';

// Roster import (I1): one CSV of registrants → accounts + enrollments, one
// course per session. Upload → preview with the session mapping → confirm →
// report. The server does the reading; this only shows it.

export function readFileText(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ''));
    reader.onerror = () => reject(new Error('Could not read that file'));
    reader.readAsText(file);
  });
}

export function mappingFrom(sessions = []) {
  const map = {};
  sessions.forEach(s => { if (s.course_id) map[s.label] = s.course_id; });
  return map;
}

export function allMapped(sessions = []) {
  return sessions.length > 0 && sessions.every(s => s.course_id);
}

const muted = 'text-[rgb(var(--text-muted))]';
const selectClass = 'text-xs px-2 py-1 rounded border bg-[rgb(var(--ink-deep))] text-[rgb(var(--text-main))] border-[rgb(var(--ink-border))]';

function Counts({ counts, done }) {
  if (!counts) return null;
  const items = done
    ? [['created', 'new accounts'], ['enrolled', 'enrollments added'], ['skipped', 'already enrolled'], ['errors', 'rows with problems'], ['welcome_emails', 'welcome emails going out']]
    : [['created', 'new accounts to create'], ['enrolled', 'enrollments to add'], ['skipped', 'already enrolled'], ['errors', 'rows with problems']];
  return (
    <ul className="grid grid-cols-2 sm:grid-cols-4 gap-2" data-testid={done ? 'import-report-counts' : 'import-preview-counts'}>
      {items.map(([key, label]) => (
        <li key={key} className="rounded border border-[rgb(var(--ink-border))] p-2">
          <p className="text-base text-[rgb(var(--gold))]">{counts[key] ?? 0}</p>
          <p className={`text-[10px] ${muted}`}>{label}</p>
        </li>
      ))}
    </ul>
  );
}

function RowErrors({ errors }) {
  if (!errors?.length) return null;
  return (
    <div data-testid="import-errors">
      <p className="text-xs text-amber-400 mb-1">Rows that won't be imported:</p>
      <ul className={`text-[11px] ${muted} space-y-0.5 max-h-40 overflow-auto`}>
        {errors.map((e, i) => (
          <li key={`${e.row}-${i}`}>Row {e.row}{e.email ? ` (${e.email})` : ''}: {e.error}</li>
        ))}
      </ul>
    </div>
  );
}

export function BulkEnrollmentImport() {
  const [courses, setCourses] = useState([]);
  const [csv, setCsv] = useState('');
  const [fileName, setFileName] = useState('');
  const [preview, setPreview] = useState(null);
  const [report, setReport] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    apiGet('/api/enrollment-imports/courses').then(setCourses).catch(() => setCourses([]));
  }, []);

  const runPreview = async (text, sessionMap) => {
    setBusy(true); setError('');
    try {
      setPreview(await apiPost('/api/enrollment-imports/preview', { csv: text, session_map: sessionMap }));
    } catch (err) { setError(err.message); setPreview(null); }
    finally { setBusy(false); }
  };

  const onFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setReport(null);
    try {
      const text = await readFileText(file);
      setCsv(text); setFileName(file.name);
      await runPreview(text, {});
    } catch (err) { setError(err.message); }
  };

  const onMap = (label, courseId) => {
    const sessions = preview.sessions.map(s => (s.label === label ? { ...s, course_id: courseId || null } : s));
    setPreview({ ...preview, sessions });
    runPreview(csv, mappingFrom(sessions));
  };

  const confirm = async () => {
    setBusy(true); setError('');
    try {
      setReport(await apiPost('/api/enrollment-imports', { csv, session_map: mappingFrom(preview.sessions) }));
      setPreview(null);
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  };

  const reset = () => { setCsv(''); setFileName(''); setPreview(null); setReport(null); setError(''); };

  return (
    <Card className="bg-[rgb(var(--ink-card))] border-[rgb(var(--ink-border))]" data-testid="bulk-enrollment-import">
      <CardContent className="p-4 space-y-3">
        <div>
          <h3 className="text-sm text-[rgb(var(--text-main))]">Enroll a list of people</h3>
          <p className={`text-[11px] ${muted}`}>
            Upload a CSV with the columns <strong>name, email, sessions</strong>. Put several sessions in one
            cell separated by <code>;</code>. Each session goes to one of your courses — including private ones.
            Anyone without an account gets one. Everyone newly enrolled gets a welcome email naming their
            course(s), with a sign-in link that needs no password. Running the same file again only adds (and
            emails) who's new.
          </p>
        </div>

        {!preview && !report && (
          <label className="inline-flex items-center gap-2 text-xs text-[rgb(var(--gold))] cursor-pointer">
            <input type="file" accept=".csv,text/csv" onChange={onFile} disabled={busy}
              className="text-xs" data-testid="import-file" aria-label="Roster CSV file" />
          </label>
        )}

        {error && <p className="text-xs text-red-400" role="alert" data-testid="import-error">{error}</p>}

        {preview && (
          <div className="space-y-3" data-testid="import-preview">
            <p className={`text-xs ${muted}`}>
              {fileName} · {preview.total_rows} row{preview.total_rows === 1 ? '' : 's'}. First rows:
            </p>
            <div className="overflow-x-auto">
              <table className="w-full text-[11px]">
                <thead><tr className={muted}><th className="text-left pr-2">Name</th><th className="text-left pr-2">Email</th><th className="text-left">Sessions</th></tr></thead>
                <tbody>
                  {preview.preview_rows.map(r => (
                    <tr key={r.row} className="text-[rgb(var(--text-main))]">
                      <td className="pr-2">{r.name}</td><td className="pr-2">{r.email}</td><td>{r.sessions.join('; ')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="space-y-1">
              <p className="text-xs text-[rgb(var(--text-main))]">Which course is each session?</p>
              {preview.sessions.map(s => (
                <div key={s.label} className="flex items-center gap-2">
                  <span className="text-xs text-[rgb(var(--text-main))] min-w-[8rem]">{s.label}</span>
                  <select value={s.course_id || ''} onChange={e => onMap(s.label, e.target.value)}
                    className={selectClass} aria-label={`Course for ${s.label}`} data-testid={`map-${s.label}`}>
                    <option value="">Choose a course…</option>
                    {courses.map(c => (
                      <option key={c.id} value={c.id}>{c.title}{c.visibility === 'private' ? ' (private)' : ''}</option>
                    ))}
                  </select>
                </div>
              ))}
            </div>

            <Counts counts={preview.report?.counts} />
            <RowErrors errors={preview.report?.errors} />

            <div className="flex gap-2">
              <Button onClick={confirm} disabled={busy || !allMapped(preview.sessions)}
                className="bg-[rgb(var(--gold))] text-[rgb(var(--ink-deep))] hover:bg-[rgb(var(--gold-soft))]"
                data-testid="import-confirm">
                {busy ? 'Working…' : 'Enroll everyone'}
              </Button>
              <Button variant="ghost" onClick={reset} disabled={busy} className={muted}>Cancel</Button>
            </div>
            {!allMapped(preview.sessions) && (
              <p className={`text-[11px] ${muted}`}>Choose a course for every session to continue.</p>
            )}
          </div>
        )}

        {report && (
          <div className="space-y-3" data-testid="import-report">
            <p className="text-xs text-emerald-400">Import finished.</p>
            <Counts counts={{ ...report.counts, welcome_emails: report.welcome_emails ?? 0 }} done />
            <RowErrors errors={report.errors} />
            <Button variant="ghost" onClick={reset} className="text-[rgb(var(--gold))]">Import another file</Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default BulkEnrollmentImport;
