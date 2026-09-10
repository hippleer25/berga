<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import Palette from '@lucide/svelte/icons/palette';
	import Database from '@lucide/svelte/icons/database';
	import Sparkles from '@lucide/svelte/icons/sparkles';
	import User from '@lucide/svelte/icons/user';
	import Tag from '@lucide/svelte/icons/tag';
	import Highlighter from '@lucide/svelte/icons/highlighter';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import { ripple } from '$lib/actions/ripple';
	import { t } from 'svelte-i18n';

	const sections = [
		{ key: 'appearance', href: '/settings/appearance', icon: Palette },
		{ key: 'highlights', href: '/settings/highlights', icon: Highlighter },
		{ key: 'tags', href: '/settings/tags', icon: Tag },
		{ key: 'affinity', href: '/settings/affinity', icon: Sparkles },
		{ key: 'subscriptions', href: '/settings/data', icon: Database },
		{ key: 'account', href: '/settings/account', icon: User },
	];

	function label(key: string): string {
		return key === 'tags'
			? $t('tags.title')
			: $t(`settings.${key === 'subscriptions' ? 'subscriptions' : key}`);
	}

	// Desktop has the sidebar in the layout — jump straight to Appearance.
	$effect(() => {
		if ($page.url.pathname !== '/settings') return;
		if (window.matchMedia('(min-width: 768px)').matches) {
			goto('/settings/appearance', { replaceState: true });
		}
	});

	function open(href: string) {
		goto(href);
	}
</script>

<div class="settings-home">
	<div class="settings-group">
		{#each sections as s, i (s.key)}
			<button class="row" use:ripple onclick={() => open(s.href)}>
				<span class="row-icon"><s.icon size={19} strokeWidth={1.9} /></span>
				<span class="row-label">{label(s.key)}</span>
				<span class="row-chevron"><ChevronRight size={17} strokeWidth={1.8} /></span>
			</button>
			{#if i < sections.length - 1}
				<div class="row-divider"></div>
			{/if}
		{/each}
	</div>
</div>

<style>
	.settings-home {
		max-width: 42rem;
		margin: 0 auto;
		padding-top: 6px;
	}

	.settings-group {
		background: color-mix(in oklch, var(--color-base-100) 60%, transparent);
		border: 1px solid var(--color-base-300);
		border-radius: var(--ui-radius-lg);
		overflow: hidden;
	}

	.row {
		display: flex;
		align-items: center;
		gap: 14px;
		width: 100%;
		padding: 13px 14px;
		background: transparent;
		border: none;
		cursor: pointer;
		text-align: left;
		font-family: inherit;
		position: relative;
		overflow: hidden;
		color: var(--color-base-content);
		transition: background 130ms ease;
	}
	.row:hover { background: var(--color-base-200); }
	.row:active { background: color-mix(in oklch, var(--color-base-content) 7%, transparent); }

	.row-icon {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 34px;
		height: 34px;
		flex-shrink: 0;
		border-radius: var(--ui-radius-sm);
		background: color-mix(in oklch, var(--color-accent) 14%, transparent);
		color: var(--color-accent);
	}

	.row-label {
		flex: 1;
		font-size: 15px;
		font-weight: 600;
	}

	.row-chevron {
		display: flex;
		color: color-mix(in oklch, var(--color-base-content) 38%, transparent);
	}

	.row-divider {
		height: 1px;
		margin-left: 62px;
		background: var(--color-base-300);
	}
</style>
