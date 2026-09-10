<script lang="ts">
 import { onMount } from 'svelte';
 import { page } from '$app/stores';
    import { goto } from '$app/navigation';
    import PostCard from '$lib/components/PostCard.svelte';
    import FollowFeedModal from '$lib/components/FollowFeedModal.svelte';
    import { Search } from '@lucide/svelte';
    import { t } from 'svelte-i18n';
import { get } from 'svelte/store';
    import { apiFetch } from '$lib/api';
    import { syncFeedItemTags, type TagRef } from '$lib/utils/syncFeedTags';
    import { subscriptionChanged } from '$lib/stores/subscription';
    import ScreenShell from '$lib/components/ScreenShell.svelte';

type Tab = 'articles' | 'feeds';

    // ── Tab state ──────────────────────────────────────────────────────────
    let activeTab = $state<Tab>('articles');

    // ── Search state ───────────────────────────────────────────────────────
    let searchQuery = $state(decodeURIComponent($page.params.query ?? ''));

    // ── Articles state ─────────────────────────────────────────────────────
    let articleResults = $state<any[]>([]);
    let articleLoading = $state(false);
    let articleError   = $state('');

    // ── User tags ──────────────────────────────────────────────────────────
    let tagList = $state<Array<{ id: number; name: string; color?: string }>>([]);

    // ── Followed feeds state ───────────────────────────────────────────────
    interface SubscribedFeed {
        feed_sha256: string;
        url: string;
        title: string;
        icon: string | null;
    }
    let subscriptions = $state<SubscribedFeed[]>([]);
    let subsLoading = $state(false);

    // ── Online feed search state ───────────────────────────────────────────
    let feedResults = $state<any[]>([]);
    let feedLoading = $state(false);
    let feedError   = $state('');
    let onlineDone  = $state(false);

    // ── Modal state ────────────────────────────────────────────────────────
    let modalFeed = $state<{ title: string; url: string } | null>(null);

    // ── Helpers ────────────────────────────────────────────────────────────
    function normalizeResult(item: any) {
        return {
            ...item,
            relevance_score: item.similarty_score ?? item.relevance_score
        };
    }

    async function loadUserTags() {
        try {
            const res = await apiFetch('/api/tags', { credentials: 'include' });
            if (res.ok) {
                const data = await res.json();
                tagList = data.tags ?? [];
            }
        } catch { /* non-critical */ }
    }

    function handleTagChange(payload: { item_id: string; tag_id: number; action: 'assign' | 'unassign'; tag?: TagRef }) {
        articleResults = syncFeedItemTags(articleResults, payload.item_id, payload.tag_id, payload.action, payload.tag);
    }

    onMount(loadUserTags);

    // Followed feeds matching the query (case-insensitive substring on title/url)
    let matchedSubs = $derived.by(() => {
        const q = decodeURIComponent($page.params.query ?? '').trim().toLowerCase();
        if (!q) return [];
        return subscriptions.filter(
            (f) => f.title.toLowerCase().includes(q) || f.url.toLowerCase().includes(q)
        );
    });

    async function loadSubscriptions() {
        subsLoading = true;
        try {
            const res = await apiFetch('/api/list-subscriptions', { credentials: 'include' });
            if (res.status === 401) { window.location.replace('/'); return; }
            if (res.ok) {
                const data = await res.json();
                subscriptions = (data.feeds ?? []).map((f: any) => ({
                    feed_sha256: f.feed_sha256 ?? '',
                    url: f.url ?? '',
                    title: f.title || f.url || '',
                    icon: f.icon ?? null
                }));
            }
        } catch { /* non-critical */ }
        subsLoading = false;
    }

    // Reload subscriptions after a feed is followed elsewhere (e.g. the modal)
    onMount(() => {
        const unsub = subscriptionChanged.subscribe((n) => {
            if (n === 0) return; // initial store value, not an actual change
            loadSubscriptions();
        });
        return unsub;
    });

    // ── Lifecycle ──────────────────────────────────────────────────────────
