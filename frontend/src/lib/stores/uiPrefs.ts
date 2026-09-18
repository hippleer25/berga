import { writable, type Writable, get } from 'svelte/store';
import { browser } from '$app/environment';

/* ── Corner radius (granular: large surfaces + small controls) ──────────── */

export const RADIUS_SURFACE_MIN = 0;
export const RADIUS_SURFACE_MAX = 32;
export const RADIUS_SURFACE_DEFAULT = 17;
const RADIUS_SURFACE_KEY = 'ui-radius-surface';

export const RADIUS_CONTROL_MIN = 0;
export const RADIUS_CONTROL_MAX = 20;
export const RADIUS_CONTROL_DEFAULT = 5;
const RADIUS_CONTROL_KEY = 'ui-radius-control';

/** Legacy single-knob key — migrated to the two granular keys once. */
const RADIUS_LEGACY_KEY = 'ui-radius';

function clamp(v: number, min: number, max: number): number {
	return Math.min(max, Math.max(min, v));
}

function setFullRadius(surface: number, control: number) {
	if (!browser) return;
	const root = document.documentElement;
	root.style.setProperty(
		'--ui-radius-full',
		surface === 0 && control === 0 ? '0px' : '999px'
	);
}

/** Large surfaces (cards, modals, panels, floating dock). */
export function applyRadiusSurfaces(px: number, persist = false) {
	if (!browser) return;
	const s = clamp(px, RADIUS_SURFACE_MIN, RADIUS_SURFACE_MAX);
	const root = document.documentElement;
	root.style.setProperty('--ui-radius-lg', `${s}px`);
	root.style.setProperty('--ui-radius-xl', `${Math.min(Math.round(s * 1.4), 40)}px`);
	root.style.setProperty('--ui-radius', `${Math.round(s * 0.7)}px`);
	root.style.setProperty('--radius-box', `${Math.round(s * 0.72)}px`);
	setFullRadius(s, get(uiRadiusControl));
	if (persist) localStorage.setItem(RADIUS_SURFACE_KEY, String(s));
}

/** Small controls (buttons, inputs, chips, selects, toggles). */
export function applyRadiusControls(px: number, persist = false) {
	if (!browser) return;
	const c = clamp(px, RADIUS_CONTROL_MIN, RADIUS_CONTROL_MAX);
	const root = document.documentElement;
	root.style.setProperty('--ui-radius-sm', `${c}px`);
	root.style.setProperty('--ui-radius-xs', `${Math.max(2, Math.round(c * 0.55))}px`);
	root.style.setProperty('--radius-field', `${c}px`);
	root.style.setProperty('--radius-selector', `${Math.max(Math.round(c * 2.2), 12)}px`);
	setFullRadius(get(uiRadiusSurface), c);
	if (persist) localStorage.setItem(RADIUS_CONTROL_KEY, String(c));
}

function readRadius(key: string, min: number, max: number, def: number): number {
	if (!browser) return def;
	const raw = localStorage.getItem(key);
	if (raw === null) return def;
	const v = Number(raw);
	return Number.isFinite(v) && v >= min && v <= max ? v : def;
}

export function getSavedRadiusSurface(): number {
	return readRadius(RADIUS_SURFACE_KEY, RADIUS_SURFACE_MIN, RADIUS_SURFACE_MAX, RADIUS_SURFACE_DEFAULT);
}

export function getSavedRadiusControl(): number {
	return readRadius(RADIUS_CONTROL_KEY, RADIUS_CONTROL_MIN, RADIUS_CONTROL_MAX, RADIUS_CONTROL_DEFAULT);
}

/** One-time migration from the legacy single ui-radius knob. */
function migrateLegacyRadius() {
	if (!browser) return;
	const hasNew =
		localStorage.getItem(RADIUS_SURFACE_KEY) !== null ||
		localStorage.getItem(RADIUS_CONTROL_KEY) !== null;
	if (hasNew) return;
	const raw = localStorage.getItem(RADIUS_LEGACY_KEY);
	if (raw === null) return;
	const r = Number(raw);
	if (!Number.isFinite(r)) return;
	localStorage.setItem(RADIUS_SURFACE_KEY, String(clamp(Math.round(r * 1.4), RADIUS_SURFACE_MIN, RADIUS_SURFACE_MAX)));
	localStorage.setItem(RADIUS_CONTROL_KEY, String(clamp(Math.round(r * 0.6), RADIUS_CONTROL_MIN, RADIUS_CONTROL_MAX)));
	localStorage.removeItem(RADIUS_LEGACY_KEY);
}

