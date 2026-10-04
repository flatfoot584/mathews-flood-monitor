// Network first: never describe cached flood conditions as current.
const CACHE='mathews-resident-v3';
const SHELL=['./index.html','./alerts.html','./guide.html','./about.html','./assets/community.css','./assets/community.js','./assets/tailwind.css','./assets/chart.umd.min.js','./assets/leaflet.js','./assets/icon.svg'];
self.addEventListener('install',event=>{event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(SHELL)));self.skipWaiting();});
self.addEventListener('activate',event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(key=>key!==CACHE).map(key=>caches.delete(key)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',event=>{
  if(event.request.method!=='GET'||new URL(event.request.url).origin!==self.location.origin)return;
  event.respondWith(fetch(event.request,{cache:'no-cache'}).then(response=>{if(response.ok){const copy=response.clone();event.waitUntil(caches.open(CACHE).then(cache=>cache.put(event.request,copy)));}return response;}).catch(async()=>{const cached=await caches.match(event.request,{ignoreSearch:event.request.mode==='navigate'});if(cached)return cached;return new Response('Offline. This information has not been saved. Flood conditions cannot be confirmed.',{status:503,headers:{'Content-Type':'text/plain'}});}));
});
