import React from 'react';
import { BACKEND_URL } from '../../lib/api';
import { useStableSrc } from '../../lib/fileAccess';

// Signed URL from the token refresh, else the one the listing returned
// (already signed by the server), never a bare /api/files path.
export function fileHref(file, signed) {
  const fresh = signed?.[file.id]?.download_url;
  if (fresh) return fresh;
  return file.download_url ? `${BACKEND_URL}${file.download_url}` : undefined;
}

// An open PDF must not reload when tokens refresh behind it.
export function StableFrame({ src, ...rest }) {
  const stable = useStableSrc(src);
  return <iframe src={stable} {...rest} />;
}
