const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../pwa/service-worker.js'), 'utf8');

function worker(fetchImpl) {
  const events = {}, precached = [], removed = [];
  const offline = new Response('offline screen');
  const cache = { addAll: async urls => precached.push(...urls), match: async () => offline };
  vm.runInNewContext(source, {
    URL, Response,
    self: { registration: { scope: 'https://field.example/' }, clients: { claim: async () => {} },
      addEventListener: (name, handler) => { events[name] = handler; } },
    caches: { open: async () => cache,
      keys: async () => ['field-shift-pwa:/:v0', 'field-shift-pwa:/:v2', 'another-app'],
      delete: async name => removed.push(name) },
    fetch: fetchImpl,
  });
  return { events, precached, removed, offline };
}
async function navigation(w) {
  let response;
  w.events.fetch({ request: { method: 'GET', mode: 'navigate', url: 'https://field.example/' },
    respondWith: p => { response = p; } });
  return response;
}
test('precache only public offline screen and icons', async () => {
  const w = worker(); let pending;
  w.events.install({ waitUntil: p => { pending = p; } }); await pending;
  assert.equal(w.precached.length, 5);
  assert.ok(w.precached.every(url => /\/pwa\/(offline\.html|icons\/[^/]+\.png)$/.test(url)));
});
test('fresh online shell and offline fallback on disconnect or server failure', async () => {
  const live = new Response('live shell');
  assert.equal(await navigation(worker(async () => live)), live);
  const down = worker(async () => { throw new TypeError('offline'); });
  assert.equal(await navigation(down), down.offline);
  const unavailable = worker(async () => new Response('', { status:503 }));
  assert.equal(await navigation(unavailable), unavailable.offline);
  const forbidden = new Response('', { status:403 });
  assert.equal(await navigation(worker(async () => forbidden)), forbidden);
});
test('only older caches from this app and scope are deleted', async () => {
  const w = worker(); let pending;
  w.events.activate({ waitUntil: p => { pending = p; } }); await pending;
  assert.deepEqual(w.removed, ['field-shift-pwa:/:v0']);
});
test('APIs, assets, non-GET requests and other origins stay on network', () => {
  const w = worker();
  for (const request of [
    { method:'POST', mode:'navigate', url:'https://field.example/' },
    { method:'GET', mode:'navigate', url:'https://other.example/' },
    { method:'GET', mode:'cors', url:'https://field.example/_stcore/health' },
    { method:'GET', mode:'navigate', url:'https://field.example/_stcore/health' },
    { method:'GET', mode:'cors', url:'https://field.example/static/main.js' },
  ]) w.events.fetch({ request, respondWith: () => assert.fail('unexpected interception') });
});
