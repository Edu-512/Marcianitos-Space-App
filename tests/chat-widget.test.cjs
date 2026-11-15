const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { JSDOM } = require('../.venv/js-tests/node_modules/jsdom');
const dir = path.join(__dirname, '../components/chat_frontend');
const html = fs.readFileSync(path.join(dir, 'chat.html'), 'utf8');
const source = fs.readFileSync(path.join(dir, 'chat.js'), 'utf8');

function setup(overrides = {}) {
  const dom = new JSDOM(`<main>${html}</main>`, { url:'http://localhost:8769/', runScripts:'outside-only', pretendToBeVisual:true });
  const w = dom.window;
  w.requestAnimationFrame = callback => callback();
  w.eval(source.replace('export default function(component)', 'window.mountChat = function(component)'));
  const events = [];
  const data = { avatar:'./avatar.png', plot_id:'lote-norte', plot_name:'North Field', messages:[], busy:false, enabled:true, open:false, ...overrides };
  let cleanup;
  const render = changes => {
    Object.assign(data, changes);
    if (cleanup) cleanup();
    cleanup = w.mountChat({ parentElement:w.document.querySelector('main'), data,
      setStateValue:(name,value) => { events.push({ name,value }); data[name] = value; },
      setTriggerValue:(name,value) => events.push({ name,value }) });
  };
  render({});
  return { dom, w, data, events, render, q:selector => w.document.querySelector(selector) };
}

test('bubble opens panel, Escape closes it, and focus returns to bubble', () => {
  const t = setup();
  assert.equal(t.q('.surco-fab').getAttribute('aria-expanded'), 'false');
  t.q('.surco-fab').click();
  assert.equal(t.q('.surco-fab').getAttribute('aria-expanded'), 'true');
  assert.equal(t.q('.surco-panel').inert, false);
  assert.equal(t.w.document.activeElement, t.q('.close'));
  t.q('.surco-panel').dispatchEvent(new t.w.KeyboardEvent('keydown', { key:'Escape', bubbles:true }));
  assert.equal(t.q('.surco-panel').inert, true);
  assert.equal(t.w.document.activeElement, t.q('.surco-fab'));
  t.dom.window.close();
});

test('submit emits one request, blocks duplicate submissions and includes plot context', () => {
  const t = setup();
  t.q('textarea').value = 'How is my plot doing?';
  t.q('textarea').dispatchEvent(new t.w.Event('input'));
  for (let i=0; i<2; i++) t.q('form').dispatchEvent(new t.w.Event('submit', { cancelable:true }));
  const submissions = t.events.filter(e => e.name === 'submit');
  assert.equal(submissions.length, 1);
  assert.equal(submissions[0].value.plot_id, 'lote-norte');
  assert.equal(submissions[0].value.text, 'How is my plot doing?');
  assert.ok(submissions[0].value.id);
  assert.equal(t.q('.send').disabled, true);
  t.dom.window.close();
});

test('draft survives rerenders; switching plots clears it', () => {
  const t = setup();
  t.q('textarea').value = 'My draft';
  t.render({ open:true });
  assert.equal(t.q('textarea').value, 'My draft');
  t.render({ plot_id:'lote-sur' });
  assert.equal(t.q('textarea').value, '');
  t.dom.window.close();
});

test('tool output is expandable and all external content is text, never executable HTML', () => {
  const dangerous = '<img src=x onerror="alert(1)">';
  const t = setup({ messages:[{ role:'assistant', content:dangerous, steps:[{ label:'Humedad', payload:{ value:dangerous } }] }] });
  assert.equal(t.q('.message-content').textContent, dangerous);
  assert.equal(t.q('.message-content img'), null);
  assert.equal(t.q('.tool-step').open, false);
  t.q('.tool-step').open = true;
  t.render({ messages:[...t.data.messages, { role:'user', content:'Gracias' }] });
  assert.equal(t.q('.tool-step').open, true);
  assert.equal(t.q('.tool-step img'), null);
  t.dom.window.close();
});

test('clear requires confirmation; missing service or network blocks submission', () => {
  const t = setup({ messages:[{ role:'user', content:'Hola' }] });
  t.q('.clear').click();
  assert.equal(t.events.filter(e => e.name === 'clear').length, 0);
  t.q('.confirm').click();
  assert.equal(t.events.filter(e => e.name === 'clear').length, 1);
  t.render({ enabled:false });
  assert.equal(t.q('textarea').disabled, true);
  t.q('form').dispatchEvent(new t.w.Event('submit', { cancelable:true }));
  assert.equal(t.events.filter(e => e.name === 'submit').length, 0);
  t.render({ enabled:true });
  Object.defineProperty(t.w.navigator, 'onLine', { configurable:true, value:false });
  t.w.dispatchEvent(new t.w.Event('offline'));
  assert.equal(t.q('.send').disabled, true);
  assert.match(t.q('.chat-status').textContent, /offline/i);
  t.dom.window.close();
});
