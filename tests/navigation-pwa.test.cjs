const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

test('all native navigation URLs retain the offline fallback without intercepting API paths', async () => {
  const handlers = {};
  const fallback = new Response('offline screen');
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../pwa/service-worker.js'), 'utf8'), {
    URL, Response,
    self: { registration: { scope:'https://field.example/' }, addEventListener:(key,fn) => handlers[key]=fn },
    caches: { open:async () => ({ match:async () => fallback }) },
    fetch:async () => { throw new TypeError('offline'); },
  });
  for (const page of ['', 'mi-terreno', 'comparar', 'recomendaciones']) {
    let response;
    handlers.fetch({ request: { method:'GET',mode:'navigate',url:'https://field.example/'+page }, respondWith:p => response=p });
    assert.equal(await response, fallback);
  }
  handlers.fetch({ request:{ method:'GET',mode:'navigate',url:'https://field.example/_stcore/health' }, respondWith:() => assert.fail('API intercepted') });
});
