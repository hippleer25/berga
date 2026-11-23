import { writable } from 'svelte/store';
import { apiFetch } from '$lib/api';
import { loadSubsCache, saveSubsCache } from '$lib/stores/feedCache';

/* ── Home filter state ─────────────────────────────────────────────────────
   Shared between the in-tab filter bar (HomeTab) and the adaptive top bar,
   so filter selections survive tab switches and both hosts stay in sync. */

export type Mode = 'recommendations' | 'recents' | 'saved';

export interface HomeFilterState {
	mode: Mode;
	selectedFolderId: string | null;
	selectedFolderName: string | null;
	selectedFeedSha: string | null;
	selectedFeedName: string | null;
	selectedTagId: number | null;
	selectedTagName: string | null;
}

export const homeFilters = writable<HomeFilterState>({
	mode: 'recommendations',
	selectedFolderId: null,
	selectedFolderName: null,
	selectedFeedSha: null,
	selectedFeedName: null,
	selectedTagId: null,
	selectedTagName: null,
});

export function setHomeMode(mode: Mode) {
	homeFilters.update(f => (f.mode === mode ? f : { ...f, mode }));
}

export function selectHomeFolder(id: string | null, name: string | null) {
	homeFilters.update(f => ({
		...f,
		selectedFolderId: id,
		selectedFolderName: name,
		selectedFeedSha: null,
		selectedFeedName: null,
		selectedTagId: null,
		selectedTagName: null,
	}));
}

export function selectHomeFeed(sha: string | null, name: string | null) {
	homeFilters.update(f => ({
		...f,
		selectedFeedSha: sha,
		selectedFeedName: name,
		selectedFolderId: null,
		selectedFolderName: null,
		selectedTagId: null,
		selectedTagName: null,
	}));
}

export function selectHomeTag(id: number | null, name: string | null) {
	homeFilters.update(f => ({
		...f,
		selectedTagId: id,
		selectedTagName: name,
		selectedFolderId: null,
		selectedFolderName: null,
		selectedFeedSha: null,
		selectedFeedName: null,
	}));
}

/** URL deep-link (?tag_id=…): sets the tag without touching other filters. */
export function applyHomeTagFromUrl(id: number, name: string) {
	homeFilters.update(f => ({ ...f, selectedTagId: id, selectedTagName: name }));
}

/* ── Subscriptions + tags data (needed by the pickers in either host) ────── */

export interface HomeTag {
	id: number;
	name: string;
	color?: string;
}

export const homeSubs = writable<any[]>([]);
export const homeTags = writable<HomeTag[]>([]);

let subsLoaded = false;

export async function loadHomeSubs(force = false) {
	if (subsLoaded && !force) return;
	subsLoaded = true;

	const cached = loadSubsCache<any>();
	if (cached) {
		homeSubs.set(Array.isArray(cached) ? cached : (cached.feeds ?? []));
	}

	try {
		const res = await apiFetch('/api/list-subscriptions', { credentials: 'include' });
		if (res.ok) {
			const raw = await res.json();
			homeSubs.set(Array.isArray(raw) ? raw : (raw.feeds ?? []));
			saveSubsCache(raw);
		}
	} catch (_e) { /* silently ignore */ }

	try {
		const res = await apiFetch('/api/tags', { credentials: 'include' });
		if (res.ok) {
			const data = await res.json();
			homeTags.set(data.tags ?? []);
		}
	} catch { /* non-critical */ }
}
