export type FontCategory = 'page-title' | 'post-title' | 'article-body' | 'ui';

export const FONT_LIST = [
	{ name: 'Manrope', category: 'sans-serif' },
	{ name: 'Figtree', category: 'sans-serif' },
	{ name: 'Barlow', category: 'sans-serif' },
	{ name: 'Karla', category: 'sans-serif' },
	{ name: 'PT Sans', category: 'sans-serif' },
	{ name: 'PT Serif', category: 'serif' },
	{ name: 'Inter', category: 'sans-serif' },
	{ name: 'Gloock', category: 'serif' },
	{ name: 'Playfair Display', category: 'serif' },
	{ name: 'Vollkorn', category: 'serif' },
	{ name: 'Newsreader', category: 'serif' },
] as const;

export type FontName = (typeof FONT_LIST)[number]['name'];

export const FONT_LABELS: Record<string, string> = {
	'Manrope': 'Manrope',
	'Figtree': 'Figtree',
	'Barlow': 'Barlow',
	'Karla': 'Karla',
	'PT Sans': 'PT Sans',
	'PT Serif': 'PT Serif',
	'Inter': 'Inter',
	'Gloock': 'Gloock',
	'Playfair Display': 'Playfair',
	'Vollkorn': 'Vollkorn',
	'Newsreader': 'Newsreader',
};

const FONT_CATEGORIES: FontCategory[] = ['page-title', 'post-title', 'article-body', 'ui'];

const FONT_DEFAULTS: Record<FontCategory, string> = {
	'page-title': 'Newsreader',
	'post-title': 'PT Serif',
	'article-body': 'Inter',
	'ui': 'Inter',
};

const CSS_VAR_MAP: Record<FontCategory, string> = {
	'page-title': '--font-page-title',
	'post-title': '--font-post-title',
	'article-body': '--font-article-body',
	'ui': '--font-ui',
};

const STORAGE_PREFIX = 'font-';

function getFontDef(fontName: string) {
	const entry = FONT_LIST.find(f => f.name === fontName);
	return entry ? entry.category : 'sans-serif';
}

export function applyFont(category: FontCategory, fontName: string, persist = false) {
	const fallback = getFontDef(fontName);
	const cssVar = CSS_VAR_MAP[category];
	const value = `'${fontName}', ${fallback}`;
	document.documentElement.style.setProperty(cssVar, value);
	if (category === 'ui') {
		document.body.style.fontFamily = value;
	}
	if (persist) {
		localStorage.setItem(STORAGE_PREFIX + category, fontName);
	}
}

export function applyTheme(themeName: string, persist = false) {
	document.documentElement.setAttribute('data-theme', themeName);
	if (persist) localStorage.setItem('preferred-theme', themeName);
}

export function extractThemeNames(css: string): string[] {
	const names: string[] = [];
	const regex = /(?:@plugin\s+"daisyui\/theme"\s*\{|\[data-theme="([^"]+)"\])/g;
	let match;
	while ((match = regex.exec(css)) !== null) {
		if (match[1]) {
			names.push(match[1]);
		} else {
			const blockStart = css.indexOf('{', match.index);
			if (blockStart !== -1) {
				const blockEnd = css.indexOf('}', blockStart);
				if (blockEnd !== -1) {
					const block = css.slice(blockStart, blockEnd + 1);
					const nameMatch = block.match(/name:\s*["']([^"']+)["']/);
					if (nameMatch) names.push(nameMatch[1]);
				}
			}
		}
	}
	return [...new Set(names)];
}

export function convertDaisyuiPluginToDataTheme(css: string): string {
	const result: string[] = [];
	let i = 0;

	while (i < css.length) {
		const pluginStart = css.indexOf('@plugin', i);
		if (pluginStart === -1) {
			result.push(css.slice(i));
			break;
		}

		result.push(css.slice(i, pluginStart));

		const quoteStart = css.indexOf('"', pluginStart);
		if (quoteStart === -1 || !css.startsWith('"daisyui/theme"', quoteStart)) {
			i = pluginStart + 1;
			continue;
		}

		const braceStart = css.indexOf('{', quoteStart);
		if (braceStart === -1) {
			result.push(css.slice(pluginStart));
			break;
		}

		let depth = 1;
		let j = braceStart + 1;
		while (j < css.length && depth > 0) {
			if (css[j] === '{') depth++;
			if (css[j] === '}') depth--;
			j++;
		}

		const blockContent = css.slice(braceStart + 1, j - 1);
		const nameMatch = blockContent.match(/name:\s*["']([^"']+)["']/);

		if (nameMatch) {
			const themeName = nameMatch[1];
			const innerRules = blockContent
				.replace(/name:\s*["'][^"']+["'];?\s*/g, '')
				.replace(/default:\s*(true|false);?\s*/g, '')
				.replace(/prefersdark:\s*(true|false);?\s*/g, '')
				.replace(/color-scheme:\s*["'][^"']+["'];?\s*/g, '')
				.replace(/^\s*;\s*/gm, '')
				.trim();

			result.push(`[data-theme="${themeName}"] {\n${innerRules}\n}`);
		}

		i = j;
	}

	return result.join('');
}

export function applyCustomCss() {
	const existing = document.getElementById('user-custom-css');
	if (existing) existing.remove();
	const css = localStorage.getItem('custom-css');
	if (css?.trim()) {
		const style = document.createElement('style');
		style.id = 'user-custom-css';
		style.textContent = convertDaisyuiPluginToDataTheme(css);
		document.head.appendChild(style);
	}
}

export function initAppearance() {
	const savedTheme = localStorage.getItem('preferred-theme') || 'berga';
	applyTheme(savedTheme);

	for (const cat of FONT_CATEGORIES) {
		const saved = localStorage.getItem(STORAGE_PREFIX + cat) || FONT_DEFAULTS[cat];
		applyFont(cat, saved);
	}

	applyCustomCss();
}

export function getSavedFont(category: FontCategory): string {
	if (typeof localStorage === 'undefined') return FONT_DEFAULTS[category];
	return localStorage.getItem(STORAGE_PREFIX + category) || FONT_DEFAULTS[category];
}

export function migrateOldFontPref() {
	const old = localStorage.getItem('preferred-font');
	if (!old) return;
	const mapping: Record<string, Record<FontCategory, string>> = {
		'Manrope': { 'ui': 'Manrope' },
		'Figtree': { 'ui': 'Figtree' },
		'Barlow': { 'ui': 'Barlow' },
		'Karla': { 'ui': 'Karla' },
		'PT Sans': { 'ui': 'PT Sans' },
		'PT Serif': { 'ui': 'PT Serif' },
		'Inter': { 'ui': 'Inter' },
	};
	if (mapping[old]) {
		for (const [cat, font] of Object.entries(mapping[old])) {
			if (!localStorage.getItem(STORAGE_PREFIX + cat)) {
				localStorage.setItem(STORAGE_PREFIX + cat, font);
			}
		}
	}
	localStorage.removeItem('preferred-font');
}