export const uiRadiusSurface: Writable<number> = writable(getSavedRadiusSurface());
export const uiRadiusControl: Writable<number> = writable(getSavedRadiusControl());

/* ── Floating deck sizing (relative proportions, universal across devices) ──
   Width is a % of the screen, height is a % of screen width (vw), and the
   corner radius is a % of the deck height — so every device ends up with
   the same proportions regardless of its physical size. */

export const DECK_WIDTH_PCT_MIN = 70;
export const DECK_WIDTH_PCT_MAX = 96;
export const DECK_WIDTH_PCT_DEFAULT = 73;
const DECK_WIDTH_PCT_KEY = 'ui-deck-width-pct';

export const DECK_HEIGHT_VW_MIN = 13;
export const DECK_HEIGHT_VW_MAX = 22;
export const DECK_HEIGHT_VW_DEFAULT = 16;
const DECK_HEIGHT_VW_KEY = 'ui-deck-height-vw';

export const DECK_RADIUS_PCT_MIN = 0;
export const DECK_RADIUS_PCT_MAX = 50;
export const DECK_RADIUS_PCT_DEFAULT = 27;
const DECK_RADIUS_PCT_KEY = 'ui-deck-radius-pct';

/** Legacy px-based keys — migrated to the relative keys once. */
const DECK_LEGACY_KEYS = ['ui-deck-margin', 'ui-deck-height', 'ui-deck-radius'] as const;

function applyDeckRadiusValue() {
	if (!browser) return;
	const r = get(uiDeckRadiusPct);
	document.documentElement.style.setProperty(
		'--deck-radius',
		`calc(var(--deck-height) * ${r} / 100)`
	);
}

export function applyDeckWidthPct(px: number, persist = false) {
	if (!browser) return;
	const v = clamp(px, DECK_WIDTH_PCT_MIN, DECK_WIDTH_PCT_MAX);
	document.documentElement.style.setProperty('--deck-width', `${v}vw`);
	if (persist) localStorage.setItem(DECK_WIDTH_PCT_KEY, String(v));
}

export function applyDeckHeightVw(px: number, persist = false) {
	if (!browser) return;
	const v = clamp(px, DECK_HEIGHT_VW_MIN, DECK_HEIGHT_VW_MAX);
	document.documentElement.style.setProperty('--deck-height', `${v}vw`);
	applyDeckRadiusValue();
	if (persist) localStorage.setItem(DECK_HEIGHT_VW_KEY, String(v));
}

export function applyDeckRadiusPct(px: number, persist = false) {
	if (!browser) return;
	const v = clamp(px, DECK_RADIUS_PCT_MIN, DECK_RADIUS_PCT_MAX);
	document.documentElement.style.setProperty(
		'--deck-radius',
		`calc(var(--deck-height) * ${v} / 100)`
	);
	if (persist) localStorage.setItem(DECK_RADIUS_PCT_KEY, String(v));
}

export function getSavedDeckWidthPct(): number {
	return readRadius(DECK_WIDTH_PCT_KEY, DECK_WIDTH_PCT_MIN, DECK_WIDTH_PCT_MAX, DECK_WIDTH_PCT_DEFAULT);
}

export function getSavedDeckHeightVw(): number {
	return readRadius(DECK_HEIGHT_VW_KEY, DECK_HEIGHT_VW_MIN, DECK_HEIGHT_VW_MAX, DECK_HEIGHT_VW_DEFAULT);
}

export function getSavedDeckRadiusPct(): number {
	return readRadius(DECK_RADIUS_PCT_KEY, DECK_RADIUS_PCT_MIN, DECK_RADIUS_PCT_MAX, DECK_RADIUS_PCT_DEFAULT);
}

