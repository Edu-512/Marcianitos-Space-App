export default function(component) {
  const { parentElement, data, setStateValue, setTriggerValue } = component;
  const root = parentElement.querySelector('.assistant-root');
  if (!root) return;
  const q = selector => root.querySelector(selector);
  const fab = q('.surco-fab'), panel = q('.surco-panel'), input = q('textarea');
  const body = q('.chat-body'), send = q('.send'), status = q('.chat-status');
  const visualViewport = window.visualViewport;
  const isMobile = () => window.matchMedia('(max-width: 767px)').matches;
  let mainScrollState = null;
  const mainElement = () => window.parent.document.querySelector('[data-testid="stMain"]');
  const keepMainScroll = () => {
    if (mainScrollState) mainScrollState.element.scrollTop = mainScrollState.scrollTop;
  };
  const lockMainScroll = () => {
    if (!isMobile() || mainScrollState) return;
    const main = mainElement();
    if (!main) return;
    mainScrollState = {
      element: main,
      scrollTop: main.scrollTop,
      overflowY: main.style.getPropertyValue('overflow-y'),
      overflowPriority: main.style.getPropertyPriority('overflow-y'),
      overscroll: main.style.getPropertyValue('overscroll-behavior-y'),
      overscrollPriority: main.style.getPropertyPriority('overscroll-behavior-y'),
    };
    main.style.setProperty('overflow-y', 'hidden');
    main.style.setProperty('overscroll-behavior-y', 'none');
    main.addEventListener('scroll', keepMainScroll, { passive:true });
    keepMainScroll();
  };
  const restoreMainScroll = () => {
    if (!mainScrollState) return;
    const { element, overflowY, overflowPriority, overscroll, overscrollPriority } = mainScrollState;
    element.removeEventListener('scroll', keepMainScroll);
    if (overflowY) element.style.setProperty('overflow-y', overflowY, overflowPriority);
    else element.style.removeProperty('overflow-y');
    if (overscroll) element.style.setProperty('overscroll-behavior-y', overscroll, overscrollPriority);
    else element.style.removeProperty('overscroll-behavior-y');
    keepMainScroll();
    mainScrollState = null;
  };
  const syncVisualViewport = () => {
    if (!visualViewport || !root.classList.contains('keyboard-open')) return;
    root.style.setProperty('--visual-viewport-height', `${visualViewport.height}px`);
    root.style.setProperty('--visual-viewport-offset-top', `${visualViewport.offsetTop}px`);
    keepMainScroll();
  };
  const handleInputFocus = () => {
    if (!isMobile()) return;
    root.classList.add('keyboard-open');
    lockMainScroll();
    syncVisualViewport();
  };
  const handleInputBlur = () => {
    root.classList.remove('keyboard-open');
    root.style.removeProperty('--visual-viewport-height');
    root.style.removeProperty('--visual-viewport-offset-top');
  };
  let busy = Boolean(data.busy);
  let enabled = Boolean(data.enabled);
  // The DOM lives only for this user's Streamlit session; never persist messages to storage.
  if (root.dataset.plot !== data.plot_id) {
    root.dataset.plot = data.plot_id;
    input.value = '';
    root._renderedMessages = null;
  }
  root.querySelectorAll('img').forEach(img => { if (img.src !== data.avatar) img.src = data.avatar; });
  q('.chat-context').textContent = data.model_context || `Let's talk about ${data.plot_name}`;
  const controls = () => {
    send.disabled = busy || !enabled || !input.value.trim() || !navigator.onLine;
    input.disabled = busy || !enabled || !navigator.onLine;
    q('.clear').disabled = busy || !data.messages?.length;
    root.querySelectorAll('[data-prompt]').forEach(button => { button.disabled = busy || !enabled || !navigator.onLine; });
    status.textContent = !navigator.onLine ? 'You are offline. Reconnect to chat.' :
      !enabled ? 'The assistant is temporarily unavailable. You can keep exploring your field.' :
      busy ? 'Mr Corn is checking your field…' : 'Ready to help.';
  };
  const setOpen = (open, emit = true) => {
    const changed = root.classList.contains('is-open') !== open;
    root.classList.toggle('is-open', open);
    q('.surco-scrim').hidden = !open;
    panel.inert = !open;
    fab.setAttribute('aria-expanded', String(open));
    if (open) lockMainScroll();
    else {
      input.blur();
      handleInputBlur();
      restoreMainScroll();
    }
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
  input.addEventListener('focus', handleInputFocus);
  input.addEventListener('blur', handleInputBlur);
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
      article.append(textNode('p', message.role === 'user' ? 'YOU' : 'DON SURCO', 'message-label'));
      (message.steps || []).forEach((step, stepIndex) => {
        const details = document.createElement('details');
        details.className = 'tool-step'; details.dataset.step = `${index}-${stepIndex}`;
        details.open = expanded.has(details.dataset.step);
        details.append(textNode('summary', `✓ ${step.label}`));
        const dl = document.createElement('dl');
        for (const [key, value] of flatten(step.payload)) dl.append(textNode('dt', key), textNode('dd', value));
        details.append(dl); article.append(details);
      });
      if (message.content) article.append(textNode('div', message.content, 'message-content'));
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
  visualViewport?.addEventListener('resize', syncVisualViewport);
  visualViewport?.addEventListener('scroll', syncVisualViewport);
  return () => {
    window.removeEventListener('online', controls);
    window.removeEventListener('offline', controls);
    visualViewport?.removeEventListener('resize', syncVisualViewport);
    visualViewport?.removeEventListener('scroll', syncVisualViewport);
    input.removeEventListener('focus', handleInputFocus);
    input.removeEventListener('blur', handleInputBlur);
    restoreMainScroll();
  };
}
