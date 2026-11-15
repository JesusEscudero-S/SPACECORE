import { $, el, openMenu, showMessage, verifyElements } from '../../lib/dom';
import { translate } from '../../lib/i18n';
import { writeUrlState } from '../../state/urlState';
import type { Store } from '../../state/store';
import type { ViewActions } from '../contracts';

export function mount(_root: ParentNode, store: Store, actions: ViewActions): void {
  if (!verifyElements(['btnExport', 'btnShare', 'menuExport', 'menuShare', 'modalTitle', 'modalBody', 'modalClose', 'backdrop'], 'modal')) return;
  document.getElementById('btnExport')?.addEventListener('click', (event) => {
    event.stopPropagation(); openMenu('menuExport', 'btnExport');
  });
  document.getElementById('btnShare')?.addEventListener('click', (event) => {
    event.stopPropagation(); openMenu('menuShare', 'btnShare');
  });
  document.getElementById('menuExport')?.addEventListener('click', (event) => {
    const button = (event.target as HTMLElement).closest<HTMLButtonElement>('button[data-act]');
    if (button?.dataset.act === 'png' || button?.dataset.act === 'csv') actions.export(button.dataset.act);
  });
  document.getElementById('menuShare')?.addEventListener('click', (event) => {
    const button = (event.target as HTMLElement).closest<HTMLButtonElement>('button[data-act]');
    if (button?.dataset.act === 'link' || button?.dataset.act === 'embed') openShare(button.dataset.act);
  });
  document.addEventListener('click', () => {
    document.querySelectorAll<HTMLElement>('.menu').forEach((menu) => { menu.hidden = true; });
    document.getElementById('btnExport')?.setAttribute('aria-expanded', 'false');
    document.getElementById('btnShare')?.setAttribute('aria-expanded', 'false');
  });
  document.getElementById('modalClose')?.addEventListener('click', closeModal);
  document.getElementById('backdrop')?.addEventListener('click', (event) => {
    if (event.target === document.getElementById('backdrop')) closeModal();
  });
  document.getElementById('bannerClose')?.addEventListener('click', () => {
    const banner = document.getElementById('banner'); if (banner) banner.hidden = true;
    store.setState({ error: '' });
  });
  document.getElementById('popClose')?.addEventListener('click', () => {
    store.setState({ selectedSource: null });
    const popup = document.getElementById('srcPop'); if (popup) popup.hidden = true;
  });
  document.getElementById('popSpec')?.addEventListener('click', () => actions.setView('spectrum'));

  function openShare(kind: 'link' | 'embed'): void {
    const state = store.getState();
    const params = writeUrlState(state, false);
    if (kind === 'embed') params.set('embed', '1');
    const url = `${location.origin}${location.pathname}?${params.toString()}`;
    const value = kind === 'embed' ? `<iframe src="${url}" title="SPACECORE · SPHEREx" width="100%" height="640" loading="lazy"></iframe>` : url;
    showTextModal(translate(state.lang, kind === 'embed' ? 'embedTitle' : 'linkTitle'), value,
      translate(state.lang, kind === 'embed' ? 'embedHelp' : 'linkHelp'));
  }

  function showTextModal(title: string, value: string, help: string): void {
    const titleNode = $('modalTitle'), body = $('modalBody'), backdrop = $('backdrop');
    if (!titleNode || !body || !backdrop) return;
    titleNode.textContent = title; body.replaceChildren();
    const note = el('p', { className: 'hint', textContent: help });
    const field = el('textarea', { className: 'inp', rows: value.includes('<iframe') ? 4 : 2, readOnly: true });
    field.value = value;
    const copy = el('button', { className: 'btn primary', type: 'button', textContent: translate(store.getState().lang, 'copy') });
    copy.addEventListener('click', async () => {
      try { await navigator.clipboard.writeText(value); }
      catch { field.focus(); field.select(); document.execCommand('copy'); }
      copy.textContent = translate(store.getState().lang, 'copied');
      window.setTimeout(() => { copy.textContent = translate(store.getState().lang, 'copy'); }, 1600);
    });
    body.append(note, field, copy);
    backdrop.hidden = false; field.focus(); field.select();
  }

  function closeModal(): void { const backdrop = document.getElementById('backdrop'); if (backdrop) backdrop.hidden = true; }
  document.addEventListener('keydown', (event) => { if (event.key === 'Escape') closeModal(); });
  window.addEventListener('spherex:show-error', (event) => {
    const detail = (event as CustomEvent<string>).detail;
    if (detail) showMessage(detail, 'error');
  });
}
