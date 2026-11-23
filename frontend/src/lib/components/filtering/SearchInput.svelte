<script lang="ts">
	import { goto } from '$app/navigation';
	import { Search } from '@lucide/svelte';
	import { t } from 'svelte-i18n';

	interface Props {
		/** Slim variant for the top bar host (shorter field, smaller type). */
		compact?: boolean;
	}

	let { compact = false }: Props = $props();

	let query = $state('');

	function handleSearch(e: Event) {
		e.preventDefault();
		const q = query.trim();
		if (q) goto(`/s/${encodeURIComponent(q)}`);
	}
</script>

<form class="search-form" class:compact onsubmit={handleSearch}>
	<div class="search-wrap">
		<input
			class="search-input"
			type="search"
			placeholder="{$t('searchtab.placeholder', { default: 'Search posts, feeds, or topics...' })}"
			bind:value={query}
			autocomplete="off"
			autocorrect="off"
			spellcheck="false"
		/>
		<Search size={18} class="search-icon" />
	</div>
</form>

<style>
	.search-form { width: 100%; }
	.search-wrap {
		display: flex;
		align-items: center;
		gap: 12px; /* Safe space between text and icon */
		background: color-mix(in oklch, var(--color-base-200) 50%, transparent);
		border: var(--ui-border-width, 1px) solid var(--btn-border-color, var(--ui-border-color));
		border-radius: var(--ui-radius-sm);
		padding: 0 16px;
		height: 46px;
		user-select: none;
		-webkit-tap-highlight-color: transparent;
		transition: background 180ms ease, border-color 180ms ease, box-shadow 180ms ease;
	}
	.search-form.compact .search-wrap {
		height: 34px;
		gap: 9px;
		padding: 0 12px;
	}
	.search-wrap:focus-within {
		background: var(--color-base-100);
		border-color: var(--color-accent);
		box-shadow: 0 0 0 3px color-mix(in oklch, var(--color-accent) 15%, transparent);
	}

	.search-input {
		flex: 1;
		min-width: 0; /* Prevents input from pushing the icon out of the bar */
		background: transparent; border: none; outline: none;
		font-size: 14px; color: var(--color-base-content); line-height: 1;
		caret-color: var(--color-accent);
		user-select: text;
		-webkit-appearance: none; appearance: none;
		-webkit-search-decoration: none;
	}
	.search-form.compact .search-input {
		font-size: 13px;
	}
	.search-input::placeholder { color: var(--ui-text-subtle, color-mix(in oklch, var(--color-base-content) 62%, transparent)); }
	.search-input::-webkit-search-cancel-button { display: none; }
	.search-input::-webkit-search-decoration { display: none; }
	.search-input::selection { background: transparent; }
	.search-input:focus,
	.search-input:focus-visible {
		outline: none !important;
		box-shadow: none !important;
	}

	.search-wrap :global(.search-icon) {
		flex-shrink: 0; /* Prevents the magnifying glass from shrinking or being hidden */
		color: var(--color-accent);
		transition: color 180ms ease;
	}
</style>
