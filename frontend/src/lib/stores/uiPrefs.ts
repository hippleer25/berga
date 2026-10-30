import { writable, type Writable, get } from 'svelte/store';
import { browser } from '$app/environment';
import { syncThemeColor } from '$lib/utils/themeColor';

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

/** Whether the user explicitly chose a surface radius (vs. the mode preset). */
export function hasSavedRadiusSurface(): boolean {
	return browser && localStorage.getItem(RADIUS_SURFACE_KEY) !== null;
}

/** Whether the user explicitly chose a control radius (vs. the mode preset). */
export function hasSavedRadiusControl(): boolean {
	return browser && localStorage.getItem(RADIUS_CONTROL_KEY) !== null;
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

/* ── Row highlight radius (hover / active / selected backgrounds) ─────────
   The tint that lights up post rows and event clusters on hover. 0 = Auto:
   follows --ui-radius-lg so it inherits the surface aesthetic; any value
   above 0 overrides it explicitly. */

export const HOVER_RADIUS_MIN = 0;
export const HOVER_RADIUS_MAX = 32;
export const HOVER_RADIUS_DEFAULT = 0;
const HOVER_RADIUS_KEY = 'ui-hover-radius';

export function applyHoverRadius(px: number, persist = false) {
	if (!browser) return;
	const v = clamp(px, HOVER_RADIUS_MIN, HOVER_RADIUS_MAX);
	document.documentElement.style.setProperty(
		'--ui-hover-radius',
		v > 0 ? `${v}px` : 'var(--ui-radius-lg)'
	);
	if (persist) localStorage.setItem(HOVER_RADIUS_KEY, String(v));
}

export function getSavedHoverRadius(): number {
	return readRadius(HOVER_RADIUS_KEY, HOVER_RADIUS_MIN, HOVER_RADIUS_MAX, HOVER_RADIUS_DEFAULT);
}

export const uiHoverRadius: Writable<number> = writable(getSavedHoverRadius());

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
export const DECK_RADIUS_PCT_DEFAULT = 17;
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

/* ── Mobile bottom navbar sizing ────────────────────────────────────────── */

export const MNAV_ICON_SIZE_MIN = 16;
export const MNAV_ICON_SIZE_MAX = 28;
export const MNAV_ICON_SIZE_DEFAULT = 21;
const MNAV_ICON_SIZE_KEY = 'ui-mnav-icon-size';

export const MNAV_ICON_BOX_MIN = 22;
export const MNAV_ICON_BOX_MAX = 40;
export const MNAV_ICON_BOX_DEFAULT = 28;
const MNAV_ICON_BOX_KEY = 'ui-mnav-icon-box';

export const MNAV_LABEL_SIZE_MIN = 9;
export const MNAV_LABEL_SIZE_MAX = 14;
export const MNAV_LABEL_SIZE_DEFAULT = 11;
const MNAV_LABEL_SIZE_KEY = 'ui-mnav-label-size';

export const MNAV_LABEL_GAP_MIN = 0;
export const MNAV_LABEL_GAP_MAX = 8;
export const MNAV_LABEL_GAP_DEFAULT = 2;
const MNAV_LABEL_GAP_KEY = 'ui-mnav-label-gap';

export const MNAV_HEIGHT_MIN = 52;
export const MNAV_HEIGHT_MAX = 88;
export const MNAV_HEIGHT_DEFAULT = 64;
const MNAV_HEIGHT_KEY = 'ui-mnav-height';

const MNAV_LABELS_KEY = 'ui-mnav-labels';

export type MnavItemRadius = 'theme' | 'round' | 'square';
const MNAV_RADIUS_KEY = 'ui-mnav-radius';
const MNAV_RADIUS_VALUES: MnavItemRadius[] = ['theme', 'round', 'square'];

export function applyMnavIconSize(px: number, persist = false) {
	if (!browser) return;
	const v = clamp(px, MNAV_ICON_SIZE_MIN, MNAV_ICON_SIZE_MAX);
	document.documentElement.style.setProperty('--mnav-icon-size', `${v}px`);
	if (persist) localStorage.setItem(MNAV_ICON_SIZE_KEY, String(v));
}

export function applyMnavIconBox(px: number, persist = false) {
	if (!browser) return;
	const v = clamp(px, MNAV_ICON_BOX_MIN, MNAV_ICON_BOX_MAX);
	document.documentElement.style.setProperty('--mnav-iconbox-h', `${v}px`);
	if (persist) localStorage.setItem(MNAV_ICON_BOX_KEY, String(v));
}

export function applyMnavLabelSize(px: number, persist = false) {
	if (!browser) return;
	const v = clamp(px, MNAV_LABEL_SIZE_MIN, MNAV_LABEL_SIZE_MAX);
	document.documentElement.style.setProperty('--mnav-label-size', `${v}px`);
	if (persist) localStorage.setItem(MNAV_LABEL_SIZE_KEY, String(v));
}

export function applyMnavLabelGap(px: number, persist = false) {
	if (!browser) return;
	const v = clamp(px, MNAV_LABEL_GAP_MIN, MNAV_LABEL_GAP_MAX);
	document.documentElement.style.setProperty('--mnav-label-gap', `${v}px`);
	if (persist) localStorage.setItem(MNAV_LABEL_GAP_KEY, String(v));
}

export function applyMnavHeight(px: number, persist = false) {
	if (!browser) return;
	const v = clamp(px, MNAV_HEIGHT_MIN, MNAV_HEIGHT_MAX);
	document.documentElement.style.setProperty('--mnav-height', `${v}px`);
	if (persist) localStorage.setItem(MNAV_HEIGHT_KEY, String(v));
}

export function applyMnavLabels(on: boolean, persist = false) {
	if (!browser) return;
	document.documentElement.setAttribute('data-mnav-labels', on ? 'on' : 'off');
	if (persist) localStorage.setItem(MNAV_LABELS_KEY, on ? 'true' : 'false');
}

export function applyMnavItemRadius(mode: MnavItemRadius, persist = false) {
	if (!browser) return;
	const root = document.documentElement;
	if (mode === 'theme') root.style.removeProperty('--mnav-item-radius');
	else if (mode === 'round') root.style.setProperty('--mnav-item-radius', 'calc(var(--mnav-iconbox-h, 28px) / 2)');
	else root.style.setProperty('--mnav-item-radius', '0px');
	if (persist) localStorage.setItem(MNAV_RADIUS_KEY, mode);
}

export function getSavedMnavIconSize(): number {
	return readRadius(MNAV_ICON_SIZE_KEY, MNAV_ICON_SIZE_MIN, MNAV_ICON_SIZE_MAX, MNAV_ICON_SIZE_DEFAULT);
}

export function getSavedMnavIconBox(): number {
	return readRadius(MNAV_ICON_BOX_KEY, MNAV_ICON_BOX_MIN, MNAV_ICON_BOX_MAX, MNAV_ICON_BOX_DEFAULT);
}

export function getSavedMnavLabelSize(): number {
	return readRadius(MNAV_LABEL_SIZE_KEY, MNAV_LABEL_SIZE_MIN, MNAV_LABEL_SIZE_MAX, MNAV_LABEL_SIZE_DEFAULT);
}

export function getSavedMnavLabelGap(): number {
	return readRadius(MNAV_LABEL_GAP_KEY, MNAV_LABEL_GAP_MIN, MNAV_LABEL_GAP_MAX, MNAV_LABEL_GAP_DEFAULT);
}

export function getSavedMnavHeight(): number {
	return readRadius(MNAV_HEIGHT_KEY, MNAV_HEIGHT_MIN, MNAV_HEIGHT_MAX, MNAV_HEIGHT_DEFAULT);
}

export function getSavedMnavLabels(): boolean {
	if (!browser) return true;
	return localStorage.getItem(MNAV_LABELS_KEY) !== 'false';
}

export function getSavedMnavItemRadius(): MnavItemRadius {
	if (!browser) return 'theme';
	const v = localStorage.getItem(MNAV_RADIUS_KEY) as MnavItemRadius | null;
	return v && MNAV_RADIUS_VALUES.includes(v) ? v : 'theme';
}

export const uiMnavIconSize: Writable<number> = writable(getSavedMnavIconSize());
export const uiMnavIconBox: Writable<number> = writable(getSavedMnavIconBox());
export const uiMnavLabelSize: Writable<number> = writable(getSavedMnavLabelSize());
export const uiMnavLabelGap: Writable<number> = writable(getSavedMnavLabelGap());
export const uiMnavHeight: Writable<number> = writable(getSavedMnavHeight());
export const uiMnavLabels: Writable<boolean> = writable(getSavedMnavLabels());
export const uiMnavItemRadius: Writable<MnavItemRadius> = writable(getSavedMnavItemRadius());

/* ── Home welcome title style ───────────────────────────────────────────── */

const WELCOME_BOLD_LEGACY_KEY = 'ui-welcome-bold';

export type WelcomeStyle = 'regular' | 'normal' | 'bold' | 'italic';
const WELCOME_STYLE_KEY = 'ui-welcome-style';
const WELCOME_STYLE_VALUES: WelcomeStyle[] = ['regular', 'normal', 'bold', 'italic'];

export function applyWelcomeStyle(style: WelcomeStyle, persist = false) {
	if (!browser) return;
	document.documentElement.setAttribute('data-welcome-style', style);
	if (persist) localStorage.setItem(WELCOME_STYLE_KEY, style);
}

export function getSavedWelcomeStyle(): WelcomeStyle {
	if (!browser) return 'normal';
	const v = localStorage.getItem(WELCOME_STYLE_KEY) as WelcomeStyle | null;
	if (v && WELCOME_STYLE_VALUES.includes(v)) return v;
	// Legacy binary toggle: true → bold, false → normal (weight now lives in CSS)
	return localStorage.getItem(WELCOME_BOLD_LEGACY_KEY) === 'true' ? 'bold' : 'normal';
}

export const uiWelcomeStyle: Writable<WelcomeStyle> = writable(getSavedWelcomeStyle());

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

/* ── Desktop navigation model ───────────────────────────────────────────── */

export type DesktopNavModel = 'sidebar' | 'dock';
const DESKTOP_NAV_KEY = 'ui-desktop-nav';

export function applyDesktopNav(model: DesktopNavModel, persist = false) {
	if (!browser) return;
	document.documentElement.setAttribute('data-desktop-nav', model);
	if (persist) localStorage.setItem(DESKTOP_NAV_KEY, model);
}

export function getSavedDesktopNav(): DesktopNavModel {
	if (!browser) return 'sidebar';
	return localStorage.getItem(DESKTOP_NAV_KEY) === 'dock' ? 'dock' : 'sidebar';
}

export const uiDesktopNav: Writable<DesktopNavModel> = writable(getSavedDesktopNav());

/* ── Desktop dock sizing (relative units — screen-size independent) ───────
   Width is a % of the viewport's smaller dimension (vmin) clamped to sane
   px bounds, and the corner radius is a % of the dock width — so a 720p
   laptop and a 4K panel end up with the same proportions. */

export const DOCK_WIDTH_MIN = 4;
export const DOCK_WIDTH_MAX = 18;
export const DOCK_WIDTH_DEFAULT = 7.5;
const DOCK_WIDTH_KEY = 'ui-dock-width-vmin';

export const DOCK_RADIUS_MIN = 0;
export const DOCK_RADIUS_MAX = 50;
export const DOCK_RADIUS_DEFAULT = 34;
const DOCK_RADIUS_KEY = 'ui-dock-radius-pct';

/* Inner padding between icon and dock border, as a % of the dock width. */
export const DOCK_PAD_MIN = 2;
export const DOCK_PAD_MAX = 25;
export const DOCK_PAD_DEFAULT = 20;
const DOCK_PAD_KEY = 'ui-dock-pad-pct';

/* Distance between the dock and the screen's left edge, in vmin. */
export const DOCK_INSET_MIN = 0.5;
export const DOCK_INSET_MAX = 20;
export const DOCK_INSET_DEFAULT = 12;
const DOCK_INSET_KEY = 'ui-dock-inset-vmin';

/* Dock length as a % of the viewport height. 0 = Auto: the dock hugs its
   content (fit-content); above 0 it is stretched and its items center. */
export const DOCK_HEIGHT_MIN = 0;
export const DOCK_HEIGHT_MAX = 90;
export const DOCK_HEIGHT_DEFAULT = 0;
const DOCK_HEIGHT_KEY = 'ui-dock-height-pct';

export function applyDockHeightPct(v: number, persist = false) {
	if (!browser) return;
	const val = clamp(v, DOCK_HEIGHT_MIN, DOCK_HEIGHT_MAX);
	const root = document.documentElement;
	if (val <= 0) root.style.removeProperty('--dock-h');
	else root.style.setProperty('--dock-h', `${val}vh`);
	if (persist) localStorage.setItem(DOCK_HEIGHT_KEY, String(val));
}

export function getSavedDockHeightPct(): number {
	return readRadius(DOCK_HEIGHT_KEY, DOCK_HEIGHT_MIN, DOCK_HEIGHT_MAX, DOCK_HEIGHT_DEFAULT);
}

/* Dock density scale, %: multiplies both the gap between icons and the
   wall padding (icon↔border). 0 = navbar hugs the icons, 200 = airy. */
export const DOCK_SPACING_MIN = 0;
export const DOCK_SPACING_MAX = 200;
export const DOCK_SPACING_DEFAULT = 100;
const DOCK_SPACING_KEY = 'ui-dock-spacing-pct';

/* Dock shadow intensity: 0 = no shadow, 100 = the design default. */
export const DOCK_SHADOW_MIN = 0;
export const DOCK_SHADOW_MAX = 100;
export const DOCK_SHADOW_DEFAULT = 0;
const DOCK_SHADOW_KEY = 'ui-dock-shadow';

export function applyDockWidthVmin(v: number, persist = false) {
	if (!browser) return;
	const val = clamp(v, DOCK_WIDTH_MIN, DOCK_WIDTH_MAX);
	document.documentElement.style.setProperty('--dock-w', `clamp(40px, ${val}vmin, 128px)`);
	applyDockRadiusPct(get(uiDockRadiusPct));
	if (persist) localStorage.setItem(DOCK_WIDTH_KEY, String(val));
}

export function applyDockRadiusPct(v: number, persist = false) {
	if (!browser) return;
	const val = clamp(v, DOCK_RADIUS_MIN, DOCK_RADIUS_MAX);
	document.documentElement.style.setProperty(
		'--dock-radius',
		`calc(var(--dock-w, 72px) * ${val} / 100)`
	);
	if (persist) localStorage.setItem(DOCK_RADIUS_KEY, String(val));
}

export function applyDockPadPct(v: number, persist = false) {
	if (!browser) return;
	const val = clamp(v, DOCK_PAD_MIN, DOCK_PAD_MAX);
	document.documentElement.style.setProperty('--dock-pad-pct', String(val));
	if (persist) localStorage.setItem(DOCK_PAD_KEY, String(val));
}

export function applyDockInsetVmin(v: number, persist = false) {
	if (!browser) return;
	const val = clamp(v, DOCK_INSET_MIN, DOCK_INSET_MAX);
	document.documentElement.style.setProperty('--dock-inset', `clamp(4px, ${val}vmin, 160px)`);
	if (persist) localStorage.setItem(DOCK_INSET_KEY, String(val));
}

export function applyDockSpacingPct(v: number, persist = false) {
	if (!browser) return;
	const val = clamp(v, DOCK_SPACING_MIN, DOCK_SPACING_MAX);
	document.documentElement.style.setProperty('--dock-space', String(val / 100));
	if (persist) localStorage.setItem(DOCK_SPACING_KEY, String(val));
}

export function applyDockShadowPct(v: number, persist = false) {
	if (!browser) return;
	const val = clamp(v, DOCK_SHADOW_MIN, DOCK_SHADOW_MAX);
	document.documentElement.style.setProperty('--dock-shadow-strength', String(val / 100));
	if (persist) localStorage.setItem(DOCK_SHADOW_KEY, String(val));
}

export function getSavedDockWidthVmin(): number {
	return readRadius(DOCK_WIDTH_KEY, DOCK_WIDTH_MIN, DOCK_WIDTH_MAX, DOCK_WIDTH_DEFAULT);
}

export function getSavedDockRadiusPct(): number {
	return readRadius(DOCK_RADIUS_KEY, DOCK_RADIUS_MIN, DOCK_RADIUS_MAX, DOCK_RADIUS_DEFAULT);
}

export function getSavedDockPadPct(): number {
	return readRadius(DOCK_PAD_KEY, DOCK_PAD_MIN, DOCK_PAD_MAX, DOCK_PAD_DEFAULT);
}

export function getSavedDockInsetVmin(): number {
	return readRadius(DOCK_INSET_KEY, DOCK_INSET_MIN, DOCK_INSET_MAX, DOCK_INSET_DEFAULT);
}

export function getSavedDockSpacingPct(): number {
	return readRadius(DOCK_SPACING_KEY, DOCK_SPACING_MIN, DOCK_SPACING_MAX, DOCK_SPACING_DEFAULT);
}

export function getSavedDockShadowPct(): number {
	return readRadius(DOCK_SHADOW_KEY, DOCK_SHADOW_MIN, DOCK_SHADOW_MAX, DOCK_SHADOW_DEFAULT);
}

export const uiDockWidthVmin: Writable<number> = writable(getSavedDockWidthVmin());
export const uiDockRadiusPct: Writable<number> = writable(getSavedDockRadiusPct());
export const uiDockPadPct: Writable<number> = writable(getSavedDockPadPct());
export const uiDockInsetVmin: Writable<number> = writable(getSavedDockInsetVmin());
export const uiDockHeightPct: Writable<number> = writable(getSavedDockHeightPct());
export const uiDockSpacingPct: Writable<number> = writable(getSavedDockSpacingPct());
export const uiDockShadowPct: Writable<number> = writable(getSavedDockShadowPct());

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
	return `color-mix(in oklch, var(--color-base-content) 24%, transparent)`;
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

/* ── Button borders toggle ──────────────────────────────────────────────── */

const BUTTON_BORDERS_KEY = 'ui-btn-borders';

export function applyButtonBorders(on: boolean, persist = false) {
	if (!browser) return;
	document.documentElement.setAttribute('data-btn-borders', on ? 'on' : 'off');
	if (persist) localStorage.setItem(BUTTON_BORDERS_KEY, on ? 'true' : 'false');
}

export function getSavedButtonBorders(): boolean {
	if (!browser) return true;
	const v = localStorage.getItem(BUTTON_BORDERS_KEY);
	return v === null ? true : v === 'true';
}

export const uiButtonBorders: Writable<boolean> = writable(getSavedButtonBorders());

/* ── Nav indicator ───────────────────────────────────────────────────────── */

export type NavIndicator = 'modern' | 'classic' | 'none';
const NAV_INDICATOR_KEY = 'ui-nav-indicator';
const NAV_INDICATOR_VALUES: NavIndicator[] = ['modern', 'classic', 'none'];

export function applyNavIndicator(style: NavIndicator, persist = false) {
	if (!browser) return;
	document.documentElement.setAttribute('data-nav-indicator', style);
	if (persist) localStorage.setItem(NAV_INDICATOR_KEY, style);
}

export function getSavedNavIndicator(): NavIndicator {
	if (!browser) return 'modern';
	const v = localStorage.getItem(NAV_INDICATOR_KEY) as NavIndicator | null;
	return v && NAV_INDICATOR_VALUES.includes(v) ? v : 'modern';
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

export type NavBg = 'default' | 'white' | 'berga-white' | 'berga-gray' | 'dark' | 'amoled';
export const NAV_BG_BERGA_WHITE = '#fbfaf7';
export const NAV_BG_BERGA_GRAY = '#f8f7f3';
const NAV_BG_KEY = 'ui-nav-bg';
const NAV_BG_VALUES: NavBg[] = ['default', 'white', 'berga-white', 'berga-gray', 'dark', 'amoled'];

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

export type PageBg = 'theme' | 'white' | 'berga-white' | 'berga-gray' | 'dark' | 'amoled';
const PAGE_BG_KEY = 'ui-page-bg';
const PAGE_BG_VALUES: PageBg[] = ['theme', 'white', 'berga-white', 'berga-gray', 'dark', 'amoled'];
const PAGE_BG_HASHES: Record<Exclude<PageBg, 'theme'>, string> = {
	'white': '#ffffff',
	'berga-white': '#fbfaf7',
	'berga-gray': '#f8f7f3',
	'dark': '#17181d',
	'amoled': '#000000',
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
		root.setAttribute('data-theme', value === 'dark' || value === 'amoled' ? 'berga' : 'berga-black');
		root.setAttribute('data-page-bg', value);
		if (persist) localStorage.setItem(PAGE_BG_KEY, value);
	}
	syncThemeColor();
}

export function getSavedPageBg(): PageBg {
	if (!browser) return 'theme';
	const v = localStorage.getItem(PAGE_BG_KEY) as PageBg | null;
	return v && PAGE_BG_VALUES.includes(v) ? v : 'theme';
}

export const uiPageBg: Writable<PageBg> = writable(getSavedPageBg());

/* ── Settings icon placement (desktop) ──────────────────────────────────── */

export type SettingsIconPlacement = 'top' | 'navbar' | 'both';
const SETTINGS_ICON_KEY = 'ui-settings-icon-placement';
const SETTINGS_ICON_VALUES: SettingsIconPlacement[] = ['top', 'navbar', 'both'];

export function applySettingsIconPlacement(v: SettingsIconPlacement, persist = false) {
	if (!browser) return;
	document.documentElement.setAttribute('data-settings-icon', v);
	if (persist) localStorage.setItem(SETTINGS_ICON_KEY, v);
}

export function getSavedSettingsIconPlacement(): SettingsIconPlacement {
	if (!browser) return 'navbar';
	const v = localStorage.getItem(SETTINGS_ICON_KEY) as SettingsIconPlacement | null;
	return v && SETTINGS_ICON_VALUES.includes(v) ? v : 'navbar';
}

export const uiSettingsIconPlacement: Writable<SettingsIconPlacement> = writable(getSavedSettingsIconPlacement());

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

/* ── Home welcome top space (title ↔ top of page, rem — universal) ─────── */

export const WELCOME_SPACE_MIN = 0;
export const WELCOME_SPACE_MAX = 4;
export const WELCOME_SPACE_DEFAULT = 0;
const WELCOME_SPACE_KEY = 'ui-welcome-space';

export function applyWelcomeSpace(rem: number, persist = false) {
	if (!browser) return;
	const v = clamp(rem, WELCOME_SPACE_MIN, WELCOME_SPACE_MAX);
	document.documentElement.style.setProperty('--welcome-space-top', `${v}rem`);
	if (persist) localStorage.setItem(WELCOME_SPACE_KEY, String(v));
}

export function getSavedWelcomeSpace(): number {
	if (!browser) return WELCOME_SPACE_DEFAULT;
	const v = Number(localStorage.getItem(WELCOME_SPACE_KEY));
	return Number.isFinite(v) && v >= WELCOME_SPACE_MIN && v <= WELCOME_SPACE_MAX
		? v
		: WELCOME_SPACE_DEFAULT;
}

export const uiWelcomeSpace: Writable<number> = writable(getSavedWelcomeSpace());

/* ── Desktop sidebar knob sizes (rem — universal) ──────────────────────── */

export const SIDEBAR_MARGIN_MIN = 0;
export const SIDEBAR_MARGIN_MAX = 2.5;
export const SIDEBAR_MARGIN_DEFAULT = 0.625;
const SIDEBAR_MARGIN_KEY = 'ui-sidebar-margin';

export function applySidebarMargin(rem: number, persist = false) {
	if (!browser) return;
	const v = clamp(rem, SIDEBAR_MARGIN_MIN, SIDEBAR_MARGIN_MAX);
	document.documentElement.style.setProperty('--sidebar-item-margin', `${v}rem`);
	if (persist) localStorage.setItem(SIDEBAR_MARGIN_KEY, String(v));
}

export function getSavedSidebarMargin(): number {
	if (!browser) return SIDEBAR_MARGIN_DEFAULT;
	const v = Number(localStorage.getItem(SIDEBAR_MARGIN_KEY));
	return Number.isFinite(v) && v >= SIDEBAR_MARGIN_MIN && v <= SIDEBAR_MARGIN_MAX
		? v
		: SIDEBAR_MARGIN_DEFAULT;
}

export const uiSidebarMargin: Writable<number> = writable(getSavedSidebarMargin());

/* ── Desktop sidebar pill size (vertical padding, rem) ─────────────────── */

export const SIDEBAR_SIZE_MIN = 0.25;
export const SIDEBAR_SIZE_MAX = 1.25;
export const SIDEBAR_SIZE_DEFAULT = 0.5;
const SIDEBAR_SIZE_KEY = 'ui-sidebar-size';

export function applySidebarSize(rem: number, persist = false) {
	if (!browser) return;
	const v = clamp(rem, SIDEBAR_SIZE_MIN, SIDEBAR_SIZE_MAX);
	document.documentElement.style.setProperty('--sidebar-item-pad-y', `${v}rem`);
	if (persist) localStorage.setItem(SIDEBAR_SIZE_KEY, String(v));
}

export function getSavedSidebarSize(): number {
	if (!browser) return SIDEBAR_SIZE_DEFAULT;
	const v = Number(localStorage.getItem(SIDEBAR_SIZE_KEY));
	return Number.isFinite(v) && v >= SIDEBAR_SIZE_MIN && v <= SIDEBAR_SIZE_MAX
		? v
		: SIDEBAR_SIZE_DEFAULT;
}

export const uiSidebarSize: Writable<number> = writable(getSavedSidebarSize());

/* ── Init / reset ───────────────────────────────────────────────────────── */

export function initUiPrefs() {
	migrateLegacyRadius();
	applyRadiusSurfaces(getSavedRadiusSurface());
	applyRadiusControls(getSavedRadiusControl());
	applyHoverRadius(getSavedHoverRadius());
	applyNavStyle(getSavedNavStyle());
	applyDesktopNav(getSavedDesktopNav());
	applyDockWidthVmin(getSavedDockWidthVmin());
	applyDockRadiusPct(getSavedDockRadiusPct());
	applyDockPadPct(getSavedDockPadPct());
	applyDockInsetVmin(getSavedDockInsetVmin());
	applyDockHeightPct(getSavedDockHeightPct());
	applyDockShadowPct(getSavedDockShadowPct());
	applyGlass(getSavedGlass());
	applyAccent(getSavedAccent());
	syncBorder();
	applyNavIndicator(getSavedNavIndicator());
	applyChipIcons(getSavedChipIcons());
	migrateLegacyDeck();
	applyDeckWidthPct(getSavedDeckWidthPct());
	applyDeckHeightVw(getSavedDeckHeightVw());
	applyDeckRadiusPct(getSavedDeckRadiusPct());
	applyWelcomeStyle(getSavedWelcomeStyle());
	applyWelcomeSpace(getSavedWelcomeSpace());
	applyNavBg(getSavedNavBg());
	applyButtonBorders(getSavedButtonBorders());
	applySettingsIconPlacement(getSavedSettingsIconPlacement());
	applySidebarCollapsed(getSavedSidebarCollapsed());
	applySidebarMargin(getSavedSidebarMargin());
	applySidebarSize(getSavedSidebarSize());
	applyMnavHeight(getSavedMnavHeight());
	applyMnavIconSize(getSavedMnavIconSize());
	applyMnavIconBox(getSavedMnavIconBox());
	applyMnavLabelSize(getSavedMnavLabelSize());
	applyMnavLabelGap(getSavedMnavLabelGap());
	applyMnavLabels(getSavedMnavLabels());
	applyMnavItemRadius(getSavedMnavItemRadius());
	applyPageBg(getSavedPageBg());
}

export function resetUiPrefs() {
	uiRadiusSurface.set(RADIUS_SURFACE_DEFAULT);
	applyRadiusSurfaces(RADIUS_SURFACE_DEFAULT);
	localStorage.removeItem(RADIUS_SURFACE_KEY);
	uiRadiusControl.set(RADIUS_CONTROL_DEFAULT);
	applyRadiusControls(RADIUS_CONTROL_DEFAULT);
	localStorage.removeItem(RADIUS_CONTROL_KEY);
	uiHoverRadius.set(HOVER_RADIUS_DEFAULT);
	applyHoverRadius(HOVER_RADIUS_DEFAULT);
	localStorage.removeItem(HOVER_RADIUS_KEY);
	uiNavStyle.set('bar');
	applyNavStyle('bar', true);
	uiDesktopNav.set('sidebar');
	applyDesktopNav('sidebar', true);
	uiDockWidthVmin.set(DOCK_WIDTH_DEFAULT);
	applyDockWidthVmin(DOCK_WIDTH_DEFAULT, true);
	uiDockRadiusPct.set(DOCK_RADIUS_DEFAULT);
	applyDockRadiusPct(DOCK_RADIUS_DEFAULT, true);
	uiDockPadPct.set(DOCK_PAD_DEFAULT);
	applyDockPadPct(DOCK_PAD_DEFAULT, true);
	uiDockInsetVmin.set(DOCK_INSET_DEFAULT);
	applyDockInsetVmin(DOCK_INSET_DEFAULT, true);
	uiDockHeightPct.set(DOCK_HEIGHT_DEFAULT);
	applyDockHeightPct(DOCK_HEIGHT_DEFAULT, true);
	uiDockSpacingPct.set(DOCK_SPACING_DEFAULT);
	applyDockSpacingPct(DOCK_SPACING_DEFAULT, true);
	uiDockShadowPct.set(DOCK_SHADOW_DEFAULT);
	applyDockShadowPct(DOCK_SHADOW_DEFAULT, true);
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
	uiWelcomeStyle.set('normal');
	applyWelcomeStyle('normal', true);
	uiWelcomeSpace.set(WELCOME_SPACE_DEFAULT);
	applyWelcomeSpace(WELCOME_SPACE_DEFAULT, true);
	uiNavBg.set('berga-gray');
	applyNavBg('berga-gray', true);
	uiSettingsIconPlacement.set('navbar');
	applySettingsIconPlacement('navbar', true);
	uiSidebarCollapsed.set(false);
	applySidebarCollapsed(false, true);
	uiSidebarMargin.set(SIDEBAR_MARGIN_DEFAULT);
	applySidebarMargin(SIDEBAR_MARGIN_DEFAULT, true);
	uiSidebarSize.set(SIDEBAR_SIZE_DEFAULT);
	applySidebarSize(SIDEBAR_SIZE_DEFAULT, true);
	uiMnavHeight.set(MNAV_HEIGHT_DEFAULT);
	applyMnavHeight(MNAV_HEIGHT_DEFAULT, true);
	uiMnavIconSize.set(MNAV_ICON_SIZE_DEFAULT);
	applyMnavIconSize(MNAV_ICON_SIZE_DEFAULT, true);
	uiMnavIconBox.set(MNAV_ICON_BOX_DEFAULT);
	applyMnavIconBox(MNAV_ICON_BOX_DEFAULT, true);
	uiMnavLabelSize.set(MNAV_LABEL_SIZE_DEFAULT);
	applyMnavLabelSize(MNAV_LABEL_SIZE_DEFAULT, true);
	uiMnavLabelGap.set(MNAV_LABEL_GAP_DEFAULT);
	applyMnavLabelGap(MNAV_LABEL_GAP_DEFAULT, true);
	uiMnavLabels.set(true);
	applyMnavLabels(true, true);
	uiMnavItemRadius.set('theme');
	applyMnavItemRadius('theme', true);
	uiPageBg.set('theme');
	applyPageBg('theme', true);
	uiButtonBorders.set(true);
	applyButtonBorders(true, true);
}
