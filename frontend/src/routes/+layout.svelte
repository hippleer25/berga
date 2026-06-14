<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { Capacitor } from '@capacitor/core';
	import { StatusBar, Style } from '@capacitor/status-bar';
	import { SplashScreen } from '@capacitor/splash-screen';
	import NavBar from '$lib/components/NavBar.svelte';
	import PageTrack from '$lib/components/PageTrack.svelte';
	import LeftPanel from '$lib/components/LeftPanel.svelte';
	import { drawerOpen } from '$lib/stores/drawer';
	import { initAppearance } from '$lib/utils/appearance';
	import "../app.css";

	const { children } = $props();

	const TAB_ROUTES = ['/followers', '/home', '/events', '/mota'];
	const isTab = $derived(
		TAB_ROUTES.some(r =>
			$page.url.pathname === r || $page.url.pathname.startsWith(r + '/')
		)
	);

	onMount(async () => {
		if (Capacitor.isNativePlatform()) {
			await StatusBar.setBackgroundColor({ color: '#000000' });
			await StatusBar.setStyle({ style: Style.Light });
		}
		initAppearance();

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

{#if isTab}
    <!-- Drawer fora do PageTrack para não sofrer com o stacking context do transform de swipe -->
    <LeftPanel bind:open={$drawerOpen} />
    <NavBar />
    <PageTrack />
{:else}
    {@render children()}
{/if}