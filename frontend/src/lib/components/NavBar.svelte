<script lang="ts">
	import { t } from 'svelte-i18n';
	import { goto } from '$app/navigation';
	import PanelLeftClose from '@lucide/svelte/icons/panel-left-close';
	import PanelLeftOpen from '@lucide/svelte/icons/panel-left-open';
	import ArrowLeftRight from '@lucide/svelte/icons/arrow-left-right';
	import X from '@lucide/svelte/icons/x';
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
		uiSidebarCollapsed
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
		e.preventDefault();
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
			<div class="brand"></div>
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
	</div>
</aside>

{#if ctxMenu}
	<NavContextMenu pos={{ x: ctxMenu.x, y: ctxMenu.y }} tab={ctxMenu.tab} onClose={() => (ctxMenu = null)} />
{/if}

<!-- ── Floating expand button (desktop, sidebar collapsed) ── -->
{#if $uiSidebarCollapsed}
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
		height: 64px;
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
		gap: 2px;
		flex: 1;
		max-width: 80px;
		height: 100%;
		padding: 6px 4px;
		border-radius: var(--ui-radius-sm);
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
		height: 28px;
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
		font-size: 11px;
		font-weight: 500;
		letter-spacing: 0.02em;
	}
	.nav-item.active .nav-label {
		font-weight: 700;
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
			border: none;
			border-radius: var(--ui-radius-sm);
			background: transparent;
			color: color-mix(in oklch, var(--nav-bg-content, var(--color-base-content)) 55%, transparent);
			cursor: pointer;
			transition: color 150ms ease, background 150ms ease;
			-webkit-tap-highlight-color: transparent;
		}
		.sidebar-collapse:hover {
			color: var(--nav-bg-content, var(--color-base-content));
			background: color-mix(in oklch, var(--nav-bg-content, var(--color-base-content)) 10%, transparent);
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
			transition: background 150ms ease;
		}
		.sidebar-expand:hover {
			background: color-mix(in oklch, var(--nav-bg-content, var(--color-base-content)) 8%, var(--nav-bg, var(--color-base-100)));
		}
		:global(.covered) ~ .sidebar-expand { pointer-events: none; }
	}

	.sidebar-inner {
		display: flex;
		flex-direction: column;
		height: 100%;
		padding: 24px 16px 32px;
		gap: 8px;
	}

	.brand { padding: 4px 8px 20px; }

	.sidebar-nav {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.sidebar-item {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 10px 16px;
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
</style>