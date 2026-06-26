<script lang="ts">
    import { onMount } from 'svelte';
    import { page } from '$app/stores';
    import { beforeNavigate, goto } from '$app/navigation';
    import PostCard from '$lib/components/PostCard.svelte';
    import { Rss, Users, ExternalLink, Check, Plus, ArrowLeft } from '@lucide/svelte';
import LoaderCircle from '@lucide/svelte/icons/loader-circle';
    import { t, locale } from 'svelte-i18n';
    import { get } from 'svelte/store';
 import { notifySubscriptionChanged } from '$lib/stores/subscription';
 import { onViewed, flushPending, destroyViewTracker } from '$lib/stores/viewTracker';
 import { apiFetch } from '$lib/api';
 import { feedBustNeeded, clearBustFlag } from '$lib/stores/feedCache';

 type Mode = 'recommendations' | 'recents';

    // ── Route param ───────────────────────────────────────
    const feedSha: string = $page.params.feed_sha256 ?? '';

    // ── Mode ──────────────────────────────────────────────
    let mode = $state<Mode>('recommendations');

    // ── Pull-to-refresh ─────────────────────────────────
    let pageRootEl: HTMLElement | null = $state(null);
    let pullOffset = $state(0);
    let pulling = $state(false);
    let pullStartY = 0;
    let scrollContainer: HTMLElement | null = null;
    const PULL_THRESHOLD = 60;
    const PULL_RESISTANCE = 0.4;

    // ── Feed info ─────────────────────────────────────────
    type FeedInfoRaw = {
        feed_sha256: string;
        feed_url: string;
        feed_title: string;
        feed_link: string | null;
        feed_filename: string | null;
        feed_description: string;
        feed_icon: string | null;
        feed_lang: string | null;
        feed_last_update: string | null;
        last_parsed_at: string | null;
        entries_count: number;
        active_users: number;
        total_users: number;
  parsed: number;
  user_feed_subscription: string;
};
let feedInfo = $state<FeedInfoRaw | null>(null);
  let infoLoading = $state(true);
  let infoError = $state('');

  // ── User tags ────────────────────────────────────────
  let tagList = $state<Array<{ id: number; name: string; color?: string }>>([]);

    // ── Follow state ──────────────────────────────────────
    let followed = $state(false);
    let followLoading = $state(false);
    let subscriberCount = $state(0);

    // ── Feed items ────────────────────────────────────────
    let feed = $state<any[]>([]);
    let loading = $state(true);
    let refreshing = $state(false);
    let loadingMore = $state(false);
    let hasMore = $state(true);
    let error = $state('');
    let page_num = $state(0);

    // ── Sentinel ──────────────────────────────────────────
    let sentinelEl: HTMLDivElement | null = $state(null);
    let observer: IntersectionObserver | null = null;

    const SKELETON_INITIAL = Array.from({ length: 6 }, (_, i) => i);
    const SKELETON_MORE = Array.from({ length: 3 }, (_, i) => i);

    // ── View tracking ────────────────────────────────────────────────────────
    let viewObserver: IntersectionObserver | null = null;

    function trackView(node: HTMLElement, item_id: string) {
        if (!viewObserver) {
            viewObserver = new IntersectionObserver(
                (entries) => {
                    entries.forEach((entry) => {
                        if (entry.isIntersecting) {
                            const id = (entry.target as HTMLElement).dataset.viewId;
                            if (id) onViewed(id);
                        }
                    });
                },
                { threshold: 0.5 }
            );
        }
        node.dataset.viewId = item_id;
        viewObserver.observe(node);

        return {
            destroy() {
                if (viewObserver) viewObserver.unobserve(node);
            }
        };
    }

    // ── Bootstrap ─────────────────────────────────────────
onMount(() => {
	observer = new IntersectionObserver(
            (entries) => {
                if (entries[0].isIntersecting) loadMore();
            },
            { rootMargin: '0px 0px 600px 0px' }
        );

	if (pageRootEl) {
		let el = pageRootEl.parentElement;
		while (el) {
			const style = getComputedStyle(el);
			if (style.overflowY === 'auto' || style.overflowY === 'scroll') {
				scrollContainer = el;
				break;
			}
			el = el.parentElement;
		}
	}

loadFeedInfo();
    loadFeed(true);
    loadUserTags();

	beforeNavigate(() => {
		flushPending();
	});

	return () => {
		observer?.disconnect();
		destroyViewTracker();
		viewObserver?.disconnect();
	};
    });

    $effect(() => {
        if (observer && sentinelEl) {
            observer.disconnect();
            observer.observe(sentinelEl);
        }
    });

