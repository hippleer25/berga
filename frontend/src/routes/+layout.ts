export const ssr = false;

import '$lib/i18n';
import { browser } from '$app/environment';
import { redirect } from '@sveltejs/kit';
import { goto } from '$app/navigation';
import { waitLocale } from 'svelte-i18n';
import { checkSession, peekAuthHint, sessionDefinitelyLoggedOut } from '$lib/stores/session';

const AUTH_PATHS = ['/', '/login', '/signup'];

if (browser) {
	// Boot the session check at module eval so the auth round-trip overlaps
	// with i18n loading and hydration instead of gating the splash.
	checkSession().then(ok => {
		// Optimistic boot proved wrong (server rejected the token): bounce
		// to /login — but only when the server answered (not offline) and
		// the user is not already on an auth screen.
		if (!ok && sessionDefinitelyLoggedOut() && !AUTH_PATHS.includes(window.location.pathname)) {
			goto(`/login?returnTo=${encodeURIComponent(window.location.pathname + window.location.search)}`, { replaceState: true });
		}
	}).catch(() => {});

	// Warm the home tab chunk while i18n + the session check are in flight,
	// so the cached feed can paint the instant /home mounts.
	if (peekAuthHint()) import('$lib/tabs/HomeTab.svelte').catch(() => {});
}

export async function load({ url }) {
	// Returning user: skip the landing stop-over entirely and go straight
	// to the tabs (HomeTab paints instantly from the localStorage caches).
	// The background check started above bounces to /login if the token
	// turns out to be dead.
	if (browser && url.pathname === '/' && peekAuthHint()) {
		redirect(302, '/home');
	}
	await Promise.race([
		waitLocale(),
		new Promise(resolve => setTimeout(resolve, 1500)),
	]);
}