export const uiDeckWidthPct: Writable<number> = writable(getSavedDeckWidthPct());
export const uiDeckHeightVw: Writable<number> = writable(getSavedDeckHeightVw());
export const uiDeckRadiusPct: Writable<number> = writable(getSavedDeckRadiusPct());

/** One-time migration from the legacy px deck knobs to relative units. */
function migrateLegacyDeck() {
	if (!browser) return;
	const hasNew =
		localStorage.getItem(DECK_WIDTH_PCT_KEY) !== null ||
		localStorage.getItem(DECK_HEIGHT_VW_KEY) !== null ||
		localStorage.getItem(DECK_RADIUS_PCT_KEY) !== null;
	if (hasNew) return;
	const oldMargin = Number(localStorage.getItem(DECK_LEGACY_KEYS[0]));
	const oldHeight = Number(localStorage.getItem(DECK_LEGACY_KEYS[1]));
	const oldRadius = Number(localStorage.getItem(DECK_LEGACY_KEYS[2]));
	if (!DECK_LEGACY_KEYS.some(k => localStorage.getItem(k) !== null)) return;
	const w = window.innerWidth || 420;
	const widthPct = clamp(Math.round(100 * (1 - (2 * (Number.isFinite(oldMargin) ? oldMargin : 24)) / w)), DECK_WIDTH_PCT_MIN, DECK_WIDTH_PCT_MAX);
	const heightVw = clamp(Math.round(((Number.isFinite(oldHeight) ? oldHeight : 68) * 1000) / w) / 10, DECK_HEIGHT_VW_MIN, DECK_HEIGHT_VW_MAX);
	const radiusPct = Number.isFinite(oldHeight) && oldHeight > 0 && Number.isFinite(oldRadius)
		? clamp(Math.round((100 * oldRadius) / oldHeight), DECK_RADIUS_PCT_MIN, DECK_RADIUS_PCT_MAX)
		: DECK_RADIUS_PCT_DEFAULT;
	localStorage.setItem(DECK_WIDTH_PCT_KEY, String(widthPct));
	localStorage.setItem(DECK_HEIGHT_VW_KEY, String(heightVw));
	localStorage.setItem(DECK_RADIUS_PCT_KEY, String(radiusPct));
	for (const k of DECK_LEGACY_KEYS) localStorage.removeItem(k);
}

/* ── Home welcome title weight ───────────────────────────────────────────── */

const WELCOME_BOLD_KEY = 'ui-welcome-bold';

export function applyWelcomeBold(on: boolean, persist = false) {
	if (!browser) return;
	document.documentElement.setAttribute('data-welcome-bold', on ? 'on' : 'off');
	if (persist) localStorage.setItem(WELCOME_BOLD_KEY, on ? 'true' : 'false');
}

export function getSavedWelcomeBold(): boolean {
	if (!browser) return false;
	return localStorage.getItem(WELCOME_BOLD_KEY) === 'true';
}

export const uiWelcomeBold: Writable<boolean> = writable(getSavedWelcomeBold());

/* ── Bottom nav style ───────────────────────────────────────────────────── */

export type NavStyle = 'bar' | 'deck';
const NAV_STYLE_KEY = 'ui-nav-style';

export function applyNavStyle(style: NavStyle, persist = false) {
	if (!browser) return;
	document.documentElement.setAttribute('data-nav-style', style);
	if (persist) localStorage.setItem(NAV_STYLE_KEY, style);
}

export function getSavedNavStyle(): NavStyle {
	if (!browser) return 'bar';
	return localStorage.getItem(NAV_STYLE_KEY) === 'deck' ? 'deck' : 'bar';
}

export const uiNavStyle: Writable<NavStyle> = writable(getSavedNavStyle());

/* ── Frosted glass ──────────────────────────────────────────────────────── */

const GLASS_KEY = 'ui-glass';

export function applyGlass(on: boolean, persist = false) {
	if (!browser) return;
	document.documentElement.setAttribute('data-glass', on ? 'on' : 'off');
	if (persist) localStorage.setItem(GLASS_KEY, on ? 'true' : 'false');
}

