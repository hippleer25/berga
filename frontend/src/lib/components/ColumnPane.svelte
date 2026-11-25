<script lang="ts">
	import { TAB_LOADERS, type TabId } from '$lib/config/tabs';
	import type { Component } from 'svelte';

	/** One pinned column: lazily loads and mounts its tab screen. */
	let {
		tab,
		paneKey
	}: {
		tab: TabId;
		/** Identity of this column, forwarded so pane-aware tabs (Mota) can scope their state. */
		paneKey: string;
	} = $props();

	let Comp = $state<Component | null>(null);
	let curTab = $state<TabId | null>(null);

	$effect(() => {
		const id = tab;
		if (!id || curTab === id) return;
		let cancelled = false;
		TAB_LOADERS[id]().then(mod => {
			if (cancelled) return;
			Comp = mod.default;
			curTab = id;
		});
		return () => {
			cancelled = true;
		};
	});
</script>

{#if curTab === tab && Comp}
	{#key tab}
		{@const Pinned = Comp}
		<div class="column-pane">
			<!-- paneKey is only meaningful to pane-aware screens (Mota chat); the
			     spread keeps it off tabs that don't declare it. -->
			<Pinned {...(tab === 'mota' ? { paneKey } : {})} />
		</div>
	{/key}
{:else}
	<div class="column-pane column-pane-loader"></div>
{/if}

<style>
	.column-pane {
		min-height: 100%;
		background: var(--color-base-100);
	}
	.column-pane-loader {
		height: 100dvh;
	}
</style>
