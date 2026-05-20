// src/lib/stores/auth.ts
// NOTE: JWT tokens are stored in httponly cookies set by the backend.
// This store only tracks auth state for the UI — it does NOT store the token.
import { writable } from 'svelte/store';

function createAuthStore() {
    const { subscribe, set } = writable<boolean>(false);

    return {
        subscribe,
        setLoggedIn: () => set(true),
        setLoggedOut: () => set(false),
    };
}

export const auth = createAuthStore();