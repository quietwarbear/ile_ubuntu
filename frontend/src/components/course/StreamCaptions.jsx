import React, { useEffect, useState } from 'react';
import { Button } from '../ui/button';
import { ClosedCaptioning, Trash, PencilSimple, Upload, Sparkle } from '@phosphor-icons/react';
import { apiGet, apiPost, apiPut, apiDelete } from '../../lib/api';

/**
 * I5: captions for a streamed lesson video, for course staff only.
 * Automatic captions are requested when the video finishes processing; here
 * staff can generate another language, upload a .vtt, or fix a track's text.
 * Viewers see captions off by default and turn them on with the player's CC
 * button. Renders nothing for videos that aren't on Stream.
 */
export default function StreamCaptions({ fileId }) {
  const [data, setData] = useState(null);
  const [lang, setLang] = useState('en');
  const [editing, setEditing] = useState(null); // {lang, text}
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const load = async () => {
    try { setData(await apiGet(`/api/stream/${fileId}/captions`)); }
    catch (e) { setData(null); }
  };

  useEffect(() => { setData(null); setEditing(null); load(); }, [fileId]);

  if (!data) return null;

  const run = async (fn) => {
    setBusy(true); setError('');
    try { await fn(); await load(); }
    catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };

  const generate = () => run(() => apiPost(`/api/stream/${fileId}/captions/${lang}/generate`, {}));
  const remove = (code) => run(() => apiDelete(`/api/stream/${fileId}/captions/${code}`));
  const startEdit = (code) => run(async () => {
    const res = await apiGet(`/api/stream/${fileId}/captions/${code}/vtt`);
    setEditing({ lang: code, text: res.vtt || '' });
  });
  const save = () => run(async () => {
    await apiPut(`/api/stream/${fileId}/captions/${editing.lang}`, { vtt: editing.text });
    setEditing(null);
  });
  const upload = (e) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;
    run(async () => {
      const text = await file.text();
      await apiPut(`/api/stream/${fileId}/captions/${lang}`, { vtt: text });
    });
  };

  const small = 'text-[10px] h-7 text-[rgb(var(--gold))] hover:text-[rgb(var(--gold-soft))]';

  return (
    <div className="space-y-2 rounded-md border border-[rgb(var(--ink-border))] p-3" data-testid="stream-captions">
      <span className="text-[10px] tracking-[0.15em] uppercase text-[rgb(var(--gold))] flex items-center gap-1">
        <ClosedCaptioning size={12} weight="duotone" /> Captions
      </span>
      {!data.ready && (
        <p className="text-xs text-[rgb(var(--text-muted))]">
          The video is still processing. Automatic captions start once it's ready.
        </p>
      )}
      {data.captions.length === 0 && data.ready && (
        <p className="text-xs text-[rgb(var(--text-muted))]" data-testid="no-captions">No captions yet.</p>
      )}
      <ul className="space-y-1">
        {data.captions.map((t) => (
          <li key={t.language} className="flex items-center gap-2 text-xs text-[rgb(var(--text-main))]" data-testid={`caption-${t.language}`}>
            <span className="flex-1">
              {t.label || t.language}{t.generated ? ' (automatic)' : ''}
              {t.status !== 'ready' && <span className="text-[rgb(var(--text-muted))]"> · {t.status === 'inprogress' ? 'generating…' : t.status}</span>}
            </span>
            {t.status === 'ready' && (
              <Button size="sm" variant="ghost" className={small} disabled={busy} onClick={() => startEdit(t.language)}>
                <PencilSimple size={12} className="mr-1" /> Edit
              </Button>
            )}
            <Button size="sm" variant="ghost" className="text-[10px] h-7 text-red-400" disabled={busy} onClick={() => remove(t.language)}
              aria-label={`Remove ${t.language} captions`}>
              <Trash size={12} />
            </Button>
          </li>
        ))}
      </ul>

      {editing ? (
        <div className="space-y-2">
          <textarea
            value={editing.text}
            onChange={(e) => setEditing({ ...editing, text: e.target.value })}
            rows={10}
            aria-label={`Captions (${editing.lang})`}
            className="w-full font-mono text-[11px] p-2 rounded bg-[rgb(var(--ink-deep))] border border-[rgb(var(--ink-border))] text-[rgb(var(--text-main))]"
          />
          <div className="flex gap-2">
            <Button size="sm" disabled={busy} onClick={save} data-testid="save-captions"
              className="bg-[rgb(var(--gold))] text-[rgb(var(--ink-deep))] hover:bg-[rgb(var(--gold-soft))] text-xs">Save captions</Button>
            <Button size="sm" variant="ghost" onClick={() => setEditing(null)} className="text-xs text-[rgb(var(--text-muted))]">Cancel</Button>
          </div>
        </div>
      ) : (
        <div className="flex flex-wrap items-center gap-2">
          <select value={lang} onChange={(e) => setLang(e.target.value)} aria-label="Caption language"
            className="h-7 text-xs rounded bg-[rgb(var(--ink-deep))] border border-[rgb(var(--ink-border))] text-[rgb(var(--text-main))]">
            {data.languages.map((code) => <option key={code} value={code}>{code}</option>)}
          </select>
          <Button size="sm" variant="ghost" className={small} disabled={busy || !data.ready} onClick={generate} data-testid="generate-captions">
            <Sparkle size={12} className="mr-1" /> Generate automatically
          </Button>
          <label className={`cursor-pointer flex items-center px-2 ${small}`}>
            <Upload size={12} className="mr-1" /> Upload .vtt
            <input type="file" accept=".vtt,text/vtt" className="hidden" onChange={upload} disabled={busy} data-testid="upload-vtt" />
          </label>
        </div>
      )}
      {error && <p className="text-xs text-red-400" role="alert">{error}</p>}
    </div>
  );
}
