const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "https://ileubuntu-production.up.railway.app";

function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return null;
}

function setCookie(name, value, days) {
  const expires = new Date(Date.now() + days * 864e5).toUTCString();
  document.cookie = `${name}=${value}; expires=${expires}; path=/`;
}

function clearCookie(name) {
  document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
}

function getSessionId() {
  return getCookie('session_id');
}

function authHeaders() {
  const sid = getSessionId();
  return sid ? { 'X-Session-ID': sid } : {};
}

async function apiGet(path) {
  const res = await fetch(`${BACKEND_URL}${path}`, { headers: authHeaders() });
  if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
  return res.json();
}

async function apiPost(path, body) {
  const res = await fetch(`${BACKEND_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
  return res.json();
}

async function apiPut(path, body) {
  const res = await fetch(`${BACKEND_URL}${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
  return res.json();
}

async function apiDelete(path) {
  const res = await fetch(`${BACKEND_URL}${path}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
  return res.json();
}

async function apiUpload(path, formData) {
  const res = await fetch(`${BACKEND_URL}${path}`, {
    method: 'POST',
    headers: authHeaders(),
    body: formData,
  });
  if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
  return res.json();
}

function parseTierError(errorMsg) {
  if (!errorMsg) return null;
  if (errorMsg.startsWith('tier_required:')) {
    const parts = errorMsg.split(':');
    return { type: 'tier_required', requiredTier: parts[1], feature: parts[2] };
  }
  if (errorMsg.startsWith('tier_limit:')) {
    const parts = errorMsg.split(':');
    return { type: 'tier_limit', feature: parts[1], tier: parts[2], limit: parseInt(parts[3]) };
  }
  return null;
}

export {
  BACKEND_URL,
  getCookie,
  setCookie,
  clearCookie,
  getSessionId,
  apiGet,
  apiPost,
  apiPut,
  apiDelete,
  apiUpload,
  parseTierError,
};
