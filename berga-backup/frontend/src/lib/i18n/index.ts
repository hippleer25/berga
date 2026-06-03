import { browser } from '$app/environment';
import { init, register, locale } from 'svelte-i18n';

const STORAGE_KEY = 'lang';
export const SUPPORTED_LOCALES = ['pt', 'en', 'es', 'de', 'fr'] as const;
export type SupportedLocale = typeof SUPPORTED_LOCALES[number];

const NAMESPACES = [
  'navbar', 'hometab', 'eventstab', 'motatab',
  'settings', 'signup', 'signin', 'welcome', 'followerstab', 'affinity',
  'search', 'feed', 'article', 'eventscard', 'followfeedmodal', 'leftpanel',
  'postcard', 'topbar', 'folder', 'searchtab'
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
    const modules = await Promise.all(
      NAMESPACES.map(async (ns) => {
        const path = `../locales/${lang}/${ns}.json`;
        if (!localeFiles[path]) {
          return {};
        }
        const mod = await localeFiles[path]() as Record<string, any>;
        const flat = flattenObject(mod.default || mod);
        const namespaced: Record<string, string> = {};
        for (const key in flat) {
          namespaced[`${ns}.${key}`] = flat[key];
        }
        return namespaced;
      })
    );
    return Object.assign({}, ...modules);
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
	if (browser) {
		try {
			localStorage.setItem(STORAGE_KEY, lang);
		} catch (e) {
			console.warn('Could not save locale to localStorage', e);
		}
	}
	locale.set(lang);
}

export { locale };
