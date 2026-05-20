import { writable } from 'svelte/store';

export const swipeOffset   = writable(0);
export const swipeDragging = writable(false);
export const activeTabIdx  = writable(0);

/**
 * Controls NavBar visibility on mobile.
 * False when scrolling down in HomeTab, restored on scroll-up or tab switch.
 */
export const navVisible = writable(true);

// ── Multi-select feature ──────────────────────────────────────────────────────

/** Whether the user is in post-selection mode (long press activated). */
export const selectionMode = writable(false);

/** Array of fully selected post items (complete objects for sending to Mota). */
export const selectedPosts = writable<any[]>([]);

/** Posts queued to be auto-sent to the Mota tab chat. */
export const pendingMotaPosts = writable<any[]>([]);