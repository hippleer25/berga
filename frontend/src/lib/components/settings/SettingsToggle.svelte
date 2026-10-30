<script lang="ts">
	import { ripple } from '$lib/actions/ripple';

	type Props = {
		label: string;
		checked: boolean;
		onClick: () => void;
		desc?: string;
		ariaLabel?: string;
	};
	let { label, checked, onClick, desc, ariaLabel }: Props = $props();
</script>

<div class="setting-row">
	<div class="setting-text">
		<span class="setting-label">{label}</span>
		{#if desc}<span class="setting-desc">{desc}</span>{/if}
	</div>
	<button class="pill-toggle" class:on={checked} use:ripple onclick={onClick} aria-label={ariaLabel ?? label}>
		<div class="pill-thumb"></div>
	</button>
</div>
