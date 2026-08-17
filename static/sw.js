const CACHE_NAME = "orakelia-public-v1";
const PUBLIC_ASSETS = [
  "/static/style.css",
  "/static/script.js",
  "/static/install.js",
  "/static/manifest.webmanifest",
  "/static/icons/orakelia-180.png",
  "/static/icons/orakelia-192.png",
  "/static/icons/orakelia-512.png"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PUBLIC_ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((names) => Promise.all(names.filter((name) => name !== CACHE_NAME).map((name) => caches.delete(name))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") {
    return;
  }

  const url = new URL(request.url);
  if (url.origin !== self.location.origin || url.pathname.startsWith("/static/uploads/")) {
    return;
  }

  if (!url.pathname.startsWith("/static/")) {
    event.respondWith(fetch(request));
    return;
  }

  event.respondWith(
    caches.match(request).then((cached) => {
      const fresh = fetch(request).then((response) => {
        if (response.ok && response.type === "basic") {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
        }
        return response;
      });
      return cached || fresh;
    })
  );
});
