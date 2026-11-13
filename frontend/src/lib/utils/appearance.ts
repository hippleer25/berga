import { syncThemeColor } from './themeColor';

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
	/* Matches the elegant design-mode preset so a first visit without
	   initDesignMode still renders the editorial look. */
	'article-body': 'Source Serif 4',
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

/* A font-family that is not a shipped face resolves silently to the generic
   fallback (sans-serif/serif) — the pickers would keep showing a name that
   renders as nothing. Treat unknown stored names as corrupt state. */
export function isKnownFont(fontName: string): boolean {
	return FONT_LIST.some(f => f.name === fontName);
}

/* ── Typography (article body) ──────────────────────────────────────────── */

/* All size knobs are stored in rem (universal — scales with the user's base
   font) and applied to CSS vars as raw rem strings. Legacy px values are
   migrated once by the pre-paint script in app.html. */
export const ARTICLE_TYPOGRAPHY = {
	fontSize: { key: 'article-font-size', min: 0.875, max: 1.625, step: 0.0625, default: 1.125, unit: 'rem' },
	fontWeight: { key: 'article-font-weight', min: 300, max: 700, step: 100, default: 400 },
	letterSpacing: { key: 'article-letter-spacing', min: -0.02, max: 0.1, step: 0.01, default: 0 },
	lineHeight: { key: 'article-line-height', min: 1.3, max: 2.0, step: 0.05, default: 1.8 },
	maxWidth: { key: 'article-max-width', min: 30, max: 75, step: 0.25, default: 50, unit: 'rem' },
	titleMaxWidth: { key: 'article-title-max-width', min: 30, max: 75, step: 0.25, default: 42, unit: 'rem' },
	imageWidth: { key: 'article-image-width', min: 0, max: 100, step: 5, default: 100 },
} as const;

/* Static-weight families only ship fixed faces (see @font-face in app.css).
   Requesting an intermediate weight (e.g. 600 on PT Sans, which has only
   400/700) makes the browser fall through to the next heavier face — 700,
   i.e. full Bold. Constrain the weight to faces that actually exist. */
const STATIC_FONT_WEIGHTS: Partial<Record<FontName, number[]>> = {
	'Barlow': [400, 500, 600, 700],
	'PT Sans': [400, 700],
	'PT Serif': [400, 700],
	'Gloock': [400],
	'Atkinson Hyperlegible': [400, 700],
	'Spectral': [400, 500, 600, 700],
};

export function allowedFontWeights(fontName: string): number[] {
	const { min, max, step } = ARTICLE_TYPOGRAPHY.fontWeight;
	const staticList = STATIC_FONT_WEIGHTS[fontName as FontName];
	if (staticList) {
		const within = staticList.filter(w => w >= min && w <= max);
		return within.length ? within : [400];
	}
	const full: number[] = [];
	for (let w = min; w <= max; w += step) full.push(w);
	return full;
}

/* Snap to the closest available face at or below the requested weight */
export function snapFontWeight(fontName: string, value: number): number {
	const list = allowedFontWeights(fontName);
	if (list.includes(value)) return value;
	const below = list.filter(w => w <= value);
	return below.length ? below[below.length - 1] : list[0];
}

export function applyFontSize(value: number, persist = false) {
	document.documentElement.style.setProperty('--article-font-size', `${value}rem`);
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
	document.documentElement.style.setProperty('--article-max-width', `${value}rem`);
	document.documentElement.style.setProperty('--article-body-max-width', `${value}rem`);
	if (persist) localStorage.setItem(ARTICLE_TYPOGRAPHY.maxWidth.key, String(value));
}

