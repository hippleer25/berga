import { writable } from 'svelte/store';
import { browser } from '$app/environment';

/* ── Generic numeric preference store ───────────────────────────────────── */
function createNumberStore(key: string, def: number) {
  const saved = browser ? localStorage.getItem(key) : null;
  const n = saved == null ? NaN : Number(saved);
  const initial = Number.isFinite(n) ? n : def;
  const { subscribe, set } = writable<number>(initial);

  return {
    subscribe,
    setValue: (value: number) => {
      if (browser) localStorage.setItem(key, String(value));
      set(value);
    },
    getValue: (): number => {
      let val = def;
      subscribe(v => (val = v))();
      return val;
    },
  };
}

function createBooleanStore(key: string, def: boolean) {
  const saved = browser ? localStorage.getItem(key) : null;
  const initial = saved == null ? def : saved !== 'false';
  const { subscribe, set } = writable<boolean>(initial);

  return {
    subscribe,
    setValue: (value: boolean) => {
      if (browser) localStorage.setItem(key, String(value));
      set(value);
    },
    getValue: (): boolean => {
      let val = def;
      subscribe(v => (val = v))();
      return val;
    },
  };
}

function createStringStore<T extends string>(key: string, def: T) {
  const saved = browser ? (localStorage.getItem(key) as T | null) : null;
  const initial = (saved ?? def) as T;
  const { subscribe, set } = writable<T>(initial);

  return {
    subscribe,
    setValue: (value: T) => {
      if (browser) localStorage.setItem(key, value);
      set(value);
    },
    getValue: (): T => {
      let val = def;
      subscribe(v => (val = v))();
      return val;
    },
  };
}

/* ── Cover images ───────────────────────────────────────────────────────── */
function createCoverImagesStore() {
  const saved = browser ? localStorage.getItem('show-cover-images') : null;
  const initial = saved === 'true';
  const { subscribe, set } = writable<boolean>(initial);

  return {
    subscribe,
    setEnabled: (enabled: boolean) => {
      if (browser) {
        localStorage.setItem('show-cover-images', enabled ? 'true' : 'false');
      }
      set(enabled);
    },
    getEnabled: (): boolean => {
      let val = false;
      subscribe(v => val = v)();
      return val;
    },
  };
}

export const showCoverImages = createCoverImagesStore();

export type CoverPosition = 'right' | 'bottom';

function createCoverPositionStore() {
  const saved = browser ? (localStorage.getItem('cover-image-position') as CoverPosition | null) : null;
  const initial: CoverPosition = saved === 'bottom' ? 'bottom' : 'right';
  const { subscribe, set } = writable<CoverPosition>(initial);

  return {
    subscribe,
    setPosition: (position: CoverPosition) => {
      if (browser) {
        localStorage.setItem('cover-image-position', position);
      }
      set(position);
    },
    getPosition: (): CoverPosition => {
      let val: CoverPosition = 'right';
      subscribe(v => val = v)();
      return val;
    },
  };
}

export const coverImagePosition = createCoverPositionStore();

export type TextAlign = 'left' | 'justify' | 'center' | 'right';

function createTextAlignStore(key: string, defaultValue: TextAlign) {
  const saved = browser ? (localStorage.getItem(key) as TextAlign | null) : null;
  const initial: TextAlign = ['left', 'justify', 'center', 'right'].includes(saved ?? '')
    ? (saved as TextAlign)
    : defaultValue;
  const { subscribe, set } = writable<TextAlign>(initial);

  return {
    subscribe,
    setPosition: (position: TextAlign) => {
      if (browser) {
        localStorage.setItem(key, position);
      }
      set(position);
    },
    getPosition: (): TextAlign => {
      let val: TextAlign = defaultValue;
      subscribe(v => val = v)();
      return val;
    },
  };
}

export const titleTextAlign = createTextAlignStore('title-text-align', 'left');
export const bodyTextAlign = createTextAlignStore('body-text-align', 'left');

/* ── Article typography ─────────────────────────────────────────────────── */
export const articleFontSize = createNumberStore('article-font-size', 18);
export const articleFontWeight = createNumberStore('article-font-weight', 400);
export const articleLetterSpacing = createNumberStore('article-letter-spacing', 0);
export const articleLineHeight = createNumberStore('article-line-height', 1.8);
export const articleMaxWidth = createNumberStore('article-max-width', 672);
export const articleTitleMaxWidth = createNumberStore('article-title-max-width', 672);
export const articleImageWidth = createNumberStore('article-image-width', 100);

/* ── Post-card ──────────────────────────────────────────────────────────── */
export const postcardDescLines = createNumberStore('postcard-desc-lines', 2);
export const postcardTitleBold = createBooleanStore('postcard-title-bold', false);

export type Density = 'compact' | 'comfortable' | 'spacious';
export const feedDensity = createStringStore<Density>('feed-density', 'comfortable');

/* ── Highlights ─────────────────────────────────────────────────────────── */
const DEFAULT_HIGHLIGHT_COLORS = ['#FFEB3B', '#66BB6A', '#42A5F5', '#F48FB1'];
const HEX_RE = /^#[0-9a-fA-F]{6}$/;

function createHighlightColorsStore(key: string, def: string[]) {
  const saved = browser ? localStorage.getItem(key) : null;
  let initial = def;
  if (saved != null) {
    try {
      const parsed = JSON.parse(saved);
      if (Array.isArray(parsed) && parsed.every((c) => typeof c === 'string' && HEX_RE.test(c))) {
        initial = parsed;
      }
    } catch { /* ignore malformed */ }
  }
  const { subscribe, set } = writable<string[]>(initial);

  const read = (): string[] => {
    let val = def;
    subscribe(v => (val = v))();
    return val;
  };

  return {
    subscribe,
    setColors: (colors: string[]) => {
      if (browser) localStorage.setItem(key, JSON.stringify(colors));
      set(colors);
    },
    addColor: (color: string) => {
      const next = [...read(), color];
      if (browser) localStorage.setItem(key, JSON.stringify(next));
      set(next);
    },
    removeColor: (index: number) => {
      const next = read().filter((_, i) => i !== index);
      if (browser) localStorage.setItem(key, JSON.stringify(next));
      set(next);
    },
    updateColor: (index: number, color: string) => {
      const next = read().map((c, i) => (i === index ? color : c));
      if (browser) localStorage.setItem(key, JSON.stringify(next));
      set(next);
    },
    getColors: (): string[] => read(),
  };
}

export const highlightColors = createHighlightColorsStore('highlight-colors', DEFAULT_HIGHLIGHT_COLORS);
export const highlightOpacity = createNumberStore('highlight-opacity', 100);
export const highlightRadius = createNumberStore('highlight-radius', 0);
export const highlightCustomColorDefault = createStringStore('highlight-custom-color-default', '#FF9800');
