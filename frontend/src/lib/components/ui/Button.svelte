<script lang="ts">
	import type { Snippet } from 'svelte';
	import { ripple } from '$lib/actions/ripple';

	type Variant = 'default' | 'accent' | 'outline' | 'ghost' | 'danger' | 'success';
	type Size = 'sm' | 'md' | 'lg';

	type Props = {
		variant?: Variant;
		size?: Size;
		block?: boolean;
		href?: string;
		type?: 'button' | 'submit' | 'reset';
		disabled?: boolean;
		title?: string;
		ariaLabel?: string;
		class?: string;
		onclick?: (event: MouseEvent) => void;
		children?: Snippet;
	};

	let {
		variant = 'default',
		size = 'md',
		block = false,
		href,
		type = 'button',
		disabled = false,
		title,
		ariaLabel,
		class: className = '',
		onclick,
		children,
	}: Props = $props();

	const classes = $derived(
		[
			'ui-btn',
			variant !== 'default' ? `ui-btn--${variant}` : '',
			size !== 'md' ? `ui-btn--${size}` : '',
			block ? 'ui-btn--block' : '',
			className,
		]
			.filter(Boolean)
			.join(' ')
	);
</script>

{#if href}
	<a
		{href}
		class={classes}
		{title}
		aria-label={ariaLabel}
		aria-disabled={disabled ? 'true' : undefined}
		use:ripple
		{onclick}
	>
		{@render children?.()}
	</a>
{:else}
	<button {type} class={classes} {disabled} {title} aria-label={ariaLabel} use:ripple {onclick}>
		{@render children?.()}
	</button>
{/if}
