/* Service worker: fast repeat visits without serving stale pages.
   - Pages (HTML): network first, cached copy only when offline.
   - Site assets (CSS, JS, images): stale-while-revalidate.
   - Google Fonts files: cache first (they are immutable).
   Bump VERSION on each release to retire old caches. */
const VERSION = 'wb-20261128e';
const PRECACHE = [
  '/',
  '/assets/css/style.css?v=20261128e',
  '/assets/js/main.js?v=20261128e',
  '/assets/img/waleed-albadawi.jpg',
  '/assets/img/favicon.svg'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(VERSION).then((cache) => cache.addAll(PRECACHE)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

function staleWhileRevalidate(request) {
  return caches.open(VERSION).then((cache) =>
    cache.match(request).then((cached) => {
      const network = fetch(request)
        .then((response) => {
          if (response && (response.ok || response.type === 'opaque')) cache.put(request, response.clone());
          return response;
        })
        .catch(() => cached);
      return cached || network;
    })
  );
}

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);

  // Never intercept analytics.
  if (/googletagmanager|google-analytics|analytics\.google/.test(url.hostname)) return;

  // Google Fonts: stylesheet revalidates, font files are immutable.
  if (url.hostname === 'fonts.gstatic.com') {
    event.respondWith(
      caches.open(VERSION).then((cache) =>
        cache.match(request).then((hit) => hit || fetch(request).then((res) => { cache.put(request, res.clone()); return res; }))
      )
    );
    return;
  }
  if (url.hostname === 'fonts.googleapis.com') {
    event.respondWith(staleWhileRevalidate(request));
    return;
  }

  if (url.origin !== self.location.origin) return;

  // Pages: always try the network so content is never stale.
  if (request.mode === 'navigate' || (request.headers.get('accept') || '').includes('text/html')) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const copy = response.clone();
          caches.open(VERSION).then((cache) => cache.put(request, copy));
          return response;
        })
        .catch(() => caches.match(request).then((hit) => hit || caches.match('/')))
    );
    return;
  }

  // Static assets.
  if (/\.(css|js|png|jpe?g|webp|svg|gif|ico|woff2?)$/.test(url.pathname)) {
    event.respondWith(staleWhileRevalidate(request));
  }
});
