import { apiFetch } from '$lib/api';
import { get } from 'svelte/store';
import { instance } from '$lib/stores/instance';

const BATCH_SIZE = 10;
const FLUSH_INTERVAL_MS = 5_000;
const MAX_SENT_VIEWS = 2000;

const pendingViews = new Set<string>();
const sentViews = new Set<string>();
let flushTimer: ReturnType<typeof setInterval> | null = null;
let started = false;

function buildViewURL(): string {
	const inst = get(instance);
	if (!inst) return '/api/articles/views';
	const instanceOrigin = `https://${inst}`;
	if (typeof window !== 'undefined' && window.location.origin === instanceOrigin) return '/api/articles/views';
	return `${instanceOrigin}/api/articles/views`;
}

function startTimer() {
	if (started) return;
	started = true;
	flushTimer = setInterval(() => {
		if (pendingViews.size > 0) flush();
	}, FLUSH_INTERVAL_MS);
}

function stopTimer() {
	if (flushTimer) {
		clearInterval(flushTimer);
		flushTimer = null;
	}
	started = false;
}

function trimSentViews() {
	if (sentViews.size > MAX_SENT_VIEWS) {
		const iter = sentViews.values();
		const excess = sentViews.size - MAX_SENT_VIEWS;
		for (let i = 0; i < excess; i++) {
			const val = iter.next().value;
			if (val !== undefined) sentViews.delete(val);
		}
	}
}

function flush(): Promise<void> {
	if (pendingViews.size === 0) return Promise.resolve();

	const ids = [...pendingViews];
	pendingViews.clear();
	for (const id of ids) sentViews.add(id);
	trimSentViews();

	return apiFetch('/api/articles/views', {
		method: 'POST',
		credentials: 'include',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ item_ids: ids }),
	}).then(() => {}).catch(() => {});
}

function flushOnUnload() {
	if (pendingViews.size === 0) return;

	const ids = [...pendingViews];
	pendingViews.clear();
	for (const id of ids) sentViews.add(id);
	trimSentViews();

	const url = buildViewURL();
	fetch(url, {
		method: 'POST',
		credentials: 'include',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ item_ids: ids }),
		keepalive: true,
		mode: url.startsWith('http') ? 'cors' : undefined,
	} as RequestInit).catch(() => {});
}

export function onViewed(item_id: string) {
	if (sentViews.has(item_id) || pendingViews.has(item_id)) return;

	pendingViews.add(item_id);
	startTimer();

	if (pendingViews.size >= BATCH_SIZE) {
		flush();
	}
}

export function flushPending(): Promise<void> {
	return flush();
}

export function destroyViewTracker() {
	flush();
	stopTimer();
	pendingViews.clear();
	sentViews.clear();
}

export function markAsSent(item_id: string) {
	sentViews.add(item_id);
}

if (typeof document !== 'undefined') {
	document.addEventListener('visibilitychange', () => {
		if (document.visibilityState === 'hidden') {
			flushOnUnload();
		}
	});

	window.addEventListener('pagehide', () => {
		flushOnUnload();
	});
}
