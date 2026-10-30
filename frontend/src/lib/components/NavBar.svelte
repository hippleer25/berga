<script lang="ts">
	import { t } from 'svelte-i18n';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import PanelLeftClose from '@lucide/svelte/icons/panel-left-close';
	import PanelLeftOpen from '@lucide/svelte/icons/panel-left-open';
	import ArrowLeftRight from '@lucide/svelte/icons/arrow-left-right';
	import X from '@lucide/svelte/icons/x';
	import Settings from '@lucide/svelte/icons/settings';
	import {
		activeTabIdx,
		navVisible,
		navDragOffset,
		navDragging,
		stackedScreenOpen
	} from '$lib/stores/swipe';
	import { orderedTabs, type TabDef } from '$lib/config/tabs';
	import {
		splitTab,
		splitSide,
		moveSplit,
		closeSplit,
		opposite,
		swapWithMain,
		navTabDragging
	} from '$lib/stores/splitView';
	import NavContextMenu from '$lib/components/NavContextMenu.svelte';
	import { ripple } from '$lib/actions/ripple';
	import {
		applySidebarCollapsed,
		uiSidebarCollapsed,
		uiDesktopNav
	} from '$lib/stores/uiPrefs';

	const tabIdx = $derived($activeTabIdx);
	const covered = $derived($stackedScreenOpen);

	// ── Multi-tab split viewer (desktop) ─────────────────────────────────
	let ctxMenu = $state<{ x: number; y: number; tab: TabDef } | null>(null);

	const isDesktop = () => window.matchMedia('(min-width: 768px)').matches;

	function navCtx(e: MouseEvent, tab: TabDef) {
		if (!isDesktop()) return;
		e.preventDefault();
		e.stopPropagation(); // don't let the event close the menu we just opened
		ctxMenu = { x: e.clientX, y: e.clientY, tab };
	}

	function invertSplit() {
		if ($splitTab === null) return;
		moveSplit(opposite($splitSide));
	}

	function navDragStart(e: DragEvent, tab: TabDef) {
		if (!e.dataTransfer) return;
		e.dataTransfer.setData('berga/tab', tab.id);
		e.dataTransfer.effectAllowed = 'copy';
		navTabDragging.set(true);
	}

	function navDragEnd() {
		navTabDragging.set(false);
	}

	/** Left-click on a pinned tab's icon swaps the main and pinned panes. */
	function navClick(e: MouseEvent, tab: TabDef) {
		ctxMenu = null;
		if ($splitTab !== tab.id) return;
		e.preventDefault();
		if (swapWithMain()) goto(tab.href);
	}

	function toggleSidebar() {
		const next = !$uiSidebarCollapsed;
		uiSidebarCollapsed.set(next);
		applySidebarCollapsed(next, true);
	}

	// ── Desktop floating dock: expand after ~2s of sustained hover ────────
	/** Hover dwell (ms) before the dock expands to the right. */
	const DOCK_EXPAND_DWELL = 2000;

	let expanded = $state(false);
	let dockTimer: ReturnType<typeof setTimeout> | undefined;

	function dockEnter() {
		if (dockTimer) clearTimeout(dockTimer);
		dockTimer = setTimeout(() => (expanded = true), DOCK_EXPAND_DWELL);
	}

	function dockLeave() {
		if (dockTimer) clearTimeout(dockTimer);
		dockTimer = undefined;
		expanded = false;
	}

	$effect(() => () => { if (dockTimer) clearTimeout(dockTimer); });

	const settingsActive = $derived($page.url.pathname.startsWith('/settings'));

	// ── Swipe-down-to-hide gesture (mobile only) ────────────────────────────
	let navEl: HTMLElement;

	let tsX = 0, tsY = 0;
	let gAxis: 'h' | 'v' | null = null;
	let lastY = 0, lastT = 0, velY = 0;
	let dragMoved = false;
	let suppressNextClick = false;

	// Total travel the bar needs to fully leave the screen (incl. safe-area/deck lift)
	function barTravel() {
		return navEl ? Math.min(140, navEl.getBoundingClientRect().height + 46) : 110;
	}

	function gestureActive() {
		return isDesktop() || $stackedScreenOpen || !$navVisible;
	}

	function onNavTouchStart(e: TouchEvent) {
		if (gestureActive()) return;
		const tch = e.touches[0];
		tsX = tch.clientX;
		tsY = tch.clientY;
		gAxis = null;
		velY = 0;
		lastY = tch.clientY;
		lastT = e.timeStamp;
		dragMoved = false;
	}

	function onNavTouchMove(e: TouchEvent) {
		if (gestureActive()) return;
		const tch = e.touches[0];
		const dx = tch.clientX - tsX;
		const dy = tch.clientY - tsY;
		if (!gAxis) {
			if (Math.abs(dx) > 6 || Math.abs(dy) > 6)
				gAxis = Math.abs(dx) > Math.abs(dy) * 1.2 ? 'h' : 'v';
			if (gAxis !== 'v') return;
			navDragging.set(true);
		}
		if (gAxis !== 'v') return;
		if (Math.abs(dy) > 4) dragMoved = true;
		const dt = e.timeStamp - lastT;
		if (dt > 0) velY = velY * 0.3 + ((tch.clientY - lastY) / dt) * 0.7;
		lastY = tch.clientY;
		lastT = e.timeStamp;
		navDragOffset.set(Math.max(0, Math.min(barTravel(), dy)));
	}

	function onNavTouchEnd() {
		if (gAxis !== 'v') {
			navDragOffset.set(0);
			navDragging.set(false);
			gAxis = null;
			return;
		}
		const dy = lastY - tsY;
		const off = $navDragOffset;
		// Fling down or dragged past ~40% of travel commits the hide
		const commit = off > 24 && (dy > barTravel() * 0.4 || velY > 0.35);
		navDragging.set(false); // restores the transition
		suppressNextClick = commit && dragMoved;
		navDragOffset.set(0); // springs back, or glides into the full hide
		if (commit) navVisible.set(false);
		gAxis = null;
	}

	function onClickCapture(e: MouseEvent) {
		if (!suppressNextClick) return;
		e.preventDefault();
		e.stopPropagation();
		suppressNextClick = false;
	}
