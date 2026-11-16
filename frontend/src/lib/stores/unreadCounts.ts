import { writable } from 'svelte/store';
import { apiFetch } from '$lib/api';

/**
 * Unread article counts per subscribed feed, served by /api/unread-counts.
 * Backed by a short-TTL server cache; refetched when the Followers tab or
 * the LeftPanel opens, after subscription changes and after the unread
 * settings are saved.
 */
export const unreadCounts = writable<Record<string, number>>({});
export const unreadTotal = writable<number>(0);

let lastFetch = 0;
let inflight: Promise<void> | null = null;
const MIN_REFETCH_MS = 4000;

export function loadUnreadCounts(force = false): Promise<void> {
	const now = Date.now();
	if (!force && inflight) return inflight;
	if (!force && now - lastFetch < MIN_REFETCH_MS) return Promise.resolve();

	inflight = (async () => {
		try {
			const res = await apiFetch('/api/unread-counts', {
				credentials: 'include',
				cache: 'no-cache',
			});
			if (!res.ok) throw new Error(String(res.status));
			const data = await res.json().catch(() => ({}));
			unreadCounts.set(data?.counts ?? {});
			unreadTotal.set(data?.total ?? 0);
			lastFetch = Date.now();
		} catch {
			// Badges stay hidden until the next successful fetch.
		} finally {
			inflight = null;
		}
	})();
	return inflight;
}

export function unreadFor(counts: Record<string, number>, sha: string | null): number {
	if (!sha) return 0;
	return counts[sha] ?? 0;
}

export function sumUnread(counts: Record<string, number>, shas: (string | null)[]): number {
	let total = 0;
	for (const sha of shas) if (sha) total += counts[sha] ?? 0;
	return total;
}
