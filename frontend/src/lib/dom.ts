export type EventHandler = (event: Event) => void;
type ElementAttributes = Record<string, string | number | boolean | EventHandler | null | undefined>;

const missingReported = new Set<string>();

export function verifyElements(ids: readonly string[], moduleName: string): boolean {
  const missing = ids.filter((id) => !document.getElementById(id));
  if (!missing.length) return true;
  missing.forEach((id) => missingReported.add(id));
  const message = `[${moduleName}] Faltan elementos de la interfaz: ${missing.map((id) => `#${id}`).join(', ')}.`;
  console.error(message);
  showMessage(message, 'error');
  return false;
}

export function showMessage(message: string, kind: 'info' | 'warn' | 'error' = 'info'): void {
  const banner = document.getElementById('banner');
  const text = document.getElementById('bannerText');
  if (banner && text) {
    text.textContent = message;
    banner.className = `banner${kind === 'warn' ? ' warn' : kind === 'error' ? ' err' : ''}`;
    banner.hidden = false;
    return;
  }
  let status = document.getElementById('runtime-ui-status');
  if (!status) {
    status = document.createElement('div');
    status.id = 'runtime-ui-status';
    status.className = 'banner err runtime-ui-status';
    status.setAttribute('role', 'alert');
    document.body.prepend(status);
  }
  status.textContent = message;
}

export function $(id: string, context: ParentNode = document): HTMLElement | null {
  const found = context.querySelector<HTMLElement>(`#${CSS.escape(id)}`);
  if (!found && !missingReported.has(id)) {
    missingReported.add(id);
    const message = `[UI] Falta el elemento #${id}.`;
    console.error(message);
    showMessage(message, 'error');
  }
  return found;
}

export function bindListener(id: string, event: string, handler: EventHandler): boolean {
  const node = $(id);
  if (!node) return false;
  node.addEventListener(event, handler);
  return true;
}

export function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  attrs: ElementAttributes = {},
  children: (Node | string)[] = [],
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === null || value === undefined) continue;
    if (key.startsWith('on') && typeof value === 'function') {
      node.addEventListener(key.slice(2).toLowerCase(), value as EventHandler);
    } else if (key === 'className') node.className = String(value);
    else if (key === 'textContent') node.textContent = String(value);
    else if (typeof value === 'boolean') node.setAttribute(key, String(value));
    else node.setAttribute(key, String(value));
  }
  children.forEach((child) => node.append(child));
  return node;
}

export function setSwitch(id: string, value: boolean): void {
  $(id)?.setAttribute('aria-checked', String(value));
}

export function bindSwitch(id: string, get: () => boolean, set: (next: boolean) => void): void {
  const node = $(id);
  if (!node) return;
  setSwitch(id, get());
  node.addEventListener('click', () => {
    set(!get());
    setSwitch(id, get());
  });
}

export function openMenu(id: string, buttonId: string): void {
  const menu = $(id);
  const button = $(buttonId);
  if (!menu || !button) return;
  const opening = menu.hidden;
  document.querySelectorAll<HTMLElement>('.menu').forEach((entry) => { entry.hidden = true; });
  menu.hidden = !opening;
  button.setAttribute('aria-expanded', String(opening));
}

export function download(filename: string, blob: Blob): void {
  const anchor = document.createElement('a');
  anchor.href = URL.createObjectURL(blob);
  anchor.download = filename;
  document.body.append(anchor);
  anchor.click();
  window.setTimeout(() => { URL.revokeObjectURL(anchor.href); anchor.remove(); }, 500);
}
