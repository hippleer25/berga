<script lang="ts">
	import { page } from '$app/stores';
	import PanelBottom from '@lucide/svelte/icons/panel-bottom';
	import House from '@lucide/svelte/icons/house';
	import FileText from '@lucide/svelte/icons/file-text';
	import BookOpen from '@lucide/svelte/icons/book-open';
	import Search from '@lucide/svelte/icons/search';
	import Settings2 from '@lucide/svelte/icons/settings-2';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import { goto } from '$app/navigation';
	import { ripple } from '$lib/actions/ripple';
	import { t } from 'svelte-i18n';

	const sections = [
		{ href: '/settings/appearance/dock', icon: PanelBottom, labelKey: 'subsecDock' },
		{ href: '/settings/appearance/home', icon: House, labelKey: 'subsecHome' },
		{ href: '/settings/appearance/post', icon: FileText, labelKey: 'subsecPost' },
		{ href: '/settings/appearance/articles', icon: BookOpen, labelKey: 'subsecArticles' },
		{ href: '/settings/appearance/search-events', icon: Search, labelKey: 'subsecSearchEvents' },
		{ href: '/settings/appearance/other', icon: Settings2, labelKey: 'subsecOther' },
	];

	function isActive(href: string): boolean {
		return $page.url.pathname === href;
	}
</script>

<div class="settings-group subnav-group">
	{#each sections as s, i}
		<button class="subnav-row" use:ripple onclick={() => goto(s.href)} aria-current={isActive(s.href) ? 'page' : undefined}>
			<span class="subnav-icon" class:active={isActive(s.href)}><s.icon size={19} strokeWidth={1.9} /></span>
			<span class="subnav-label">{$t(`settings.${s.labelKey}`)}</span>
			<span class="subnav-chevron"><ChevronRight size={17} strokeWidth={1.8} /></span>
		</button>
		{#if i < sections.length - 1}
			<div class="subnav-divider"></div>
		{/if}
	{/each}
</div>

<style>
	.subnav-icon.active { background: color-mix(in oklch, var(--color-accent) 26%, transparent); }
</style>
