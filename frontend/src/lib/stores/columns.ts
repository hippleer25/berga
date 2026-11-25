import { writable, get } from 'svelte/store';
import { browser } from '$app/environment';
import { goto } from '$app/navigation';
import { orderedTabs, TAB_DEFS, type TabId } from '$lib/config/tabs';

export type { TabId };
import { activeTabIdx } from '$lib/stores/swipe';

/**
 * Dynamic desktop columns: the content area is a user-configurable grid of
 * 1–3 columns. Exactly one column is 'main' — it follows the URL-active tab
 * and is rendered by PageTrack. Every other column pins one of the four tab
 * screens; duplicates are allowed (two feed columns, two Mota chats, ...).
 * Mobile (<768px) ignores the layout entirely and keeps the swipe track.
 */

export type ColumnContent = TabId | 'main';

export type Pane = {
	/** Stable per-session id (Svelte each key). Not persisted. */
	id: number;
	content: ColumnContent;
};

export type ColumnsLayout = {
	panes: Pane[];
	/** Width share per pane, in % of the grid's flexible space (sums to ~100). */
	widths: number[];
};

export const MAX_COLUMNS = 3;
/** A pane never shrinks below this share of the flexible space. */
export const MIN_PANE_PCT = 14;
/** Gutter thickness between two panes. */
export const GUTTER_PX = 8;

const KEY = 'ui-columns';
/** Pre-columns split viewer storage, migrated once. */
const LEGACY_KEY = 'ui-split-view';

const TAB_IDS = Object.keys(TAB_DEFS) as TabId[];

let nextId = 1;
function makePane(content: ColumnContent): Pane {
	return { id: nextId++, content };
}

function equalized(n: number): number[] {
	return Array(n).fill(100 / n);
}

/** Floors every share; shares are only consumed as fr ratios, so the exact sum is free. */
function clampWidths(widths: number[]): number[] {
	return widths.map(v => Math.max(MIN_PANE_PCT, Number.isFinite(v) ? v : MIN_PANE_PCT));
}

function sanitizeWidths(raw: unknown, n: number): number[] {
	const w = Array.isArray(raw)
		? raw.slice(0, n).map(v => (typeof v === 'number' && Number.isFinite(v) && v > 0 ? v : 0))
		: [];
	while (w.length < n) w.push(0);
	const sum = w.reduce((a, b) => a + b, 0);
	if (sum <= 0) return equalized(n);
	return clampWidths(w.map(v => (v / sum) * 100));
}

function loadSaved(): ColumnsLayout {
	if (!browser) return { panes: [makePane('main')], widths: [100] };

	// ── New format ──
	try {
		const raw = JSON.parse(localStorage.getItem(KEY) ?? 'null');
		if (raw && typeof raw === 'object' && Array.isArray(raw.contents)) {
			const panes: Pane[] = [];
			for (const c of raw.contents) {
				if (c === 'main') panes.push(makePane('main'));
				else if (typeof c === 'string' && TAB_IDS.includes(c as TabId)) {
					panes.push(makePane(c as TabId));
				}
			}
			if (panes.length) {
				// Enforce 1..MAX columns with exactly one main pane.
				let seenMain = false;
				for (const p of panes) {
					if (p.content === 'main') {
						if (seenMain) p.content = 'events';
						else seenMain = true;
					}
				}
				if (!seenMain) panes[0].content = 'main';
				const trimmed = panes.slice(0, MAX_COLUMNS);
				return { panes: trimmed, widths: sanitizeWidths(raw.widths, trimmed.length) };
			}
		}
	} catch {}

	// ── Legacy 2-pane split migration ──
	try {
		const legacy = JSON.parse(localStorage.getItem(LEGACY_KEY) ?? 'null');
		if (legacy && typeof legacy.tab === 'string' && TAB_IDS.includes(legacy.tab)) {
			localStorage.removeItem(LEGACY_KEY);
			const pinned = makePane(legacy.tab as TabId);
			return legacy.side === 'left'
				? { panes: [pinned, makePane('main')], widths: equalized(2) }
				: { panes: [makePane('main'), pinned], widths: equalized(2) };
		}
	} catch {}

	return { panes: [makePane('main')], widths: [100] };
}

export const columnsLayout = writable<ColumnsLayout>(loadSaved());

function persist(l: ColumnsLayout) {
	if (!browser) return;
	try {
		localStorage.setItem(
			KEY,
			JSON.stringify({ contents: l.panes.map(p => p.content), widths: l.widths })
		);
	} catch {
		/* storage unavailable — layout stays session-only */
	}
}

function commit(panes: Pane[], widths: number[]) {
	const l = { panes, widths };
	columnsLayout.set(l);
	persist(l);
}

/** Id of the tab shown by the main (URL-active) column, or null. */
export function mainTabId(): TabId | null {
	const tabs = get(orderedTabs);
	const idx = get(activeTabIdx);
	return tabs[idx]?.id ?? null;
}

