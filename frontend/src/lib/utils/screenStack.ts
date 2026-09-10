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

/** Called by the root layout after navigating to a non-stacked route. */
export function resetScreenStack(): void {
	stackBaseLen = null;
}

export function isScreenClosing(): boolean {
	return closing;
}

/** Called by ScreenShell on mount. */
export function shellOpened(el: HTMLElement, fallbackHref: string): void {
	activeShell = { el, fallbackHref };
	if (stackBaseLen === null) stackBaseLen = history.length;
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
			history.go(-steps);
		} else {
			await goto(shell.fallbackHref, { replaceState: true });
		}
	} else {
		// Deep link with nothing behind: replace with the tab directly.
		await goto(shell.fallbackHref, { replaceState: true });
	}
	resetScreenStack();
	// Safety reset in case the shell is not unmounted synchronously.
	setTimeout(() => {
		closing = false;
	}, 350);
}
