<script lang="ts">
	import { t } from 'svelte-i18n';
	import Portal from './Portal.svelte';
	import {
		pinToSide,
		removeSplit,
		splitTab,
		type SplitSide
	} from '$lib/stores/splitView';
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

	// Null while the pinned pane hasn't been signal-flushed yet on first open.
	const pinned = $derived($splitTab === tab.id);

	const MENU_W = 208;
	const menuH = $derived(pinned ? 132 : 96);

	const posStyle = $derived.by(() => {
		if (typeof window === 'undefined') return 'left:0;top:0;';
		const x = Math.max(8, Math.min(pos.x, window.innerWidth - MENU_W - 8));
		const y = Math.max(8, Math.min(pos.y, window.innerHeight - menuH - 8));
		return `left:${x}px;top:${y}px`;
	});

	function pin(side: SplitSide) {
		pinToSide(tab.id, side);
		onClose();
	}

	function remove() {
		removeSplit(tab.id);
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
		{#if pinned}
			<button class="nav-ctx-item" role="menuitem" onclick={() => pin('left')}>
				{$t('navbar.splitMoveLeft')}
			</button>
			<button class="nav-ctx-item" role="menuitem" onclick={() => pin('right')}>
				{$t('navbar.splitMoveRight')}
			</button>
			<button class="nav-ctx-item nav-ctx-danger" role="menuitem" onclick={remove}>
				{$t('navbar.splitRemove')}
			</button>
		{:else}
			<button class="nav-ctx-item" role="menuitem" onclick={() => pin('left')}>
				{$t('navbar.splitOpenLeft')}
			</button>
			<button class="nav-ctx-item" role="menuitem" onclick={() => pin('right')}>
				{$t('navbar.splitOpenRight')}
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
	.nav-ctx-danger {
		color: var(--color-error);
	}
</style>
