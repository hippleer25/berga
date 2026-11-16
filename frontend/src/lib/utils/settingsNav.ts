// src/lib/utils/settingsNav.ts
// Shared navigation for the Settings stacked screen.
//
// Desktop: the sidebar replaces the settings hub, so the whole session is
// kept as a single history entry (replaceState) and "Back" is purely
// hierarchy-driven (second-level pages pop to their parent section with
// replaceState; first-level pages close the screen).
// Mobile: sections are drill-down pages pushed onto history; "Back" climbs
// the route hierarchy one level (/settings/appearance/dock ->
// /settings/appearance -> /settings) and only the root closes the screen.
import { goto } from '$app/navigation';
import { closeScreen } from '$lib/utils/screenStack';

export const SETTINGS_ROOT = '/settings';

export function isDesktopViewport(): boolean {
	return window.matchMedia('(min-width: 768px)').matches;
}

/**
 * Navigate between settings pages: replaceState on desktop (one history
 * entry for the whole session), drill-down push on mobile.
 */
export function openSettings(href: string): void {
	if (isDesktopViewport()) {
		goto(href, { replaceState: true });
	} else {
		goto(href);
	}
}

/**
 * Hierarchy-aware back for the settings screen: goes to the route
 * immediately above the current one inside settings. Only closes the
 * stacked screen (back to the tab layer) when there is no parent inside
 * settings — the root itself, or a first-level page on desktop (where the
 * sidebar replaces the hub).
 */
export async function settingsBack(pathname: string): Promise<void> {
	const segments = pathname.split('/').filter(Boolean);
	if (segments.length <= 1 || (isDesktopViewport() && segments.length <= 2)) {
		closeScreen();
		return;
	}
	openSettings('/' + segments.slice(0, -1).join('/'));
}
