<script lang="ts">
	import { browser } from '$app/environment';
	import HomeFilterBar from '$lib/components/filtering/HomeFilterBar.svelte';
	import SearchInput from '$lib/components/filtering/SearchInput.svelte';
	import { uiTopBar } from '$lib/stores/uiPrefs';
	import { activeTabId, type TabId } from '$lib/config/tabs';
	import { stackedScreenOpen } from '$lib/stores/swipe';

	// Adaptive content: each tab contributes the controls it owns
	// (home → mode pill + filter chips; events → search field).
	// Tabs without bar content (mota, followers) render nothing.
	const tabId = $derived<TabId>($activeTabId);
	const hasContent = $derived(tabId === 'home' || tabId === 'events');
	const visible = $derived($uiTopBar && !$stackedScreenOpen && hasContent);

	// The tab layer reserves the bar's height while it is rendered —
	// PageTrack sizes its mobile scroll containers with `--topbar-h`.
	const TOPBAR_H = '44px';
	$effect(() => {
		if (!browser) return;
		if (visible) {
			document.documentElement.style.setProperty('--topbar-h', TOPBAR_H);
		} else {
			document.documentElement.style.removeProperty('--topbar-h');
		}
		return () => {
			if (browser) document.documentElement.style.removeProperty('--topbar-h');
		};
	});
</script>

{#if visible}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="top-bar">
		<div class="top-bar-inner">
			{#if tabId === 'home'}
				<HomeFilterBar variant="bar" />
			{:else if tabId === 'events'}
				<SearchInput compact />
			{/if}
		</div>
	</div>
{/if}

<style>
	/* ── Slim chrome bar, always visible at the top of the tab layer ──
	   Background follows the navbar palette (--nav-bg / --nav-bg-content). */
	.top-bar {
		position: sticky; /* desktop: window scroll — mobile: in-flow above panels */
		top: 0;
		z-index: 30;
		isolation: isolate;
		background: var(--nav-bg, var(--color-base-100));
		color: var(--nav-bg-content, var(--color-base-content));
		/* Chrome text/icons read against the navbar palette */
		--color-base-content: var(--nav-bg-content, var(--color-base-content));
		border-bottom: 1px solid var(--ui-border-color, color-mix(in oklch, var(--color-base-content) 14%, transparent));
	}

	.top-bar-inner {
		display: flex;
		align-items: center;
		min-height: 44px;
		max-width: 42rem;
		margin: 0 auto;
		padding: 4px 16px;
	}

	@media (min-width: 768px) {
		.top-bar-inner {
			padding: 4px 0;
			margin-left: max(var(--sidebar-w, 240px), calc(50vw - 21rem));
			margin-right: auto;
		}
		/* Split viewer: re-center within the 50% pane (same contract as tabs) */
		:global(.tabs-layer.split) .top-bar-inner {
			margin-left: auto !important;
			margin-right: auto !important;
			max-width: none;
			padding: 4px 16px;
		}
	}
</style>
