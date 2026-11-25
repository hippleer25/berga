<script lang="ts">
	import { get } from 'svelte/store';
	import {
		columnsLayout,
		gridTemplate,
		setWidths,
		equalizeWidths,
		GUTTER_PX,
		MIN_PANE_PCT
	} from '$lib/stores/columns';

	/**
	 * Resize handles rendered over the column grid (same template). Drag
	 * adjusts the two neighbouring shares live (no persist); double-click
	 * equalizes. Gutter cells sit between the panes in the template order.
	 */

	let layerEl: HTMLElement | null = $state(null);
	let dragIdx = $state<number | null>(null);
	let hoverIdx = $state<number | null>(null);
	let startX = 0;
	let startW: number[] = [];
	let frSpace = 0;

	const multi = $derived($columnsLayout.panes.length > 1);
	const template = $derived(
		multi ? gridTemplate($columnsLayout.panes, $columnsLayout.widths) : '1fr'
	);

	function onDown(e: PointerEvent, gi: number) {
		e.preventDefault();
		e.stopPropagation();
		const l = $columnsLayout;
		if (!layerEl || l.panes.length < 2) return;
		dragIdx = gi;
		hoverIdx = gi;
		startX = e.clientX;
		startW = [...l.widths];
		frSpace = layerEl.clientWidth - (l.panes.length - 1) * GUTTER_PX;
		layerEl.setPointerCapture(e.pointerId);
		document.body.classList.add('col-resizing');
	}

	function onMove(e: PointerEvent) {
		if (dragIdx === null || !layerEl) return;
		const dxPct = ((e.clientX - startX) / frSpace) * 100;
		const i = dragIdx;
		const j = dragIdx + 1;
		// Clamp both neighbours to the floor share.
		const lo = MIN_PANE_PCT - startW[i];
		const hi = startW[j] - MIN_PANE_PCT;
		const d = Math.max(lo, Math.min(hi, dxPct));
		const w = [...startW];
		w[i] = startW[i] + d;
		w[j] = startW[j] - d;
		setWidths(w, false);
	}

	function onUp(e: PointerEvent) {
		if (dragIdx === null) return;
		dragIdx = null;
		document.body.classList.remove('col-resizing');
		setWidths(get(columnsLayout).widths, true);
		try {
			layerEl?.releasePointerCapture(e.pointerId);
		} catch {
			/* pointer already released */
		}
	}

	function onDblClick(e: MouseEvent) {
		e.preventDefault();
		if (dragIdx !== null) return;
		equalizeWidths();
	}
</script>

{#if multi}
	<div
		bind:this={layerEl}
		class="gutter-layer"
		class:dragging={dragIdx !== null}
		style:--col-template={template}
		onpointermove={onMove}
		onpointerup={onUp}
		onpointercancel={onUp}
		aria-hidden="true"
	>
		{#each $columnsLayout.panes as pane, i (pane.id)}
			{#if i > 0}
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<div
					class="gutter-cell"
					class:hover={hoverIdx === i - 1 && dragIdx === null}
					class:active={dragIdx === i - 1}
					onpointerdown={e => onDown(e, i - 1)}
					onpointerenter={() => (hoverIdx = i - 1)}
					onpointerleave={() => {
						if (dragIdx === null) hoverIdx = null;
					}}
					ondblclick={onDblClick}
				></div>
			{/if}
			<div class="gutter-spacer"></div>
		{/each}
	</div>
{/if}

<style>
	.gutter-layer {
		display: none;
	}
	@media (min-width: 768px) {
		.gutter-layer {
			display: grid;
			position: fixed;
			inset: 0;
			left: var(--sidebar-w, 240px);
			grid-template-columns: var(--col-template, 1fr);
			z-index: 40;
			pointer-events: none;
		}
		/* Overlay mirror of the pane cells — transparent, inert. */
		.gutter-spacer {
			pointer-events: none;
		}
		.gutter-cell {
			pointer-events: auto;
			cursor: col-resize;
			position: relative;
			touch-action: none;
		}
		.gutter-cell::after {
			content: '';
			position: absolute;
			top: 0;
			bottom: 0;
			left: 50%;
			width: 2px;
			transform: translateX(-50%) scaleY(0);
			background: var(--color-accent);
			opacity: 0.55;
			transition: transform 140ms var(--ui-ease, ease), opacity 140ms ease;
		}
		.gutter-cell:hover::after,
		.gutter-cell.active::after {
			transform: translateX(-50%) scaleY(1);
		}
	}
	:global(body.col-resizing) {
		user-select: none;
		cursor: col-resize;
	}
</style>
