<script lang="ts">
    import { t } from 'svelte-i18n';
import { get } from 'svelte/store';
    import { goto } from '$app/navigation';
    import { ChevronDown, Sparkles } from '@lucide/svelte';
    import PostCard from '$lib/components/PostCard.svelte';
    import { showEventCovers, eventTitleBelow } from '$lib/stores/preferences';
    import { selectionMode, selectedPosts, pendingMotaPosts } from '$lib/stores/swipe';

    let {
        event,
        open = false,
        onToggle,
    } = $props<{
        rank?: number;
        open?: boolean;
        onToggle?: () => void;
        event: {
            summary: string;
            article_count: number;
            unique_feeds: number;
            affinity_pct?: number;
            articles: {
                item_id?: string;
                title: string;
                url: string;
                source?: string;
                feed_sha256?: string;
                feed_icon?: string;
                published_at?: string;
                image_url?: string;
                description?: string;
            }[];
        };
    }>();

    function domainOf(url?: string): string {
        try { return new URL(url || '').hostname.replace('www.', ''); } catch { return ''; }
    }

    function ddgIcon(domain: string): string {
        return `https://icons.duckduckgo.com/ip3/${domain}.ico`;
    }

    let publishers = $derived.by(() => {
        const seen = new Map<string, { name: string; icon: string }>();
        for (const a of event.articles) {
            const domain = domainOf(a.url);
            const name = a.source || domain;
            if (!name || seen.has(name)) continue;
            seen.set(name, { name, icon: a.feed_icon || (domain ? ddgIcon(domain) : '') });
            if (seen.size >= 3) break;
        }
        return [...seen.values()];
    });

    let moreSources = $derived(Math.max(0, event.unique_feeds - publishers.length));

    /** First image found among the cluster's own posts (hidden by its toggle). */
    let coverUrl = $derived.by(() => {
        if (!$showEventCovers) return null;
        for (const a of event.articles) {
            if (a.image_url) return a.image_url;
        }
        return null;
    });

    /** Earliest publication moment across the cluster's articles. */
    let earliestTs = $derived.by(() => {
        let min: number | null = null;
        for (const a of event.articles) {
            if (!a.published_at) continue;
            const ts = new Date(a.published_at).getTime();
            if (Number.isFinite(ts) && (min === null || ts < min)) min = ts;
        }
        return min;
    });

    function formatSince(ts: number): string {
        const d = new Date(ts);
        const diff = Date.now() - ts;
        const h = Math.floor(diff / 3600000);
        if (h < 24) return `${h}${get(t)('eventscard.hoursAgo')}`;
        return d.toLocaleDateString(undefined, { day: '2-digit', month: 'short' });
    }

    /** Expand/collapse is controlled by the parent (accordion: one open at a time). */
    function toggle() {
        onToggle?.();
    }

    function hideImage(e: Event) {
        (e.currentTarget as HTMLImageElement).style.display = 'none';
    }

    function formatDate(dateStr?: string): string {
        if (!dateStr) return '';
        const d = new Date(dateStr);
        const now = new Date();
        const diff = now.getTime() - d.getTime();
        const h = Math.floor(diff / 3600000);
        if (h < 24) return `${h}${get(t)('eventscard.hoursAgo')}`;
        return d.toLocaleDateString(undefined, { day: '2-digit', month: 'short' });
    }

    /** Map a cluster article onto PostCard's item contract (fields .map()). */
    function asPostItem(a: any) {
        return {
            item_id: a.item_id ?? '',
            title: a.title ?? '',
            description: a.description,
            author: undefined,
            link: a.url ?? '#',
            pub_date: a.published_at ?? '',
            feed_title: a.source,
            feed_icon: a.feed_icon,
            feed_sha256: a.feed_sha256,
            image_url: a.image_url,
        };
    }

    let embeddable = $derived(event.articles.filter((a: any) => a.item_id));

    // ── Multi-select (shared with the global selection bar in HomeTab) ─────
    function toggleSelect(article: any) {
        const item = asPostItem(article);
        selectedPosts.update(current => {
            const idx = current.findIndex((p: any) => p.item_id === item.item_id);
            if (idx >= 0) {
                const next = [...current.slice(0, idx), ...current.slice(idx + 1)];
                if (next.length === 0) selectionMode.set(false);
                return next;
            } else {
                if (!get(selectionMode)) selectionMode.set(true);
                return [...current, item];
            }
        });
    }

    /** Send every article of the cluster straight into the Mota chat. */
    async function sendTopicToMota() {
        const posts = embeddable.map(asPostItem);
        if (posts.length === 0) return;
        pendingMotaPosts.set(posts);
        await goto('/mota');
    }

    /* Embedded posts load in pages of 5 via the "+N more" button. */
    const MORE_PAGE = 5;
    let visibleCount = $state(8);
    let visiblePosts = $derived(embeddable.slice(0, visibleCount));
    let hiddenCount = $derived(Math.max(0, embeddable.length - visibleCount));

    function showMore() {
        visibleCount = Math.min(visibleCount + MORE_PAGE, embeddable.length);
    }
