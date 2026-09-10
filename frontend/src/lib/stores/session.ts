// src/lib/stores/session.ts
// Auth session state. JWT lives in httponly cookies (or native storage) —
// this only tracks whether the user is logged in for routing/UI decisions.
import { writable, type Writable } from 'svelte/store';
import { browser } from '$app/environment';
import { apiFetch } from '$lib/api';

const CHECK_TTL = 5 * 60 * 1000;
let lastCheck = 0;
let inFlight: Promise<boolean> | null = null;

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
			sessionLoggedIn.set(ok);
			sessionChecked.set(true);
			return ok;
		} catch {
			sessionLoggedIn.set(false);
			sessionChecked.set(true);
			return false;
		} finally {
			inFlight = null;
		}
	})();
	return inFlight;
}

export function setSessionLoggedIn() {
	lastCheck = Date.now();
	sessionChecked.set(true);
	sessionLoggedIn.set(true);
}

export function setSessionLoggedOut() {
	lastCheck = Date.now();
	sessionChecked.set(true);
	sessionLoggedIn.set(false);
}
