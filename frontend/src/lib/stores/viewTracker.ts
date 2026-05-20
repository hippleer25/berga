import { apiFetch } from '$lib/api';

const BATCH_SIZE = 10;
const FLUSH_INTERVAL_MS = 10_000;

const pendingViews = new Set<string>();
const sentViews = new Set<string>();
let flushTimer: ReturnType<typeof setInterval> | null = null;
let started = false;

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

function flush() {
    if (pendingViews.size === 0) return;

    const ids = [...pendingViews];
    pendingViews.clear();

    apiFetch('/api/articles/views', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ item_ids: ids }),
    }).catch(() => {});
}

export function onViewed(item_id: string) {
    if (sentViews.has(item_id) || pendingViews.has(item_id)) return;

    pendingViews.add(item_id);
    startTimer();

    if (pendingViews.size >= BATCH_SIZE) {
        flush();
    }
}

export function flushPending() {
    flush();
}

export function destroyViewTracker() {
    flush();
    stopTimer();
    pendingViews.clear();
}

export function markAsSent(item_id: string) {
    sentViews.add(item_id);
}
