import { apiGet, apiPost } from './api';

// I4 phase 2: lesson video goes straight from the browser to Cloudflare Stream
// over tus (resumable upload), so a multi-gigabyte recording never passes
// through our server. The server only hands out the one-time upload URL
// (POST /api/stream/uploads) after checking the caller is course staff.

// Cloudflare: chunks must be the same size throughout, a multiple of 256 KiB,
// and at least 5 MiB (except the last). 50 MiB is their recommendation.
export const CHUNK_SIZE = 50 * 1024 * 1024;
const MAX_ATTEMPTS = 4;

let configPromise = null;

/** {enabled, caption_languages, max_duration_seconds}; disabled on any error. */
export function streamConfig() {
  if (!configPromise) {
    configPromise = apiGet('/api/stream/config').catch(() => ({ enabled: false }));
  }
  return configPromise;
}

export function resetStreamConfig() { configPromise = null; }

const wait = (ms) => new Promise((r) => setTimeout(r, ms));

async function sendChunk(uploadUrl, blob, offset, fetchImpl) {
  const res = await fetchImpl(uploadUrl, {
    method: 'PATCH',
    headers: {
      'Tus-Resumable': '1.0.0',
      'Upload-Offset': String(offset),
      'Content-Type': 'application/offset+octet-stream',
    },
    body: blob,
  });
  if (res.status !== 204 && res.status !== 200) {
    throw new Error(`Upload stopped (${res.status})`);
  }
  const next = Number(res.headers?.get?.('Upload-Offset'));
  return Number.isFinite(next) && next > offset ? next : offset + blob.size;
}

async function serverOffset(uploadUrl, fetchImpl) {
  const res = await fetchImpl(uploadUrl, { method: 'HEAD', headers: { 'Tus-Resumable': '1.0.0' } });
  const n = Number(res.headers?.get?.('Upload-Offset'));
  return Number.isFinite(n) ? n : null;
}

/**
 * Upload `file` to Stream for a lesson. Returns the new file id, which the
 * lesson stores as video_file_id exactly like an S3 upload.
 * onProgress(fraction 0..1) is called after each chunk.
 */
export async function uploadToStream(file, {
  courseId, lessonId, onProgress, fetchImpl = fetch, sleep = wait,
} = {}) {
  const { file_id: fileId, upload_url: uploadUrl } = await apiPost('/api/stream/uploads', {
    course_id: courseId,
    lesson_id: lessonId,
    size: file.size,
    filename: file.name,
    mime_type: file.type || 'video/mp4',
  });

  let offset = 0;
  let attempts = 0;
  while (offset < file.size) {
    const end = Math.min(offset + CHUNK_SIZE, file.size);
    try {
      offset = await sendChunk(uploadUrl, file.slice(offset, end), offset, fetchImpl);
      attempts = 0;
      onProgress?.(offset / file.size);
    } catch (err) {
      attempts += 1;
      if (attempts >= MAX_ATTEMPTS) throw err;
      await sleep(1000 * attempts);
      // Resume from wherever Cloudflare says it got to.
      try {
        const known = await serverOffset(uploadUrl, fetchImpl);
        // Chunk size must stay constant, so only resume on a chunk boundary.
        if (known !== null && known % CHUNK_SIZE === 0) offset = known;
      } catch (e) { /* retry the same chunk */ }
    }
  }
  try { await apiPost(`/api/stream/${fileId}/refresh`, {}); } catch (e) { /* checked again on view */ }
  return fileId;
}
