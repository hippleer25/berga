<script lang="ts">
    import { onMount, tick } from 'svelte';
    import { goto } from '$app/navigation';
    import { Search, Rss } from '@lucide/svelte';
    import LeftPanel from './LeftPanel.svelte';
    import { drawerOpen } from '$lib/stores/drawer';
    import { t } from 'svelte-i18n';

    interface Props {
        showSubscriptionsButton?: boolean;
        showSearchButton?: boolean;
    }

    let {
        showSubscriptionsButton = true,
        showSearchButton = true
    }: Props = $props();

    // ── Scroll visibility ────────────────────────────────
    let topBarVisible = $state(true);
    let lastScrollY = 0;

    onMount(() => {
        const handleScroll = () => {
            const y = window.scrollY;
            if (y < 10)               topBarVisible = true;
            else if (y < lastScrollY) topBarVisible = true;
            else if (y > lastScrollY) topBarVisible = false;
            lastScrollY = y;
        };
        window.addEventListener('scroll', handleScroll, { passive: true });
        return () => window.removeEventListener('scroll', handleScroll);
    });

    // ── Search ───────────────────────────────────────────
    let searchExpanded = $state(false);
    let searchQuery    = $state('');
    let inputEl: HTMLInputElement | undefined;

    async function openSearch() {
        searchExpanded = true;
        await tick();
        inputEl?.focus();
    }

    function closeSearch() {
        searchExpanded = false;
        searchQuery    = '';
    }

    function handleSearchKey(e: KeyboardEvent) {
        if (e.key === 'Enter' && searchQuery.trim()) {
            goto(`/s/${encodeURIComponent(searchQuery.trim())}`);
            closeSearch();
        }
        if (e.key === 'Escape') closeSearch();
    }

    // Close search on outside click
    function handleWindowClick(e: MouseEvent) {
        if (!searchExpanded) return;
        if (!(e.target as HTMLElement).closest('.search-pill')) closeSearch();
    }
</script>

<svelte:window onclick={handleWindowClick} />

<!-- ── Top bar ─────────────────────────────────────────── -->
<div class="top-bar" class:top-bar--hidden={!topBarVisible}>
    <div class="top-bar-inner">

        <!-- Left: RSS / Subscriptions outlined button (only if allowed) -->
        {#if showSubscriptionsButton}
            <button
                class="topbar-btn"
                onclick={(e) => { e.stopPropagation(); $drawerOpen = true; }}
                aria-label="{$t('topbar.subscriptions')}"
            >
                <Rss size={16} strokeWidth={2} />
            </button>
        {:else}
            <!-- Empty spacer to keep layout balanced when search button is present -->
            <div style="width: 36px;"></div>
        {/if}

        <!-- Right: search icon button (only if allowed) -->
        {#if showSearchButton}
            {#if !searchExpanded}
                <button
                    class="topbar-btn"
                    onclick={(e) => { e.stopPropagation(); openSearch(); }}
                    aria-label="{$t('topbar.search')}"
                >
                    <Search size={16} strokeWidth={2} />
                </button>
            {/if}
        {:else}
            <!-- Empty spacer to keep layout balanced when subscriptions button is present -->
            <div style="width: 36px;"></div>
        {/if}

    </div>

    <!-- Full-width search overlay (only shown when search is expanded) -->
    {#if showSearchButton && searchExpanded}
        <div
            class="search-overlay"
            onclick={(e) => e.stopPropagation()}
            style="background: color-mix(in oklch, var(--color-base-100) 82%, transparent); backdrop-filter: blur(20px);"
        >
            <div class="search-overlay-inner">
                <div class="search-input-wrapper">
                    <input
                        bind:this={inputEl}
                        bind:value={searchQuery}
                        onkeydown={handleSearchKey}
                        type="text"
                        placeholder="{$t('topbar.searchPlaceholder')}"
                        class="input input-bordered w-full h-12 pr-10 border-primary shadow-accent rounded-2xl border-[1.5px] focus:outline-none focus:border-primary bg-base-200 backdrop-blur-sm"
                        autocomplete="off"
                        spellcheck="false"
                    />
                    <span class="search-icon-right">
                        <Search size={18} />
                    </span>
                </div>
            </div>
        </div>
    {/if}
</div>

<!-- ── Subscriptions left panel (only mounted if subscriptions button is allowed) ───────────────────────── -->
{#if showSubscriptionsButton}
    <LeftPanel bind:open={$drawerOpen} />
{/if}

<style>
    /* ── Top bar ──────────────────────────────────────── */
    .top-bar {
        position: sticky;
        top: 0;
        z-index: 30;
        isolation: isolate;
        transform: translateY(0);
        transition: transform 320ms cubic-bezier(0.4, 0, 0.2, 1);
        background: color-mix(in oklch, var(--color-base-100) 82%, transparent);
        backdrop-filter: blur(20px) saturate(165%);
        -webkit-backdrop-filter: blur(20px) saturate(165%);
    }
    .top-bar--hidden {
        transform: translateY(-110%);
    }

    .top-bar-inner {
        max-width: 42rem;
        margin: 0 auto;
        padding: 10px 16px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }

    @media (min-width: 768px) {
        .top-bar-inner {
            margin-left: calc(50vw - 21rem - 220px);
            margin-right: 0;
        }
    }

    /* ── Outlined top-bar buttons ────────────────────── */
    .topbar-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 36px;
        height: 36px;
        border-radius: 10px;
        border: 1.5px solid var(--color-primary);
        background: var(--color-base-100);
        color: var(--color-base-content);
        cursor: pointer;
        flex-shrink: 0;
        transition:
            border-color 150ms ease,
            background   150ms ease,
            color        150ms ease,
            box-shadow   150ms ease;
    }
    .topbar-btn:hover {
        border-color: var(--color-primary);
        background: var(--color-base-200);
        color: var(--color-primary);
        box-shadow: var(--color-base-200);
    }
    .topbar-btn:active {
        background: color-mix(in oklch, var(--color-primary) 16%, var(--color-base-200));
    }

    /* ── Full-width search overlay ───────────────────── */
    .search-overlay {
        position: absolute;
        inset: 0;
        z-index: 10;
        display: flex;
        align-items: center;
        animation: overlay-expand 260ms cubic-bezier(0.4, 0, 0.2, 1) both;
    }

    .search-overlay-inner {
        position: relative;
        display: flex;
        align-items: center;
        width: 100%;
        max-width: 42rem;
        margin: 0 auto;
        padding: 0 16px;
    }

    @media (min-width: 768px) {
        .search-overlay-inner {
            margin-left: calc(50vw - 21rem - 220px);
            margin-right: 0;
        }
    }

    .search-input-wrapper {
        position: relative;
        width: 100%;
    }

    .search-icon-right {
        position: absolute;
        right: 12px;
        top: 50%;
        transform: translateY(-50%);
        color: var(--color-primary);
        pointer-events: none;
        display: flex;
        align-items: center;
        z-index: 10;
    }

    @keyframes overlay-expand {
        from {
            clip-path: inset(0 0 0 100%);
            opacity: 0.5;
        }
        to {
            clip-path: inset(0 0 0 0%);
            opacity: 1;
        }
    }
</style>