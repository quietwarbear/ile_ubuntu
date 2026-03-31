const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

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
};
