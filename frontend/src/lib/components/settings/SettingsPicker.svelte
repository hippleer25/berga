<script lang="ts">
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import Check from '@lucide/svelte/icons/check';
	import { t } from 'svelte-i18n';
	import Portal from '$lib/components/Portal.svelte';

	type Option = {
		value: string;
		labelKey?: string;
		label?: string;
		/** Optional style hint shown next to the option (font pickers). */
		category?: string;
		/** Secondary hint rendered small next to the label. */
		descKey?: string;
		/** Fill of the option swatch (`null` = theme gradient). Requires `colorList`. */
		color?: string | null;
	};

	type Props = {
		options: Option[];
		onSelect: (value: string) => void;
		/** Current value (for highlighting). */
		value: string;
		/** Anything rendered inside the trigger button (before the chevron). */
		trigger?: string;
		/**
		 * Renders the option label in its own font-family (font pickers).
		 * Only meaningful when options carry `category`.
		 */
		fontList?: boolean;
		/** Renders a color swatch per option (and in the trigger). */
		colorList?: boolean;
	};
	let { options, onSelect, value, trigger, fontList = false, colorList = false }: Props = $props();

	let open = $state(false);
	let btnEl: HTMLButtonElement | null = $state(null);
	let dropStyle = $state('');

	function toggle() {
		if (open) {
			open = false;
			return;
		}
		open = true;
		if (btnEl) {
			const r = btnEl.getBoundingClientRect();
			const maxH = window.innerHeight - r.bottom - 12;
			dropStyle = `top:${r.bottom + 6}px;left:${Math.max(8, r.left)}px;min-width:${r.width}px;max-height:${Math.max(maxH, 120)}px;overflow-y:auto`;
		}
	}

	function pick(option: Option) {
		onSelect(option.value);
		open = false;
	}

	function labelOf(option: Option): string {
		if (option.labelKey) return $t(option.labelKey);
		if (option.label) return option.label;
		return option.value;
	}

	function colorOf(value: string): string | null | undefined {
		return options.find((o) => o.value === value)?.color;
	}

	function onClickOutside(e: MouseEvent) {
		const target = e.target as Node;
		if (!btnEl || !btnEl.contains(target)) {
			const dropdown = document.querySelector('.sp-dropdown');
			if (!dropdown || !dropdown.contains(target)) open = false;
		}
	}
</script>

<div class="picker-wrap">
	<button bind:this={btnEl} class="setting-btn" onclick={toggle} aria-haspopup="listbox" aria-expanded={open}>
		{#if trigger}
			<span style={fontList ? `font-family: '${value}', sans-serif;` : ''}>
				{#if colorList}
					{@const cur = colorOf(value)}
					{#if cur !== undefined}
						<span
							class="sp-swatch sp-swatch--sm"
							class:sp-swatch--theme={cur === null}
							style:background={cur}
						></span>
					{/if}
				{/if}
				{trigger}
			</span>
		{/if}
		<span class="chevron-icon" class:rotated={open}>
			<ChevronDown size={14} />
		</span>
	</button>
</div>

{#if open}
	<Portal>
		<div class="sp-backdrop" onclick={() => (open = false)} aria-hidden="true"></div>
		<div class="sp-dropdown" style={dropStyle} role="listbox" tabindex="-1" onmousedown={onClickOutside}>
			{#each options as option (option.value)}
				<button
					class="sp-item"
					class:sp-selected={value === option.value}
					role="option"
					aria-selected={value === option.value}
					onclick={() => pick(option)}
				>
				{#if fontList}
					<span class="sp-item-text" style={`font-family: '${option.value}', sans-serif;`}>
						{option.label ?? option.value}
					</span>
					<span class="sp-cat-label">{option.category === 'serif' ? $t('settings.serif') : $t('settings.sans')}</span>
				{:else}
					{#if colorList && option.color !== undefined}
						<span
							class="sp-swatch"
							class:sp-swatch--theme={option.color === null}
							style:background={option.color}
						></span>
					{/if}
					<span class="sp-item-text">{labelOf(option)}</span>
					{#if option.descKey}
						<span class="sp-item-desc">{$t(option.descKey)}</span>
					{/if}
				{/if}
				{#if value === option.value}<Check size={12} class="sp-check" />{/if}
				</button>
			{/each}
		</div>
	</Portal>
{/if}