// ── Helpers ───────────────────────────────────────────
function getDomain(url: string) {
        try {
            return new URL(url).hostname.replace('www.', '');
        } catch {
            return url;
        }
    }

    function formatDate(iso: string | null): string {
        if (!iso) return '';
        try {
            return new Intl.DateTimeFormat(get(locale) ?? 'en', {
                day: '2-digit',
                month: 'short',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
            }).format(new Date(iso));
        } catch {
            return iso;
        }
    }

    // ── Feed info API ─────────────────────────────────────
    async function loadFeedInfo() {
        infoLoading = true;
        infoError = '';
        try {
            const res = await apiFetch(`/api/feed-info/${feedSha}`, { credentials: 'include' });
            if (res.status === 401) {
                window.location.replace('/login');
                return;
            }
            if (!res.ok) throw new Error(`${get(t)('feed.loadInfoError')} (${res.status})`);
            const data: FeedInfoRaw = await res.json();
    feedInfo = data;
    followed = data.user_feed_subscription === 'Subscribed';
    subscriberCount = data.total_users ?? 0;
        } catch (e: any) {
            infoError = (e as Error).message || get(t)('feed.loadInfoError');
        }
        infoLoading = false;
    }

    // ── Follow / Unfollow ─────────────────────────────────
    async function toggleFollow() {
        if (followLoading || !feedInfo?.feed_url) return;
        followLoading = true;
        const wasFollowing = followed;
        const endpoint = wasFollowing ? '/api/feed-remove' : '/api/feed-add';
        try {
const res = await apiFetch(endpoint, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: feedInfo.feed_url }),
    });
            if (res.status === 401) {
                window.location.replace('/login');
                return;
            }
            if (!res.ok) throw new Error(`${get(t)('feed.loadFeedError')} (${res.status})`);
    followed = !wasFollowing;
    subscriberCount = subscriberCount + (followed ? 1 : -1);
    notifySubscriptionChanged();
        } catch (e) {
            console.error('toggleFollow failed:', e);
        }
  followLoading = false;
  }

  // ── Tags API ─────────────────────────────────────────
  async function loadUserTags() {
    try {
      const res = await apiFetch('/api/tags', { credentials: 'include' });
      if (res.ok) {
        const data = await res.json();
        tagList = data.tags ?? [];
      }
    } catch { /* non-critical */ }
  }

    // ── Feed items API ────────────────────────────────────
    function buildUrl(pageNum: number, limit: number = 20): string {
const p = new URLSearchParams({
        limit: String(limit),
        feed_sha256: feedSha!,
    });
        if (mode === 'recommendations') {
            p.set('page', String(pageNum));
            return `/api/feed/recommendations?${p}`;
        }
        p.set('max_days', '10');
        return `/api/feed/recents?${p}`;
    }

    async function loadFeed(reset: boolean = false) {
	const bust = feedBustNeeded();
	if (bust) clearBustFlag();
	const fetchOpt: RequestInit = bust ? { credentials: 'include', cache: 'no-store' } : { credentials: 'include' };
        if (reset) {
            loading = true;
            feed = [];
            page_num = 0;
            hasMore = true;
            error = '';
        }
        try {
const res = await apiFetch(buildUrl(0), fetchOpt);
    if (res.status === 401) {
      window.location.replace('/login');
      return;
    }
    if (!res.ok) throw new Error(`${get(t)('feed.loadFeedError')} (${res.status})`);
    const data: any[] = await res.json();
    feed = data;
    hasMore = data.length > 0;
        } catch (e: any) {
            error = (e as Error).message || get(t)('feed.loadFeedError');
        }
        loading = false;
        refreshing = false;
    }

    async function loadMore() {
        if (loadingMore || !hasMore || loading) return;
        loadingMore = true;
        try {
            let newItems: any[];
            if (mode === 'recommendations') {
                const nextPage = page_num + 1;
                const res = await apiFetch(buildUrl(nextPage), { credentials: 'include' });
                if (!res.ok) throw new Error(`${get(t)('feed.loadFeedError')} (${res.status})`);
                const data: any[] = await res.json();
                if (data.length === 0) {
                    hasMore = false;
                    loadingMore = false;
                    return;
                }
                const seen = new Set(feed.map((x: any) => x.item_id));
                newItems = data.filter((x: any) => !seen.has(x.item_id));
                if (newItems.length === 0) {
                    hasMore = false;
                    loadingMore = false;
                    return;
                }
                page_num = nextPage;
            } else {
                const requestedLimit = feed.length + 20;
                const res = await apiFetch(buildUrl(0, requestedLimit), { credentials: 'include' });
                if (!res.ok) throw new Error(`${get(t)('feed.loadFeedError')} (${res.status})`);
                const data: any[] = await res.json();
                const seen = new Set(feed.map((x: any) => x.item_id));
                newItems = data.filter((x: any) => !seen.has(x.item_id));
                if (newItems.length === 0) {
                    hasMore = false;
                    loadingMore = false;
                    return;
                }
            }
            feed = [...feed, ...newItems];
        } catch (e: any) {
            console.error('loadMore failed:', e);
        }
        loadingMore = false;
    }

    function setMode(next: Mode) {
        if (mode === next) return;
        mode = next;
        loadFeed(true);
    }

    // ── Pull-to-refresh ─────────────────────────────────────
    function onPullStart(e: TouchEvent) {
        if (loading || refreshing) return;
        if (scrollContainer && scrollContainer.scrollTop > 4) return;
        pullStartY = e.touches[0].clientY;
        pulling = false;
        pullOffset = 0;
    }

    function onPullMove(e: TouchEvent) {
        if (loading || refreshing) return;
        if (scrollContainer && scrollContainer.scrollTop > 4) return;
        const dy = e.touches[0].clientY - pullStartY;
        if (dy > 0) {
            pulling = true;
            pullOffset = Math.min(dy * PULL_RESISTANCE, 120);
            if (pageRootEl) {
                pageRootEl.style.transition = 'none';
                pageRootEl.style.transform = `translateY(${pullOffset}px)`;
            }
        } else if (pulling) {
            pulling = false;
            pullOffset = 0;
            snapPtrBack();
        }
    }

    function onPullEnd(_e: TouchEvent) {
        if (!pulling) return;
        pulling = false;
        if (pullOffset > PULL_THRESHOLD && !refreshing) {
            if (pageRootEl) {
                pageRootEl.style.transition = 'transform 0.25s ease';
                pageRootEl.style.transform = 'translateY(55px)';
            }
            pullOffset = 55;
            refreshing = true;
            loadFeed(true);
        } else {
            snapPtrBack();
        }
    }

    $effect(() => {
        if (!refreshing && pullOffset > 0) {
            snapPtrBack();
        }
    });

    function snapPtrBack() {
        pullOffset = 0;
        if (pageRootEl) {
            pageRootEl.style.transition = 'transform 0.3s ease';
            pageRootEl.style.transform = 'translateY(0)';
        }
    }
