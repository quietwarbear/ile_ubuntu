import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { apiPost } from './api';
import { fetchFileTokens, fileIdsIn, signFileUrls } from './fileAccess';
import { ProtectedVideo } from '../components/course/LessonVideoPlayer';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

jest.mock('./api', () => ({
  BACKEND_URL: 'https://api.test',
  apiPost: jest.fn(),
  apiUpload: jest.fn(),
  apiPut: jest.fn(),
}));

const ID = '11111111-2222-3333-4444-555555555555';
const OTHER = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee';

describe('signing stored file URLs', () => {
  test('finds every file id in lesson content', () => {
    const text = `![](https://api.test/api/files/${ID}/download)\nhttps://api.test/api/files/${OTHER}/download?file=a.pdf`;
    expect(fileIdsIn(text).sort()).toEqual([ID, OTHER].sort());
  });

  test('puts the token first so a trailing .pdf still ends the URL', () => {
    const text = `https://api.test/api/files/${ID}/download?file=notes.pdf`;
    const out = signFileUrls(text, { [ID]: { token: 'TOK' } });
    expect(out).toBe(`https://api.test/api/files/${ID}/download?t=TOK&file=notes.pdf`);
    expect(/\.pdf(\?|$)/.test(out)).toBe(true);
  });

  test('relative URLs become absolute and stale tokens are replaced', () => {
    const out = signFileUrls(`/api/files/${ID}/stream?t=OLD`, { [ID]: { token: 'NEW' } });
    expect(out).toBe(`https://api.test/api/files/${ID}/stream?t=NEW`);
  });

  test('files without a token are left alone (signed out, no access)', () => {
    const text = `https://api.test/api/files/${ID}/download`;
    expect(signFileUrls(text, {})).toBe(text);
  });

  test('a failed token request yields no tokens rather than throwing', async () => {
    apiPost.mockRejectedValueOnce(new Error('Session ID required'));
    await expect(fetchFileTokens([ID])).resolves.toEqual({});
  });
});

describe('ProtectedVideo', () => {
  let container;
  let root;

  beforeEach(() => {
    apiPost.mockReset();
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
  });

  const flush = () => act(async () => { await Promise.resolve(); await Promise.resolve(); });

  test('plays from a tokenized stream URL with downloads disabled', async () => {
    apiPost.mockResolvedValue({ tokens: { [ID]: { token: 'T1', url: `/api/files/${ID}/stream?t=T1` } } });
    act(() => root.render(<ProtectedVideo fileId={ID} />));
    await flush();
    const video = container.querySelector('video');
    expect(video.getAttribute('src')).toBe(`https://api.test/api/files/${ID}/stream?t=T1`);
    expect(video.getAttribute('controlsList')).toBe('nodownload');
    expect(apiPost).toHaveBeenCalledWith('/api/files/access-tokens', { file_ids: [ID] });
  });

  test('fetches a fresh token when the link expires mid-playback', async () => {
    apiPost
      .mockResolvedValueOnce({ tokens: { [ID]: { token: 'T1', url: `/api/files/${ID}/stream?t=T1` } } })
      .mockResolvedValueOnce({ tokens: { [ID]: { token: 'T2', url: `/api/files/${ID}/stream?t=T2` } } });
    act(() => root.render(<ProtectedVideo fileId={ID} />));
    await flush();
    act(() => { container.querySelector('video').dispatchEvent(new Event('error')); });
    await flush();
    expect(container.querySelector('video').getAttribute('src')).toContain('t=T2');
  });

  test('shows an access message when no token is granted', async () => {
    apiPost.mockResolvedValue({ tokens: {} });
    act(() => root.render(<ProtectedVideo fileId={ID} />));
    await flush();
    expect(container.querySelector('video')).toBeNull();
    expect(container.querySelector('[data-testid="video-unavailable"]')).not.toBeNull();
  });
});
