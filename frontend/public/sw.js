const CACHE_NAME = 'ile-ubuntu-v2';
const urlsToCache = [
  '/',
  '/static/js/bundle.js',
  '/static/css/main.css',
  '/manifest.json'
];

// Install event - cache resources
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('Opened cache');
        return cache.addAll(urlsToCache);
      })
      .catch((error) => {
        console.log('Cache install failed:', error);
      })
  );
});

// Fetch event - serve cached content when offline
self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request)
      .then((response) => {
        // Return cached version or fetch from network
        if (response) {
          return response;
        }
        return fetch(event.request);
      }
    )
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});

// Push notification handling
self.addEventListener('push', (event) => {
  const options = {
    body: event.data ? event.data.text() : 'New notification from The Ile Ubuntu',
    icon: 'https://customer-assets.emergentagent.com/job_lessonhub-4/artifacts/58m7009f_anhk.png',
    badge: 'https://customer-assets.emergentagent.com/job_lessonhub-4/artifacts/58m7009f_anhk.png',
    vibrate: [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    },
    actions: [
      {
        action: 'explore',
        title: 'View',
        icon: 'https://customer-assets.emergentagent.com/job_lessonhub-4/artifacts/58m7009f_anhk.png'
      },
      {
        action: 'close',
        title: 'Close',
        icon: 'https://customer-assets.emergentagent.com/job_lessonhub-4/artifacts/58m7009f_anhk.png'
      }
    ]
  };

  event.waitUntil(
    self.registration.showNotification('The Ile Ubuntu', options)
  );
});

// Handle notification clicks
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  if (event.action === 'explore') {
    // Open the app
    event.waitUntil(
      self.clients.openWindow('/')
    );
  }
});