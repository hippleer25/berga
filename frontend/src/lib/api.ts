import { get } from 'svelte/store';
import { locale } from 'svelte-i18n';
import { instance } from '$lib/stores/instance';

const LOCALE_MAP: Record<string, string> = {
  pt: 'pt-BR,pt;q=0.9,en;q=0.8',
  en: 'en-US,en;q=0.9',
  es: 'es-ES,es;q=0.9,en;q=0.8',
  de: 'de-DE,de;q=0.9,en;q=0.8',
  fr: 'fr-FR,fr;q=0.9,en;q=0.8',
};

function getAcceptLanguage(): string {
  const loc = get(locale) ?? 'en';
  const key = (Array.isArray(loc) ? loc[0] : String(loc)) as string;
  return LOCALE_MAP[key] ?? LOCALE_MAP['en'];
}

function getBaseURL(): string {
  const inst = get(instance);
  if (!inst) return '';
  const instanceOrigin = `https://${inst}`;
  if (typeof window !== 'undefined' && window.location.origin === instanceOrigin) return '';
  return instanceOrigin;
}

export function apiFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  let url: string;
  if (typeof input === 'string') {
    const base = getBaseURL();
    url = base && input.startsWith('/api/') ? `${base}${input}` : input;
  } else if (input instanceof URL) {
    url = input.toString();
  } else {
    url = (input as Request).url;
  }

  const headers = new Headers(init?.headers);
  if (!headers.has('Accept-Language')) {
    headers.set('Accept-Language', getAcceptLanguage());
  }

  const isCrossOrigin = url.startsWith('https://') || url.startsWith('http://');
  const mergedInit: RequestInit = {
    ...init,
    headers,
    credentials: 'include',
    ...(isCrossOrigin ? { mode: 'cors' } : {}),
  };

  return fetch(url, mergedInit);
}
