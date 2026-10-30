<script lang="ts">
	import { ripple } from '$lib/actions/ripple';

	type Props = {
		label: string;
		value: number;
		min: number;
		max: number;
		step: number;
		onInput: (v: number) => void;
		format?: (v: number) => string;
		hint?: string;
	};
	let { label, value, min, max, step, onInput, format, hint }: Props = $props();
</script>

<div class="setting-slider-row">
	<div class="slider-head">
		<span class="setting-label">{label}</span>
		<span class="slider-value">{format ? format(value) : `${value}`}</span>
	</div>
	<input
		type="range"
		class="range"
		min={min}
		max={max}
		{step}
		{value}
		use:ripple
		oninput={(e) => onInput(Number((e.target as HTMLInputElement).value))}
	/>
	{#if hint}<p class="row-hint">{hint}</p>{/if}
</div>
