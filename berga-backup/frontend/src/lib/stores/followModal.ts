import { writable } from 'svelte/store';

export interface FollowFeedData {
    title: string;
    url: string;
}

export const followModalStore = writable<FollowFeedData | null>(null);

export function openFollowModal(title: string, url: string) {
    followModalStore.set({ title, url });
}

export function closeFollowModal() {
    followModalStore.set(null);
}