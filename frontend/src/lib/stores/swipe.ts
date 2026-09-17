import { writable } from 'svelte/store';

export const swipeOffset   = writable(0);
export const swipeDragging = writable(false);
export const activeTabIdx  = writable(0);

/**
 * Controls NavBar visibility on mobile.
 * False when scrolling down in HomeTab, restored on scroll-up or tab switch.
 * Also forced false on the Mota tab (mobile) so the chat gets the full screen.
 */
export const navVisible = writable(true);

/**
 * Px offset applied on top of the NavBar's resting transform while the user
 * drags it (down on the bar to hide, up on the bottom reveal zone to show).
 * Positive = pulled further down; negative = pulled up from the hidden state.
 */
export const navDragOffset = writable(0);

/** True while a nav drag gesture is in progress (disables the CSS transition). */
export const navDragging = writable(false);

/**
 * True while a stacked screen (settings, article, feed, folder, search)
 * covers the tab layer. NavBar is hidden; ScreenShell flips it to false
 * when the screen starts closing so the nav reappears during the reveal.
 */
export const stackedScreenOpen = writable(false);

// ── Multi-select feature ──────────────────────────────────────────────────────

/** Whether the user is in post-selection mode (long press activated). */
export const selectionMode = writable(false);

/** Array of fully selected post items (complete objects for sending to Mota). */
export const selectedPosts = writable<any[]>([]);

/** Posts queued to be auto-sent to the Mota tab chat. */
export const pendingMotaPosts = writable<any[]>([]);