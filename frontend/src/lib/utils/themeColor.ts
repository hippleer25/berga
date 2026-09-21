/**
 * Keeps the Android system bars (status/navigation) in sync with the selected
 * background. Chrome re-themes them live from `<meta name="theme-color">` in
 * standalone (installed PWA / WebAPK) mode — no reinstall required.
 */

const PAGE_BG_OVERRIDES: Record<string, string> = {
	white: '#ffffff',
	'berga-white': '#fbfaf7',
	'berga-gray': '#f8f7f3',
	dark: '#17181d',
	amoled: '#000000',
};

const THEME_FALLBACKS: Record<string, string> = {
	'berga': '#000000',
	'berga-black': '#ffffff',
};

const DEFAULT_THEME_COLOR = '#000000';

export function getThemeColor(): string {
	try {
		const pageBg = localStorage.getItem('ui-page-bg');
		if (pageBg && PAGE_BG_OVERRIDES[pageBg]) return PAGE_BG_OVERRIDES[pageBg];
	} catch {
		/* ignore */
	}

	const theme = document.documentElement.getAttribute('data-theme') || 'berga';
	if (THEME_FALLBACKS[theme]) return THEME_FALLBACKS[theme];

	if (typeof getComputedStyle === 'function') {
		const raw = getComputedStyle(document.documentElement)
			.getPropertyValue('--color-base-100')
			.trim();
		if (/^(#[0-9a-f]{3,8}|rgb\(.+\))$/i.test(raw)) return raw;
	}
	return DEFAULT_THEME_COLOR;
}

export function syncThemeColor() {
	const meta = document.querySelector('meta[name="theme-color"]');
	const color = getThemeColor();
	if (meta) (meta as HTMLMetaElement).content = color;
}