</script>

<!-- ── Snippets ─────────────────────────────────────── -->

{#snippet skeletonCard()}
    <div class="skeleton-card" aria-hidden="true">
        <div class="sk-row sk-publisher">
            <div class="sk-circle"></div>
            <div class="sk-bar" style="width:72px"></div>
            <div class="sk-dot"></div>
            <div class="sk-bar" style="width:52px; opacity:.5"></div>
            <div class="sk-bar sk-ml-auto" style="width:36px; opacity:.4"></div>
        </div>
        <div class="sk-bar sk-title" style="width:92%"></div>
        <div class="sk-bar sk-title" style="width:62%; margin-bottom:8px"></div>
        <div class="sk-bar sk-desc" style="width:100%"></div>
        <div class="sk-bar sk-desc" style="width:78%; margin-bottom:10px"></div>
        <div class="sk-row sk-actions">
            <div class="sk-circle sk-sm"></div>
            <div class="sk-circle sk-sm"></div>
        </div>
    </div>
{/snippet}

{#snippet skeletonHeader()}
    <div class="feed-header feed-header--skeleton" aria-hidden="true">
        <div class="sk-circle fh-icon-sk"></div>
        <div class="fh-meta">
            <div class="sk-bar" style="width:160px; height:18px; border-radius:6px"></div>
            <div class="sk-bar" style="width:100px; height:11px; border-radius:4px; margin-top:8px; opacity:.6"></div>
            <div class="sk-bar" style="width:220px; height:10px; border-radius:4px; margin-top:10px; opacity:.4"></div>
        </div>
        <div class="sk-bar fh-btn-sk" style="width:88px; height:34px; border-radius:10px; flex-shrink:0"></div>
    </div>
{/snippet}

<!-- ── Markup ──────────────────────────────────────── -->

<div
    class="page-root"
    bind:this={pageRootEl}
    ontouchstart={onPullStart}
    ontouchmove={onPullMove}
    ontouchend={onPullEnd}
>
    <!-- Pull-to-refresh indicator -->
    <div class="ptr-indicator" class:ptr-visible={pullOffset > 0 || refreshing}>
        {#if refreshing}
            <LoaderCircle size={20} class="spin" />
        {:else if pullOffset > PULL_THRESHOLD}
            <span class="ptr-text">{$t('feed.releaseToRefresh', { default: 'Release to refresh' })}</span>
        {:else}
            <span class="ptr-text">{$t('feed.pullToRefresh', { default: 'Pull to refresh' })}</span>
        {/if}
    </div>

    <div class="main-content">

        <!-- Back navigation -->
        <header class="top-header">
            <button class="back-btn" onclick={() => history.back()} aria-label="{$t('feed.back', { default: 'Back' })}">
                <ArrowLeft size={20} />
            </button>
        </header>

        <!-- Feed profile header -->
        {#if infoLoading}
            {@render skeletonHeader()}
        {:else if feedInfo}
            <header class="feed-header">
                <!-- Icon -->
                <div class="fh-icon-wrap">
                    {#if feedInfo.feed_icon}
                        <img
                            src={feedInfo.feed_icon}
                            alt={feedInfo.feed_title}
                            class="fh-icon"
                            onerror={(e) => {
                                const img = e.target as HTMLImageElement;
                                img.style.display = 'none';
                                img.parentElement?.classList.add('fh-icon-wrap--fallback');
                            }}
                        />
                        <span class="fh-icon-fallback" aria-hidden="true">
                            <Rss size={22} strokeWidth={1.8} />
                        </span>
                    {:else}
                        <span class="fh-icon-fallback fh-icon-fallback--visible" aria-hidden="true">
                            <Rss size={22} strokeWidth={1.8} />
                        </span>
                    {/if}
                </div>

                <!-- Meta -->
                <div class="fh-meta">
                    <h1 class="fh-title">{feedInfo.feed_title}</h1>

                    <div class="fh-sub-row">
                        {#if feedInfo.feed_link}
                            <a
                                href={feedInfo.feed_link}
                                target="_blank"
                                rel="noopener noreferrer"
                                class="fh-domain"
                            >
                                {getDomain(feedInfo.feed_link)}
                                <ExternalLink size={10} strokeWidth={2} />
                            </a>
                        {/if}

                        {#if feedInfo.feed_lang}
                            <span class="fh-lang-badge">{feedInfo.feed_lang}</span>
                        {/if}

                        <span class="fh-subs" title="{$t('feed.subscribers')}">
                            <Users size={10} strokeWidth={2} />
                            {subscriberCount.toLocaleString()}
                        </span>
                    </div>

                    {#if feedInfo.feed_description}
                        <p class="fh-description">{feedInfo.feed_description}</p>
                    {/if}

                    {#if feedInfo.feed_last_update}
                        <p class="fh-last-update">
                            {$t('feed.updatedAt')} {formatDate(feedInfo.feed_last_update)}
                        </p>
                    {/if}
                </div>

                <!-- Follow / Unfollow -->
                <button
                    class="follow-btn"
                    class:follow-btn--following={followed}
                    disabled={followLoading}
                    onclick={toggleFollow}
                    aria-label={followed ? $t('feed.unfollowFeed') : $t('feed.followFeed')}
                >
                    {#if followLoading}
                        <span class="loading loading-spinner loading-xs"></span>
                    {:else if followed}
                        <Check size={13} strokeWidth={2.5} />
                        <span>{$t('feed.following')}</span>
                    {:else}
                        <Plus size={13} strokeWidth={2.5} />
                        <span>{$t('feed.follow')}</span>
                    {/if}
                </button>
            </header>
        {:else if infoError}
            <div class="header-error">
                <span class="header-error__icon" aria-hidden="true">⚠</span>
                {infoError}
                <button class="header-error__retry" onclick={loadFeedInfo}>{$t('feed.tryAgain')}</button>
            </div>
        {/if}

        <!-- Mode selector -->
        <div class="filter-bar" ontouchstart={(e) => e.stopPropagation()} ontouchmove={(e) => e.stopPropagation()} ontouchend={(e) => e.stopPropagation()}>
            <div class="mode-pill" role="group" aria-label="{$t('feed.filterMode', { default: 'Feed mode' })}">
                <button
                    class="mode-btn"
                    class:active={mode === 'recommendations'}
                    onclick={() => setMode('recommendations')}
                    aria-pressed={mode === 'recommendations'}
                >
                    <span>{$t('feed.forYou')}</span>
                </button>
                <button
                    class="mode-btn"
                    class:active={mode === 'recents'}
                    onclick={() => setMode('recents')}
                    aria-pressed={mode === 'recents'}
                >
                    <span>{$t('feed.recents')}</span>
                </button>
            </div>
        </div>

        <!-- Posts -->
        <div class="feed-wrap">
            {#if loading}
                {#each SKELETON_INITIAL as n (n)}
                    {@render skeletonCard()}
                {/each}
            {:else if error}
                <div class="state-error">
                    <p>{error}</p>
                    <button class="retry-btn" onclick={() => loadFeed(true)}>{$t('feed.tryAgain')}</button>
                </div>
            {:else if feed.length === 0}
                <p class="state-empty">{$t('feed.noPosts')}</p>
            {:else}
                {#each feed as item (item.item_id)}
                    <div use:trackView={item.item_id}>
                        <PostCard {item} server="" tags={item.tags || []} userTags={tagList} onTagClick={(tag) => goto(`/home?tag_id=${tag.tag_id}`)} />
                    </div>
                {/each}

                {#if loadingMore}
                    {#each SKELETON_MORE as n (n)}
                        {@render skeletonCard()}
                    {/each}
                {/if}

                {#if !hasMore}
                    <p class="end-label">{$t('feed.upToDate')}</p>
                {/if}
            {/if}

            <div bind:this={sentinelEl} class="sentinel" aria-hidden="true"></div>
        </div>

    </div>
</div>

<style>
/* ── Pull-to-refresh ────────────────────────── */
    .ptr-indicator {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        height: 40px;
        margin-top: -40px;
        margin-bottom: 0;
        pointer-events: none;
        opacity: 0;
        transition: opacity 0.15s ease;
    }
    .ptr-indicator.ptr-visible {
        opacity: 1;
    }
    .ptr-text {
        font-size: 13px;
        font-weight: 500;
        color: color-mix(in oklch, var(--color-base-content) 55%, transparent);
    }
    .spin {
        animation: rot 0.8s linear infinite;
        color: var(--color-accent);
    }
    @keyframes rot { to { transform: rotate(360deg); } }

/* ── Centralizer ─────────────────────────────────────────── */
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

    /* ── Top Header ──────────────────────────────────────────── */
    .top-header {
        display: flex;
        justify-content: flex-start;
        align-items: center;
        padding-top: 12px;
        padding-bottom: 4px;
    }

    .back-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        background: transparent;
        border: none;
        border-radius: 40px;
        padding: 8px;
        cursor: pointer;
        color: color-mix(in oklch, var(--color-base-content) 70%, transparent);
        transition: all 0.2s ease;
    }

    .back-btn:hover {
        background: color-mix(in oklch, var(--color-base-content) 10%, transparent);
        color: var(--color-base-content);
    }

    /* ── Feed Header ─────────────────────────────────────────── */
    .feed-header {
        display: flex;
        align-items: flex-start;
        gap: 14px;
        padding: 12px 0 18px;
        border-bottom: 1px solid var(--color-base-300);
    }

    .feed-header--skeleton {
        align-items: center;
    }

    /* ── Feed Icon ───────────────────────────────────────────── */
    .fh-icon-wrap {
        flex-shrink: 0;
        width: 52px;
        height: 52px;
        border-radius: 14px;
        overflow: hidden;
        background: color-mix(in oklch, var(--color-base-200) 70%, transparent);
        display: flex;
        align-items: center;
        justify-content: center;
        position: relative;
    }

    .fh-icon {
        width: 100%;
        height: 100%;
        object-fit: contain;
        position: relative;
        z-index: 1;
    }

    .fh-icon-fallback {
        position: absolute;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        color: var(--color-accent);
        opacity: 0.45;
        z-index: 0;
    }

    .fh-icon-fallback--visible {
        position: static;
        opacity: 0.45;
    }

    .fh-icon-wrap--fallback .fh-icon-fallback {
        position: static;
    }

    .fh-icon-sk {
        width: 52px !important;
        height: 52px !important;
        border-radius: 14px !important;
    }

    .fh-btn-sk {
        border-radius: 10px !important;
    }

    /* ── Feed Meta ───────────────────────────────────────────── */
    .fh-meta {
        flex: 1;
        min-width: 0;
        display: flex;
        flex-direction: column;
        gap: 3px;
    }

.fh-title {
font-family: var(--font-page-title);
        font-size: 1.75rem;
        font-weight: 400;
        letter-spacing: -0.02em;
        line-height: 1.15;
        color: var(--color-base-content);
        margin: 0;
        word-break: break-word;
    }

    .fh-sub-row {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
    }

    .fh-domain {
        display: inline-flex;
        align-items: center;
        gap: 3px;
        font-size: 11.5px;
        font-weight: 500;
        color: var(--color-accent);
        text-decoration: none;
        transition: opacity 130ms;
    }

    .fh-domain:hover {
        opacity: 0.7;
    }

    .fh-lang-badge {
        font-size: 10px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        padding: 1px 5px;
        border-radius: 4px;
        background: color-mix(in oklch, var(--color-base-200) 80%, transparent);
        color: color-mix(in oklch, var(--color-base-content) 55%, transparent);
    }

    .fh-subs {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        font-size: 11.5px;
        font-weight: 500;
        color: color-mix(in oklch, var(--color-base-content) 45%, transparent);
    }

    .fh-description {
        font-size: 12.5px;
        line-height: 1.45;
        color: color-mix(in oklch, var(--color-base-content) 60%, transparent);
        margin: 4px 0 0;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }

    .fh-last-update {
        font-size: 10.5px;
        color: color-mix(in oklch, var(--color-base-content) 35%, transparent);
        margin: 3px 0 0;
    }

    /* ── Follow Button ───────────────────────────────────────── */
    .follow-btn {
        flex-shrink: 0;
        display: inline-flex;
        align-items: center;
        gap: 5px;
        padding: 7px 14px;
        border-radius: 10px;
        border: 1.5px solid var(--color-accent);
        background: var(--color-accent);
        color: var(--color-base-100);
        font-size: 12.5px;
        font-weight: 700;
        cursor: pointer;
        transition:
            background 150ms ease,
            color 150ms ease,
            border-color 150ms ease;
        white-space: nowrap;
        align-self: flex-start;
        margin-top: 2px;
    }

    .follow-btn:hover:not(:disabled) {
        opacity: 0.85;
    }

    .follow-btn:disabled {
        cursor: default;
        opacity: 0.6;
    }

    .follow-btn--following {
        background: transparent;
        color: color-mix(in oklch, var(--color-base-content) 65%, transparent);
        border-color: var(--color-base-300);
    }

    .follow-btn--following:hover:not(:disabled) {
        background: color-mix(in oklch, var(--color-error, #e74c3c) 8%, transparent);
        border-color: color-mix(in oklch, var(--color-error, #e74c3c) 50%, transparent);
        color: var(--color-error, #e74c3c);
        opacity: 1;
    }

    /* ── Header Error ────────────────────────────────────────── */
    .header-error {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 12px 0;
        font-size: 12.5px;
        color: color-mix(in oklch, var(--color-error, #e74c3c) 75%, transparent);
        border-bottom: 1px solid var(--color-base-300);
        flex-wrap: wrap;
    }

    .header-error__icon {
        font-style: normal;
        font-size: 14px;
    }

    .header-error__retry {
        margin-left: auto;
        padding: 4px 12px;
        border-radius: 10px;
        border: 1px solid
            color-mix(in oklch, var(--color-error, #e74c3c) 40%, transparent);
        background: transparent;
        color: var(--color-error, #e74c3c);
        font-size: 11.5px;
        font-weight: 600;
        cursor: pointer;
        transition: background 130ms;
    }

    .header-error__retry:hover {
        background: color-mix(in oklch, var(--color-error, #e74c3c) 10%, transparent);
    }

    /* ── Filter Bar ──────────────────────────────────────────── */
.filter-bar {
display: flex;
align-items: center;
gap: 8px;
padding-top: 8px;
padding-bottom: 12px;
background: var(--color-base-100);
overflow-x: auto;
scrollbar-width: none;
touch-action: pan-y;
}

    .filter-bar::-webkit-scrollbar {
        display: none;
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
        transition:
            background 150ms ease,
            color 150ms ease,
            font-weight 0ms;
        white-space: nowrap;
    }

    .mode-btn.active {
        background: var(--color-base-100);
        color: var(--color-base-content);
        font-weight: 700;
        box-shadow: 0 1px 3px color-mix(in oklch, black 10%, transparent);
    }

    /* ── Feed Wrap ───────────────────────────────────────────── */
    .feed-wrap {
        border-top: 1px solid var(--color-base-300);
    }

    .sentinel {
        height: 1px;
    }

    /* ── Skeleton ────────────────────────────────────────────── */
    .skeleton-card {
        padding: 12px 20px 10px;
        border-bottom: 1px solid var(--color-base-300);
    }

    .sk-row {
        display: flex;
        align-items: center;
        gap: 6px;
    }

    .sk-ml-auto {
        margin-left: auto;
    }

    .sk-publisher {
        margin-bottom: 10px;
    }

    .sk-actions {
        gap: 6px;
    }

    .sk-bar,
    .sk-circle,
    .sk-dot {
        border-radius: 4px;
        background: linear-gradient(
            90deg,
            color-mix(in oklch, var(--color-base-300) 60%, transparent) 0%,
            color-mix(in oklch, var(--color-base-300) 90%, transparent) 40%,
            color-mix(in oklch, var(--color-base-300) 60%, transparent) 80%
        );
        background-size: 200% 100%;
        animation: shimmer 1.6s ease-in-out infinite;
    }

    .sk-circle {
        width: 16px;
        height: 16px;
        border-radius: 50%;
        flex-shrink: 0;
    }

    .sk-circle.sk-sm {
        width: 24px;
        height: 24px;
        border-radius: 6px;
    }

    .sk-dot {
        width: 3px;
        height: 3px;
        border-radius: 50%;
        flex-shrink: 0;
    }

    .sk-bar {
        height: 10px;
        flex-shrink: 0;
    }

    .sk-title {
        height: 14px;
        margin-bottom: 5px;
        border-radius: 5px;
    }

    .sk-desc {
        height: 11px;
        margin-bottom: 4px;
    }

    .skeleton-card:nth-child(1) .sk-bar,
    .skeleton-card:nth-child(1) .sk-circle {
        animation-delay: 0s;
    }
    .skeleton-card:nth-child(2) .sk-bar,
    .skeleton-card:nth-child(2) .sk-circle {
        animation-delay: 0.15s;
    }
    .skeleton-card:nth-child(3) .sk-bar,
    .skeleton-card:nth-child(3) .sk-circle {
        animation-delay: 0.3s;
    }
    .skeleton-card:nth-child(4) .sk-bar,
    .skeleton-card:nth-child(4) .sk-circle {
        animation-delay: 0.45s;
    }
    .skeleton-card:nth-child(5) .sk-bar,
    .skeleton-card:nth-child(5) .sk-circle {
        animation-delay: 0.6s;
    }
    .skeleton-card:nth-child(6) .sk-bar,
    .skeleton-card:nth-child(6) .sk-circle {
        animation-delay: 0.75s;
    }

    @keyframes shimmer {
        0% {
            background-position: 200% center;
        }
        100% {
            background-position: -200% center;
        }
    }

    /* ── States ──────────────────────────────────────────────── */
    .state-empty {
        text-align: center;
        padding: 48px 16px;
        color: color-mix(in oklch, var(--color-base-content) 40%, transparent);
        font-size: 15px;
    }

    .state-error {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 12px;
        padding: 48px 16px;
        color: color-mix(in oklch, var(--color-error, #e74c3c) 80%, transparent);
        font-size: 14px;
        text-align: center;
    }

    .retry-btn {
        padding: 7px 18px;
        border-radius: 6px;
        border: 1px solid
            color-mix(in oklch, var(--color-error, #e74c3c) 40%, transparent);
        background: transparent;
        color: var(--color-error, #e74c3c);
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
        transition: background 130ms;
    }

    .retry-btn:hover {
        background: color-mix(in oklch, var(--color-error, #e74c3c) 10%, transparent);
    }

    .end-label {
        text-align: center;
        padding: 28px 16px 40px;
        font-size: 12px;
        font-weight: 500;
        color: color-mix(in oklch, var(--color-base-content) 35%, transparent);
        letter-spacing: 0.03em;
    }
</style>