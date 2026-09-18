<script lang="ts">
	import { splitTab } from '$lib/stores/splitView';
	import { TAB_LOADERS, type TabId } from '$lib/config/tabs';
	import type { Component } from 'svelte';

	let Comp = $state<Component | null>(null);
	let curTab = $state<TabId | null>(null);

	$effect(() => {
		const id = $splitTab;
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

{#if $splitTab && curTab === $splitTab && Comp}
	{#key curTab}
		{@const Pinned = Comp}
		<div class="split-pane">
			<Pinned />
		</div>
	{/key}
{:else}
	<div class="split-pane split-pane-loader"></div>
{/if}

<style>
	.split-pane {
		min-height: 100%;
		background: var(--color-base-100);
	}
	.split-pane-loader {
		height: 100dvh;
	}
</style>
