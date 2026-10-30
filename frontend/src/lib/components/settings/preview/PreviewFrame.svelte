<script lang="ts">
	import type { Snippet } from 'svelte';

	let { label, children }: { label?: string; children: Snippet } = $props();
</script>

<div class="preview-frame" inert aria-hidden="true">
	{#if label}
		<span class="preview-label">{label}</span>
	{/if}
	<div class="preview-stage">
		{@render children()}
	</div>
</div>

<style>
	.preview-frame {
		position: relative;
		margin-top: 8px;
		padding: 26px 14px 16px;
		border-radius: var(--ui-radius-lg);
		border: 1px dashed color-mix(in oklch, var(--color-base-content) 26%, transparent);
		background:
			linear-gradient(color-mix(in oklch, var(--color-base-100) 55%, transparent), color-mix(in oklch, var(--color-base-100) 55%, transparent))
				content-box,
			repeating-linear-gradient(
				135deg,
				color-mix(in oklch, var(--color-base-content) 3%, transparent) 0 12px,
				transparent 12px 24px
			)
				padding-box;
		pointer-events: none;
		user-select: none;
	}
	.preview-label {
		position: absolute;
		top: 8px;
		left: 14px;
		font-size: 10.5px;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.09em;
		color: color-mix(in oklch, var(--color-base-content) 45%, transparent);
	}
	.preview-stage {
		pointer-events: none;
	}
</style>
