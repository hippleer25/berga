// src/lib/utils/screenStack.ts
// Coordinates "stacked screens" (settings, article, feed, folder, search)
// that slide over the live tab layer, Spotify-style.
import { goto } from '$app/navigation';
import { stackedScreenOpen } from '$lib/stores/swipe';

type Shell = {
	el: HTMLElement;
	fallbackHref: string;
};

let activeShell: Shell | null = null;
let closing = false;
let openCount = 0;

/**
 * history.length captured when the FIRST screen of the current stack
 * mounted. Every screen of the stack closes back to the entry beneath
 * that first screen — the active tab, whose live layer is exactly what
 * the swipe-reveal shows. Null when no stack is open.
 */
let stackBaseLen: number | null = null;

/**
 * Href of the tab beneath the first screen of the current stack, captured
 * together with stackBaseLen. Authoritative landing target when unwinding —
 * unlike history positions it cannot be desynced by system-back pops or
 * WebView restore.
 */
let stackBaseHref: string | null = null;

/**
 * Set by closeScreen() right before unwinding history; consumed (and
 * cleared) by the root layout's afterNavigate. If the pop lands on anything
 * other than the base tab, the layout forces a goto to the base href.
 * Deliberately NOT cleared by resetScreenStack() — it must survive the
 * reset closeScreen performs while the pop is still in flight.
 */
let pendingReconcile: string | null = null;

/**
 * Called by the root layout after navigating to a non-stacked route (tab or
 * auth). Authoritative reconciliation: no shell can be alive on those routes,
 * so the module state is fully reset and the store is forced closed. This
 * self-heals any race that leaves `stackedScreenOpen` stuck true after the
 * shell is gone (which would keep the tab layer at pointer-events: none).
 */
export function resetScreenStack(): void {
	stackBaseLen = null;
	stackBaseHref = null;
	openCount = 0;
	activeShell = null;
	closing = false;
	stackedScreenOpen.set(false);
}

/**
 * Returns (and clears) the href a pending screen-stack unwind is expected
 * to land on, or null when no unwind is in flight. Called by the root
 * layout's afterNavigate to reconcile a missed landing.
 */
export function consumePendingReconcile(): string | null {
	const href = pendingReconcile;
	pendingReconcile = null;
	return href;
}

export function isScreenClosing(): boolean {
	return closing;
}

/** Called by ScreenShell on mount. */
export function shellOpened(el: HTMLElement, fallbackHref: string): void {
	activeShell = { el, fallbackHref };
	if (stackBaseLen === null) {
		stackBaseLen = history.length;
		stackBaseHref = fallbackHref;
	}
	openCount++;
	stackedScreenOpen.set(true);
}

/** Called by ScreenShell on destroy. */
export function shellClosed(): void {
	openCount = Math.max(0, openCount - 1);
	if (openCount === 0) {
		stackedScreenOpen.set(false);
		if (activeShell && !closing) activeShell = null;
	}
}

/**
 * Close the active stacked screen: animate it away, then unwind every
 * history entry the whole screen stack added, landing on the active tab.
 */
export async function closeScreen(opts: { animated?: boolean } = {}): Promise<void> {
	const shell = activeShell;
	if (!shell || closing) return;
	closing = true;
	stackedScreenOpen.set(false);

	if (opts.animated !== false && shell.el) {
		shell.el.style.transition =
			'transform 260ms cubic-bezier(0.32, 0, 0.67, 0), opacity 260ms ease';
		shell.el.style.transform = 'translate3d(100%, 0, 0)';
		shell.el.style.opacity = '0.3';
		await new Promise(r => setTimeout(r, 270));
	}

	// Steps back to the entry beneath the first screen of the stack.
	if (stackBaseLen !== null && stackBaseLen - 2 >= 0) {
		const steps = history.length - 1 - (stackBaseLen - 2);
		if (steps >= 1) {
			// The pop must land on the base tab. Stale history (system-back
			// pops keep forward entries; WebView restore can reshape the
			// session) can overshoot into old entries — arm the reconcile
			// so the root layout corrects a missed landing.
			pendingReconcile = stackBaseHref ?? shell.fallbackHref;
			history.go(-steps);
		} else {
			pendingReconcile = null;
			await goto(shell.fallbackHref, { replaceState: true });
		}
	} else {
		// Deep link with nothing behind: replace with the tab directly.
		pendingReconcile = null;
		await goto(shell.fallbackHref, { replaceState: true });
	}
	resetScreenStack();
	// Safety reset in case the shell is not unmounted synchronously.
	setTimeout(() => {
		closing = false;
	}, 350);
}
