<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { Capacitor } from '@capacitor/core';
	import { StatusBar, Style } from '@capacitor/status-bar';
	import { SplashScreen } from '@capacitor/splash-screen';
	import { useRegisterSW } from 'virtual:pwa-register/svelte';
	import { t } from 'svelte-i18n';
	import NavBar from '$lib/components/NavBar.svelte';
	import PageTrack from '$lib/components/PageTrack.svelte';
	import LeftPanel from '$lib/components/LeftPanel.svelte';
	import { drawerOpen } from '$lib/stores/drawer';
	import { initAppearance } from '$lib/utils/appearance';
	import { RefreshCw, X } from '@lucide/svelte';
	import "../app.css";

	const { children } = $props();

	const TAB_ROUTES = ['/followers', '/home', '/events', '/mota'];
	const isTab = $derived(
		TAB_ROUTES.some(r =>
			$page.url.pathname === r || $page.url.pathname.startsWith(r + '/')
		)
	);

	const {
		needRefresh,
		updateServiceWorker,
	} = useRegisterSW({
		onRegisteredSW(_url: string, registration?: ServiceWorkerRegistration) {
			if (registration) {
				setInterval(() => registration.update().catch(() => {}), 60 * 60 * 1000);
			}
		},
		onRegisterError(error: unknown) {
			console.error('[pwa] SW registration error:', error);
		},
	});

	function dismissUpdate() {
		needRefresh.set(false);
	}
	function applyUpdate() {
		updateServiceWorker(true);
	}

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

{#if $needRefresh}
	<div class="pwa-update-toast" role="alert" aria-live="polite">
		<div class="pwa-update-card">
			<span class="pwa-update-text">{$t('pwa.updateAvailable')}</span>
			<div class="pwa-update-actions">
				<button class="pwa-update-btn pwa-reload" onclick={applyUpdate} aria-label={$t('pwa.reload')}>
					<RefreshCw size={16} />
					<span>{$t('pwa.reload')}</span>
				</button>
				<button class="pwa-update-btn pwa-dismiss" onclick={dismissUpdate} aria-label={$t('pwa.dismiss')}>
					<X size={16} />
				</button>
			</div>
		</div>
	</div>
{/if}

<style>
	.pwa-update-toast {
		position: fixed;
		left: 50%;
		bottom: calc(env(safe-area-inset-bottom, 0px) + 1rem);
		transform: translateX(-50%);
		z-index: 9999;
		width: min(92vw, 28rem);
		pointer-events: auto;
		animation: pwa-toast-in 0.22s ease-out;
	}

	.pwa-update-card {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.75rem;
		padding: 0.625rem 0.875rem;
		border-radius: 0.75rem;
		background: color-mix(in oklch, var(--color-base-100, #fff) 92%, transparent);
		border: 1px solid color-mix(in oklch, var(--color-accent, #888) 35%, transparent);
		box-shadow: 0 6px 24px rgba(0, 0, 0, 0.28);
		backdrop-filter: blur(8px);
	}

	.pwa-update-text {
		font-size: 0.875rem;
		line-height: 1.2;
		color: var(--color-base-content, #111);
		flex: 1 1 auto;
		min-width: 0;
	}

	.pwa-update-actions {
		display: flex;
		align-items: center;
		gap: 0.375rem;
		flex-shrink: 0;
	}

	.pwa-update-btn {
		display: inline-flex;
		align-items: center;
		gap: 0.375rem;
		border: none;
		border-radius: 0.5rem;
		padding: 0.4rem 0.6rem;
		font-size: 0.8125rem;
		font-weight: 600;
		cursor: pointer;
		transition: background 0.15s ease, opacity 0.15s ease;
	}

	.pwa-reload {
		background: var(--color-accent, #888);
		color: var(--color-accent-content, #fff);
	}
	.pwa-reload:hover { filter: brightness(1.08); }

	.pwa-dismiss {
		background: transparent;
		color: var(--color-base-content, #111);
		opacity: 0.6;
	}
	.pwa-dismiss:hover { opacity: 1; background: color-mix(in oklch, var(--color-base-content, #111) 8%, transparent); }

	@keyframes pwa-toast-in {
		from { opacity: 0; transform: translate(-50%, 0.6rem); }
		to   { opacity: 1; transform: translate(-50%, 0); }
	}
</style>