export function applyArticleTitleMaxWidth(value: number, persist = false) {
	document.documentElement.style.setProperty('--article-title-max-width', `${value}rem`);
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
	titleSize: { key: 'postcard-title-size', min: 80, max: 150, step: 5, default: 110 },
	descSize: { key: 'postcard-desc-size', min: 80, max: 150, step: 5, default: 110 },
	coverFit: { key: 'cover-image-fit', default: 'fill' as 'fill' | 'proportions' },
	coverMaxW: { key: 'cover-image-max-w', min: 5, max: 25, step: 0.25, default: 5 },
	coverMaxH: { key: 'cover-image-max-h', min: 4, max: 25, step: 0.25, default: 20.625 },
	coverRadius: { key: 'cover-image-radius', min: 0, max: 2, step: 0.0625, default: 0.9375 },
	searchCoverRadius: { key: 'search-cover-image-radius', min: 0, max: 2, step: 0.0625, default: 0.9375 },
	coverAlign: { key: 'cover-image-align', default: 'center' as CoverAlign },
	searchCoverAlign: { key: 'search-cover-image-align', default: 'center' as CoverAlign },
	eventCoverPos: { key: 'event-cover-position', default: 'bottom' as EventCoverPos },
	eventTitleSize: { key: 'event-title-size', min: 80, max: 150, step: 5, default: 100 },
	/* Space between the bottom-positioned cluster banner and the row separator, px. */
	eventCoverSpacing: { key: 'event-cover-spacing', min: 0, max: 24, step: 1, default: 10 },
} as const;

export type CoverAlign = 'left' | 'center' | 'right';
export type EventCoverPos = 'side' | 'top' | 'bottom';

const COVER_ALIGN_VALUES: CoverAlign[] = ['left', 'center', 'right'];
/* Margin shorthands aligning a shrunken cover box inside the card row. */
const COVER_ALIGN_MARGINS: Record<Exclude<CoverAlign, 'center'>, string> = {
	left: '0 auto',
	right: 'auto 0',
};

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

export function applyTitleSize(value: number, persist = false) {
	const v = Math.min(POSTCARD_PREFS.titleSize.max, Math.max(POSTCARD_PREFS.titleSize.min, value));
	document.documentElement.style.setProperty('--postcard-title-scale', String(v / 100));
	if (persist) localStorage.setItem(POSTCARD_PREFS.titleSize.key, String(v));
}

export function applyDescSize(value: number, persist = false) {
	const v = Math.min(POSTCARD_PREFS.descSize.max, Math.max(POSTCARD_PREFS.descSize.min, value));
	document.documentElement.style.setProperty('--postcard-desc-scale', String(v / 100));
	if (persist) localStorage.setItem(POSTCARD_PREFS.descSize.key, String(v));
}

export function applyEventTitleSize(value: number, persist = false) {
	const v = Math.min(POSTCARD_PREFS.eventTitleSize.max, Math.max(POSTCARD_PREFS.eventTitleSize.min, value));
	document.documentElement.style.setProperty('--event-title-scale', String(v / 100));
	if (persist) localStorage.setItem(POSTCARD_PREFS.eventTitleSize.key, String(v));
}

export function getSavedTitleSize(): number {
	if (typeof localStorage === 'undefined') return POSTCARD_PREFS.titleSize.default;
	const v = Number(localStorage.getItem(POSTCARD_PREFS.titleSize.key));
	return Number.isFinite(v) && v >= POSTCARD_PREFS.titleSize.min && v <= POSTCARD_PREFS.titleSize.max
		? v
		: POSTCARD_PREFS.titleSize.default;
}

