<script lang="ts">
	import { t } from 'svelte-i18n';
	import {
		navTabDragging,
		columnsLayout,
		assignTabToPane,
		navigateMainTo,
		gridTemplate
	} from '$lib/stores/columns';
	import { TAB_DEFS, type TabId } from '$lib/config/tabs';
	import PanelLeft from '@lucide/svelte/icons/panel-left';
	import Columns2 from '@lucide/svelte/icons/columns-2';

	let hovered = $state<number | null>(null);

	const multi = $derived($columnsLayout.panes.length > 1);
	const template = $derived(
		multi ? gridTemplate($columnsLayout.panes, $columnsLayout.widths) : '1fr'
	);

	function onDragOver(e: DragEvent, i: number) {
		e.preventDefault();
		if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy';
		hovered = i;
	}

	function onDragLeave(i: number) {
		if (hovered === i) hovered = null;
	}

	function onDrop(e: DragEvent, i: number) {
		e.preventDefault();
		const id = e.dataTransfer?.getData('berga/tab');
		hovered = null;
		if (!id || !(id in TAB_DEFS)) return;
		const pane = $columnsLayout.panes[i];
		if (!pane) return;
		if (pane.content === 'main') navigateMainTo(id as TabId);
		else assignTabToPane(pane.id, id as TabId);
	}

	function onDragEnd() {
		navTabDragging.set(false);
		hovered = null;
	}
</script>

<svelte:window ondragend={onDragEnd} />

{#if $navTabDragging && multi}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="drop-frost" style:--col-template={template} aria-hidden="true">
		{#each $columnsLayout.panes as pane, i (pane.id)}
			{#if i > 0}<div class="zone-spacer"></div>{/if}
			<div
				class="zone"
				class:hover={hovered === i}
				ondragover={e => onDragOver(e, i)}
				ondragleave={() => onDragLeave(i)}
				ondrop={e => onDrop(e, i)}
			>
				<div class="zone-card">
					{#if pane.content === 'main'}
						<PanelLeft size={30} strokeWidth={1.6} />
						<span class="zone-label">{$t('navbar.colMain')}</span>
					{:else}
						<Columns2 size={30} strokeWidth={1.6} />
						<span class="zone-label">{$t('navbar.colN', { values: { n: i + 1 } })}</span>
					{/if}
				</div>
			</div>
		{/each}
	</div>
{/if}

<style>
	.drop-frost {
		display: none;
	}
	@media (min-width: 768px) {
		/* Frozen scrim mirroring the column grid: sidebar and nav stay visible
		   (theme-aware frosted glass). */
		.drop-frost {
			display: grid;
			position: fixed;
			inset: 0;
			left: var(--sidebar-w, 240px);
			grid-template-columns: var(--col-template, 1fr);
			z-index: 60;
			pointer-events: none;
			background: color-mix(in oklch, var(--color-base-100) 80%, transparent);
			backdrop-filter: blur(6px);
			-webkit-backdrop-filter: blur(6px);
		}
		.zone {
			display: flex;
			align-items: center;
			justify-content: center;
			pointer-events: auto;
		}
		.zone-spacer {
			pointer-events: none;
		}
		.zone-card {
			display: flex;
			flex-direction: column;
			align-items: center;
			justify-content: center;
			gap: 12px;
			width: min(280px, 60%);
			padding: 34px 20px;
			border: 2px dashed
				color-mix(in oklch, var(--color-base-content) 25%, transparent);
			border-radius: var(--ui-radius-lg, 14px);
			color: color-mix(in oklch, var(--color-base-content) 55%, transparent);
			transition:
				border-color 140ms ease,
				color 140ms ease,
				background 140ms ease,
				transform 140ms ease;
		}
		.zone.hover {
			box-shadow: inset 0 0 0 2px var(--color-accent);
			background: color-mix(in oklch, var(--color-accent) 10%, transparent);
		}
		.zone.hover .zone-card {
			border-color: var(--color-accent);
			border-style: solid;
			color: var(--color-accent);
			transform: scale(1.04);
		}
		.zone-label {
			font-size: 15px;
			font-weight: 700;
			letter-spacing: 0.03em;
			text-align: center;
		}
	}
</style>