$effect(() => {
        const query = decodeURIComponent($page.params.query ?? '');
        searchQuery = query; // Atualiza o input se a URL mudar
        feedResults = [];
        feedError   = '';
        onlineDone  = false;
        if (query) {
            runArticleSearch(query);
            loadSubscriptions();
        }
    });

    // ── Search functions ───────────────────────────────────────────────────
    function handleSearch(e: Event) {
        e.preventDefault();
        const q = searchQuery.trim();
        if (q) goto(`/s/${encodeURIComponent(q)}`);
    }

    async function runArticleSearch(query: string) {
        articleLoading = true;
        articleError   = '';
        articleResults = [];
        try {
            // Using relative path to the API
const res = await apiFetch(
      `/api/search?limit=10&threshold=0.6&query=${encodeURIComponent(query)}`,
      { credentials: 'include' }
    );
            if (res.status === 401) { window.location.replace('/'); return; }
            if (!res.ok) throw new Error(`${get(t)('search.searchFailed')} (${res.status})`);
            const raw = await res.json();
            articleResults = raw.map(normalizeResult);
        } catch (err: any) {
            articleError = err.message || get(t)('search.searchFailed');
        }
        articleLoading = false;
    }

    async function runFeedSearch(query: string) {
        feedLoading = true;
        onlineDone = false;
        feedError   = '';
        feedResults = [];
        try {
const res = await apiFetch(
      `/api/online-discover?query=${encodeURIComponent(query)}`,
      { credentials: 'include' }
    );
            if (res.status === 401) { window.location.replace('/'); return; }
            if (!res.ok) throw new Error(`${get(t)('search.discoveryFailed')} (${res.status})`);
            const data = await res.json();
            feedResults = data.candidates ?? data.feed ?? [];
        } catch (err: any) {
            feedError = err.message || get(t)('search.discoveryFailed');
        }
        feedLoading = false;
        onlineDone = true;
    }

    // ── Modal functions ────────────────────────────────────────────────────
    function openModal(feed: { title: string; url: string }) {
        modalFeed = feed;
    }

    function closeModal() {
        modalFeed = null;
}
</script>