</script>

<article class="event-row" class:is-expanded={open}>
    <!-- svelte-ignore a11y_no_noninteractive_element_interactions, a11y_click_events_have_key_events -->
    <div
        class="row-trigger"
        role="button"
        tabindex="0"
        aria-expanded={open}
        onclick={toggle}
        onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); } }}
    >
        <div class="row-text" class:title-below={$eventTitleBelow}>
            <h3 class="event-title">{event.summary}</h3>
            <div class="meta-row">
                <div class="publishers-group">
                    {#each publishers as pub}
                        <div class="publisher-logo-wrap" title={pub.name}>
                            {#if pub.icon}
                                <img
                                    src={pub.icon}
                                    alt={pub.name}
                                    class="publisher-logo"
                                    loading="lazy"
                                    onerror={hideImage}
                                />
                            {:else}
                                <span class="publisher-fallback">{pub.name.slice(0, 1).toUpperCase()}</span>
                            {/if}
                        </div>
                    {/each}
                </div>
                <span class="meta-count">
                    {event.article_count}
                    {$t('eventscard.publications', { default: 'posts' })}
                </span>
                <span class="meta-sep" aria-hidden="true">·</span>
                {#if earliestTs !== null}
                    <span class="meta-since">
                        {$t('eventscard.started', { default: 'since' })} {formatSince(earliestTs)}
                    </span>
                {/if}
                {#if moreSources > 0}
                    <span class="more-sources">+{moreSources}</span>
                {/if}
                {#if event.affinity_pct != null}
                    {@const pct = event.affinity_pct}
                    <span
                        class="meta-affinity"
                        class:meta-affinity--mid={pct >= 30 && pct < 60}
                        class:meta-affinity--high={pct >= 60}
                        title={String($t('eventscard.fitTooltip', { default: 'How related this topic is to your reading profile' }))}
                    >{event.affinity_pct}%</span>
                {/if}
            </div>
        </div>

        {#if coverUrl}
            <img
                src={coverUrl}
                alt=""
                class="event-cover"
                loading="lazy"
                onerror={hideImage}
            />
        {/if}

        <div class="expand-chevron" class:rotated={open}>
            <ChevronDown size={16} strokeWidth={2} />
        </div>

        <button
            class="send-mota-btn"
            onclick={(e) => { e.stopPropagation(); sendTopicToMota(); }}
            title="{$t('eventscard.sendToMota')}"
            aria-label="{$t('eventscard.sendToMota')}"
        >
            <Sparkles size={14} strokeWidth={2} />
        </button>
    </div>

    {#if open}
        <div class="expanded-posts">
            {#each visiblePosts as article (article.item_id)}
                <div class="embedded-item">
                    <span class="embedded-dash" aria-hidden="true">–</span>
                    <PostCard
                        item={asPostItem(article)}
                        server=""
                        coverVariant="embedded"
                        selectionMode={$selectionMode}
                        selected={$selectedPosts.some((p: any) => p.item_id === article.item_id)}
                        onToggleSelect={toggleSelect}
                    />
                </div>
            {/each}
            {#if hiddenCount > 0}
                <button class="expanded-note expanded-more" onclick={showMore}>
                    +{hiddenCount}
                    {$t('eventscard.moreArticles', { default: 'more articles in this topic' })}
                </button>
            {/if}
        </div>
    {/if}
</article>

<style>
    /* Row rhythm mirrors PostCard: hairline separators, no boxes */
    .event-row {
        border-bottom: var(--ui-border-width, 1px) solid var(--ui-border-color);
        transition: background 120ms ease;
    }
    /* Expanded clusters stand out like selected posts: an accent outline
       wraps trigger + embedded posts, while the accent tint itself stays on
       the cluster bar only — the posts keep a neutral background. */
    .event-row.is-expanded {
        outline: 1px solid color-mix(in oklch, var(--color-accent) 55%, transparent);
        outline-offset: -1px;
        border-radius: var(--ui-hover-radius, var(--ui-radius-lg));
    }
    .event-row.is-expanded .row-trigger {
        background: color-mix(in oklch, var(--color-accent) 8%, transparent);
        border-radius: var(--ui-hover-radius, var(--ui-radius-lg)) var(--ui-hover-radius, var(--ui-radius-lg)) 0 0;
    }

    .row-trigger {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: var(--postcard-padding, 12px 6px 4px);
        cursor: pointer;
        user-select: none;
        transition: background 120ms ease, border-radius 120ms ease;
    }
    .row-trigger:hover {
        background: var(--color-base-200);
        border-radius: var(--ui-hover-radius, var(--ui-radius-lg));
    }
    .row-trigger:active {
        background: color-mix(in oklch, var(--color-base-content) 8%, transparent);
        border-radius: var(--ui-hover-radius, var(--ui-radius-lg));
    }

    .row-text {
        flex: 1;
        min-width: 0;
        display: flex;
        flex-direction: column;
    }
    .row-text.title-below {
        flex-direction: column-reverse;
    }
    .row-text.title-below .event-title {
        margin: 6px 0 0;
    }

    .event-title {
        font-family: var(--font-post-title);
        font-size: calc(16px * var(--event-title-scale, 1));
        font-weight: var(--postcard-title-weight, 500);
        line-height: 1.4;
        color: var(--color-base-content);
        margin: 0 0 6px;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden;
        transition: color 140ms;
    }
    .row-trigger:hover .event-title {
        color: var(--color-accent);
    }

    .meta-row {
        display: flex;
        align-items: center;
        gap: 7px;
        flex-wrap: wrap;
    }

    .meta-count {
        font-size: 11.5px;
        font-weight: 700;
        color: var(--color-accent);
        white-space: nowrap;
    }

    .meta-sep {
        color: var(--ui-text-faint, color-mix(in oklch, var(--color-base-content) 48%, transparent));
        font-size: 11px;
    }

    .meta-since {
        font-size: 11.5px;
        color: var(--ui-text-subtle, color-mix(in oklch, var(--color-base-content) 62%, transparent));
        white-space: nowrap;
    }

    /* Affinity % styled like the PostCard score pill (no icon), banded by
       value: neutral below 30, accent 30–59, success green 60+. */
    .meta-affinity {
        flex-shrink: 0;
        padding: 1px 6px;
        border-radius: var(--ui-radius-full);
        font-size: 10px;
        font-family: ui-monospace, monospace;
        line-height: 1.6;
        user-select: none;
        cursor: help;
        background: color-mix(in oklch, var(--color-base-content) 10%, transparent);
        color: var(--ui-text-subtle, color-mix(in oklch, var(--color-base-content) 62%, transparent));
    }
    .meta-affinity--mid {
        color: var(--color-accent);
        background: color-mix(in oklch, var(--color-accent) 14%, transparent);
    }
    .meta-affinity--high {
        color: var(--color-success, var(--color-accent));
        background: color-mix(in oklch, var(--color-success, var(--color-accent)) 16%, transparent);
    }

    .more-sources {
        font-size: 11px;
        color: var(--ui-text-subtle, color-mix(in oklch, var(--color-base-content) 62%, transparent));
        font-weight: 500;
        white-space: nowrap;
    }

    .publishers-group {
        display: flex;
        align-items: center;
    }
    .publisher-logo-wrap {
        width: 16px;
        height: 16px;
        border-radius: 50%;
        overflow: hidden;
        border: 1.5px solid var(--color-base-100);
        background: var(--color-base-200);
        display: flex;
        align-items: center;
        justify-content: center;
        margin-left: -4px;
    }
    .publisher-logo { width: 100%; height: 100%; object-fit: contain; }
    .publisher-fallback {
        font-size: 9px;
        font-weight: 700;
        color: var(--ui-text-subtle, color-mix(in oklch, var(--color-base-content) 62%, transparent));
    }

    /* Illustrative cover — first available article image, PostCard-style */
    .event-cover {
        width: 96px;
        height: 64px;
        object-fit: cover;
        border-radius: var(--cover-image-radius, var(--ui-radius-sm));
        flex-shrink: 0;
        transition: opacity 140ms ease;
    }

    /* ── Cover placement: full-width banner above/below the text row ────── */
    :global([data-event-cover-pos='top']) .row-trigger,
    :global([data-event-cover-pos='bottom']) .row-trigger {
        flex-direction: column;
        align-items: stretch;
        position: relative;
    }
    :global([data-event-cover-pos='top']) .event-cover {
        order: -1;
        width: 100%;
        height: var(--cover-max-h, 160px);
    }
    :global([data-event-cover-pos='bottom']) .event-cover {
        width: 100%;
        height: var(--cover-max-h, 160px);
    }
    :global([data-event-cover-pos='top']) .expand-chevron,
    :global([data-event-cover-pos='bottom']) .expand-chevron {
        position: absolute;
        right: 6px;
        padding: 3px;
        border-radius: var(--ui-radius-full, 999px);
        background: color-mix(in oklch, var(--color-base-100) 72%, transparent);
        box-shadow: 0 1px 4px color-mix(in oklch, black 18%, transparent);
    }
    :global([data-event-cover-pos='top']) .expand-chevron { top: 10px; }
    :global([data-event-cover-pos='bottom']) .expand-chevron { bottom: 10px; }

    .expand-chevron {
        color: var(--ui-text-muted, color-mix(in oklch, var(--color-base-content) 74%, transparent));
        flex-shrink: 0;
        display: flex;
        align-items: center;
        transition: transform 200ms ease;
    }
    .expand-chevron.rotated {
        transform: rotate(180deg);
    }

    /* Send the whole topic to the Mota chat */
    .send-mota-btn {
        flex-shrink: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        width: 28px;
        height: 28px;
        padding: 0;
        margin-left: 2px;
        border: none;
        border-radius: 50%;
        background: transparent;
        color: var(--ui-text-muted, color-mix(in oklch, var(--color-base-content) 74%, transparent));
        cursor: pointer;
        transition: background 140ms, color 140ms;
    }
    .send-mota-btn:hover {
        background: color-mix(in oklch, var(--color-accent) 14%, transparent);
        color: var(--color-accent);
    }

    /* ── Expanded: real PostCards, same rhythm as the feed ───── */
    .expanded-posts {
        padding: 0 4px 4px;
        /* Smaller type for the posts nested inside the cluster. */
        --postcard-title-scale: 0.9;
        --postcard-desc-scale: 0.9;
    }
    .embedded-item {
        display: flex;
        align-items: flex-start;
        gap: 18px;
    }
    .embedded-item :global(.post-card) {
        flex: 1;
        min-width: 0;
        padding-left: 0;
        padding-right: 0;
    }
    .embedded-dash {
        flex-shrink: 0;
        min-width: 16px;
        text-align: center;
        padding-top: 15px;
        font-size: 13px;
        font-weight: 700;
        line-height: 1;
        color: color-mix(in oklch, var(--color-base-content) 40%, transparent);
        user-select: none;
    }
    .expanded-note {
        display: block;
        width: 100%;
        border: none;
        background: transparent;
        font-family: inherit;
        font-size: 12px;
        font-weight: 500;
        color: var(--ui-text-subtle, color-mix(in oklch, var(--color-base-content) 62%, transparent));
        text-align: center;
        padding: 4px 0 16px;
        cursor: pointer;
        transition: color 140ms ease;
    }
    .expanded-more:hover {
        color: var(--color-accent);
    }
</style>
