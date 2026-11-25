<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { afterNavigate, goto } from '$app/navigation';
	import { Capacitor } from '@capacitor/core';
	import { SplashScreen } from '@capacitor/splash-screen';
	import { registerSW } from 'virtual:pwa-register';
	import { t } from 'svelte-i18n';
	import NavBar from '$lib/components/NavBar.svelte';
	import PageTrack from '$lib/components/PageTrack.svelte';
	import TopBar from '$lib/components/TopBar.svelte';
	import LeftPanel from '$lib/components/LeftPanel.svelte';
	import ColumnPane from '$lib/components/ColumnPane.svelte';
	import ColumnGutter from '$lib/components/ColumnGutter.svelte';
	import ColumnDropZones from '$lib/components/ColumnDropZones.svelte';
	import { drawerOpen } from '$lib/stores/drawer';
	import { initAppearance } from '$lib/utils/appearance';
	import { initUiPrefs } from '$lib/stores/uiPrefs';
	import { initDesignMode } from '$lib/stores/designMode';
	import { sessionChecked, sessionLoggedIn } from '$lib/stores/session';
	import { stackedScreenOpen } from '$lib/stores/swipe';
	import { columnsLayout, gridTemplate, type TabId } from '$lib/stores/columns';
	import { resetScreenStack, consumePendingReconcile } from '$lib/utils/screenStack';
	import { orderedTabs } from '$lib/config/tabs';
	import "../app.css";

	const { children } = $props();

	// Dynamic desktop columns (1–3). The main column follows the URL-active
	// tab via PageTrack; the rest pin a tab screen each.
	const multiPane = $derived($columnsLayout.panes.length > 1);
	const colTemplate = $derived(
		multiPane ? gridTemplate($columnsLayout.panes, $columnsLayout.widths) : '1fr'
	);

	const AUTH_ROUTES = ['/', '/login', '/signup'];
	const isAuthRoute = $derived(AUTH_ROUTES.includes($page.url.pathname));
	// Optimistic: render the tab layer before the session check resolves,
	// hide it only once the backend confirms the user is logged out.
	const showTabsLayer = $derived(
		!isAuthRoute && (!$sessionChecked || $sessionLoggedIn)
	);

	// Leaving the stacked-screen world resets the unwind base.
	afterNavigate(({ to, type }) => {
		if (!to) return;
		const path = to.url.pathname;
		const isTab = $orderedTabs.some(
			t => path === t.href || path.startsWith(t.href + '/')
		);
		// A screen-stack unwind must land on the tab beneath the stack. Stale
		// history (system-back pops keep forward entries; WebView restore
		// after minimize can reshape the session) can make history.go(-steps)
		// overshoot into old entries — including ones still inside the stack,
		// which leaves the shell mounted but invisible. Force the base tab
		// whenever the landing misses it. Only a popstate landing can be a
		// missed unwind — push/goto navigations are always intentional and
		// must never be hijacked by a stale armed value.
		const base = consumePendingReconcile();
		if (base && type === 'popstate' && path !== base) {
			goto(base, { replaceState: true });
			return;
		}
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
		initAppearance();
		initUiPrefs();
		initDesignMode();

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
    <div class="tabs-layer" class:stacked={$stackedScreenOpen} class:columns={multiPane}>
        <LeftPanel bind:open={$drawerOpen} />
        <NavBar />
        <div class="page-panes" style:--col-template={multiPane ? colTemplate : undefined}>
            {#if multiPane}
                {#each $columnsLayout.panes as pane, i (pane.id)}
                    {#if i > 0}<div class="pane-gap" aria-hidden="true"></div>{/if}
                    <div class="pane" class:pane-main={pane.content === 'main'}>
                        {#if pane.content === 'main'}
                            <TopBar />
                            <PageTrack />
                        {:else}
                            <ColumnPane tab={pane.content as TabId} paneKey={`col-${pane.id}`} />
                        {/if}
                    </div>
                {/each}
            {:else}
                <div class="pane pane-main">
                    <TopBar />
                    <PageTrack />
                </div>
            {/if}
        </div>
        <ColumnGutter />
        <ColumnDropZones />
    </div>
{/if}
{@render children()}

<style>
	.tabs-layer.stacked {
		pointer-events: none;
	}

	/* Dynamic columns (desktop only): a grid of 1–3 panes side by side.
	   Panes get their own scroll; the stacked-screen rules below still
	   hide the whole layer while a screen is open. Single-column keeps the
	   legacy block flow. */
	.page-panes {
		display: block;
	}
	@media (min-width: 768px) {
		.tabs-layer.columns .page-panes {
			display: grid;
			position: fixed;
			inset: 0;
			left: var(--sidebar-w, 240px);
			grid-template-columns: var(--col-template, 1fr);
		}
		.tabs-layer.columns .pane {
			min-width: 0;
			height: 100%;
			overflow-y: auto;
			overflow-x: hidden;
			scrollbar-width: none;
			background: var(--color-base-100);
		}
		.tabs-layer.columns .pane::-webkit-scrollbar {
			width: 0;
			height: 0;
			display: none;
		}
		/* Fixed track between panes (mirrors GUTTER_PX in the template). */
		.tabs-layer.columns .pane-gap {
			pointer-events: none;
		}
		/* Tab content assumes full-viewport width (sidebar-aware centering);
		   inside a column, re-center within the pane instead. */
		.tabs-layer.columns :global(.main-content) {
			padding-left: 16px !important;
			padding-right: 16px !important;
			margin-left: auto !important;
			margin-right: auto !important;
		}
	}
	/* Mobile ignores the column layout: only the main (route-driven) pane shows. */
	@media (max-width: 767px) {
		.tabs-layer.columns .pane:not(.pane-main) {
			display: none;
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