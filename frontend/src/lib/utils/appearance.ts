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
	{ name: 'Atkinson Hyperlegible', category: 'sans-serif' },
	{ name: 'Spectral', category: 'serif' },
	{ name: 'Lora', category: 'serif' },
	{ name: 'Lexend', category: 'sans-serif' },
	{ name: 'JetBrains Mono', category: 'monospace' },
	{ name: 'Source Serif 4', category: 'serif' },
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
	'Atkinson Hyperlegible': 'Atkinson Hyperlegible',
	'Spectral': 'Spectral',
	'Lora': 'Lora',
	'Lexend': 'Lexend',
	'JetBrains Mono': 'JetBrains Mono',
	'Source Serif 4': 'Source Serif 4',
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

/* ── Typography (article body) ──────────────────────────────────────────── */

export const ARTICLE_TYPOGRAPHY = {
	fontSize: { key: 'article-font-size', min: 14, max: 26, step: 1, default: 18, unit: 'rem' },
	fontWeight: { key: 'article-font-weight', min: 300, max: 700, step: 100, default: 400 },
	letterSpacing: { key: 'article-letter-spacing', min: -0.02, max: 0.1, step: 0.01, default: 0 },
	lineHeight: { key: 'article-line-height', min: 1.3, max: 2.0, step: 0.05, default: 1.8 },
	maxWidth: { key: 'article-max-width', min: 480, max: 1200, step: 20, default: 672, unit: 'px' },
	titleMaxWidth: { key: 'article-title-max-width', min: 480, max: 1200, step: 20, default: 672, unit: 'px' },
	imageWidth: { key: 'article-image-width', min: 0, max: 100, step: 5, default: 100 },
} as const;

export function pxToRem(px: number): string {
	return `${(px / 16).toFixed(4)}rem`;
}

export function applyFontSize(value: number, persist = false) {
	document.documentElement.style.setProperty('--article-font-size', pxToRem(value));
	if (persist) localStorage.setItem(ARTICLE_TYPOGRAPHY.fontSize.key, String(value));
}

export function applyFontWeight(value: number, persist = false) {
	document.documentElement.style.setProperty('--article-font-weight', String(value));
	if (persist) localStorage.setItem(ARTICLE_TYPOGRAPHY.fontWeight.key, String(value));
}

export function applyLetterSpacing(value: number, persist = false) {
	document.documentElement.style.setProperty(
		'--article-letter-spacing',
		value === 0 ? 'normal' : `${value}em`,
	);
	if (persist) localStorage.setItem(ARTICLE_TYPOGRAPHY.letterSpacing.key, String(value));
}

export function applyLineHeight(value: number, persist = false) {
	document.documentElement.style.setProperty('--article-line-height', value.toFixed(2));
	if (persist) localStorage.setItem(ARTICLE_TYPOGRAPHY.lineHeight.key, String(value));
}

export function applyArticleMaxWidth(value: number, persist = false) {
	document.documentElement.style.setProperty('--article-max-width', `${value}px`);
	document.documentElement.style.setProperty('--article-body-max-width', `${value}px`);
	if (persist) localStorage.setItem(ARTICLE_TYPOGRAPHY.maxWidth.key, String(value));
}

export function applyArticleTitleMaxWidth(value: number, persist = false) {
	document.documentElement.style.setProperty('--article-title-max-width', `${value}px`);
	if (persist) localStorage.setItem(ARTICLE_TYPOGRAPHY.titleMaxWidth.key, String(value));
}

export function applyArticleImageWidth(value: number, persist = false) {
	document.documentElement.style.setProperty('--article-image-width', `${value}%`);
	if (persist) localStorage.setItem(ARTICLE_TYPOGRAPHY.imageWidth.key, String(value));
}

/* ── Post-card ──────────────────────────────────────────────────────────── */

export const POSTCARD_PREFS = {
	descLines: { key: 'postcard-desc-lines', min: 0, max: 6, step: 1, default: 2 },
	titleBold: { key: 'postcard-title-bold', default: false },
	density: { key: 'feed-density', default: 'comfortable' as Density },
} as const;

export type Density = 'compact' | 'comfortable' | 'spacious';

const DENSITY_PADDING: Record<Density, string> = {
	compact: '6px 6px 2px',
	comfortable: '12px 6px 4px',
	spacious: '20px 10px 8px',
};

const DENSITY_GAP: Record<Density, string> = {
	compact: '0px',
	comfortable: '0px',
	spacious: '0px',
};

export function applyDescLines(value: number, persist = false) {
	document.documentElement.style.setProperty('--postcard-desc-lines', String(value));
	if (persist) localStorage.setItem(POSTCARD_PREFS.descLines.key, String(value));
}

export function applyTitleBold(value: boolean, persist = false) {
	document.documentElement.style.setProperty(
		'--postcard-title-weight',
		value ? '700' : '500',
	);
	if (persist) localStorage.setItem(POSTCARD_PREFS.titleBold.key, String(value));
}

export function applyDensity(value: Density, persist = false) {
	document.documentElement.style.setProperty('--postcard-padding', DENSITY_PADDING[value]);
	document.documentElement.style.setProperty('--feed-density-gap', DENSITY_GAP[value]);
	if (persist) localStorage.setItem(POSTCARD_PREFS.density.key, value);
}

export function getSavedDensity(): Density {
	if (typeof localStorage === 'undefined') return 'comfortable';
	const v = localStorage.getItem(POSTCARD_PREFS.density.key);
	return v === 'compact' || v === 'spacious' ? v : 'comfortable';
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

function numPref(key: string, def: number): number {
	const v = localStorage.getItem(key);
	const n = v == null ? NaN : Number(v);
	return Number.isFinite(n) ? n : def;
}

export function initAppearance() {
	const savedTheme = localStorage.getItem('preferred-theme') || 'berga';
	applyTheme(savedTheme);

	for (const cat of FONT_CATEGORIES) {
		const saved = localStorage.getItem(STORAGE_PREFIX + cat) || FONT_DEFAULTS[cat];
		applyFont(cat, saved);
	}

	const t = ARTICLE_TYPOGRAPHY;
	applyFontSize(numPref(t.fontSize.key, t.fontSize.default));
	applyFontWeight(numPref(t.fontWeight.key, t.fontWeight.default));
	applyLetterSpacing(numPref(t.letterSpacing.key, t.letterSpacing.default));
	applyLineHeight(numPref(t.lineHeight.key, t.lineHeight.default));
	applyArticleMaxWidth(numPref(t.maxWidth.key, t.maxWidth.default));
	applyArticleTitleMaxWidth(numPref(t.titleMaxWidth.key, t.titleMaxWidth.default));
	applyArticleImageWidth(numPref(t.imageWidth.key, t.imageWidth.default));

	applyDescLines(numPref(POSTCARD_PREFS.descLines.key, POSTCARD_PREFS.descLines.default));
	applyTitleBold(localStorage.getItem(POSTCARD_PREFS.titleBold.key) === 'true');
	applyDensity(getSavedDensity());

	applyCustomCss();
}

export function getSavedFont(category: FontCategory): string {
	if (typeof localStorage === 'undefined') return FONT_DEFAULTS[category];
	return localStorage.getItem(STORAGE_PREFIX + category) || FONT_DEFAULTS[category];
}

export function migrateOldFontPref() {
	const old = localStorage.getItem('preferred-font');
	if (!old) return;
	const mapping: Record<string, Partial<Record<FontCategory, string>>> = {
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
