import { browser } from '$app/environment';
import { init, register, locale } from 'svelte-i18n';

const STORAGE_KEY = 'lang';
export const SUPPORTED_LOCALES = ['pt', 'en', 'es', 'de', 'fr'] as const;
export type SupportedLocale = typeof SUPPORTED_LOCALES[number];

const NAMESPACES = [
	'navbar', 'hometab', 'eventstab', 'motatab',
	'settings', 'signup', 'signin', 'welcome', 'followerstab', 'affinity',
	'search', 'feed', 'article', 'eventscard', 'followfeedmodal', 'leftpanel',
	'postcard', 'topbar', 'folder', 'searchtab', 'tags', 'pwa'
] as const;

const localeFiles = import.meta.glob('../locales/**/*.json');

function flattenObject(obj: Record<string, any>, prefix = ''): Record<string, string> {
  return Object.keys(obj).reduce((acc, k) => {
    const pre = prefix.length ? prefix + '.' : '';
    if (typeof obj[k] === 'object' && obj[k] !== null) {
      Object.assign(acc, flattenObject(obj[k], pre + k));
    } else {
      acc[pre + k] = obj[k];
    }
    return acc;
  }, {} as Record<string, string>);
}

function buildLoader(lang: string) {
  return async () => {
    console.log(`[i18n] buildLoader('${lang}') started`);
    const modules = await Promise.all(
      NAMESPACES.map(async (ns) => {
        const path = `../locales/${lang}/${ns}.json`;
        if (!localeFiles[path]) {
          console.warn(`[i18n] No locale file found for path: ${path}`);
          return {};
        }
        try {
          const mod = await localeFiles[path]() as Record<string, any>;
          const flat = flattenObject(mod.default || mod);
          const namespaced: Record<string, string> = {};
          for (const key in flat) {
            namespaced[`${ns}.${key}`] = flat[key];
          }
          return namespaced;
		} catch (e) {
			console.error(`[i18n] Failed to load ${path}:`, e);
			return {};
		}
      })
    );
    const result = Object.assign({}, ...modules);
    console.log(`[i18n] buildLoader('${lang}') loaded ${Object.keys(result).length} keys`);
    return result;
  };
}

register('pt', buildLoader('pt'));
register('en', buildLoader('en'));
register('es', buildLoader('es'));
register('de', buildLoader('de'));
register('fr', buildLoader('fr'));

let initialLocale: SupportedLocale = 'en';

if (browser) {
  try {
    const saved = localStorage.getItem(STORAGE_KEY) as SupportedLocale;
    const browser_lang = navigator.language.split('-')[0];
    if (saved && SUPPORTED_LOCALES.includes(saved)) {
      initialLocale = saved;
    } else if (SUPPORTED_LOCALES.includes(browser_lang as SupportedLocale)) {
      initialLocale = browser_lang as SupportedLocale;
    }
  } catch (e) {
    console.warn('Could not access localStorage', e);
  }
}

init({
  fallbackLocale: 'en',
  initialLocale,
});

export function setLocale(lang: SupportedLocale) {
  console.log('[i18n] setLocale called with:', lang);
  if (browser) {
    try {
      localStorage.setItem(STORAGE_KEY, lang);
      console.log('[i18n] localStorage saved, key=', STORAGE_KEY, 'value=', lang);
    } catch (e) {
      console.warn('[i18n] Could not save locale to localStorage', e);
    }
  }
  const result = locale.set(lang);
  if (result && typeof result === 'object' && 'then' in result) {
    console.log('[i18n] locale.set() returned Promise — awaiting flush...');
    result
      .then(() => console.log('[i18n] locale.set() Promise RESOLVED — locale should now be:', lang))
      .catch((e: unknown) => console.error('[i18n] locale.set() Promise REJECTED:', e));
  } else {
    console.log('[i18n] locale.set() returned synchronously (direct path — dictionary already loaded)');
  }
}

export { locale };