export function getSavedGlass(): boolean {
	if (!browser) return true;
	return localStorage.getItem(GLASS_KEY) !== 'false';
}

export const uiGlass: Writable<boolean> = writable(getSavedGlass());

/* ── Accent color ───────────────────────────────────────────────────────── */

const ACCENT_KEY = 'ui-accent';
const HEX_RE = /^#[0-9a-fA-F]{6}$/;

/** null = follow the active theme's accent */
export function applyAccent(hex: string | null, persist = false) {
	if (!browser) return;
	const root = document.documentElement;
	if (hex && HEX_RE.test(hex)) {
		root.style.setProperty('--color-accent', hex);
		root.style.setProperty('--color-accent-content', contrastContentFor(hex));
	} else {
		root.style.removeProperty('--color-accent');
		root.style.removeProperty('--color-accent-content');
	}
	if (persist) {
		if (hex && HEX_RE.test(hex)) localStorage.setItem(ACCENT_KEY, hex);
		else localStorage.removeItem(ACCENT_KEY);
	}
}

export function getSavedAccent(): string | null {
	if (!browser) return null;
	const v = localStorage.getItem(ACCENT_KEY);
	return v && HEX_RE.test(v) ? v : null;
}

export const uiAccent: Writable<string | null> = writable(getSavedAccent());

/** Relative luminance (0 dark … 1 light) of a #rrggbb color. */
export function luminanceOf(hex: string): number {
	const n = parseInt(hex.slice(1), 16);
	const r = (n >> 16) & 255, g = (n >> 8) & 255, b = n & 255;
	const lin = (c: number) => {
		const s = c / 255;
		return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
	};
	return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
}

/** Pick a readable text color for content placed over the given accent. */
export function contrastContentFor(hex: string): string {
	return luminanceOf(hex) > 0.45 ? '#16130a' : '#ffffff';
}

/* ── Border option ──────────────────────────────────────────────────────── */

const BORDER_ON_KEY = 'ui-border-on';
const BORDER_WIDTH_KEY = 'ui-border-width';
const BORDER_COLOR_KEY = 'ui-border-color';

export const BORDER_WIDTH_MIN = 1;
export const BORDER_WIDTH_MAX = 3;

function defaultBorderColor(): string {
	return `color-mix(in oklch, var(--color-base-content) 16%, transparent)`;
}

export function applyBorder(
	on: boolean,
	width: number,
	color: string | null,
	persist = false
) {
	if (!browser) return;
	const root = document.documentElement;
	root.setAttribute('data-border', on ? 'on' : 'off');
	root.style.setProperty(
		'--ui-border-width',
		`${Math.min(BORDER_WIDTH_MAX, Math.max(BORDER_WIDTH_MIN, width))}px`
	);
	if (color && HEX_RE.test(color)) {
		root.style.setProperty('--ui-border-color', color);
	} else {
		root.style.setProperty('--ui-border-color', defaultBorderColor());
	}
	if (persist) {
		localStorage.setItem(BORDER_ON_KEY, on ? 'true' : 'false');
		localStorage.setItem(BORDER_WIDTH_KEY, String(width));
		if (color && HEX_RE.test(color)) localStorage.setItem(BORDER_COLOR_KEY, color);
		else localStorage.removeItem(BORDER_COLOR_KEY);
	}
}

export function getSavedBorderOn(): boolean {
	if (!browser) return false;
	return localStorage.getItem(BORDER_ON_KEY) === 'true';
}

export function getSavedBorderWidth(): number {
	if (!browser) return 1;
	const v = Number(localStorage.getItem(BORDER_WIDTH_KEY));
	return Number.isFinite(v) && v >= BORDER_WIDTH_MIN && v <= BORDER_WIDTH_MAX ? v : 1;
}

export function getSavedBorderColor(): string | null {
	if (!browser) return null;
	const v = localStorage.getItem(BORDER_COLOR_KEY);
	return v && HEX_RE.test(v) ? v : null;
}

