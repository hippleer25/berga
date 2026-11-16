// src/lib/stores/session.ts
// Auth session state. JWT lives in httponly cookies (or native storage) —
// this only tracks whether the user is logged in for routing/UI decisions.
import { writable, type Writable } from 'svelte/store';
import { browser } from '$app/environment';
import { apiFetch } from '$lib/api';

const CHECK_TTL = 5 * 60 * 1000;
	let lastCheck = 0;
	let inFlight: Promise<boolean> | null = null;
	// True only when the backend answered and rejected the session (HTTP
	// 401/etc). Distinguishes "server said no" (bounce to /login) from
	// "we could not reach the server" (stay on cached content).
	let httpRejected = false;

// Persisted auth hint for optimistic boot: a returning user skips the
// splash and lands straight on the tabs while the real check runs in the
// background. Cleared on logout and on failed checks.
const AUTH_HINT_KEY = 'berga_auth';

function writeHint(ok: boolean): void {
	try {
		if (ok) localStorage.setItem(AUTH_HINT_KEY, '1');
		else localStorage.removeItem(AUTH_HINT_KEY);
	} catch { /* localStorage blocked — optimistic boot unavailable */ }
}

/** Synchronous last-known auth state from localStorage. */
export function peekAuthHint(): boolean {
	try {
		return localStorage.getItem(AUTH_HINT_KEY) === '1';
	} catch {
		return false;
	}
}

/** True only when the server explicitly rejected the last check (HTTP 4xx). */
export function sessionDefinitelyLoggedOut(): boolean {
	return httpRejected;
}

/** True once the first /api/meu-perfil check has completed. */
export const sessionChecked: Writable<boolean> = writable(false);
/** Whether the current session is authenticated. */
export const sessionLoggedIn: Writable<boolean> = writable(false);

/**
 * Verify the session against the backend. Cached for CHECK_TTL and
 * de-duplicated while a request is in flight.
 */
export async function checkSession(force = false): Promise<boolean> {
	if (!browser) return false;
	const now = Date.now();
	if (!force && lastCheck && now - lastCheck < CHECK_TTL) {
		let v = false;
		sessionLoggedIn.subscribe(x => (v = x))();
		return v;
	}
	if (inFlight) return inFlight;

	lastCheck = now;
	inFlight = (async () => {
		try {
			const res = await apiFetch('/api/meu-perfil', { credentials: 'include' });
			const ok = res.ok;
			httpRejected = !ok;
			writeHint(ok);
			sessionLoggedIn.set(ok);
			sessionChecked.set(true);
			return ok;
		} catch {
			// Network failure (no HTTP response): not proof of logout. Keep the
			// persisted hint and leave the stores untouched so the optimistic
			// tab layer stays visible (cached feed while offline).
			return false;
		} finally {
			inFlight = null;
		}
	})();
	return inFlight;
}

export function setSessionLoggedIn() {
	lastCheck = Date.now();
	httpRejected = false;
	writeHint(true);
	sessionChecked.set(true);
	sessionLoggedIn.set(true);
}

export function setSessionLoggedOut() {
	lastCheck = Date.now();
	httpRejected = false;
	writeHint(false);
	sessionChecked.set(true);
	sessionLoggedIn.set(false);
}
