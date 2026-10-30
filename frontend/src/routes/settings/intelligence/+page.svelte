<script lang="ts">
	import { goto } from '$app/navigation';
	import SlidersHorizontal from '@lucide/svelte/icons/sliders-horizontal';
	import Tag from '@lucide/svelte/icons/tag';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import { ripple } from '$lib/actions/ripple';
	import { t } from 'svelte-i18n';

	const entries = [
		{ href: '/settings/intelligence/affinity', icon: SlidersHorizontal, titleKey: 'settings.affinityTitle', descKey: 'settings.affinityDesc' },
		{ href: '/settings/intelligence/tags', icon: Tag, titleKey: 'settings.tagsTitle', descKey: 'settings.tagsDesc' },
	];

	function open(href: string) {
		goto(href);
	}
</script>

<div class="tab-panel">
	<h2 class="section-title">{$t('settings.intelligence')}</h2>

	<div class="settings-group">
		{#each entries as e}
			<button class="row" use:ripple onclick={() => open(e.href)}>
				<span class="row-icon"><e.icon size={19} strokeWidth={1.9} /></span>
				<span class="row-copy">
					<span class="row-label">{$t(e.titleKey)}</span>
					<span class="row-desc">{$t(e.descKey)}</span>
				</span>
				<span class="row-chevron"><ChevronRight size={17} strokeWidth={1.8} /></span>
			</button>
		{/each}
	</div>
</div>

<style>
	.tab-panel { display: flex; flex-direction: column; gap: 16px; padding-top: 12px; }
	.section-title { font-size: 16px; font-weight: 700; color: var(--color-base-content); margin: 0; }

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
	.row-copy { flex: 1; display: flex; flex-direction: column; gap: 2px; min-width: 0; }
	.row-label { font-size: 15px; font-weight: 600; }
	.row-desc { font-size: 12.5px; color: color-mix(in oklch, var(--color-base-content) 55%, transparent); line-height: 1.4; overflow-wrap: anywhere; }
	.row-chevron { display: flex; color: color-mix(in oklch, var(--color-base-content) 38%, transparent); }
</style>
