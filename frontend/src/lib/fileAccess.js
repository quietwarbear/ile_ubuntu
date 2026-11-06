import { useEffect, useRef, useState } from 'react';
import { BACKEND_URL, apiPost } from './api';

// /api/files/{id}/download and /stream check who is asking. <video>, <iframe>,
// <img> and plain links can't send the X-Session-ID header, so they carry a
// short-lived playback token (?t=) instead, issued per user and per file by
// POST /api/files/access-tokens. Tokens last ten minutes; REFRESH_MS renews
// them before that for anything that stays on screen.

export const REFRESH_MS = 8 * 60 * 1000;

// Matches stored file URLs, absolute or relative, with or without a query.
const FILE_URL_RE = /((?:https?:\/\/[^\s"')]+)?\/api\/files\/([0-9a-f-]{36})\/(download|stream))(\?[^\s"')]*)?/gi;

export function fileIdsIn(text) {
  if (!text) return [];
  const ids = new Set();
  for (const m of String(text).matchAll(FILE_URL_RE)) ids.add(m[2].toLowerCase());
  return [...ids];
}

/** {fileId: {token, url, download_url, expires_at}}; {} when signed out or on error. */
export async function fetchFileTokens(ids) {
  const unique = [...new Set((ids || []).filter(Boolean))];
  if (!unique.length) return {};
  try {
    const res = await apiPost('/api/files/access-tokens', { file_ids: unique });
    return res?.tokens || {};
  } catch (e) {
    return {};
  }
}

/** Rewrite every /api/files URL in `text` to carry its token. The token goes
 * first in the query so a trailing "?file=x.pdf" still ends the URL — the
 * lesson viewer recognises PDF embeds by that ending. */
export function signFileUrls(text, tokens) {
  if (!text || !tokens) return text;
  return String(text).replace(FILE_URL_RE, (whole, base, id, kind, query) => {
    const tok = tokens[id.toLowerCase()]?.token;
    if (!tok) return whole;
    const rest = (query || '').replace(/^\?/, '').replace(/(^|&)t=[^&]*/g, '').replace(/^&/, '');
    const abs = base.startsWith('http') ? base : `${BACKEND_URL}${base}`;
    return `${abs}?t=${encodeURIComponent(tok)}${rest ? `&${rest}` : ''}`;
  });
}

/** Signed absolute URLs for a set of file ids, renewed every REFRESH_MS while
 * mounted. Pass {refresh: false} for things that must not reload (an open
 * PDF frame), or use useStableSrc on the result. */
export function useSignedFileUrls(ids, { refresh = true } = {}) {
  const key = [...new Set((ids || []).filter(Boolean))].sort().join(',');
  const [urls, setUrls] = useState({});

  useEffect(() => {
    let cancelled = false;
    const list = key ? key.split(',') : [];
    const load = async () => {
      const tokens = await fetchFileTokens(list);
      if (cancelled) return;
      const out = {};
      for (const [id, t] of Object.entries(tokens)) {
        out[id] = { url: `${BACKEND_URL}${t.url}`, download_url: `${BACKEND_URL}${t.download_url}` };
      }
      setUrls(out);
    };
    if (!list.length) { setUrls({}); return undefined; }
    load();
    const timer = refresh ? setInterval(load, REFRESH_MS) : null;
    return () => { cancelled = true; if (timer) clearInterval(timer); };
  }, [key, refresh]);

  return urls;
}

/** Keeps the first non-empty src, so a token refresh doesn't reload a frame
 * the reader is already in. */
export function useStableSrc(src) {
  const ref = useRef(null);
  if (!ref.current && src) ref.current = src;
  return ref.current || src;
}
