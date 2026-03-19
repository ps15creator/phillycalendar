// Service Worker for offline support
const CACHE_NAME = 'philly-calendar-v22';
const urlsToCache = [
    '/',
    '/static/styles.css?v=33',
    '/static/app.js?v=11'
];

// Install service worker
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(urlsToCache))
    );
    self.skipWaiting();
});

// Network-first for API calls, cache-first for static assets
self.addEventListener('fetch', event => {
    const url = event.request.url;
    const isApi = url.includes('/events') || new URL(url).pathname.startsWith('/stats');

    if (isApi) {
        event.respondWith(
            fetch(event.request)
                .then(fetchResponse => {
                    if (fetchResponse.ok) {
                        caches.open(CACHE_NAME).then(cache => {
                            cache.put(event.request, fetchResponse.clone());
                        });
                    }
                    return fetchResponse;
                })
                .catch(() => caches.match(event.request))
        );
    } else {
        event.respondWith(
            caches.match(event.request)
                .then(response => response || fetch(event.request))
        );
    }
});

// Clean up old caches
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheName !== CACHE_NAME) {
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
});
