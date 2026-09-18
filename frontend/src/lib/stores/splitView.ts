import { writable, get } from 'svelte/store';
import { browser } from '$app/environment';
import { orderedTabs, type TabId } from '$lib/config/tabs';
import { activeTabIdx } from '$lib/stores/swipe';

/**
 * Multi-tab split viewer (desktop only): the screen shows the main
 * (URL-active) tab on one half and one pinned tab on the other half.
 * Accepts exactly one pinned tab; the "side" is where the pinned pane sits.
 */
export type SplitSide = 'left' | 'right';

const KEY = 'ui-split-view';

function loadSaved(): { tab: TabId | null; side: SplitSide } {
	const fallback = { tab: null as TabId | null, side: 'right' as SplitSide };
	if (!browser) return fallback;
	try {
		const raw = JSON.parse(localStorage.getItem(KEY) ?? 'null');
		if (!raw || typeof raw !== 'object') return fallback;
		const tab =
			typeof raw.tab === 'string' && getTabIds().includes(raw.tab as TabId)
				? (raw.tab as TabId)
				: null;
		const side = raw.side === 'left' ? 'left' : 'right';
		return { tab, side };
	} catch {
		return fallback;
	}
}

function getTabIds(): TabId[] {
	return Object.keys(TAB_ID_SET) as TabId[];
}
/** Placeholder kept in sync with TAB_DEFS without importing svelte components. */
const TAB_ID_SET: Record<TabId, true> = {
	followers: true,
	home: true,
	events: true,
	mota: true
};

const saved = loadSaved();

export const splitTab = writable<TabId | null>(saved.tab);
export const splitSide = writable<SplitSide>(saved.side);

function persist() {
	if (!browser) return;
	try {
		localStorage.setItem(
			KEY,
			JSON.stringify({ tab: get(splitTab), side: get(splitSide) })
		);
	} catch {
		/* storage unavailable — split stays session-only */
	}
}

export function opposite(side: SplitSide): SplitSide {
	return side === 'left' ? 'right' : 'left';
}

/** Id of the main (URL-active) tab, or null when it can't be resolved. */
export function mainTabId(): TabId | null {
	const tabs = get(orderedTabs);
	const idx = get(activeTabIdx);
	return tabs[idx]?.id ?? null;
}

/** Pin a tab on a half. No-op when the tab equals the main pane's tab. */
export function openSplit(tab: TabId, side: SplitSide) {
	if (tab === mainTabId()) return;
	splitTab.set(tab);
	splitSide.set(side);
	persist();
}

export function closeSplit() {
	splitTab.set(null);
	persist();
}

/** Move the pinned pane to the other half (no remount, CSS only). */
export function moveSplit(side: SplitSide) {
	if (get(splitTab) === null) return;
	if (get(splitSide) === side) return;
	splitSide.set(side);
	persist();
}

/** Unpin a specific tab; only closes when the id matches what's pinned. */
export function removeSplit(tab: TabId) {
	if (get(splitTab) !== tab) return;
	closeSplit();
}

/**
 * Pin any tab to a half, honouring the interaction rules:
 *  - no pinned tab yet: pin it (dropping/picking the main tab is a no-op)
 *  - tab is the main tab: "swap sides" — main takes the requested half,
 *    the pinned tab moves to the opposite half
 *  - any other tab: replaces whatever is pinned on the requested side
 */
export function pinToSide(tab: TabId, side: SplitSide) {
	const main = mainTabId();
	if (!main) return;
	if (main === tab) {
		if (get(splitTab) === null) return;
		moveSplit(opposite(side));
		return;
	}
	openSplit(tab, side);
}

/**
 * Swap panes (left-click on a pinned tab's icon): the previously main tab
 * becomes pinned on the same half. Returns false when there is nothing to
 * swap; the caller un-wraps the swap by navigating to the pinned tab's href.
 */
export function swapWithMain(): boolean {
	const main = mainTabId();
	const cur = get(splitTab);
	if (!main || !cur || main === cur) return false;
	openSplit(main, get(splitSide));
	return true;
}

/** True while a nav icon is being HTML5-dragged (drives the drop zones). */
export const navTabDragging = writable(false);

export { getTabIds };