</script>

<!-- ── Mobile Bottom Nav ─────────────────────────────────── -->
<nav
	bind:this={navEl}
	class="mobile-nav"
	class:nav-hidden={!$navVisible}
	class:dragging={$navDragging}
	class:covered
	style:--nav-drag="{$navDragOffset}px"
	aria-label="{$t('navbar.mainNav')}"
	onclickcapture={onClickCapture}
	ontouchstart={onNavTouchStart}
	ontouchmove={onNavTouchMove}
	ontouchend={onNavTouchEnd}
>
	{#each $orderedTabs as tab, i (tab.id)}
		{@const active = tabIdx === i}

		<a
			href={tab.href}
			class="nav-item"
			class:active
			aria-current={active ? 'page' : undefined}
		>
			<span class="nav-icon">
				<span class="nav-pill"></span>
				<tab.icon size={21} strokeWidth={active ? 2.2 : 1.8} />
			</span>
			<span class="nav-label">{$t(`navbar.${tab.id}`)}</span>
		</a>
	{/each}
</nav>

<!-- ── Desktop Sidebar ───────────────────────────────────── -->
<aside class="sidebar" class:covered aria-label="{$t('navbar.mainNav')}">
	<div class="sidebar-inner">
		<div class="sidebar-top">
			<a href="/" class="brand" aria-label="Berga">
				<img src="/icons/berga_64.png" alt="" class="brand-logo" draggable="false" />
				<span class="brand-name">Berga</span>
			</a>
			{#if $splitTab}
				<button
					class="sidebar-collapse"
					use:ripple
					onclick={invertSplit}
					title={$t('navbar.splitInvert')}
					aria-label={$t('navbar.splitInvert')}
				>
					<ArrowLeftRight size={18} strokeWidth={1.8} />
				</button>
				<button
					class="sidebar-collapse"
					use:ripple
					onclick={closeSplit}
					title={$t('navbar.splitClose')}
					aria-label={$t('navbar.splitClose')}
				>
					<X size={18} strokeWidth={1.8} />
				</button>
			{/if}
			<button
				class="sidebar-collapse"
				use:ripple
				onclick={toggleSidebar}
				title={$t('settings.collapseSidebar')}
				aria-label={$t('settings.collapseSidebar')}
			>
				<PanelLeftClose size={18} strokeWidth={1.8} />
			</button>
		</div>
		<nav class="sidebar-nav">
			{#each $orderedTabs as tab, i (tab.id)}
				{@const active = tabIdx === i}
				{@const pinned = $splitTab === tab.id}
				<a
					href={tab.href}
					class="sidebar-item"
					class:active
					class:pinned
					aria-current={active ? 'page' : undefined}
					title={$t(`navbar.${tab.id}`)}
					draggable="true"
					onclick={e => navClick(e, tab)}
					oncontextmenu={e => navCtx(e, tab)}
					ondragstart={e => navDragStart(e, tab)}
					ondragend={navDragEnd}
				>
					<tab.icon size={20} strokeWidth={active ? 2.2 : 1.6} />
					<span class="s-label">{$t(`navbar.${tab.id}`)}</span>
				</a>
			{/each}
		</nav>
		<nav class="sidebar-bottom">
			<button
				class="sidebar-item"
				class:active={$page.url.pathname.startsWith('/settings')}
				use:ripple
				onclick={() => goto('/settings')}
				title={$t('settings.title')}
				aria-label={$t('settings.title')}
			>
				<Settings size={20} strokeWidth={$page.url.pathname.startsWith('/settings') ? 2.2 : 1.6} />
				<span class="s-label">{$t('settings.title')}</span>
			</button>
		</nav>
	</div>
</aside>

<!-- ── Desktop Floating Dock (left, vertical, icon-only) ─────────────────── -->
<div
	class="dock-wrap"
	class:expanded
	role="presentation"
	onmouseenter={dockEnter}
	onmouseleave={dockLeave}
>
	<nav class="dock" aria-label="{$t('navbar.mainNav')}">
		{#each $orderedTabs as tab, i (tab.id)}
			{@const active = tabIdx === i}
			{@const pinned = $splitTab === tab.id}
			<a
				href={tab.href}
				class="dock-item"
				class:active
				class:pinned
				aria-current={active ? 'page' : undefined}
				title={expanded ? undefined : $t(`navbar.${tab.id}`)}
				draggable="true"
				onclick={e => navClick(e, tab)}
				oncontextmenu={e => navCtx(e, tab)}
				ondragstart={e => navDragStart(e, tab)}
				ondragend={navDragEnd}
			>
				<span class="dock-icon">
					<span class="nav-pill"></span>
					<tab.icon size={24} strokeWidth={active ? 2.2 : 1.7} />
				</span>
				<span class="dock-label">{$t(`navbar.${tab.id}`)}</span>
			</a>
		{/each}

		{#if $splitTab}
			<!-- Split is alive: mini inverter/closer ride at the dock's tail -->
			<div class="dock-divider"></div>
			<button
				class="dock-item"
				use:ripple
				onclick={invertSplit}
				title={expanded ? undefined : $t('navbar.splitInvert')}
				aria-label={$t('navbar.splitInvert')}
			>
				<span class="dock-icon"><ArrowLeftRight size={22} strokeWidth={1.8} /></span>
				<span class="dock-label">{$t('navbar.splitInvert')}</span>
			</button>
			<button
				class="dock-item"
				use:ripple
				onclick={closeSplit}
				title={expanded ? undefined : $t('navbar.splitClose')}
				aria-label={$t('navbar.splitClose')}
			>
				<span class="dock-icon"><X size={22} strokeWidth={1.8} /></span>
				<span class="dock-label">{$t('navbar.splitClose')}</span>
			</button>
		{/if}
	</nav>

	<nav class="dock dock-sub" aria-label="{$t('settings.title')}">
		<button
			class="dock-item"
			class:active={settingsActive}
			use:ripple
			onclick={() => goto('/settings')}
			title={expanded ? undefined : $t('settings.title')}
			aria-label={$t('settings.title')}
		>
			<span class="dock-icon">
				<span class="nav-pill"></span>
				<Settings size={24} strokeWidth={settingsActive ? 2.2 : 1.7} />
			</span>
			<span class="dock-label">{$t('settings.title')}</span>
		</button>
	</nav>
</div>

{#if ctxMenu}
	<NavContextMenu pos={{ x: ctxMenu.x, y: ctxMenu.y }} tab={ctxMenu.tab} onClose={() => (ctxMenu = null)} />
{/if}

<!-- ── Floating expand button (desktop, sidebar collapsed) ── -->
{#if $uiSidebarCollapsed && $uiDesktopNav !== 'dock'}
	<button
		class="sidebar-expand"
		use:ripple
		onclick={toggleSidebar}
		title={$t('settings.expandSidebar')}
		aria-label={$t('settings.expandSidebar')}
	>
		<PanelLeftOpen size={18} strokeWidth={1.8} />
	</button>
{/if}

<style>
	/* ── Mobile Nav ──────────────────────────────────────── */
	.mobile-nav {
		display: flex;
		position: fixed;
		bottom: 0; left: 0; right: 0;
		z-index: 50;
		height: var(--mnav-height, 64px);
		padding: 0 8px env(safe-area-inset-bottom, 8px);
		align-items: center;
		justify-content: center;
		background: var(--nav-glass, color-mix(in oklch, var(--nav-bg, var(--color-base-100)) 58%, transparent));
		backdrop-filter: var(--glass-blur);
		-webkit-backdrop-filter: var(--glass-blur);
		border-top: 1px solid var(--glass-border);
		box-shadow: 0 -4px 20px color-mix(in oklch, black 10%, transparent);
		transform: translateY(var(--nav-drag, 0px));
		touch-action: none;
		transition: transform 320ms cubic-bezier(0.4, 0, 0.2, 1), opacity 220ms ease;
	}
	:global([data-glass="off"]) .mobile-nav {
		background: var(--nav-bg, var(--color-base-100));
	}
	:global([data-glass="off"]) .nav-item {
		color: color-mix(in oklch, var(--nav-bg-content, var(--color-base-content)) 58%, transparent);
	}
	.mobile-nav.nav-hidden,
	.mobile-nav.covered {
		transform: translateY(
			calc(100% + env(safe-area-inset-bottom, 0px) + var(--nav-drag, 0px))
		);
	}
	.mobile-nav.dragging { transition: none; }

	/* ── Floating deck variant ────────────────────────────── */
	:global([data-nav-style="deck"]) .mobile-nav {
		bottom: calc(env(safe-area-inset-bottom, 8px) + 14px);
		width: var(--deck-width, 73vw);
		left: calc(50% - var(--deck-width, 73vw) / 2);
		height: var(--deck-height, 16vw);
		padding: 0 12px;
		background: var(--nav-glass-strong, color-mix(in oklch, var(--nav-bg, var(--color-base-100)) 82%, transparent));
		border: var(--ui-border-width, 1px) solid var(--ui-border-color, var(--glass-border));
		border-radius: var(--deck-radius, var(--ui-radius-xl));
		overflow: hidden;
		box-shadow:
			0 10px 30px color-mix(in oklch, black 14%, transparent),
			0 2px 6px color-mix(in oklch, black 8%, transparent);
	}
	:global([data-nav-style="deck"]) .mobile-nav.nav-hidden,
	:global([data-nav-style="deck"]) .mobile-nav.covered {
		transform: translateY(
			calc(100% + env(safe-area-inset-bottom, 0px) + 26px + var(--nav-drag, 0px))
		);
	}

	@media (min-width: 768px) { .mobile-nav { display: none; } }

	/* ── Nav items (shared by bar + deck) ────────────────── */
	.nav-item {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: var(--mnav-label-gap, 2px);
		flex: 1;
		max-width: 80px;
		height: 100%;
		padding: 6px 4px;
		border-radius: var(--mnav-item-radius, var(--ui-radius-sm));
		text-decoration: none;
		-webkit-tap-highlight-color: transparent;
		color: color-mix(in oklch, var(--color-base-content) 58%, transparent);
		transition: color 180ms ease, background 180ms ease;
	}
	.nav-item.active {
		color: var(--color-accent);
	}

	/* Modern indicator: the icon sits above a fixed-size pill that
	   pops in accent-tinted behind the active tab's icon only. The pill
	   is a background layer — the icon always stays visible. */
	.nav-icon {
		position: relative;
		display: flex;
		align-items: center;
		justify-content: center;
		width: 52px;
		height: var(--mnav-iconbox-h, 28px);
	}
	/* Icon glyph scales with the --mnav-icon-size knob (CSS wins over the
	   size attribute set on the <svg>, which stays as SSR fallback). */
	.nav-icon :global(svg) {
		width: var(--mnav-icon-size, 21px);
		height: var(--mnav-icon-size, 21px);
	}
	.nav-pill {
		position: absolute;
		inset: 0;
		border-radius: var(--ui-radius-full);
		background: transparent;
		opacity: 0;
		transform: scale(0.5);
		transition:
			background 220ms ease,
			transform 320ms cubic-bezier(0.34, 1.56, 0.64, 1),
			opacity 200ms ease;
	}
	.nav-item.active .nav-pill {
		background: color-mix(in oklch, var(--color-accent) 16%, transparent);
		opacity: 1;
		transform: scale(1);
	}
	.nav-item.active:active .nav-pill {
		transform: scale(0.94);
	}

	/* Classic indicator: the whole item lights up (old look) */
	:global([data-nav-indicator="classic"]) .nav-item.active {
		background: color-mix(in oklch, var(--color-accent) 13%, transparent);
	}
	:global([data-nav-indicator="classic"]) .nav-pill {
		background: transparent;
		opacity: 0;
		transform: none;
	}
	:global([data-nav-style="deck"][data-nav-indicator="classic"]) .nav-item {
		border-radius: var(--ui-radius-full);
	}

	.nav-label {
		font-size: var(--mnav-label-size, 11px);
		font-weight: 500;
		letter-spacing: 0.02em;
	}
	.nav-item.active .nav-label {
		font-weight: 700;
	}
	/* Icons-only mode (settings: Mobile navbar → Labels) */
	:global(html[data-mnav-labels="off"]) .mobile-nav .nav-label {
		display: none;
	}

	@media (prefers-reduced-motion: reduce) {
		.nav-pill {
			transition: none !important;
		}
		.nav-item.active .nav-pill {
			transform: none;
		}
	}

	/* ── Desktop sidebar ───────────────────────────────── */
	.sidebar { display: none; }
	.sidebar.covered { pointer-events: none; }
	@media (min-width: 768px) {
		.sidebar {
			display: flex;
			position: fixed;
			top: 0; left: 0; bottom: 0;
			z-index: 50;
			width: 240px;
			flex-direction: column;
			background: var(--nav-bg, var(--color-base-100));
			border-right: 1px solid var(--glass-border, var(--color-base-200));
		}
		:global([data-sidebar-collapsed="on"]) .sidebar { display: none; }
		.sidebar-item {
			--sidebar-item-color: color-mix(in oklch, var(--nav-bg-content, var(--color-base-content)) 60%, transparent);
			--sidebar-item-hover-color: var(--nav-bg-content, var(--color-base-content));
			--sidebar-item-hover-bg: color-mix(in oklch, var(--nav-bg-content, var(--color-base-content)) 8%, transparent);
		}
		.sidebar-collapse {
			display: inline-flex;
			align-items: center;
			justify-content: center;
			width: 32px;
			height: 32px;
			border: 1px solid var(--ui-border-color);
			border-radius: var(--ui-radius-sm);
			background: transparent;
			color: color-mix(in oklch, var(--nav-bg-content, var(--color-base-content)) 55%, transparent);
			cursor: pointer;
			transition: border-color var(--ui-dur-1, 150ms) var(--ui-ease, ease),
				transform var(--ui-dur-1, 150ms) var(--ui-ease, ease),
				box-shadow var(--ui-dur-1, 150ms) var(--ui-ease, ease);
			-webkit-tap-highlight-color: transparent;
		}
		.sidebar-collapse:hover {
			border-color: color-mix(in oklch, var(--nav-bg-content, var(--color-base-content)) 45%, transparent);
			transform: translateY(-1px);
			box-shadow: var(--ui-shadow-1);
		}
		.sidebar-collapse:active {
			transform: translateY(0);
		}
	}
	.sidebar-top {
		display: flex;
		align-items: center;
		justify-content: space-between;
	}
	.sidebar-expand {
		display: none;
	}
	@media (min-width: 768px) {
		.sidebar-expand {
			display: inline-flex;
			align-items: center;
			justify-content: center;
			position: fixed;
			top: 14px;
			left: 14px;
			z-index: 60;
			width: 38px;
			height: 38px;
			border: 1px solid var(--glass-border, var(--color-base-200));
			border-radius: var(--ui-radius-sm);
			background: var(--nav-bg, var(--color-base-100));
			color: var(--nav-bg-content, var(--color-base-content));
			cursor: pointer;
			box-shadow: 0 2px 10px color-mix(in oklch, black 12%, transparent);
			transition: border-color var(--ui-dur-1, 150ms) var(--ui-ease, ease),
				transform var(--ui-dur-1, 150ms) var(--ui-ease, ease),
				box-shadow var(--ui-dur-1, 150ms) var(--ui-ease, ease);
		}
		.sidebar-expand:hover {
			border-color: color-mix(in oklch, var(--nav-bg-content, var(--color-base-content)) 45%, transparent);
			transform: translateY(-1px);
			box-shadow: var(--ui-shadow-1);
		}
		.sidebar-expand:active {
			transform: translateY(0);
		}
		:global(.covered) ~ .sidebar-expand { pointer-events: none; }
	}

	.sidebar-inner {
		display: flex;
		flex-direction: column;
		height: 100%;
		padding: 24px var(--sidebar-item-margin, 0.625rem) 12px;
		gap: 8px;
	}

	.brand {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 4px 2px 20px;
		text-decoration: none;
		color: var(--nav-bg-content, var(--color-base-content));
		transition: opacity 150ms ease;
	}
	.brand:hover {
		opacity: 0.8;
	}
	.brand-logo {
		width: 26px;
		height: 26px;
		border-radius: 6px;
		display: block;
		user-select: none;
	}
	.brand-name {
		font-family: var(--font-page-title);
		font-weight: 400;
		font-size: 1.15rem;
		/* Gloock's metrics ride high: match the logo's box height so the
		   em box centers optically next to it */
		line-height: 26px;
		height: 26px;
		display: flex;
		align-items: center;
	}

	.sidebar-nav {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.sidebar-bottom {
		display: flex;
		flex-direction: column;
		gap: 2px;
		margin-top: auto;
		border-top: 1px solid var(--glass-border, var(--color-base-200));
		padding-top: 8px;
	}
	:global([data-settings-icon="top"]) .sidebar-bottom { display: none; }
	.sidebar-bottom .sidebar-item {
		width: 100%;
		background: none;
		border: none;
		border-left: 3px solid transparent;
		cursor: pointer;
		font-family: inherit;
		text-align: left;
	}
	.sidebar-bottom .sidebar-item:hover {
		color: var(--sidebar-item-hover-color, var(--color-base-content));
		background: var(--sidebar-item-hover-bg, var(--color-base-200));
	}
	.sidebar-bottom .sidebar-item.active {
		color: var(--color-accent);
		background: color-mix(in oklch, var(--color-accent) 8%, transparent);
		border-left-color: var(--color-accent);
	}
	.sidebar-bottom .sidebar-item.active .s-label {
		font-weight: 700;
	}

	.sidebar-item {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: var(--sidebar-item-pad-y, 0.5rem) var(--sidebar-item-margin, 0.625rem);
		border-radius: var(--ui-radius-sm);
		border-left: 3px solid transparent;
		text-decoration: none;
		color: var(--sidebar-item-color, color-mix(in oklch, var(--color-base-content) 60%, transparent));
		position: relative;
		overflow: hidden;
		transition: color 150ms ease, background 150ms ease, border-color 150ms ease;
	}

	.sidebar-item:hover {
		color: var(--sidebar-item-hover-color, var(--color-base-content));
		background: var(--sidebar-item-hover-bg, var(--color-base-200));
	}

	/* Active State: Strong Contrast with Border and Accent */
	.sidebar-item.active {
		color: var(--color-accent);
		background: color-mix(in oklch, var(--color-accent) 8%, transparent);
		border-left-color: var(--color-accent);
	}

	/* Pinned in the split viewer: small dot on the icon's corner */
	.sidebar-item.pinned::after {
		content: '';
		position: absolute;
		top: 12px;
		right: 12px;
		width: 6px;
		height: 6px;
		border-radius: var(--ui-radius-full);
		background: var(--color-accent);
		opacity: 0.9;
	}

	.s-label {
		font-size: 14px;
		font-weight: 500;
		letter-spacing: 0.01em;
	}

	.sidebar-item.active .s-label {
		font-weight: 700;
	}

	/* ── Desktop floating dock ─────────────────────────────────────────── */
	/* Vertical icon-only rail floating on the screen's left edge; a second
	   sub-dock below it hosts settings. Sustained hover (2s) expands both
	   docks to the right, revealing tab labels over an overlay (content
	   doesn't reflow). All dimensions key off --dock-w, which is vmin-based
	   with px clamps — 720p and 4K render with identical proportions. */

	.dock-wrap {
		display: none;
	}
	@media (min-width: 768px) {
		:global([data-desktop-nav="dock"]) .dock-wrap {
			display: flex;
			position: fixed;
			top: 50%;
			left: var(--dock-inset, 12px);
			z-index: 55;
			flex-direction: column;
			align-items: flex-start;
			gap: clamp(6px, 1.4vmin, 14px);
			transform: translateY(-50%);
		}
		:global([data-desktop-nav="dock"]) .sidebar { display: none; }

		.dock {
			--dock-expand-w: calc(var(--dock-w, 72px) + clamp(9.5rem, 24vmin, 17rem));
			--dock-pad: calc(var(--dock-w, 72px) * (var(--dock-pad-pct, 10) / 100));
			--dock-item-inset: var(--dock-pad);
			--dock-item-size: calc(var(--dock-w, 72px) - var(--dock-item-inset) * 2);
			display: flex;
			flex-direction: column;
			align-items: center;
			justify-content: center;
			width: var(--dock-w, 72px);
			height: var(--dock-h, fit-content);
			padding: var(--dock-pad) 0;
			gap: calc(var(--dock-gap, clamp(3px, 0.9vmin, 7px)) * var(--dock-space, 1));
			background: var(--nav-glass-strong, color-mix(in oklch, var(--nav-bg, var(--color-base-100)) 82%, transparent));
			backdrop-filter: var(--glass-blur);
			-webkit-backdrop-filter: var(--glass-blur);
			border: var(--ui-border-width, 1px) solid var(--ui-border-color, var(--glass-border));
			border-radius: var(--dock-radius, calc(var(--dock-w, 72px) * 0.34));
			box-shadow:
				0 8px 20px color-mix(in oklch, black calc(10% * var(--dock-shadow-strength, 1)), transparent),
				0 1px 4px color-mix(in oklch, black calc(6% * var(--dock-shadow-strength, 1)), transparent);
			overflow: hidden;
			transition:
				width 300ms cubic-bezier(0.22, 1, 0.36, 1),
				box-shadow 300ms ease,
				transform 220ms var(--ui-ease, ease);
		}
		:global([data-glass="off"]) .dock {
			background: var(--nav-bg, var(--color-base-100));
		}

		.dock-wrap.expanded .dock {
			width: var(--dock-expand-w);
			box-shadow:
				0 12px 28px color-mix(in oklch, black calc(13% * var(--dock-shadow-strength, 1)), transparent),
				0 2px 8px color-mix(in oklch, black calc(6% * var(--dock-shadow-strength, 1)), transparent);
		}

		.dock-wrap.expanded .dock-item {
			width: calc(var(--dock-expand-w) - var(--dock-item-inset) * 2);
		}
		.dock-wrap.expanded .dock-item .dock-icon {
			width: var(--dock-item-size, 58px);
		}

		.dock-item {
			position: relative;
			display: flex;
			align-items: center;
			gap: calc(clamp(10px, 1.6vmin, 14px) * var(--dock-space, 1));
			width: var(--dock-item-size, 58px);
			height: var(--dock-item-size, 58px);
			flex-shrink: 0;
			padding: 0;
			border: none;
			background: transparent;
			cursor: pointer;
			justify-content: flex-start;
			/* Buttons carry UA text-align:center — labels must sit flush left */
			text-align: left;
			color: color-mix(in oklch, var(--color-base-content) 60%, transparent);
			text-decoration: none;
			border-radius: calc(var(--dock-radius, calc(var(--dock-w, 72px) * 0.34)) * 0.82);
			margin: 0 var(--dock-item-inset, 7px);
			overflow: hidden;
			transition:
				width 300ms cubic-bezier(0.22, 1, 0.36, 1),
				color 150ms ease,
				background 150ms ease;
		}
		.dock-item:hover {
			color: var(--color-base-content);
			background: color-mix(in oklch, var(--color-base-content) 8%, transparent);
		}
		.dock-item.active {
			color: var(--color-accent);
		}

		.dock-icon {
			position: relative;
			display: inline-flex;
			align-items: center;
			justify-content: center;
			width: 100%;
			height: 100%;
			flex-shrink: 0;
		}
		.dock-icon :global(svg) {
			/* Scales with the item box (not the dock), so the inner-padding
			   slider actually closes/opens the gap between icon and border.
			   0.5 keeps the default 10% pad visually identical to 0.4×dock-w. */
			width: calc(var(--dock-item-size, 58px) * 0.5);
			height: calc(var(--dock-item-size, 58px) * 0.5);
		}

		/* Active pill mirrors the mobile nav's indicator */
		.dock-item .nav-pill {
			position: absolute;
			inset: 10%;
			border-radius: var(--ui-radius-full);
			background: transparent;
			opacity: 0;
			transform: scale(0.5);
			transition:
				background 220ms ease,
				transform 320ms cubic-bezier(0.34, 1.56, 0.64, 1),
				opacity 200ms ease;
		}
		.dock-item.active .nav-pill {
			background: color-mix(in oklch, var(--color-accent) 16%, transparent);
			opacity: 1;
			transform: scale(1);
		}
		.dock-item.active:active .nav-pill {
			transform: scale(0.94);
		}

		/* Pinned in the split viewer: dot on the icon's corner */
		.dock-item.pinned::after {
			content: '';
			position: absolute;
			top: 18%;
			right: 16%;
			width: calc(var(--dock-item-size, 58px) * 0.125);
			height: calc(var(--dock-item-size, 58px) * 0.125);
			border-radius: var(--ui-radius-full);
			background: var(--color-accent);
			opacity: 0.9;
		}

		.dock-label {
			width: 0;
			min-width: 0;
			overflow: hidden;
			white-space: nowrap;
			font-size: 14px;
			font-weight: 500;
			letter-spacing: 0.01em;
			opacity: 0;
			transform: translateX(-8px);
			transition:
				opacity 220ms ease,
				transform 300ms cubic-bezier(0.22, 1, 0.36, 1);
			visibility: hidden;
		}
		.dock-item.active .dock-label {
			font-weight: 700;
		}
		.dock-wrap.expanded .dock-label {
			width: clamp(8rem, 20vmin, 14rem);
			opacity: 1;
			transform: none;
			visibility: visible;
		}
		/* Thin "|" hairline centered in the icon–label gap, revealed with the label */
		.dock-wrap.expanded .dock-label::before {
			content: '';
			display: inline-block;
			width: 1px;
			height: calc(var(--dock-item-size, 58px) * 0.22);
			background: var(--ui-border-color, var(--glass-border, var(--color-base-200)));
			border-radius: 1px;
			vertical-align: -0.08em;
			margin-left: calc(clamp(10px, 1.6vmin, 14px) * var(--dock-space, 1) / -2);
			margin-right: calc(clamp(10px, 1.6vmin, 14px) * var(--dock-space, 1) / 2);
		}

		.dock-divider {
			width: calc(var(--dock-w, 72px) * 0.5);
			height: 1px;
			flex-shrink: 0;
			background: var(--glass-border, var(--color-base-200));
			margin: 2px 0;
		}

		@media (prefers-reduced-motion: reduce) {
			.dock,
			.dock-label,
			.dock-item .nav-pill {
				transition: none !important;
			}
		}
	}

	/* ── Active indicator "none": no background on any selected tab ────── */
	:global([data-nav-indicator="none"]) .nav-item.active .nav-pill {
		background: transparent;
		opacity: 0;
		transform: none;
	}
	:global([data-nav-indicator="none"]) .dock-item.active .nav-pill {
		background: transparent;
		opacity: 0;
		transform: none;
	}
	:global([data-nav-indicator="none"]) .sidebar-item.active,
	:global([data-nav-indicator="none"]) .sidebar-bottom .sidebar-item.active {
		background: transparent;
	}
</style>