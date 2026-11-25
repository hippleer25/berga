import { writable } from 'svelte/store';

/**
 * Server-side chat session list (shared across all Mota instances/columns).
 * Per-instance chat state (current session id, overlay visibility) lives
 * inside each MotaTab instance — Mota is hostable in several columns.
 */

export type ChatSession = {
  id: number;
  title: string | null;
  fallback_title: string | null;
  message_count: number;
  created_at: string | null;
  updated_at: string | null;
};

export const chatSessions = writable<ChatSession[]>([]);
