import { writable, type Writable } from 'svelte/store';
import { browser } from '$app/environment';
import { Rss, House, Search, Sparkles } from '@lucide/svelte';
import type { Component } from 'svelte';

export type TabId = 'followers' | 'home' | 'events' | 'mota';

export type TabDef = {
	id: TabId;
	href: string;
	icon: typeof Rss;
};

export const TAB_DEFS: Record<TabId, TabDef> = {
	followers: { id: 'followers', href: '/followers', icon: Rss },
	home: { id: 'home', href: '/home', icon: House },
	events: { id: 'events', href: '/events', icon: Search },
	mota: { id: 'mota', href: '/mota', icon: Sparkles },
};

export const DEFAULT_TAB_ORDER: TabId[] = ['followers', 'home', 'events', 'mota'];

const ORDER_KEY = 'ui-tab-order';

function normalizeOrder(saved: unknown): TabId[] {
	const known = Object.keys(TAB_DEFS) as TabId[];
	if (!Array.isArray(saved)) return [...DEFAULT_TAB_ORDER];
	const valid = saved.filter((id): id is TabId => typeof id === 'string' && known.includes(id as TabId));
	const missing = known.filter(id => !valid.includes(id));
	return [...valid, ...missing];
}

function loadOrder(): TabId[] {
	if (!browser) return [...DEFAULT_TAB_ORDER];
	try {
		return normalizeOrder(JSON.parse(localStorage.getItem(ORDER_KEY) ?? 'null'));
	} catch {
		return [...DEFAULT_TAB_ORDER];
	}
}

export const tabOrder: Writable<TabId[]> = writable(loadOrder());

export const orderedTabs: Writable<TabDef[]> = writable(
	loadOrder().map(id => TAB_DEFS[id])
);

export function setTabOrder(order: TabId[]) {
	const clean = normalizeOrder(order);
	if (browser) localStorage.setItem(ORDER_KEY, JSON.stringify(clean));
	tabOrder.set(clean);
	orderedTabs.set(clean.map(id => TAB_DEFS[id]));
}

export function getTabHref(id: TabId): string {
	return TAB_DEFS[id].href;
}

/** href of the tab at the given position index (clamped). */
export function hrefAtIdx(idx: number): string {
	let val = DEFAULT_TAB_ORDER;
	orderedTabs.subscribe(tabs => {
		val = tabs.map(t => t.id);
	})();
	const id = val[Math.min(Math.max(idx, 0), val.length - 1)];
	return TAB_DEFS[id].href;
}

/** Tab loaders keyed by id — used by PageTrack. */
export const TAB_LOADERS: Record<TabId, () => Promise<{ default: Component }>> = {
	followers: () => import('$lib/tabs/FollowersTab.svelte'),
	home: () => import('$lib/tabs/HomeTab.svelte'),
	events: () => import('$lib/tabs/EventsTab.svelte'),
	mota: () => import('$lib/tabs/MotaTab.svelte'),
};
