<script lang="ts">
 import { page } from '$app/stores';
    import { goto } from '$app/navigation';
    import PostCard from '$lib/components/PostCard.svelte';
    import FollowFeedModal from '$lib/components/FollowFeedModal.svelte';
    import { Search } from '@lucide/svelte';
    import { t } from 'svelte-i18n';
import { get } from 'svelte/store';
import { apiFetch } from '$lib/api';

type Tab = 'articles' | 'feeds';

    // ── Tab state ──────────────────────────────────────────────────────────
    let activeTab = $state<Tab>('articles');

    // ── Search state ───────────────────────────────────────────────────────
    let searchQuery = $state(decodeURIComponent($page.params.query ?? ''));

    // ── Articles state ─────────────────────────────────────────────────────
    let articleResults = $state<any[]>([]);
    let articleLoading = $state(false);
    let articleError   = $state('');

    // ── Feeds state ────────────────────────────────────────────────────────
    let feedResults = $state<any[]>([]);
    let feedLoading = $state(false);
    let feedError   = $state('');

    // ── Modal state ────────────────────────────────────────────────────────
    let modalFeed = $state<{ title: string; url: string } | null>(null);

    // ── Helpers ────────────────────────────────────────────────────────────
    function normalizeResult(item: any) {
        return {
            ...item,
            relevance_score: item.similarty_score ?? item.relevance_score
        };
    }

    // ── Lifecycle ──────────────────────────────────────────────────────────
$effect(() => {
        const query = decodeURIComponent($page.params.query ?? '');
        searchQuery = query; // Atualiza o input se a URL mudar
        if (query) {
            runArticleSearch(query);
            runFeedSearch(query);
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
    }

    // ── Modal functions ────────────────────────────────────────────────────
    function openModal(feed: { title: string; url: string }) {
        modalFeed = feed;
    }

    function closeModal() {
        modalFeed = null;
}
</script>

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
        <div class="tab-bar">
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
                        <PostCard {item} server="" />
                    {/each}
                {/if}

            <!-- ── Feeds tab ─────────────────────────────────────────────── -->
            {:else}
                {#if feedLoading}
                    <div class="state-center">
                        <span class="loading loading-spinner loading-lg"></span>
                    </div>
                {:else if feedError}
                    <div class="state-error">{feedError}</div>
{:else if feedResults.length === 0}
			<div class="state-center">
				<p class="state-empty">
					{$t('search.noFeedResults')} <span class="query-label">"{decodeURIComponent($page.params.query ?? '')}"</span>
				</p>
				<p class="state-hint">{$t('search.tryDifferentQuery')}</p>
			</div>
                {:else}
                    <p class="results-meta">
                        {feedResults.length} {feedResults.length !== 1 ? $t('search.feeds') : $t('search.feed')} {$t('search.foundFor')}
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
                {/if}
            {/if}

        </div>

    </div>
</div>

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
        border-radius: 10px;
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
    }

    .mode-pill {
        display: flex;
        background: var(--color-base-200);
        border-radius: 13px;
        padding: 3px;
        gap: 2px;
        flex-shrink: 0;
    }
    .mode-btn {
        display: flex;
        align-items: center;
        gap: 5px;
        padding: 6px 14px;
        border-radius: 10px;
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
  border-radius: 6px;
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
        border-radius: 10px;
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