/** Navigate the main column to a tab (route + nav pill index). */
export function navigateMainTo(tab: TabId) {
	const tabs = get(orderedTabs);
	const idx = tabs.findIndex(t => t.id === tab);
	if (idx >= 0) activeTabIdx.set(idx);
	goto(TAB_DEFS[tab].href);
}

/** Change how many columns the desktop shows (1–MAX). */
export function setColumnCount(n: number) {
	const count = Math.max(1, Math.min(MAX_COLUMNS, Math.round(n)));
	const l = get(columnsLayout);
	const panes = l.panes.map(p => ({ ...p }));
	// Grow: defaults mirror the classic review layouts (feed / +search / +mota)
	const DEFAULTS: TabId[] = ['events', 'mota'];
	while (panes.length < count) panes.push(makePane(DEFAULTS[panes.length - 1] ?? 'events'));
	// Shrink: never drop the main pane
	while (panes.length > count) {
		let idx = -1;
		for (let i = panes.length - 1; i >= 0; i--) {
			if (panes[i].content !== 'main') {
				idx = i;
				break;
			}
		}
		if (idx === -1) break;
		panes.splice(idx, 1);
	}
	commit(panes, clampWidths(equalized(panes.length)));
}

/**
 * Pin a tab into a specific pane. Dropping/picking into the main column
 * navigates it instead — the main column follows the route by definition.
 */
export function assignTabToPane(paneId: number, tab: TabId) {
	const l = get(columnsLayout);
	const pane = l.panes.find(p => p.id === paneId);
	if (!pane) return;
	if (pane.content === 'main') {
		navigateMainTo(tab);
		return;
	}
	if (pane.content === tab) return;
	const panes = l.panes.map(p => (p.id === paneId ? { ...p, content: tab } : p));
	commit(panes, l.widths);
}

/** Left-click on a pinned tab's icon: that column becomes the main (route-driven) one. */
export function promotePane(paneId: number) {
	const l = get(columnsLayout);
	const pane = l.panes.find(p => p.id === paneId);
	const main = l.panes.find(p => p.content === 'main');
	if (!pane || !main || pane.id === main.id) return;
	const shownTab = pane.content as TabId;
	const oldMainTab = mainTabId();
	const panes = l.panes.map(p => {
		if (p.id === pane.id) return { ...p, content: 'main' as ColumnContent };
		if (p.id === main.id) return { ...p, content: (oldMainTab ?? 'home') as ColumnContent };
		return p;
	});
	commit(panes, l.widths);
	navigateMainTo(shownTab);
}

/** Remove the first pinned pane showing a tab (duplicates pinned → removes one). */
export function removePaneWithTab(tab: TabId) {
	const l = get(columnsLayout);
	const idx = l.panes.findIndex(p => p.content === tab);
	if (idx === -1 || l.panes.length <= 1) return;
	const panes = l.panes.filter((_, i) => i !== idx);
	const widths = l.widths.filter((_, i) => i !== idx);
	commit(panes, clampWidths(widths));
}

/** Rotate all columns one position left (the old "invert panes"). */
export function rotateColumns() {
	const l = get(columnsLayout);
	if (l.panes.length < 2) return;
	const panes = [...l.panes.slice(1), l.panes[0]];
	const widths = [...l.widths.slice(1), l.widths[0]];
	commit(panes, widths);
}

/** Back to a single column. */
export function resetColumns() {
	commit([makePane('main')], [100]);
}

/** Live width update; pass persist=false while dragging. */
export function setWidths(widths: number[], persistNow = true) {
	const l = get(columnsLayout);
	const w = clampWidths(widths);
	if (persistNow) commit(l.panes, w);
	else columnsLayout.set({ panes: l.panes, widths: w });
}

/** Double-click a gutter: back to equal shares. */
export function equalizeWidths() {
	const l = get(columnsLayout);
	commit(l.panes, equalized(l.panes.length));
}

export type ColumnsPreset = 'single' | 'feedMota' | 'triple';

/** Quick layout presets mirroring the classic reading setups. */
export function applyPreset(preset: ColumnsPreset) {
	if (preset === 'single') {
		resetColumns();
	} else if (preset === 'feedMota') {
		commit([makePane('main'), makePane('mota')], equalized(2));
	} else {
		commit([makePane('main'), makePane('events'), makePane('mota')], equalized(3));
	}
}

/** Grid template: `<share>fr` per pane with fixed gutters between them. */
export function gridTemplate(panes: Pane[], widths: number[]): string {
	const parts: string[] = [];
	panes.forEach((_, i) => {
		if (i > 0) parts.push(`${GUTTER_PX}px`);
		parts.push(`${Math.max(widths[i] ?? 0.01, 0.01)}fr`);
	});
	return parts.join(' ');
}

/** True while a nav icon is being HTML5-dragged (drives the drop zones). */
export const navTabDragging = writable(false);