<ScreenShell>
<div class="page-root">
    <div class="main-content">

        <!-- ── Header & Search ──────────────────────────── -->
        <header class="page-header">
            <form class="search-form" onsubmit={handleSearch}>
                <div class="search-wrap">
                    <input
                        class="search-input"
                        type="search"
                        placeholder="{$t('searchtab.placeholder', { default: 'Search posts, feeds, or topics...' })}"
                        bind:value={searchQuery}
                        autocomplete="off"
                        autocorrect="off"
                        spellcheck="false"
                    />
                    <Search size={18} class="search-icon" />
                </div>
            </form>
        </header>

        <!-- Tab bar -->
        <div class="tab-bar" ontouchstart={(e) => e.stopPropagation()} ontouchmove={(e) => e.stopPropagation()} ontouchend={(e) => e.stopPropagation()}>
            <div class="mode-pill" role="group" aria-label="Search tabs">
                <button
                    class="mode-btn"
                    class:active={activeTab === 'articles'}
                    onclick={() => (activeTab = 'articles')}
                    aria-pressed={activeTab === 'articles'}
                >
                    <span>{$t('search.articles')}</span>
                </button>
                <button
                    class="mode-btn"
                    class:active={activeTab === 'feeds'}
                    onclick={() => (activeTab = 'feeds')}
                    aria-pressed={activeTab === 'feeds'}
                >
                    <span>{$t('search.feeds')}</span>
                </button>
            </div>
        </div>

        <div class="results-wrap">

            <!-- ── Articles tab ──────────────────────────────────────────── -->
            {#if activeTab === 'articles'}
                {#if articleLoading}
                    <div class="state-center">
                        <span class="loading loading-spinner loading-lg"></span>
                    </div>
                {:else if articleError}
                    <div class="state-error">{articleError}</div>
                {:else if articleResults.length === 0}
                    <p class="state-empty">
                        {$t('search.noArticleResults')} <span class="query-label">"{decodeURIComponent($page.params.query ?? '')}"</span>
                    </p>
                {:else}
                    <p class="results-meta">
{articleResults.length} {articleResults.length !== 1 ? $t('search.results') : $t('search.result')} {$t('search.for')}
                <span class="query-label">"{decodeURIComponent($page.params.query ?? '')}"</span>
                    </p>
                    {#each articleResults as item}
                        <PostCard {item} server="" tags={item.tags || []} userTags={tagList} onTagClick={(tag) => goto(`/home?tag_id=${tag.tag_id}`)} onTagChange={handleTagChange} />
                    {/each}
                {/if}

            <!-- ── Feeds tab ─────────────────────────────────────────────── -->
            {:else}
                {#if subsLoading}
                    <div class="state-center">
                        <span class="loading loading-spinner loading-lg"></span>
                    </div>
                {:else}
                    {#if matchedSubs.length > 0}
                        <p class="section-label">{$t('search.yourFeeds')}</p>
                        {#each matchedSubs as sub (sub.feed_sha256)}
                            <a class="sub-row" href={`/f/${sub.feed_sha256}`}>
                                {#if sub.icon}
                                    <img class="sub-icon" src={sub.icon} alt="" loading="lazy" />
                                {:else}
                                    <span class="sub-fallback">RSS</span>
                                {/if}
                                <span class="sub-info">
                                    <span class="sub-title">{sub.title}</span>
                                    <span class="sub-url">{sub.url}</span>
                                </span>
                            </a>
                        {/each}
                    {/if}

                    <div class="online-divider">
                        <span class="divider-line"></span>
                        {#if feedLoading}
                            <span class="divider-label">
                                <span class="mini-spinner"></span>
                                {$t('search.searchingOnline')}
                            </span>
                        {:else}
                            <button class="btn-search-online" onclick={() => runFeedSearch(searchQuery.trim())}>
                                {$t('search.searchOnline')}
                            </button>
                        {/if}
                        <span class="divider-line"></span>
                    </div>

                    {#if feedError}
                        <div class="state-error">{feedError}</div>
                    {:else if feedResults.length > 0}
                        <p class="results-meta">
                            {feedResults.length} {feedResults.length !== 1 ? $t('search.feedsCount') : $t('search.feed')} {$t('search.foundFor')}
                            <span class="query-label">"{decodeURIComponent($page.params.query ?? '')}"</span>
                        </p>
                        {#each feedResults as feed, i}
                            <div class="feed-card" class:best={i === 0}>
                                {#if i === 0}
                                    <span class="best-badge">{$t('search.bestMatch')}</span>
                                {/if}
                                <p class="feed-title">{feed.title}</p>
                                <a class="feed-url" href={feed.url} target="_blank" rel="noopener noreferrer">
                                    {feed.url}
                                </a>
                                <div class="feed-actions">
                                    <button class="btn-follow" onclick={() => openModal(feed)}>{$t('search.follow')}</button>
                                </div>
                            </div>
                        {/each}
                    {:else if onlineDone && !feedLoading}
                        <div class="state-center">
                            <p class="state-empty">
                                {$t('search.noFeedResults')} <span class="query-label">"{decodeURIComponent($page.params.query ?? '')}"</span>
                            </p>
                            <p class="state-hint">{$t('search.tryDifferentQuery')}</p>
                        </div>
                    {/if}
                {/if}
            {/if}

        </div>

    </div>
</div>
</ScreenShell>

<!-- ── Follow Feed Modal ───────────────────────────────────────────────── -->
{#if modalFeed}
    <FollowFeedModal feed={modalFeed} onclose={closeModal} />
{/if}

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
            margin-left: max(240px, calc(50vw - 21rem));
            margin-right: auto;
        }
    }

    /* ── Header & Search ──────────────────────────── */
    .page-header {
        padding: 24px 0 0;
    }

    .search-form { width: 100%; }
    .search-wrap {
        display: flex;
        align-items: center;
        gap: 12px;
        background: color-mix(in oklch, var(--color-base-200) 50%, transparent);
        border: 1px solid var(--color-base-300);
        border-radius: var(--ui-radius-sm);
        padding: 0 16px;
        height: 46px;
        transition: background 180ms ease, border-color 180ms ease, box-shadow 180ms ease;
    }
    .search-wrap:focus-within {
        background: var(--color-base-100);
        border-color: var(--color-accent);
        box-shadow: 0 0 0 3px color-mix(in oklch, var(--color-accent) 15%, transparent);
    }

    .search-input {
        flex: 1;
        min-width: 0;
        background: transparent; border: none; outline: none;
        font-size: 15px; color: var(--color-base-content); line-height: 1;
        -webkit-appearance: none; appearance: none;
    }
    .search-input::placeholder { color: color-mix(in oklch, var(--color-base-content) 35%, transparent); }
    .search-input::-webkit-search-cancel-button { display: none; }

    .search-icon {
        flex-shrink: 0;
        color: color-mix(in oklch, var(--color-base-content) 40%, transparent);
        transition: color 180ms ease;
    }
    .search-wrap:focus-within .search-icon { color: var(--color-accent); }

    /* ── Tab bar (Pill Style) ──────────────────────────────── */
.tab-bar {
  display: flex;
  padding: 16px 0 12px;
  touch-action: pan-y;
}

    .mode-pill {
        display: flex;
        background: var(--color-base-200);
        border-radius: calc(var(--ui-radius-sm) + 3px);
        padding: 3px;
        gap: 2px;
        flex-shrink: 0;
    }
    .mode-btn {
        display: flex;
        align-items: center;
        gap: 5px;
        padding: 6px 14px;
        border-radius: var(--ui-radius-sm);
        border: none;
        background: transparent;
        font-size: 13px;
        font-weight: 500;
        color: color-mix(in oklch, var(--color-base-content) 65%, transparent);
        cursor: pointer;
        transition: background 150ms ease, color 150ms ease, font-weight 0ms;
        white-space: nowrap;
    }
    .mode-btn.active {
        background: var(--color-base-100);
        color: var(--color-base-content);
        font-weight: 700;
        box-shadow: 0 1px 3px color-mix(in oklch, black 10%, transparent);
    }

    /* ── Results wrap ─────────────────────────────────────────────────────── */
    .results-wrap {
        border-top: 1px solid var(--color-base-300);
    }

.state-center {
	display: flex;
	flex-direction: column;
	align-items: center;
	gap: 10px;
	padding: 48px 0;
}

.state-empty {
	text-align: center;
	padding: 0 16px;
	color: color-mix(in oklch, var(--color-base-content) 40%, transparent);
	font-size: 15px;
	margin: 0;
}

.state-hint {
	font-size: 13px;
	color: color-mix(in oklch, var(--color-base-content) 35%, transparent);
	margin: 0;
}

    .state-error { padding: 16px; color: var(--color-error); text-align: center; }

    .results-meta {
        font-size: 13px;
        color: color-mix(in oklch, var(--color-base-content) 40%, transparent);
        padding: 12px 0 4px;
    }

    .query-label {
        font-weight: 600;
        color: color-mix(in oklch, var(--color-base-content) 65%, transparent);
    }

    /* ── Followed feed rows ──────────────────────────────────────────────── */
    .section-label {
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: color-mix(in oklch, var(--color-base-content) 40%, transparent);
        padding: 14px 0 4px;
        margin: 0;
    }

    .sub-row {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 10px 0;
        text-decoration: none;
        border-bottom: 1px solid var(--color-base-300);
        transition: background 0.15s;
    }
    .sub-row:hover {
        background: color-mix(in oklch, var(--color-base-content) 4%, transparent);
        margin: 0 -16px;
        padding-left: 16px;
        padding-right: 16px;
        border-radius: var(--ui-radius-xs);
    }
    .sub-row:active {
        background: color-mix(in oklch, var(--color-base-content) 8%, transparent);
    }

    .sub-icon {
        width: 28px;
        height: 28px;
        border-radius: var(--ui-radius-xs);
        flex-shrink: 0;
        object-fit: cover;
        background: color-mix(in oklch, var(--color-base-content) 8%, transparent);
    }

    .sub-fallback {
        width: 28px;
        height: 28px;
        border-radius: var(--ui-radius-xs);
        flex-shrink: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 9px;
        font-weight: 800;
        color: color-mix(in oklch, var(--color-base-content) 55%, transparent);
        background: color-mix(in oklch, var(--color-base-content) 8%, transparent);
    }

    .sub-info {
        display: flex;
        flex-direction: column;
        gap: 1px;
        min-width: 0;
    }

    .sub-title {
        font-size: 14px;
        font-weight: 600;
        color: var(--color-base-content);
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        transition: color 140ms;
    }
    .sub-row:hover .sub-title {
        color: var(--color-accent);
    }

    .sub-url {
        font-size: 11px;
        color: color-mix(in oklch, var(--color-base-content) 50%, transparent);
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    /* ── Online search divider ───────────────────────────────────────────── */
    .online-divider {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 18px 0;
    }

    .divider-line {
        flex: 1;
        height: 1px;
        background: var(--color-base-300);
    }

    .divider-label {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 12px;
        color: color-mix(in oklch, var(--color-base-content) 50%, transparent);
        white-space: nowrap;
    }

    .mini-spinner {
        width: 12px;
        height: 12px;
        border: 2px solid color-mix(in oklch, var(--color-base-content) 15%, transparent);
        border-top-color: var(--color-accent);
        border-radius: 50%;
        animation: spin 0.7s linear infinite;
        flex-shrink: 0;
    }

    @keyframes spin { to { transform: rotate(360deg); } }

    .btn-search-online {
        font-size: 12px;
        font-weight: 600;
        padding: 6px 14px;
        border-radius: var(--ui-radius-full);
        border: 1px solid var(--color-base-300);
        background: transparent;
        cursor: pointer;
        color: var(--color-base-content);
        white-space: nowrap;
        transition: background 0.15s, border-color 0.15s, color 0.15s;
    }

    .btn-search-online:hover {
        background: color-mix(in oklch, var(--color-accent) 10%, transparent);
        border-color: color-mix(in oklch, var(--color-accent) 60%, transparent);
        color: var(--color-accent);
    }

    /* ── Feed cards ───────────────────────────────────────────────────────── */
    .feed-card {
        position: relative;
        display: flex;
        flex-direction: column;
        gap: 4px;
        padding: 14px 0;
        border-bottom: 1px solid var(--color-base-300);
        transition: background 0.15s;
    }

.feed-card:hover {
  background: color-mix(in oklch, var(--color-base-content) 4%, transparent);
  margin: 0 -16px;
  padding-left: 16px;
  padding-right: 16px;
  border-radius: var(--ui-radius-xs);
}
.feed-card:active {
  background: color-mix(in oklch, var(--color-base-content) 8%, transparent);
}

    .feed-card.best {
        border-left: 3px solid var(--color-accent); /* Yellow for Best Match */
        padding-left: 13px; /* Compensar a borda */
    }

    .best-badge {
        font-size: 10px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: var(--color-accent);
        margin-bottom: 2px;
    }

.feed-title {
font-family: var(--font-post-title);
  font-size: 16px;
  font-weight: 500;
  line-height: 1.4;
  color: var(--color-base-content);
  margin: 0;
  transition: color 140ms;
}
.feed-card:hover .feed-title {
  color: var(--color-accent);
}

    .feed-url {
        font-size: 12px;
        color: color-mix(in oklch, var(--color-base-content) 50%, transparent);
        text-decoration: none;
        word-break: break-all;
    }

.feed-url:hover {
  color: var(--color-accent);
}

    .feed-actions { margin-top: 6px; }

    .btn-follow {
        font-size: 12px;
        font-weight: 600;
        padding: 4px 14px;
        border-radius: var(--ui-radius-sm);
        border: 1px solid var(--color-base-300);
        background: transparent;
        cursor: pointer;
        color: var(--color-base-content);
        transition: background 0.15s, border-color 0.15s;
    }

    .btn-follow:hover {
        background: color-mix(in oklch, var(--color-accent) 10%, transparent);
        border-color: color-mix(in oklch, var(--color-accent) 60%, transparent);
        color: var(--color-accent);
    }
</style>