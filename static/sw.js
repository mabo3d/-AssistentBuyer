const CACHE='assistentbuyer-v1-shell';
const ASSETS=['/','/manifest.webmanifest','/icon.svg'];
self.addEventListener('install',e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS))));
self.addEventListener('activate',e=>e.waitUntil(self.clients.claim()));
self.addEventListener('fetch',e=>{
  if(e.request.method!=='GET'||new URL(e.request.url).pathname.startsWith('/api/')) return;
  e.respondWith(fetch(e.request).catch(()=>caches.match(e.request)));
});
