import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { apiGet, apiPost, apiPut } from '../../lib/api';
import { ProtectedVideo } from './LessonVideoPlayer';
import StreamCaptions from './StreamCaptions';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

jest.mock('../../lib/api', () => ({
  BACKEND_URL: 'https://api.test',
  apiGet: jest.fn(), apiPost: jest.fn(), apiPut: jest.fn(), apiDelete: jest.fn(), apiUpload: jest.fn(),
}));

const flush = () => act(() => new Promise((r) => setTimeout(r, 0)));
let container;
let root;

beforeEach(() => {
  [apiGet, apiPost, apiPut].forEach((m) => m.mockReset());
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
});
afterEach(() => { act(() => root.unmount()); container.remove(); });

test('a streamed video plays in the signed Stream player, captions not forced on', async () => {
  apiPost.mockResolvedValueOnce({ tokens: { f1: { token: 't', url: '/x', stream: {
    state: 'ready', iframe_url: 'https://customer-abc.cloudflarestream.com/TOKEN/iframe?preload=metadata' } } } });
  act(() => root.render(<ProtectedVideo fileId="f1" />));
  await flush();
  const frame = container.querySelector('[data-testid="stream-video"]');
  expect(frame.getAttribute('src')).toContain('cloudflarestream.com/TOKEN/iframe');
  expect(frame.getAttribute('src')).not.toContain('defaultTextTrack');
  expect(container.querySelector('video')).toBeNull();
});

test('a video still processing says so instead of playing', async () => {
  apiPost.mockResolvedValueOnce({ tokens: { f1: { token: 't', url: '/x', stream: { state: 'inprogress' } } } });
  act(() => root.render(<ProtectedVideo fileId="f1" />));
  await flush();
  expect(container.querySelector('[data-testid="video-processing"]').textContent).toContain('still processing');
});

test('an S3 video still uses the plain player', async () => {
  apiPost.mockResolvedValueOnce({ tokens: { f1: { token: 't', url: '/api/files/f1/stream?t=t' } } });
  act(() => root.render(<ProtectedVideo fileId="f1" />));
  await flush();
  expect(container.querySelector('video').getAttribute('src')).toBe('https://api.test/api/files/f1/stream?t=t');
});

describe('StreamCaptions', () => {
  const listing = (captions) => ({ captions, ready: true, languages: ['en', 'es'] });

  test('renders nothing for videos that are not on Stream', async () => {
    apiGet.mockRejectedValueOnce(new Error('Not a streamed video'));
    act(() => root.render(<StreamCaptions fileId="f1" />));
    await flush();
    expect(container.innerHTML).toBe('');
  });

  test('lists tracks and edits one', async () => {
    apiGet.mockResolvedValueOnce(listing([{ language: 'en', label: 'English', generated: true, status: 'ready' }]))
      .mockResolvedValueOnce({ vtt: 'WEBVTT\n\nhello' })
      .mockResolvedValueOnce(listing([{ language: 'en', label: 'English', generated: true, status: 'ready' }]))
      .mockResolvedValue(listing([{ language: 'en', label: 'English', generated: false, status: 'ready' }]));
    apiPut.mockResolvedValue({ success: true });
    act(() => root.render(<StreamCaptions fileId="f1" />));
    await flush();
    expect(container.querySelector('[data-testid="caption-en"]').textContent).toContain('English (automatic)');

    await act(async () => { container.querySelector('[data-testid="caption-en"] button').click(); });
    await flush();
    const area = container.querySelector('textarea');
    expect(area.value).toBe('WEBVTT\n\nhello');
    await act(async () => {
      Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set.call(area, 'WEBVTT\n\nfixed');
      area.dispatchEvent(new Event('input', { bubbles: true }));
    });
    await act(async () => { container.querySelector('[data-testid="save-captions"]').click(); });
    await flush();
    expect(apiPut).toHaveBeenCalledWith('/api/stream/f1/captions/en', { vtt: 'WEBVTT\n\nfixed' });
  });

  test('generates automatic captions in the chosen language', async () => {
    apiGet.mockResolvedValue(listing([]));
    apiPost.mockResolvedValue({ success: true });
    act(() => root.render(<StreamCaptions fileId="f1" />));
    await flush();
    await act(async () => { container.querySelector('[data-testid="generate-captions"]').click(); });
    await flush();
    expect(apiPost).toHaveBeenCalledWith('/api/stream/f1/captions/en/generate', {});
  });
});
