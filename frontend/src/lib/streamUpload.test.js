import { apiGet, apiPost } from './api';
import { CHUNK_SIZE, resetStreamConfig, streamConfig, uploadToStream } from './streamUpload';

jest.mock('./api', () => ({ apiGet: jest.fn(), apiPost: jest.fn() }));

const fakeFile = (size) => ({
  size, name: 'talk.mov', type: 'video/quicktime',
  slice: (a, b) => ({ size: b - a, start: a }),
});
const response = (status, offset) => ({ status, headers: { get: (h) => (h === 'Upload-Offset' && offset != null ? String(offset) : null) } });

beforeEach(() => { apiGet.mockReset(); apiPost.mockReset(); resetStreamConfig(); });

test('chunk size follows the Stream rules (256 KiB multiple, at least 5 MiB)', () => {
  expect(CHUNK_SIZE % (256 * 1024)).toBe(0);
  expect(CHUNK_SIZE).toBeGreaterThanOrEqual(5 * 1024 * 1024);
});

test('stream is off when the config call fails', async () => {
  apiGet.mockRejectedValueOnce(new Error('offline'));
  await expect(streamConfig()).resolves.toEqual({ enabled: false });
});

test('uploads a large file straight to Cloudflare in tus chunks', async () => {
  const size = CHUNK_SIZE * 2 + 1234;
  apiPost.mockResolvedValueOnce({ file_id: 'f1', upload_url: 'https://upload.test/u1' })
    .mockResolvedValueOnce({});
  const offsets = [];
  const fetchImpl = jest.fn(async (url, init) => {
    offsets.push(Number(init.headers['Upload-Offset']));
    return response(204, Number(init.headers['Upload-Offset']) + init.body.size);
  });
  const progress = [];
  const id = await uploadToStream(fakeFile(size), { courseId: 'c1', lessonId: 'l1', onProgress: (p) => progress.push(p), fetchImpl });

  expect(id).toBe('f1');
  expect(apiPost).toHaveBeenNthCalledWith(1, '/api/stream/uploads', expect.objectContaining({ course_id: 'c1', lesson_id: 'l1', size }));
  expect(offsets).toEqual([0, CHUNK_SIZE, CHUNK_SIZE * 2]);
  expect(fetchImpl.mock.calls[0][0]).toBe('https://upload.test/u1');
  expect(fetchImpl.mock.calls[0][1].headers['Tus-Resumable']).toBe('1.0.0');
  expect(progress[progress.length - 1]).toBe(1);
  expect(apiPost).toHaveBeenLastCalledWith('/api/stream/f1/refresh', {});
});

test('retries a failed chunk and gives up after repeated failures', async () => {
  apiPost.mockResolvedValue({ file_id: 'f1', upload_url: 'https://upload.test/u1' });
  const fetchImpl = jest.fn(async (url, init) => (init.method === 'HEAD' ? response(200, 0) : response(500)));
  await expect(uploadToStream(fakeFile(10), { courseId: 'c1', fetchImpl, sleep: () => Promise.resolve() }))
    .rejects.toThrow('Upload stopped (500)');
  expect(fetchImpl.mock.calls.filter(([, init]) => init.method === 'PATCH')).toHaveLength(4);
});

test('a dropped chunk resumes and the upload finishes', async () => {
  apiPost.mockResolvedValue({ file_id: 'f1', upload_url: 'https://upload.test/u1' });
  let failOnce = true;
  const fetchImpl = jest.fn(async (url, init) => {
    if (init.method === 'HEAD') return response(200, 0);
    if (failOnce) { failOnce = false; throw new Error('network'); }
    return response(204, 10);
  });
  await expect(uploadToStream(fakeFile(10), { courseId: 'c1', fetchImpl, sleep: () => Promise.resolve() }))
    .resolves.toBe('f1');
});
