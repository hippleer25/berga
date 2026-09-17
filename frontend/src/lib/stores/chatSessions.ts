import { writable } from 'svelte/store';

export type ChatSession = {
  id: number;
  title: string | null;
  fallback_title: string | null;
  message_count: number;
  created_at: string | null;
  updated_at: string | null;
};

export const chatSessions = writable<ChatSession[]>([]);
export const currentSessionId = writable<number | null>(null);
export const sessionsOpen = writable(false);
