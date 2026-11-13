import { writable, get } from 'svelte/store';
import { browser } from '$app/environment';
import { apiFetch } from '$lib/api';

export type VersionInfo = {
	version: string;
	latestVersion: string | null;
	latestUrl: string | null;
	updateAvailable: boolean;
	loaded: boolean;
};

function createVersionStore() {
	const { subscribe, update } = writable<VersionInfo>({
		version: '',
		latestVersion: null,
		latestUrl: null,
		updateAvailable: false,
		loaded: false,
	});

	let fetched = false;

	async function load(force = false) {
		if (!browser) return;
		if (fetched && !force) return;
		fetched = true;
		try {
			const res = await apiFetch('/api/version', { credentials: 'include' });
			if (!res.ok) return;
			const data = await res.json();
			update(() => ({
				version: data.version ?? '',
				latestVersion: data.latest_version ?? null,
				latestUrl: data.latest_url ?? null,
				updateAvailable: !!data.update_available,
				loaded: true,
			}));
		} catch {
			// Fail-quiet: version display simply stays empty.
		}
	}

	return {
		subscribe,
		load,
		get(): VersionInfo {
			return get({ subscribe });
		},
	};
}

export const version = createVersionStore();
