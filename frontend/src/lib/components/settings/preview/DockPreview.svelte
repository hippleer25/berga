<script lang="ts">
	import House from '@lucide/svelte/icons/house';
	import Rss from '@lucide/svelte/icons/rss';
	import Search from '@lucide/svelte/icons/search';
	import Sparkles from '@lucide/svelte/icons/sparkles';
	import Settings2 from '@lucide/svelte/icons/settings-2';
	import { orderedTabs, type TabDef } from '$lib/config/tabs';
	import { t } from 'svelte-i18n';
	import {
		uiDockWidthVmin,
		uiDockHeightPct,
		uiDockRadiusPct,
		uiDockPadPct,
		uiDockInsetVmin,
		uiDockSpacingPct,
		uiDockShadowPct,
		uiDeckWidthPct,
		uiDeckHeightVw,
		uiDeckRadiusPct,
	} from '$lib/stores/uiPrefs';

	let { device = 'desktop', mode = 'sidebar' }: { device?: 'desktop' | 'mobile'; mode?: 'sidebar' | 'dock' | 'bar' | 'deck' } = $props();

	let screenW = $state(360);
	let screenH = $state(210);

	function dockWidthPx(w: number): number {
		// Mirrors NavBar: width is % of the screen's smaller dimension, px-clamped.
		const vmin = Math.min(screenW, screenH);
		return Math.min(128, Math.max(40, vmin * (w / 100)));
	}

	function dockPadPx(w: number, p: number): number {
		return dockWidthPx(w) * (p / 100);
	}

	function dockInsetPx(w: number, inset: number): number {
		const vmin = Math.min(screenW, screenH);
		return Math.min(48, Math.max(3, vmin * (inset / 100)));
	}

	function dockGapPx(w: number, spacing: number): number {
		const vmin = Math.min(screenW, screenH);
		return Math.min(7, Math.max(3, vmin * 0.009)) * (spacing / 100);
	}

	function dockHeightPx(h: number): string {
		return h > 0 ? `${(screenH * h) / 100}px` : 'fit-content';
	}

	function deckWidthPx(w: number): number {
		return screenW * (w / 100);
	}

	function deckHeightPx(h: number): number {
		// Deck height is a % of screen *width* (vw in the real app).
		return screenW * (h / 100);
	}
</script>