export function getSavedDescSize(): number {
	if (typeof localStorage === 'undefined') return POSTCARD_PREFS.descSize.default;
	const v = Number(localStorage.getItem(POSTCARD_PREFS.descSize.key));
	return Number.isFinite(v) && v >= POSTCARD_PREFS.descSize.min && v <= POSTCARD_PREFS.descSize.max
		? v
		: POSTCARD_PREFS.descSize.default;
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

export function applyCoverFit(value: 'fill' | 'proportions', persist = false) {
	document.documentElement.setAttribute('data-cover-fit', value);
	if (persist) localStorage.setItem(POSTCARD_PREFS.coverFit.key, value);
}

export function applyCoverMaxWidth(value: number, persist = false) {
	const v = Math.min(POSTCARD_PREFS.coverMaxW.max, Math.max(POSTCARD_PREFS.coverMaxW.min, value));
	document.documentElement.style.setProperty('--cover-max-w', `${v}rem`);
	if (persist) localStorage.setItem(POSTCARD_PREFS.coverMaxW.key, String(v));
}

export function applyCoverMaxHeight(value: number, persist = false) {
	const v = Math.min(POSTCARD_PREFS.coverMaxH.max, Math.max(POSTCARD_PREFS.coverMaxH.min, value));
	document.documentElement.style.setProperty('--cover-max-h', `${v}rem`);
	if (persist) localStorage.setItem(POSTCARD_PREFS.coverMaxH.key, String(v));
}

/* 0 = Auto: drop the override so covers fall back to --ui-radius-sm.
   Non-zero values are rem (universal units). */
export function applyCoverRadius(value: number, persist = false) {
	const v = Math.min(POSTCARD_PREFS.coverRadius.max, Math.max(POSTCARD_PREFS.coverRadius.min, value));
	if (v <= 0) {
		document.documentElement.style.removeProperty('--cover-image-radius');
	} else {
		document.documentElement.style.setProperty('--cover-image-radius', `${v}rem`);
	}
	if (persist) localStorage.setItem(POSTCARD_PREFS.coverRadius.key, String(v));
}

/* Independent knob for the search results page. 0 = Auto. */
export function applySearchCoverRadius(value: number, persist = false) {
	const v = Math.min(POSTCARD_PREFS.searchCoverRadius.max, Math.max(POSTCARD_PREFS.searchCoverRadius.min, value));
	if (v <= 0) {
		document.documentElement.style.removeProperty('--search-cover-image-radius');
	} else {
		document.documentElement.style.setProperty('--search-cover-image-radius', `${v}rem`);
	}
	if (persist) localStorage.setItem(POSTCARD_PREFS.searchCoverRadius.key, String(v));
}

/* Horizontal alignment of the photo inside its cover box. 'center' = Auto
   (drops the override, matching the browser default). Sets both the
   object-position string and the margin shorthand used when the box hugs
   the photo in proportions mode. */
function applyCoverAlignVars(base: string, value: CoverAlign) {
	if (!value || value === 'center') {
		document.documentElement.style.removeProperty(base);
		document.documentElement.style.removeProperty(`${base}-margin`);
	} else {
		document.documentElement.style.setProperty(base, value);
		document.documentElement.style.setProperty(`${base}-margin`, COVER_ALIGN_MARGINS[value]);
	}
}

export function applyCoverAlign(value: CoverAlign, persist = false) {
	applyCoverAlignVars('--cover-image-align', value);
	if (persist) localStorage.setItem(POSTCARD_PREFS.coverAlign.key, value);
}

/* Independent knob for the search results page. */
export function applySearchCoverAlign(value: CoverAlign, persist = false) {
	applyCoverAlignVars('--search-cover-image-align', value);
	if (persist) localStorage.setItem(POSTCARD_PREFS.searchCoverAlign.key, value);
}

export function getSavedCoverAlign(): CoverAlign {
	if (typeof localStorage === 'undefined') return POSTCARD_PREFS.coverAlign.default;
	const v = localStorage.getItem(POSTCARD_PREFS.coverAlign.key) as CoverAlign | null;
	return v && COVER_ALIGN_VALUES.includes(v) ? v : POSTCARD_PREFS.coverAlign.default;
}

export function getSavedSearchCoverAlign(): CoverAlign {
	if (typeof localStorage === 'undefined') return POSTCARD_PREFS.searchCoverAlign.default;
	const v = localStorage.getItem(POSTCARD_PREFS.searchCoverAlign.key) as CoverAlign | null;
	return v && COVER_ALIGN_VALUES.includes(v) ? v : POSTCARD_PREFS.searchCoverAlign.default;
}

/* Space between the bottom-positioned cluster banner and the separator line
   under the row. Applies only when the cover sits below the text. */
export function applyEventCoverSpacing(value: number, persist = false) {
	const v = Math.min(POSTCARD_PREFS.eventCoverSpacing.max, Math.max(POSTCARD_PREFS.eventCoverSpacing.min, value));
	document.documentElement.style.setProperty('--event-cover-gap', `${v}px`);
	if (persist) localStorage.setItem(POSTCARD_PREFS.eventCoverSpacing.key, String(v));
}

/* Cluster cover placement on the event card: right thumbnail (default),
   full-width banner above the text, or below it. */
export function applyEventCoverPosition(value: EventCoverPos, persist = false) {
	const v = value === 'top' || value === 'bottom' ? value : 'side';
	document.documentElement.setAttribute('data-event-cover-pos', v);
	if (persist) localStorage.setItem(POSTCARD_PREFS.eventCoverPos.key, v);
}

export function getSavedEventCoverPosition(): EventCoverPos {
	if (typeof localStorage === 'undefined') return POSTCARD_PREFS.eventCoverPos.default;
	const v = localStorage.getItem(POSTCARD_PREFS.eventCoverPos.key) as EventCoverPos | null;
	return v === 'top' || v === 'bottom' || v === 'side' ? v : POSTCARD_PREFS.eventCoverPos.default;
}

export function getSavedCoverFit(): 'fill' | 'proportions' {
	if (typeof localStorage === 'undefined') return POSTCARD_PREFS.coverFit.default;
	return localStorage.getItem(POSTCARD_PREFS.coverFit.key) === 'proportions' ? 'proportions' : 'fill';
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
	syncThemeColor();
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
	const savedTheme = localStorage.getItem('preferred-theme');
	if (savedTheme) applyTheme(savedTheme);

	migrateOldFontPref();

	for (const cat of FONT_CATEGORIES) {
		const stored = localStorage.getItem(STORAGE_PREFIX + cat);
		if (stored !== null && !isKnownFont(stored)) {
			/* Corrupt/legacy entry — the family would only render as its generic
			   fallback. Drop it so the role falls back to its real default. */
			localStorage.removeItem(STORAGE_PREFIX + cat);
		}
		const saved = localStorage.getItem(STORAGE_PREFIX + cat) || FONT_DEFAULTS[cat];
		applyFont(cat, saved);
	}

	const t = ARTICLE_TYPOGRAPHY;
	applyFontSize(numPref(t.fontSize.key, t.fontSize.default));
	applyFontWeight(snapFontWeight(getSavedFont('article-body'), numPref(t.fontWeight.key, t.fontWeight.default)));
	applyLetterSpacing(numPref(t.letterSpacing.key, t.letterSpacing.default));
	applyLineHeight(numPref(t.lineHeight.key, t.lineHeight.default));
	applyArticleMaxWidth(numPref(t.maxWidth.key, t.maxWidth.default));
	applyArticleTitleMaxWidth(numPref(t.titleMaxWidth.key, t.titleMaxWidth.default));
	applyArticleImageWidth(numPref(t.imageWidth.key, t.imageWidth.default));

	applyDescLines(numPref(POSTCARD_PREFS.descLines.key, POSTCARD_PREFS.descLines.default));
	applyTitleBold(localStorage.getItem(POSTCARD_PREFS.titleBold.key) === 'true');
	applyTitleSize(numPref(POSTCARD_PREFS.titleSize.key, POSTCARD_PREFS.titleSize.default));
	applyDescSize(numPref(POSTCARD_PREFS.descSize.key, POSTCARD_PREFS.descSize.default));
	applyDensity(getSavedDensity());
	applyCoverFit(getSavedCoverFit());
	applyCoverMaxWidth(numPref(POSTCARD_PREFS.coverMaxW.key, POSTCARD_PREFS.coverMaxW.default));
	applyCoverMaxHeight(numPref(POSTCARD_PREFS.coverMaxH.key, POSTCARD_PREFS.coverMaxH.default));
	applyCoverRadius(numPref(POSTCARD_PREFS.coverRadius.key, POSTCARD_PREFS.coverRadius.default));
	applySearchCoverRadius(numPref(POSTCARD_PREFS.searchCoverRadius.key, POSTCARD_PREFS.searchCoverRadius.default));
	applyCoverAlign(getSavedCoverAlign());
	applySearchCoverAlign(getSavedSearchCoverAlign());
	applyEventCoverPosition(getSavedEventCoverPosition());
	applyEventTitleSize(numPref(POSTCARD_PREFS.eventTitleSize.key, POSTCARD_PREFS.eventTitleSize.default));
	applyEventCoverSpacing(numPref(POSTCARD_PREFS.eventCoverSpacing.key, POSTCARD_PREFS.eventCoverSpacing.default));

	applyCustomCss();
	syncThemeColor();
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
