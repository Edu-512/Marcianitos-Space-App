export default function(component) {
  const { parentElement, data, setStateValue, setTriggerValue } = component;
  const root = parentElement.querySelector('.assistant-root');
  if (!root) return;
  const q = selector => root.querySelector(selector);
  const fab = q('.surco-fab'), panel = q('.surco-panel'), input = q('textarea');
  const body = q('.chat-body'), send = q('.send'), status = q('.chat-status');
  let busy = Boolean(data.busy);
  let enabled = Boolean(data.enabled);
  // The DOM lives only for this user's Streamlit session; never persist messages to storage.
  if (root.dataset.plot !== data.plot_id) {
    root.dataset.plot = data.plot_id;
    input.value = '';
    root._renderedMessages = null;
  }
  root.querySelectorAll('img').forEach(img => { if (img.src !== data.avatar) img.src = data.avatar; });
  q('.chat-context').textContent = `Hablemos de ${data.plot_name}`;
  const controls = () => {
    send.disabled = busy || !enabled || !input.value.trim() || !navigator.onLine;
    input.disabled = busy || !enabled || !navigator.onLine;
    q('.clear').disabled = busy || !data.messages?.length;
    root.querySelectorAll('[data-prompt]').forEach(button => { button.disabled = busy || !enabled || !navigator.onLine; });
    status.textContent = !navigator.onLine ? 'Sin conexión. Vuelve a conectarte para charlar.' :
      !enabled ? 'El asistente no está disponible por el momento. Puedes seguir explorando tu campo.' :
      busy ? 'Don Surco está consultando tu campo…' : 'Listo para echarte una mano.';
  };
  const setOpen = (open, emit = true) => {
    const changed = root.classList.contains('is-open') !== open;
    root.classList.toggle('is-open', open);
    q('.surco-scrim').hidden = !open;
    panel.inert = !open;
    fab.setAttribute('aria-expanded', String(open));
    if (changed) {
      if (open) requestAnimationFrame(() => q('.close').focus());
      else fab.focus();
    }
    if (emit) setStateValue('open', open);
  };
  fab.onclick = () => setOpen(true);
  q('.close').onclick = () => setOpen(false);
  q('.surco-scrim').onclick = () => setOpen(false);
  panel.onkeydown = event => {
    if (event.key === 'Escape') { event.preventDefault(); setOpen(false); }
    if (event.key !== 'Tab') return;
    const focusable = [...panel.querySelectorAll('button:not(:disabled),textarea:not(:disabled),[tabindex="0"],summary')]
      .filter(element => !element.closest('[hidden]'));
    if (!focusable.length) return;
    const active = parentElement.activeElement || document.activeElement;
    if (event.shiftKey && active === focusable[0]) { event.preventDefault(); focusable.at(-1).focus(); }
    else if (!event.shiftKey && active === focusable.at(-1)) { event.preventDefault(); focusable[0].focus(); }
  };
  const submit = text => {
    const value = text.trim();
    if (busy || !enabled || !navigator.onLine || !value || value.length > 2000) return;
    busy = true;
    controls();
    input.value = '';
    root._renderedMessages = null;
    setTriggerValue('submit', { text:value, id:crypto.randomUUID(), plot_id:data.plot_id });
  };
  q('form').onsubmit = event => { event.preventDefault(); submit(input.value); };
  input.oninput = controls;
  input.onkeydown = event => {
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
      event.preventDefault(); submit(input.value);
    }
  };
  root.querySelectorAll('[data-prompt]').forEach(button => { button.onclick = () => submit(button.dataset.prompt); });
  q('.clear').onclick = () => { q('.clear-confirm').hidden = false; q('.keep').focus(); };
  q('.keep').onclick = () => { q('.clear-confirm').hidden = true; q('.clear').focus(); };
  q('.confirm').onclick = () => {
    if (busy) return;
    q('.clear-confirm').hidden = true;
    setTriggerValue('clear', { plot_id:data.plot_id });
  };

  // All user/model/tool content is inserted as text, never as HTML.
  const textNode = (tag, text, className) => {
    const element = document.createElement(tag);
    element.textContent = text;
    if (className) element.className = className;
    return element;
  };
  const friendlyKey = key => key.replaceAll('_', ' ').replaceAll('pct', '%');
  const flatten = (value, prefix = '') => {
    if (!value || typeof value !== 'object') return [[prefix || 'Resultado', String(value ?? 'Sin datos')]];
    return Object.entries(value).flatMap(([key, item]) => {
      const label = prefix ? `${prefix} · ${friendlyKey(key)}` : friendlyKey(key);
      if (Array.isArray(item)) return [[label, item.map(v => typeof v === 'object' ? 'Consultar detalle del modelo' : String(v)).join(', ')]];
      if (item && typeof item === 'object') return flatten(item, label);
      return [[label, String(item ?? 'Sin datos')]];
    }).slice(0, 18);
  };
  const digest = JSON.stringify(data.messages || []);
  if (root._renderedMessages !== digest) {
    const nearBottom = body.scrollHeight - body.scrollTop - body.clientHeight < 80;
    const expanded = new Set([...root.querySelectorAll('.tool-step[open]')].map(el => el.dataset.step));
    const fragment = document.createDocumentFragment();
    (data.messages || []).forEach((message, index) => {
      const article = textNode('article', '', `message ${message.role}${message.error ? ' error' : ''}`);
      article.append(textNode('p', message.role === 'user' ? 'TÚ' : 'DON SURCO', 'message-label'));
      if (message.content) article.append(textNode('div', message.content, 'message-content'));
      (message.steps || []).forEach((step, stepIndex) => {
        const details = document.createElement('details');
        details.className = 'tool-step'; details.dataset.step = `${index}-${stepIndex}`;
        details.open = expanded.has(details.dataset.step);
        details.append(textNode('summary', `✓ ${step.label}`));
        const dl = document.createElement('dl');
        for (const [key, value] of flatten(step.payload)) dl.append(textNode('dt', key), textNode('dd', value));
        details.append(dl); article.append(details);
      });
      fragment.append(article);
    });
    q('.messages').replaceChildren(fragment);
    q('.welcome').hidden = Boolean(data.messages?.length);
    root._renderedMessages = digest;
    if (nearBottom || !root._hasRendered) body.scrollTop = body.scrollHeight;
    root._hasRendered = true;
  }
  controls();
  setOpen(Boolean(data.open), false);
  window.addEventListener('online', controls);
  window.addEventListener('offline', controls);
  return () => {
    window.removeEventListener('online', controls);
    window.removeEventListener('offline', controls);
  };
}
