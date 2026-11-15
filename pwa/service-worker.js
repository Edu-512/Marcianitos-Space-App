/* Only the public offline screen and icons are cached. Never farm/session data. */
const ROOT = new URL(self.registration.scope);
const CACHE_PREFIX = `field-shift-pwa:${ROOT.pathname}:`;
const CACHE_NAME = `${CACHE_PREFIX}v1`;
const OFFLINE_URL = new URL("pwa/offline.html", ROOT).href;
const PUBLIC_FILES = [
  OFFLINE_URL,
  new URL("pwa/icons/icon-192.png", ROOT).href,
  new URL("pwa/icons/icon-512.png", ROOT).href,
  new URL("pwa/icons/icon-maskable-512.png", ROOT).href,
  new URL("pwa/icons/apple-touch-icon.png", ROOT).href,
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(PUBLIC_FILES)));
  // Updated workers wait for existing tabs to close; never interrupt a farm session.
});

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter((key) => key.startsWith(CACHE_PREFIX) && key !== CACHE_NAME)
      .map((key) => caches.delete(key)));
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== ROOT.origin) return;
  if (request.mode !== "navigate") return;
  // Leave Streamlit HTTP APIs, static assets and WebSockets to the network.
  if (url.pathname !== ROOT.pathname && url.pathname !== `${ROOT.pathname}index.html`) return;
  event.respondWith((async () => {
    try {
      const response = await fetch(request);
      if (response.status < 500) return response;
    } catch (_) {
      // No internet or the server is unreachable.
    }
    const cache = await caches.open(CACHE_NAME);
    return (await cache.match(OFFLINE_URL)) || Response.error();
  })());
});
