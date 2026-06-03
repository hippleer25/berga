// src/lib/stores/auth.ts
import { writable } from 'svelte/store';

function createAuthStore() {
    const token = typeof localStorage !== 'undefined' ? localStorage.getItem('token') : null;
    const { subscribe, set } = writable<string | null>(token);

    return {
        subscribe,
        setToken: (token: string | null) => {
            if (typeof localStorage !== 'undefined') {
                if (token) localStorage.setItem('token', token);
                else localStorage.removeItem('token');
            }
            set(token);
        }
    };
}

export const auth = createAuthStore();