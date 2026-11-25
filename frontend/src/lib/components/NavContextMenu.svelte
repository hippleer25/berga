<script lang="ts">
	import { t } from 'svelte-i18n';
	import Portal from './Portal.svelte';
	import {
		columnsLayout,
		assignTabToPane,
		navigateMainTo,
		removePaneWithTab,
		type Pane
	} from '$lib/stores/columns';
	import type { TabDef } from '$lib/config/tabs';

	let {
		pos,
		tab,
		onClose
	}: {
		pos: { x: number; y: number };
		tab: TabDef;
		onClose: () => void;
	} = $props();

	// First column currently pinning this tab (duplicates pin → removes one).
	const pinnedPane = $derived($columnsLayout.panes.find(p => p.content === tab.id));

	const ITEM_H = 37;
	const TITLE_H = 34;
	const menuH = $derived(
		$columnsLayout.panes.length * ITEM_H + (pinnedPane ? ITEM_H : 0) + TITLE_H
	);

	const posStyle = $derived.by(() => {
		if (typeof window === 'undefined') return 'left:0;top:0;';
		const x = Math.max(8, Math.min(pos.x, window.innerWidth - 208 - 8));
		const y = Math.max(8, Math.min(pos.y, window.innerHeight - menuH - 8));
		return `left:${x}px;top:${y}px`;
	});

	function assign(pane: Pane) {
		assignTabToPane(pane.id, tab.id);
		onClose();
	}

	function openMain() {
		navigateMainTo(tab.id);
		onClose();
	}

	function remove() {
		if (pinnedPane) removePaneWithTab(tab.id);
		onClose();
	}

	function onWindowKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') onClose();
	}

	function insideMenu(e: Event) {
		return menuEl && e.target instanceof Node && menuEl.contains(e.target);
	}

	function onWindowClick(e: MouseEvent) {
		if (insideMenu(e)) return;
		onClose();
	}

	function onWindowContext(e: MouseEvent) {
		if (insideMenu(e)) return;
		onClose();
	}

	let menuEl: HTMLDivElement;
</script>

<Portal>
	<div
		bind:this={menuEl}
		class="nav-ctx"
		style={posStyle}
		role="menu"
		aria-label={$t('navbar.mainNav')}
	>
		<div class="nav-ctx-title">{$t(`navbar.${tab.id}`)}</div>
		{#each $columnsLayout.panes as pane, i (pane.id)}
			<button
				class="nav-ctx-item"
				class:nav-ctx-current={pane.content === tab.id}
				role="menuitem"
				onclick={() => (pane.content === 'main' ? openMain() : assign(pane))}
			>
				{#if pane.content === 'main'}
					{$t('navbar.colOpenMain')}
				{:else}
					{$t('navbar.colOpenN', { values: { n: i + 1 } })}
				{/if}
			</button>
		{/each}
		{#if pinnedPane}
			<button class="nav-ctx-item nav-ctx-danger" role="menuitem" onclick={remove}>
				{$t('navbar.colRemove')}
			</button>
		{/if}
	</div>
</Portal>

<svelte:window onclick={onWindowClick} onkeydown={onWindowKeydown} oncontextmenu={onWindowContext} />

<style>
	.nav-ctx {
		position: fixed;
		z-index: 9999;
		width: 208px;
		padding: 6px;
		background: var(--color-base-100);
		border: 1px solid var(--color-base-200);
		border-radius: var(--ui-radius-sm);
		box-shadow: 0 10px 30px color-mix(in oklch, black 14%, transparent);
		pointer-events: auto;
		display: flex;
		flex-direction: column;
	}
	.nav-ctx-title {
		font-size: 11px;
		font-weight: 700;
		letter-spacing: 0.04em;
		text-transform: uppercase;
		color: color-mix(in oklch, var(--color-base-content) 45%, transparent);
		padding: 6px 10px 4px;
	}
	.nav-ctx-item {
		text-align: left;
		font-size: 13px;
		padding: 8px 10px;
		border-radius: var(--ui-radius-sm);
		color: var(--color-base-content);
		transition: background 120ms ease;
	}
	.nav-ctx-item:hover {
		background: var(--color-base-200);
	}
	.nav-ctx-current {
		color: var(--color-accent);
		font-weight: 600;
	}
	.nav-ctx-danger {
		color: var(--color-error);
	}
</style>
