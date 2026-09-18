<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { afterNavigate } from '$app/navigation';
	import { Capacitor } from '@capacitor/core';
	import { StatusBar, Style } from '@capacitor/status-bar';
	import { SplashScreen } from '@capacitor/splash-screen';
	import { registerSW } from 'virtual:pwa-register';
	import { t } from 'svelte-i18n';
	import NavBar from '$lib/components/NavBar.svelte';
	import PageTrack from '$lib/components/PageTrack.svelte';
	import LeftPanel from '$lib/components/LeftPanel.svelte';
	import SplitView from '$lib/components/SplitView.svelte';
	import SplitDropZones from '$lib/components/SplitDropZones.svelte';
	import { drawerOpen } from '$lib/stores/drawer';
	import { initAppearance } from '$lib/utils/appearance';
	import { initUiPrefs } from '$lib/stores/uiPrefs';
	import { sessionChecked, sessionLoggedIn } from '$lib/stores/session';
	import { stackedScreenOpen } from '$lib/stores/swipe';
	import { splitTab, splitSide } from '$lib/stores/splitView';
	import { resetScreenStack } from '$lib/utils/screenStack';
	import { orderedTabs } from '$lib/config/tabs';
	import "../app.css";

	const { children } = $props();

	const AUTH_ROUTES = ['/', '/login', '/signup'];
	const isAuthRoute = $derived(AUTH_ROUTES.includes($page.url.pathname));
	// Optimistic: render the tab layer before the session check resolves,
	// hide it only once the backend confirms the user is logged out.
	const showTabsLayer = $derived(
		!isAuthRoute && (!$sessionChecked || $sessionLoggedIn)
	);

	// Leaving the stacked-screen world resets the unwind base.
	afterNavigate(({ to }) => {
		if (!to) return;
		const path = to.url.pathname;
		const isTab = $orderedTabs.some(
			t => path === t.href || path.startsWith(t.href + '/')
		);
		if (isTab || AUTH_ROUTES.includes(path)) resetScreenStack();
	});

	// Service worker registers silently and auto-updates in the background
	// (registerType: 'autoUpdate'). The hourly check keeps long-running
	// sessions in sync with new deploys without any prompt.
	registerSW({
		onRegisteredSW(_url: string, registration?: ServiceWorkerRegistration) {
			if (registration) {
				setInterval(() => registration.update().catch(() => {}), 60 * 60 * 1000);
			}
		},
		onRegisterError(error: unknown) {
			console.error('[pwa] SW registration error:', error);
		},
	});

	onMount(async () => {
		if (Capacitor.isNativePlatform()) {
			await StatusBar.setBackgroundColor({ color: '#000000' });
			await StatusBar.setStyle({ style: Style.Light });
		}
		initAppearance();
		initUiPrefs();

		if (Capacitor.isNativePlatform()) {
			requestAnimationFrame(() => {
				setTimeout(async () => {
					try {
						await SplashScreen.hide({ fadeOutDuration: 300 });
					} catch { /* splash already hidden */ }
				}, 100);
			});
		}

		setTimeout(async () => {
			try {
				await SplashScreen.hide({ fadeOutDuration: 300 });
			} catch { /* already hidden */ }
		}, 5000);
	});
</script>

<svelte:head>
	<title>Berga</title>
  <link rel="icon" href="/icons/berga_32.png" />
</svelte:head>

{#if showTabsLayer}
    <!-- Tab layer: always mounted beneath stacked screens so swipe-to-close
         reveals the live tab. Drawer outside PageTrack to avoid its
         transform stacking context. -->
    <div class="tabs-layer" class:stacked={$stackedScreenOpen} class:split={$splitTab !== null}>
        <LeftPanel bind:open={$drawerOpen} />
        <NavBar />
        <div class="page-panes">
            {#if $splitTab && $splitSide === 'left'}
                <div class="pane pane-split"><SplitView /></div>
            {/if}
            <div class="pane pane-main"><PageTrack /></div>
            {#if $splitTab && $splitSide === 'right'}
                <div class="pane pane-split"><SplitView /></div>
            {/if}
        </div>
        <SplitDropZones />
    </div>
{/if}
{@render children()}

<style>
	.tabs-layer.stacked {
		pointer-events: none;
	}

	/* Split viewer (desktop only): main pane + pinned pane side by side.
	   Panes get their own scroll; the stacked-screen rules below still
	   hide the whole layer while a screen is open. */
	.page-panes {
		display: block;
	}
	@media (min-width: 768px) {
		.tabs-layer.split .page-panes {
			display: flex;
			position: fixed;
			inset: 0;
			left: var(--sidebar-w, 240px);
		}
		.tabs-layer.split .pane {
			flex: 1 1 50%;
			min-width: 0;
			height: 100%;
			overflow-y: auto;
			overflow-x: hidden;
			scrollbar-width: none;
			background: var(--color-base-100);
		}
		.tabs-layer.split .pane::-webkit-scrollbar {
			width: 0;
			height: 0;
			display: none;
		}
		/* Tab content assumes full-viewport width (sidebar-aware centering);
		   inside a 50% pane, re-center within the pane instead. */
		.tabs-layer.split :global(.main-content) {
			padding-left: 16px !important;
			padding-right: 16px !important;
			margin-left: auto !important;
			margin-right: auto !important;
		}
	}

	/* Desktop: stacked screens are normal pages with the sidebar visible,
	   so the tab layer steps aside entirely. */
	@media (min-width: 768px) {
		.tabs-layer.stacked {
			display: none;
		}
	}
</style>