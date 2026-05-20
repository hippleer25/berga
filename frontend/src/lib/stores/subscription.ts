import { writable } from 'svelte/store';

export const subscriptionChanged = writable<number>(0);

export function notifySubscriptionChanged() {
	subscriptionChanged.update((n) => n + 1);
}