export const uiBorderOn: Writable<boolean> = writable(getSavedBorderOn());
export const uiBorderWidth: Writable<number> = writable(getSavedBorderWidth());
export const uiBorderColor: Writable<string | null> = writable(getSavedBorderColor());

function syncBorder(persist = false) {
	applyBorder(
		get(uiBorderOn),
		get(uiBorderWidth),
		get(uiBorderColor),
		persist
	);
}

/* ── Nav indicator ───────────────────────────────────────────────────────── */

export type NavIndicator = 'modern' | 'classic';
const NAV_INDICATOR_KEY = 'ui-nav-indicator';

export function applyNavIndicator(style: NavIndicator, persist = false) {
	if (!browser) return;
	document.documentElement.setAttribute('data-nav-indicator', style);
	if (persist) localStorage.setItem(NAV_INDICATOR_KEY, style);
}

export function getSavedNavIndicator(): NavIndicator {
	if (!browser) return 'modern';
	return localStorage.getItem(NAV_INDICATOR_KEY) === 'classic' ? 'classic' : 'modern';
}

export const uiNavIndicator: Writable<NavIndicator> = writable(getSavedNavIndicator());

/* ── Filter pill icons ───────────────────────────────────────────────────── */

const CHIP_ICONS_KEY = 'ui-chip-icons';

export function applyChipIcons(on: boolean, persist = false) {
	if (!browser) return;
	document.documentElement.setAttribute('data-chip-icons', on ? 'on' : 'off');
	if (persist) localStorage.setItem(CHIP_ICONS_KEY, on ? 'true' : 'false');
}

export function getSavedChipIcons(): boolean {
	if (!browser) return true;
	return localStorage.getItem(CHIP_ICONS_KEY) !== 'false';
}

export const uiChipIcons: Writable<boolean> = writable(getSavedChipIcons());

/* ── Navbar background ─────────────────────────────────────────────────── */

export type NavBg = 'default' | 'white' | 'berga-white' | 'berga-gray' | 'dark';
export const NAV_BG_BERGA_WHITE = '#fbfaf7';
export const NAV_BG_BERGA_GRAY = '#f8f7f3';
const NAV_BG_KEY = 'ui-nav-bg';
const NAV_BG_VALUES: NavBg[] = ['default', 'white', 'berga-white', 'berga-gray', 'dark'];

/** Pre-rename 'berga-white' (#f8f7f3) → 'berga-gray'. */
function migrateNavBg(raw: string | null): NavBg | null {
	if (raw === 'berga-white') {
		localStorage.setItem(NAV_BG_KEY, 'berga-gray');
		return 'berga-gray';
	}
	return raw && NAV_BG_VALUES.includes(raw as NavBg) ? (raw as NavBg) : null;
}

export function applyNavBg(value: NavBg, persist = false) {
	if (!browser) return;
	document.documentElement.setAttribute('data-nav-bg', value);
	if (persist) localStorage.setItem(NAV_BG_KEY, value);
}

export function getSavedNavBg(): NavBg {
	if (!browser) return 'berga-gray';
	return migrateNavBg(localStorage.getItem(NAV_BG_KEY)) ?? 'berga-gray';
}

export const uiNavBg: Writable<NavBg> = writable(getSavedNavBg());

/* ── Page background ───────────────────────────────────────────────────── */

export type PageBg = 'theme' | 'white' | 'berga-white' | 'berga-gray' | 'dark';
const PAGE_BG_KEY = 'ui-page-bg';
const PAGE_BG_VALUES: PageBg[] = ['theme', 'white', 'berga-white', 'berga-gray', 'dark'];
const PAGE_BG_HASHES: Record<Exclude<PageBg, 'theme'>, string> = {
	'white': '#ffffff',
	'berga-white': '#fbfaf7',
	'berga-gray': '#f8f7f3',
	'dark': '#17181d',
};

/**
 * Full theme switch: light values ride on the light (`berga-black`) palette,
 * dark on the dark (`berga`) one; the chosen attribute only re-points the
 * base surfaces. 'theme' clears the override and follows preferred-theme.
 */
