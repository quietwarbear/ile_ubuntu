const CACHE_NAME = 'ile-ubuntu-v5';
const API_CACHE = 'ile-api-v1';

// Offline tolerance (eval §11.3): community programs run in gyms, basements,
// and buses. The app shell and the API data you've already seen stay readable
// when connectivity dies; writes still require a connection.
//
// - App shell + hashed static assets: cached, so the app boots offline.
// - GET /api/* JSON: network-first with cache fallback (any origin — the API
//   lives on a different host than the page).
// - Media (/api/files/*) is never cached: downloads redirect to short-lived
//   presigned URLs and videos would blow the cache.
// - The API cache is personal data; the app clears it on logout (see
//   clearOfflineCache() in lib/api.js — the cache name must match there).

const API_CACHE_MAX_ENTRIES = 300;

// Install - precache the shell entry AND every built asset (from CRA's
// asset-manifest.json) so the app boots offline even if the first online
// visit ended before the worker controlled the page.
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(async (cache) => {
      await cache.add('/').catch(() => {});
      // Brand images live in public/, not the CRA asset manifest.
      await Promise.all(
        ['/favicon.png', '/icon-192.png', '/icon-512.png', '/manifest.json']
          .map((p) => cache.add(p).catch(() => {}))
      );
      try {
        const manifest = await (await fetch('/asset-manifest.json')).json();
        const assets = Object.values(manifest.files || {})
          .filter((p) => typeof p === 'string' && p.startsWith('/'))
          // main bundle + route chunks + css; skip sourcemaps
          .filter((p) => !p.endsWith('.map'));
        await Promise.all(assets.map((p) => cache.add(p).catch(() => {})));
      } catch (e) { /* precache is best-effort; runtime caching still applies */ }
    })
  );
  self.skipWaiting();
});

// Activate - claim clients and clear caches from older versions
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((names) =>
      Promise.all(
        names
          .filter((n) => n !== CACHE_NAME && n !== API_CACHE)
          .map((n) => caches.delete(n))
      )
    ).then(() => self.clients.claim())
  );
});

function isApiGet(request) {
  if (request.method !== 'GET') return false;
  const url = new URL(request.url);
  if (!url.pathname.startsWith('/api/')) return false;
  // Media and auth flows must never come from cache: file downloads redirect
  // to expiring presigned URLs; OAuth redirects are one-shot.
  if (url.pathname.startsWith('/api/files/')) return false;
  if (url.pathname.startsWith('/api/auth/google')) return false;
  if (url.pathname.startsWith('/api/auth/apple')) return false;
  return true;
}

async function trimApiCache() {
  try {
    const cache = await caches.open(API_CACHE);
    const keys = await cache.keys();
    if (keys.length > API_CACHE_MAX_ENTRIES) {
      // keys() is oldest-first in practice; drop the oldest chunk.
      await Promise.all(keys.slice(0, 50).map((k) => cache.delete(k)));
    }
  } catch (e) { /* cache trim is best-effort */ }
}

async function apiNetworkFirst(request) {
  const cache = await caches.open(API_CACHE);
  try {
    const response = await fetch(request);
    if (response.ok) {
      cache.put(request, response.clone());
      trimApiCache();
    }
    return response;
  } catch (e) {
    const cached = await cache.match(request);
    if (cached) return cached;
    throw e;
  }
}

// Fetch routing
self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  // API data (cross-origin to the page): network-first, cache fallback
  if (isApiGet(request)) {
    event.respondWith(apiNetworkFirst(request));
    return;
  }

  // Everything below is same-origin only
  if (!request.url.startsWith(self.location.origin)) return;

  // Navigation (HTML pages): network-first; offline falls back to the cached
  // request, then to the shell entry ('/') so client-side routes still boot.
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response.ok) {
            caches.open(CACHE_NAME).then((c) => c.put('/', response.clone())).catch(() => {});
          }
          return response;
        })
        .catch(() =>
          caches.match(request).then((cached) => cached || caches.match('/'))
        )
    );
    return;
  }

  // Static assets: stale-while-revalidate
  if (request.url.includes('/static/')) {
    event.respondWith(
      caches.open(CACHE_NAME).then((cache) =>
        cache.match(request).then((cached) => {
          const fetched = fetch(request).then((response) => {
            if (response.ok) cache.put(request, response.clone());
            return response;
          }).catch(() => cached);
          return cached || fetched;
        })
      )
    );
    return;
  }

  // Everything else: network-first
  event.respondWith(
    fetch(request).catch(() => caches.match(request))
  );
});

// Logout: the app asks us to drop the personal API cache (shared devices).
self.addEventListener('message', (event) => {
  if (event.data === 'clear-api-cache') {
    event.waitUntil(caches.delete(API_CACHE));
  }
});

// Push notification handling
self.addEventListener('push', (event) => {
  let data = { title: 'The Ile Ubuntu', body: 'New notification', url: '/dashboard' };
  try {
    if (event.data) data = Object.assign(data, JSON.parse(event.data.text()));
  } catch (e) {
    if (event.data) data.body = event.data.text();
  }

  const options = {
    body: data.body,
    icon: data.icon || '/logo192.png',
    badge: data.badge || '/logo192.png',
    vibrate: [100, 50, 100],
    data: { url: data.url || '/dashboard' },
    actions: [
      { action: 'open', title: 'View' },
      { action: 'close', title: 'Dismiss' },
    ],
  };

  event.waitUntil(self.registration.showNotification(data.title, options));
});

// Handle notification clicks
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = event.notification.data?.url || '/';
  if (event.action !== 'close') {
    event.waitUntil(
      self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clients) => {
        for (const client of clients) {
          if (client.url.includes(self.location.origin)) {
            client.focus();
            client.navigate(url);
            return;
          }
        }
        return self.clients.openWindow(url);
      })
    );
  }
});
