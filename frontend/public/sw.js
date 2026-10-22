// PRAHARI Service Worker — SIH 26186
// SECURITY: Never cache auth tokens, CSRF tokens, session cookies, or private API responses.
// Navigation requests (page loads) are always fetched live — never intercepted or cached.
const CACHE_NAME = "prahari-v2";
const STATIC_ASSETS = ["/manifest.json", "/icon.svg"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const { request } = event;

  // 1. Never intercept navigation requests (page loads/router pushes).
  //    Let the browser handle them directly — this prevents the "FetchEvent navigation
  //    error for /login?" and ensures Next.js router.push() works cleanly.
  if (request.mode === "navigate") {
    return; // browser default: fresh network fetch
  }

  // 2. Never intercept API calls — operational data must always be live.
  if (request.url.includes("/api/")) {
    return;
  }

  // 3. Only handle cacheable static GET assets.
  if (request.method !== "GET") {
    return;
  }

  // 4. Network-first for everything else (static assets with cache fallback).
  event.respondWith(
    fetch(request).catch(() => caches.match(request))
  );
});