{#snippet tabIcon(tab: TabDef, size: number)}
	{#if tab.id === 'home'}<House {size} strokeWidth={1.8} />
	{:else if tab.id === 'followers'}<Rss {size} strokeWidth={1.8} />
	{:else if tab.id === 'events'}<Search {size} strokeWidth={1.8} />
	{:else}<Sparkles {size} strokeWidth={1.8} />{/if}
{/snippet}

<div class="dock-preview">
	<div class="screen" bind:clientWidth={screenW} bind:clientHeight={screenH}>
		<div class="screen-page">
			<span class="screen-banner"></span>
			<span class="screen-line"></span>
			<span class="screen-line short"></span>
		</div>

		{#if device === 'desktop' && mode === 'sidebar'}
			<aside class="pv-sidebar">
				<span class="pv-brand">
					<span class="pv-logo"></span>
				</span>
				<nav class="pv-sb-nav">
					{#each $orderedTabs as tab, i (tab.id)}
						<span class="pv-side-item" class:active={i === 1}>
							<span class="pv-side-icon">{@render tabIcon(tab, 16)}</span>
							<span class="pv-side-label">{$t(`navbar.${tab.id}`)}</span>
						</span>
					{/each}
					<span class="pv-side-item">
						<span class="pv-side-icon"><Settings2 size={16} strokeWidth={1.8} /></span>
						<span class="pv-side-label">settings</span>
					</span>
				</nav>
			</aside>
		{:else if device === 'desktop' && mode === 'dock'}
			{@const dw = dockWidthPx($uiDockWidthVmin)}
			{@const pad = dockPadPx($uiDockWidthVmin, $uiDockPadPct)}
			{@const subSize = Math.max(10, dw - pad * 2)}
			<nav
				class="pv-dock"
				class:no-shadow={$uiDockShadowPct <= 0}
				style:width={`${dw}px`}
				style:height={dockHeightPx($uiDockHeightPct)}
				style:border-radius={`${dw * ($uiDockRadiusPct / 100)}px`}
				style:padding={`${pad}px 0`}
				style:gap={`${dockGapPx($uiDockWidthVmin, $uiDockSpacingPct)}px`}
				style:left={`${dockInsetPx($uiDockWidthVmin, $uiDockInsetVmin)}px`}
				style:box-shadow={`0 8px 20px color-mix(in oklch, black ${10 * ($uiDockShadowPct / 100)}%, transparent), 0 1px 4px color-mix(in oklch, black ${6 * ($uiDockShadowPct / 100)}%, transparent)`}
			>
				{#each $orderedTabs as tab, i (tab.id)}
					{@const itemSize = Math.max(10, dw - pad * 2)}
					<span class="pv-dock-item" class:active={i === 1} style:width={`${itemSize}px`} style:height={`${itemSize}px`} style:border-radius={`${dw * ($uiDockRadiusPct / 100) * 0.82}px`}>
						<span class="pv-dock-icon"><span class="pv-icon-pill" class:visible={i === 1}></span>{@render tabIcon(tab, itemSize * 0.5)}</span>
					</span>
				{/each}
				<span class="pv-dock-item" style:width={`${subSize}px`} style:height={`${subSize}px`} style:border-radius={`${dw * ($uiDockRadiusPct / 100) * 0.82}px`}>
					<span class="pv-dock-icon"><span class="pv-icon-pill"></span><Settings2 size={subSize * 0.5} strokeWidth={1.8} /></span>
				</span>
			</nav>
		{:else if mode === 'deck'}
			{@const dw = deckWidthPx($uiDeckWidthPct)}
			{@const dh = deckHeightPx($uiDeckHeightVw)}
			<nav
				class="pv-bar pv-bar--deck"
				style:width={`${dw}px`}
				style:height={`${dh}px`}
				style:bottom={`12px`}
				style:left={`calc(50% - ${dw / 2}px)`}
				style:border-radius={`${dh * ($uiDeckRadiusPct / 100)}px`}
			>
				{#each $orderedTabs as tab, i (tab.id)}
					<span class="pv-bar-item" class:active={i === 1}>
						<span class="pv-icon-pill" class:visible={i === 1}></span>
						{@render tabIcon(tab, Math.max(16, dh * 0.34))}
					</span>
				{/each}
			</nav>
		{:else}
			<nav class="pv-bar pv-bar--plain">
				{#each $orderedTabs as tab, i (tab.id)}
					<span class="pv-bar-item" class:active={i === 1}>
						<span class="pv-bar-itembox">
							<span class="pv-icon-pill" class:visible={i === 1}></span>
							{@render tabIcon(tab, 21)}
						</span>
						<span class="pv-bar-label">{$t(`navbar.${tab.id}`)}</span>
					</span>
				{/each}
			</nav>
		{/if}
	</div>
</div>

<style>
	.dock-preview { display: flex; justify-content: center; }
	.screen {
		position: relative;
		width: min(100%, 300px);
		min-width: 240px;
		height: 200px;
		overflow: hidden;
		border-radius: 18px;
		border: 6px solid color-mix(in oklch, var(--color-base-content) 60%, transparent);
		outline: 2px solid color-mix(in oklch, var(--color-base-content) 18%, transparent);
		background: var(--color-base-100);
	}

	/* Fake page content */
	.screen-page { padding: 14px 14px 60px; display: flex; flex-direction: column; gap: 8px; }
	.screen-banner {
		display: block;
		width: 55%;
		height: 14px;
		border-radius: var(--ui-radius-sm);
		background: color-mix(in oklch, var(--color-base-content) 28%, transparent);
	}
	.screen-line {
		display: block;
		width: 92%;
		height: 8px;
		border-radius: var(--ui-radius-full);
		background: color-mix(in oklch, var(--color-base-content) 12%, transparent);
	}
	.screen-line.short { width: 70%; }

	/* ── Sidebar replica ── */
	.pv-sidebar {
		position: absolute;
		inset: 0 auto 0 0;
		display: flex;
		flex-direction: column;
		width: 88px;
		background: var(--nav-bg, var(--color-base-100));
		border-right: 1px solid var(--glass-border);
		padding: 18px var(--sidebar-item-margin, 0.625rem) 10px;
	}
	.pv-brand { height: 18px; margin-bottom: 12px; display: flex; }
	.pv-logo {
		width: 18px; height: 18px;
		border-radius: var(--ui-radius-sm);
		background: var(--color-accent);
	}
	.pv-sb-nav { display: flex; flex-direction: column; gap: 4px; }
	.pv-side-item {
		display: flex; align-items: center; gap: 8px;
		padding: var(--sidebar-item-pad-y, 0.5rem) var(--sidebar-item-margin, 0.625rem);
		border-left: 3px solid transparent;
		color: color-mix(in oklch, var(--color-base-content) 60%, transparent);
		white-space: nowrap; overflow: hidden;
	}
	.pv-side-item.active { color: var(--color-accent); border-left-color: var(--color-accent); }
	:global([data-nav-indicator='none']) .pv-side-item.active { border-left-color: transparent; }
	.pv-side-icon { display: flex; flex-shrink: 0; }
	.pv-side-label { font-size: 10px; font-weight: 600; }

	/* ── Desktop floating dock replica ── */
	.pv-dock {
		position: absolute;
		top: 50%;
		transform: translateY(-50%);
		display: flex;
		flex-direction: column;
		align-items: center;
		border: 1px solid var(--glass-border);
		background: var(--nav-glass-strong, color-mix(in oklch, var(--nav-bg, var(--color-base-100)) 82%, transparent));
		backdrop-filter: var(--glass-blur);
		overflow: hidden;
		transition: none;
	}
	:global([data-glass='off']) .pv-dock {
		background: var(--nav-bg, var(--color-base-100));
	}
	.pv-dock.no-shadow { box-shadow: none; }
	.pv-dock-item {
		position: relative;
		display: flex;
		align-items: center;
		justify-content: center;
		width: calc(100% - 2 * 0px);
		margin: 0;
		border-radius: calc(0.82 * 34px);
		color: color-mix(in oklch, var(--color-base-content) 58%, transparent);
	}
	.pv-dock-item.active { color: var(--color-accent); }
	.pv-dock-icon { position: relative; display: flex; align-items: center; justify-content: center; }
	.pv-icon-pill {
		position: absolute;
		inset: -4px -6px;
		border-radius: var(--ui-radius-full);
		background: transparent;
		opacity: 0;
	}
	.pv-icon-pill.visible {
		background: color-mix(in oklch, var(--color-accent) 26%, transparent);
		opacity: 1;
	}
	/* classic: whole item lights up */
	:global([data-nav-indicator='classic']) .pv-dock-item.active,
	:global([data-nav-indicator='classic']) .pv-bar-item.active {
		background: color-mix(in oklch, var(--color-accent) 13%, transparent);
	}
	:global([data-nav-indicator='none']) .pv-icon-pill.visible { background: transparent; opacity: 0; }

	/* ── Mobile bar / deck replica ── */
	.pv-bar {
		position: absolute;
		display: flex;
		align-items: center;
		justify-content: space-around;
		background: var(--nav-glass-strong, color-mix(in oklch, var(--nav-bg, var(--color-base-100)) 82%, transparent));
		backdrop-filter: var(--glass-blur);
		border: var(--ui-border-width, 1px) solid var(--ui-border-color, var(--glass-border));
		box-shadow: var(--ui-shadow-1);
	}
	:global([data-glass='off']) .pv-bar {
		background: var(--nav-bg, var(--color-base-100));
	}
	.pv-bar--deck { z-index: 2; }
	.pv-bar--plain { left: 0; right: 0; bottom: 0; height: calc(var(--mnav-height, 64px) - 10px); width: auto; border-left: none; border-right: none; border-bottom: none; box-shadow: 0 -4px 16px color-mix(in oklch, black 10%, transparent); }
	.pv-bar-item {
		position: relative;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: calc(2px * 1);
		color: color-mix(in oklch, var(--color-base-content) 55%, transparent);
	}
	.pv-bar-item.active { color: var(--color-accent); }
	.pv-bar-itembox {
		position: relative;
		display: flex; align-items: center; justify-content: center;
		width: var(--mnav-iconbox-h, 28px);
		height: calc(var(--mnav-iconbox-h, 28px) - 6px);
		border-radius: var(--mnav-item-radius, var(--ui-radius-sm));
	}
	.pv-bar--deck .pv-icon-pill {
		inset: -5px -7px;
	}
	.pv-bar-label {
		font-size: var(--mnav-label-size, 11px);
		letter-spacing: 0.01em;
	}
	:global([data-mnav-labels='off']) .pv-bar-label { display: none; }
</style>
