const FEED_PREFIX = 'berga_feed_';
const SUBS_KEY = 'berga_subs_cache';
const MAX_AGE_MS = 24 * 60 * 60 * 1000;

interface CacheEntry<T> {
	ts: number;
	items: T;
}

function read<T>(key: string, maxAge = MAX_AGE_MS): T | null {
	try {
		const raw = localStorage.getItem(key);
		if (!raw) return null;
		const entry: CacheEntry<T> = JSON.parse(raw);
		if (Date.now() - entry.ts > maxAge) return null;
		return entry.items;
	} catch {
		return null;
	}
}

function readStale<T>(key: string): T | null {
	try {
		const raw = localStorage.getItem(key);
		if (!raw) return null;
		const entry: CacheEntry<T> = JSON.parse(raw);
		return entry.items;
	} catch {
		return null;
	}
}

function write<T>(key: string, items: T): void {
	try {
		const entry: CacheEntry<T> = { ts: Date.now(), items };
		localStorage.setItem(key, JSON.stringify(entry));
	} catch {
		// localStorage full or blocked — silently ignore
	}
}

function remove(key: string): void {
	try {
		localStorage.removeItem(key);
	} catch { /* ignore */ }
}

export function feedCacheKey(mode: string, folderId: string | null, feedSha: string | null, tagId: number | null = null): string {
	return `${FEED_PREFIX}${mode}_${folderId ?? 'all'}_${feedSha ?? 'all'}_${tagId ?? 'all'}`;
}

export function loadFeedCache<T>(key: string): T | null {
	const fresh = read<T>(key);
	if (fresh !== null) return fresh;
	return readStale<T>(key);
}

export function saveFeedCache<T>(key: string, items: T): void {
	write(key, items);
}

export function clearFeedCache(key?: string): void {
	if (key) {
		remove(key);
		return;
	}
	try {
		const keys: string[] = [];
		for (let i = 0; i < localStorage.length; i++) {
			const k = localStorage.key(i);
			if (k?.startsWith(FEED_PREFIX)) keys.push(k);
		}
		keys.forEach(k => localStorage.removeItem(k));
	} catch { /* ignore */ }
}

export function loadSubsCache<T>(): T | null {
	const fresh = read<T>(SUBS_KEY, MAX_AGE_MS);
	if (fresh !== null) return fresh;
	return readStale<T>(SUBS_KEY);
}

export function saveSubsCache<T>(items: T): void {
	write(SUBS_KEY, items);
}

export function clearSubsCache(): void {
	remove(SUBS_KEY);
}