export function applyPageBg(value: PageBg, persist = false) {
	if (!browser) return;
	const root = document.documentElement;
	if (value === 'theme') {
		root.removeAttribute('data-page-bg');
		if (persist) localStorage.removeItem(PAGE_BG_KEY);
	} else {
		root.setAttribute('data-theme', value === 'dark' ? 'berga' : 'berga-black');
		root.setAttribute('data-page-bg', value);
		if (persist) localStorage.setItem(PAGE_BG_KEY, value);
	}
}

export function getSavedPageBg(): PageBg {
	if (!browser) return 'theme';
	const v = localStorage.getItem(PAGE_BG_KEY) as PageBg | null;
	return v && PAGE_BG_VALUES.includes(v) ? v : 'theme';
}

export const uiPageBg: Writable<PageBg> = writable(getSavedPageBg());

/* ── Desktop sidebar collapse ──────────────────────────────────────────── */

const SIDEBAR_COLLAPSED_KEY = 'ui-sidebar-collapsed';

export function applySidebarCollapsed(on: boolean, persist = false) {
	if (!browser) return;
	document.documentElement.setAttribute('data-sidebar-collapsed', on ? 'on' : 'off');
	if (persist) localStorage.setItem(SIDEBAR_COLLAPSED_KEY, on ? 'true' : 'false');
}

export function getSavedSidebarCollapsed(): boolean {
	if (!browser) return false;
	return localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === 'true';
}

export const uiSidebarCollapsed: Writable<boolean> = writable(getSavedSidebarCollapsed());

/* ── Init / reset ───────────────────────────────────────────────────────── */

export function initUiPrefs() {
	migrateLegacyRadius();
	applyRadiusSurfaces(getSavedRadiusSurface());
	applyRadiusControls(getSavedRadiusControl());
	applyNavStyle(getSavedNavStyle());
	applyGlass(getSavedGlass());
	applyAccent(getSavedAccent());
	syncBorder();
	applyNavIndicator(getSavedNavIndicator());
	applyChipIcons(getSavedChipIcons());
	migrateLegacyDeck();
	applyDeckWidthPct(getSavedDeckWidthPct());
	applyDeckHeightVw(getSavedDeckHeightVw());
	applyDeckRadiusPct(getSavedDeckRadiusPct());
	applyWelcomeBold(getSavedWelcomeBold());
	applyNavBg(getSavedNavBg());
	applySidebarCollapsed(getSavedSidebarCollapsed());
	applyPageBg(getSavedPageBg());
}

export function resetUiPrefs() {
	uiRadiusSurface.set(RADIUS_SURFACE_DEFAULT);
	applyRadiusSurfaces(RADIUS_SURFACE_DEFAULT, true);
	uiRadiusControl.set(RADIUS_CONTROL_DEFAULT);
	applyRadiusControls(RADIUS_CONTROL_DEFAULT, true);
	uiNavStyle.set('bar');
	applyNavStyle('bar', true);
	uiGlass.set(true);
	applyGlass(true, true);
	uiAccent.set(null);
	applyAccent(null, true);
	uiBorderOn.set(false);
	uiBorderWidth.set(1);
	uiBorderColor.set(null);
	syncBorder(true);
	uiNavIndicator.set('modern');
	applyNavIndicator('modern', true);
	uiChipIcons.set(true);
	applyChipIcons(true, true);
	uiDeckWidthPct.set(DECK_WIDTH_PCT_DEFAULT);
	applyDeckWidthPct(DECK_WIDTH_PCT_DEFAULT, true);
	uiDeckHeightVw.set(DECK_HEIGHT_VW_DEFAULT);
	applyDeckHeightVw(DECK_HEIGHT_VW_DEFAULT, true);
	uiDeckRadiusPct.set(DECK_RADIUS_PCT_DEFAULT);
	applyDeckRadiusPct(DECK_RADIUS_PCT_DEFAULT, true);
	uiWelcomeBold.set(false);
	applyWelcomeBold(false, true);
	uiNavBg.set('berga-gray');
	applyNavBg('berga-gray', true);
	uiSidebarCollapsed.set(false);
	applySidebarCollapsed(false, true);
	uiPageBg.set('theme');
	applyPageBg('theme', true);
}
