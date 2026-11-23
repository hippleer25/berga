<script lang="ts">
 import { onMount } from 'svelte';
    import EventCard from '$lib/components/EventCard.svelte';
 import { t } from 'svelte-i18n';
  import { get } from 'svelte/store';
  import { apiFetch } from '$lib/api';
    import { activeTabIdx, stackedScreenOpen } from '$lib/stores/swipe';
    import { orderedTabs } from '$lib/config/tabs';
  import SearchInput from '$lib/components/filtering/SearchInput.svelte';
  import { uiTopBar } from '$lib/stores/uiPrefs';

let events = $state<any[]>([]);
    let loading = $state(true);
    let error   = $state('');
    /* Accordion: at most one cluster expanded at a time (stable cluster_hash key). */
    let openCluster = $state<string | null>(null);

    function toggleCluster(hash: string | undefined, i: number) {
        const key = hash ?? String(i);
        openCluster = openCluster === key ? null : key;
    }

    function isOpen(event: any, i: number): boolean {
        return openCluster === (event.cluster_hash ?? String(i));
    }

    // PageTrack keeps this tab mounted across switches, so collapse the
    // expanded cluster whenever the user leaves the screen (tab switch
    // or a stacked screen covering the tab layer).
    $effect(() => {
        const activeId = $orderedTabs[$activeTabIdx]?.id;
        if (activeId === 'events' && !$stackedScreenOpen) return;
        openCluster = null;
    });

onMount(async () => {
	try {
            const res = await apiFetch('/api/feed/events', { credentials: 'include' });
            if (res.status === 401) { window.location.replace('/'); return; }
            if (!res.ok) throw new Error(`${get(t)('eventstab.loadError')} (${res.status})`);
            const data = await res.json();
            events = data.events ?? [];
        } catch (err: any) {
            error = err.message || get(t)('eventstab.loadError');
        }

        loading = false;
});
</script>

<div class="page-root">
    <div class="main-content">

        <!-- ── Header & Search (hidden while the top bar hosts it) ── -->
        {#if !$uiTopBar}
            <header class="page-header">
                <SearchInput />
            </header>
        {:else}
            <div class="topbar-gap" aria-hidden="true"></div>
        {/if}

        <!-- ── Trending Events Section ──────────────────── -->
        <section class="events-section">
            <h2 class="section-title sr-only">{$t('searchtab.trending', { default: 'Trending Clusters' })}</h2>

{#if loading}
  <div class="skeleton-list" aria-hidden="true">
    {#each Array.from({ length: 5 }) as _, i}
    <div class="sk-event" style="animation-delay: {i * 0.1}s">
      <div class="sk-bar sk-title" style="width: {80 + Math.random() * 20 | 0}%"></div>
      <div class="sk-bar sk-title" style="width: {50 + Math.random() * 25 | 0}%"></div>
      <div class="sk-meta">
        <div class="sk-bar" style="width: 48px; height: 10px;"></div>
        <div class="sk-pub-row">
          <div class="sk-circle"></div>
          <div class="sk-circle"></div>
          <div class="sk-circle"></div>
        </div>
      </div>
    </div>
    {/each}
  </div>
            {:else if error}
                <div class="state-error">{error}</div>
            {:else if events.length === 0}
                <p class="state-empty">{$t('eventstab.emptyTitle')}</p>
            {:else}
                <div class="events-list">
                    {#each events as event, i (event.cluster_hash ?? i)}
                        <EventCard {event} rank={i + 1} open={isOpen(event, i)} onToggle={() => toggleCluster(event.cluster_hash, i)} />
                    {/each}
                </div>
            {/if}
        </section>

    </div>
</div>

<style>
/* ── Centralizer Logic (Idêntico ao HomeTab) ─────────────── */
    .main-content {
        max-width: 42rem;
        margin: 0 auto;
        padding: 0 16px;
    }
    @media (min-width: 768px) {
        .main-content {
            padding: 0;
            margin-left: max(var(--sidebar-w, 240px), calc(50vw - 21rem));
            margin-right: auto;
        }
    }

    /* ── Header ────────────────────────────────────────── */
    .page-header {
        padding: 24px 0 0;
    }

    /* When the top bar hosts the search field the in-tab header is
       gone — keep a matching breathing room before the clusters. */
    .topbar-gap { height: 24px; }

    /* ── Search input ── lives in filtering/SearchInput.svelte ── */

    /* ── Events Section ────────────────────────────────── */
    .events-section {
        margin-top: 8px;
    }

    /* Extra breathing room between the event clusters. */
    .events-list {
        display: flex;
        flex-direction: column;
        gap: 8px;
    }

    .sr-only {
        position: absolute;
        width: 1px;
        height: 1px;
        padding: 0;
        margin: -1px;
        overflow: hidden;
        clip: rect(0, 0, 0, 0);
        white-space: nowrap;
        border: 0;
    }

/* ── States ────────────────────────────────────────── */
.state-empty { text-align: center; padding: 48px 16px; color: var(--ui-text-subtle, color-mix(in oklch, var(--color-base-content) 62%, transparent)); font-size: 15px; }
.state-error { padding: 16px; color: var(--color-error); text-align: center; }

/* ── Skeleton ────────────────────────────────────────── */
.skeleton-list { display: flex; flex-direction: column; }
.sk-event {
  padding: 16px 0;
  border-bottom: 1px solid var(--color-base-300);
}
.sk-bar {
  border-radius: var(--ui-radius-xs);
  background: linear-gradient(
    90deg,
    color-mix(in oklch, var(--color-base-300) 60%, transparent) 0%,
    color-mix(in oklch, var(--color-base-300) 90%, transparent) 40%,
    color-mix(in oklch, var(--color-base-300) 60%, transparent) 80%
  );
  background-size: 200% 100%;
  animation: shimmer 1.6s ease-in-out infinite;
}
.sk-title {
  height: 14px;
  margin-bottom: 6px;
  border-radius: var(--ui-radius-xs);
}
.sk-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
}
.sk-pub-row {
  display: flex;
  align-items: center;
  margin-left: 4px;
}
.sk-circle {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  margin-left: -4px;
  border: 1.5px solid var(--color-base-100);
  background: linear-gradient(
    90deg,
    color-mix(in oklch, var(--color-base-300) 60%, transparent) 0%,
    color-mix(in oklch, var(--color-base-300) 90%, transparent) 40%,
    color-mix(in oklch, var(--color-base-300) 60%, transparent) 80%
  );
  background-size: 200% 100%;
  animation: shimmer 1.6s ease-in-out infinite;
}
@keyframes shimmer {
  0% { background-position: 200% center; }
  100% { background-position: -200% center; }
}
</style>