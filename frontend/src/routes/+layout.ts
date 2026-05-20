export const ssr = false;

import '$lib/i18n';
import { waitLocale } from 'svelte-i18n';

export async function load() {
  await waitLocale();
}
