<script lang="ts">
	import { t } from 'svelte-i18n';
	import { navTabDragging, pinToSide, type SplitSide } from '$lib/stores/splitView';
	import { TAB_DEFS, type TabId } from '$lib/config/tabs';
	import PanelLeft from '@lucide/svelte/icons/panel-left';
	import PanelRight from '@lucide/svelte/icons/panel-right';

	let hovered = $state<SplitSide | null>(null);

	function onDragOver(e: DragEvent, side: SplitSide) {
		e.preventDefault();
		if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy';
		hovered = side;
	}

	function onDragLeave(side: SplitSide) {
		if (hovered === side) hovered = null;
	}

	function onDrop(e: DragEvent, side: SplitSide) {
		e.preventDefault();
		const id = e.dataTransfer?.getData('berga/tab');
		hovered = null;
		if (id && id in TAB_DEFS) pinToSide(id as TabId, side);
	}

	function onDragEnd() {
		navTabDragging.set(false);
		hovered = null;
	}
</script>

<svelte:window ondragend={onDragEnd} />

{#if $navTabDragging}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="drop-frost" aria-hidden="true">
		<div
			class="zone"
			class:hover={hovered === 'left'}
			ondragover={e => onDragOver(e, 'left')}
			ondragleave={() => onDragLeave('left')}
			ondrop={e => onDrop(e, 'left')}
		>
			<div class="zone-card">
				<PanelLeft size={30} strokeWidth={1.6} />
				<span class="zone-label">{$t('navbar.splitPaneLeft')}</span>
			</div>
		</div>
		<div
			class="zone"
			class:hover={hovered === 'right'}
			ondragover={e => onDragOver(e, 'right')}
			ondragleave={() => onDragLeave('right')}
			ondrop={e => onDrop(e, 'right')}
		>
			<div class="zone-card">
				<PanelRight size={30} strokeWidth={1.6} />
				<span class="zone-label">{$t('navbar.splitPaneRight')}</span>
			</div>
		</div>
	</div>
{/if}

<style>
	.drop-frost {
		display: none;
	}
	@media (min-width: 768px) {
		/* Frozen scrim: covers the content area only — sidebar and nav stay
		   visible (theme-aware frosted glass). */
		.drop-frost {
			display: flex;
			position: fixed;
			inset: 0;
			left: var(--sidebar-w, 240px);
			z-index: 60;
			pointer-events: none;
			background: color-mix(in oklch, var(--color-base-100) 80%, transparent);
			backdrop-filter: blur(6px);
			-webkit-backdrop-filter: blur(6px);
		}
		.zone {
			flex: 1;
			display: flex;
			align-items: center;
			justify-content: center;
			pointer-events: auto;
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
