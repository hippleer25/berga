<script lang="ts">
    import { page } from '$app/stores';
    import { goto, beforeNavigate } from '$app/navigation';
    import { onMount } from 'svelte';
    import { Heart, ThumbsDown, Bookmark, ArrowLeft, ExternalLink, FileText, Globe, AlertTriangle, Sparkles, Layers, Tag, X } from '@lucide/svelte';

import { t, locale } from 'svelte-i18n';
import { get } from 'svelte/store';
import { apiFetch } from '$lib/api';
import { flushPending } from '$lib/stores/viewTracker';
	import { clearFeedCache } from '$lib/stores/feedCache';

type ItemMeta = {
  item_id: string;
  title: string;
  link: string;
  feed_title?: string;
  feed_icon?: string;
  feed_sha256?: string;
  author?: string;
  pub_date?: string;
  liked?: boolean;
  disliked?: boolean;
  saved?: boolean;
};

    type SimilarArticle = {
        item_id: string;
        title: string;
        link: string;
        feed_title?: string;
        feed_icon?: string;
        similarity_score?: number;
    };

type ReaderData = {
  title: string;
  content_html: string;
  url: string;
  feed_title?: string;
  feed_icon?: string;
  feed_sha256?: string;
  author?: string;
  pub_date?: string;
  liked?: boolean;
  disliked?: boolean;
  saved?: boolean;
  similar_articles?: SimilarArticle[];
};

    let loadedItemId = $state<string | null>(null);

    let meta       = $state<ItemMeta | null>(null);
    let readerData = $state<ReaderData | null>(null);
    let loading    = $state(true);
    let error      = $state('');

    let liked          = $state(false);
    let disliked       = $state(false);
    let saved          = $state(false);
    let likeLoading    = $state(false);
    let dislikeLoading = $state(false);
    let saveLoading    = $state(false);

    // Resume state
    let resumeVisible  = $state(false);
    let resumeText     = $state('');
    let resumeLoading  = $state(false);
    let resumeError    = $state('');

type ArticleTag = { tag_id: number; name: string; color?: string; source: string };
type UserTag = { id: number; name: string; color?: string };

let articleTags = $state<ArticleTag[]>([]);
let userTags = $state<UserTag[]>([]);
let tagDropdownOpen = $state(false);
let tagAssignLoading = $state(false);

// View toggle
let webView = $state(false);
let iframeLoading = $state(false);
let iframeBlocked = $state(false);
let iframeTimeout: ReturnType<typeof setTimeout> | null = null;

    const IFRAME_TIMEOUT_MS = 12_000;

    async function loadArticle(id: string) {
        if (!id || id === loadedItemId) return;

        loadedItemId = id;
        loading = true;
        error = '';
        meta = null;
        readerData = null;

        liked = false;
        disliked = false;
        saved = false;
        likeLoading = false;
        dislikeLoading = false;
        saveLoading = false;

        resumeVisible = false;
        resumeText = '';
        resumeLoading = false;
        resumeError = '';

        webView = false;
        iframeLoading = false;
        iframeBlocked = false;
        if (iframeTimeout) {
            clearTimeout(iframeTimeout);
            iframeTimeout = null;
        }

        try {
const res = await apiFetch(`/api/load-text/${id}`, {
      method: 'POST',
      credentials: 'include'
    });

            if (res.status === 401) { goto('/'); return; }
            if (!res.ok) throw new Error(`${get(t)('article.loadError')} (${res.status})`);

            const data: ReaderData = await res.json();
            readerData = data;

            apiFetch(`/api/feed/${id}/read`, {
                method: 'POST',
                credentials: 'include',
            }).catch(() => {});

            const feedTitleFallback = (() => {
                try { return new URL(data.url).hostname.replace('www.', ''); }
                catch { return ''; }
            })();

      meta = {
        item_id: id,
        title: data.title ?? '',
        link: data.url ?? '',
        feed_title: data.feed_title ?? feedTitleFallback,
        feed_icon: data.feed_icon,
        feed_sha256: data.feed_sha256,
        author: data.author,
        pub_date: data.pub_date,
        liked: data.liked,
        disliked: data.disliked,
        saved: data.saved,
      };

            liked    = data.liked    ?? false;
            disliked = data.disliked ?? false;
            saved    = data.saved    ?? false;

		if (data.title) document.title = `${data.title} — Berga`;
		loadArticleTags(id);
	} catch (err: any) {
            error = err.message || get(t)('article.loadError');
	} finally {
		loading = false;
	}
 }

async function loadArticleTags(id: string) {
	try {
		const [tagRes, userRes] = await Promise.all([
			apiFetch(`/api/tags/article/${id}`, { credentials: 'include' }),
			apiFetch(`/api/tags`, { credentials: 'include' }),
		]);
		if (tagRes.ok) {
			const data = await tagRes.json();
			articleTags = data.tags ?? [];
		}
		if (userRes.ok) {
			const data = await userRes.json();
			userTags = data.tags ?? [];
		}
	} catch { /* non-critical */ }
}

async function assignTag(tagId: number) {
	if (!loadedItemId || tagAssignLoading) return;
	tagAssignLoading = true;
	try {
		const res = await apiFetch('/api/tags/assign', {
			method: 'POST',
			credentials: 'include',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ item_id: loadedItemId, tag_id: tagId }),
		});
if (res.ok) {
				clearFeedCache();
				const ut = userTags.find(t => t.id === tagId);
			if (ut && !articleTags.some(t => t.tag_id === tagId)) {
				articleTags = [...articleTags, { tag_id: ut.id, name: ut.name, color: ut.color, source: 'manual' }];
			}
			tagDropdownOpen = false;
		}
	} catch { /* */ }
	finally { tagAssignLoading = false; }
}

async function unassignTag(tagId: number) {
	if (!loadedItemId || tagAssignLoading) return;
	tagAssignLoading = true;
	try {
		const res = await apiFetch('/api/tags/assign', {
			method: 'DELETE',
			credentials: 'include',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ item_id: loadedItemId, tag_id: tagId }),
		});
if (res.ok) {
				clearFeedCache();
				articleTags = articleTags.filter(t => t.tag_id !== tagId);
		}
	} catch { /* */ }
	finally { tagAssignLoading = false; }
}

function toggleTagDropdown() {
	tagDropdownOpen = !tagDropdownOpen;
}

function outsideClick(e: MouseEvent) {
	if (tagDropdownOpen) tagDropdownOpen = false;
}

	onMount(() => {
    const id = $page.params.item_id;
    if (id) loadArticle(id);

	beforeNavigate(() => {
		flushPending();
	});
});

    $effect(() => {
        const id = $page.params.item_id;
        if (id && id !== loadedItemId) {
            loadArticle(id);
        }
    });

function formatDate(dateStr?: string) {
    if (!dateStr) return '';
    return new Date(dateStr).toLocaleString(get(locale) ?? 'en', {
            day: '2-digit', month: 'long', year: 'numeric',
            hour: '2-digit', minute: '2-digit'
        });
    }

    function toggleView() {
        webView = !webView;
        if (webView) {
            iframeLoading = true;
            iframeBlocked = false;
            iframeTimeout = setTimeout(() => {
                if (iframeLoading) {
                    iframeLoading = false;
                    iframeBlocked = true;
                }
            }, IFRAME_TIMEOUT_MS);
        } else {
            clearIframeState();
        }
    }

    function clearIframeState() {
        iframeLoading = false;
        iframeBlocked = false;
        if (iframeTimeout) {
            clearTimeout(iframeTimeout);
            iframeTimeout = null;
        }
    }

    function onIframeLoad() {
        if (iframeTimeout) { clearTimeout(iframeTimeout); iframeTimeout = null; }
        if (iframeLoading) iframeLoading = false;
    }

    function onIframeError() {
        if (iframeTimeout) { clearTimeout(iframeTimeout); iframeTimeout = null; }
        iframeLoading = false;
        iframeBlocked = true;
    }

    async function fetchResume() {
        if (resumeLoading) return;

        if (resumeText && !resumeError) {
            resumeVisible = !resumeVisible;
            return;
        }

        resumeVisible = true;
        resumeLoading = true;
        resumeError   = '';
        resumeText    = '';

        try {
const res = await apiFetch(`/api/mota/resume/${loadedItemId}`, {
        method: 'POST',
        credentials: 'include',
      });

            if (res.status === 401) { goto('/'); return; }
            if (!res.ok) throw new Error(`${get(t)('article.loadError')} (${res.status})`);

            const reader = res.body?.getReader();
            const decoder = new TextDecoder();
            if (!reader) throw new Error(get(t)('article.streamUnavailable'));

            let buffer = '';
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() ?? '';

                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue;
                    const chunk = line.slice(6);
                    if (chunk === '[DONE]') break;
                    resumeText += chunk;
                }
            }
        } catch (err: any) {
            resumeError = err.message || get(t)('article.resumeError');
        } finally {
            resumeLoading = false;
        }
    }

    async function sendVote(type: 'like' | 'dislike') {
        if ((type === 'like' && likeLoading) || (type === 'dislike' && dislikeLoading)) return;
        if (type === 'like') likeLoading = true;
        else dislikeLoading = true;

        try {
const res = await apiFetch(`/api/feed/${loadedItemId}/${type}`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' }
    });
            if (res.status === 401) { goto('/'); return; }
            if (!res.ok) throw new Error();

            if (type === 'like') {
                liked = !liked;
                if (liked) disliked = false;
            } else {
                disliked = !disliked;
                if (disliked) liked = false;
            }
        } catch {
            console.error(`Erro ao votar ${type}`);
        } finally {
            if (type === 'like') likeLoading = false;
            else dislikeLoading = false;
        }
    }

async function toggleSave() {
  if (saveLoading) return;
  saveLoading = true;
  try {
    const res = await apiFetch(`/api/feed/${loadedItemId}/save`, {
      method: saved ? 'DELETE' : 'POST',
      credentials: 'include'
    });
    if (!res.ok) throw new Error();
    saved = !saved;
  } catch {
    console.error('Erro ao salvar');
  } finally {
    saveLoading = false;
  }
}
</script>

<svelte:head>
	{#if meta?.title}
	<title>{meta.title} — Berga</title>
	<meta property="og:title" content={meta.title} />
	<meta property="og:url" content={$page.url.href} />
	{/if}
</svelte:head>

<svelte:window onclick={outsideClick} />

<div class="reader-page" class:web-mode={webView}>

    <!-- ── Top Navigation (Ghost Toolbar) ────────────────────── -->
    <header class="top-bar-wrap">
        <div class="top-bar">
            <button class="ghost-btn back-btn" onclick={() => goto('/home')} title="{$t('article.backToFeed')}">
                <ArrowLeft size={18} />
                <span class="back-label">{$t('article.backToFeed')}</span>
            </button>

        <div class="top-spacer"></div>

        <div class="top-actions">
          <button
            class="ghost-btn"
            class:active-view={webView}
            onclick={toggleView}
            title={webView ? $t('article.viewExtractedText') : $t('article.viewOriginalPage')}
            disabled={loading || !!error}
          >
            {#if webView}
              <FileText size={16} />
            {:else}
              <Globe size={16} />
            {/if}
          </button>

          {#if meta?.link}
            <a
              href={meta.link}
              target="_blank"
              rel="noopener noreferrer"
              class="ghost-btn"
              title="{$t('article.openOriginal')}"
            >
              <ExternalLink size={16} />
            </a>
          {/if}
        </div>
        </div>
    </header>

    <!-- ── Web view ──────────────────────────────────────────── -->
    {#if webView && meta?.link}
        <div class="web-view">
            <iframe
                src={meta.link}
                title={meta.title ?? $t('article.originalPage')}
                sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-popups-to-escape-sandbox"
                loading="lazy"
                class:hidden={iframeBlocked}
                onload={onIframeLoad}
                onerror={onIframeError}
            ></iframe>

            {#if iframeLoading}
                <div class="iframe-overlay">
                    <span class="loading loading-spinner loading-lg"></span>
                </div>
            {/if}

            {#if iframeBlocked}
                <div class="iframe-blocked">
                    <div class="blocked-content">
                        <AlertTriangle size={32} class="blocked-icon" />
                        <p class="blocked-title">{$t('article.iframeBlockedTitle')}</p>
                        <p class="blocked-body">
                            {meta.feed_title ?? $t('article.thisSite')} {$t('article.iframeBlockedBody')}
                        </p>
                        <a href={meta.link} target="_blank" rel="noopener noreferrer" class="blocked-link">
                            {$t('article.openOriginalSite')} <ExternalLink size={14} />
                        </a>
                        <button class="ghost-btn" onclick={toggleView} style="margin-top: 12px;">
                            {$t('article.backToExtractedText')}
                        </button>
                    </div>
                </div>
            {/if}
        </div>

    <!-- ── Reader view ────────────────────────────────────────── -->
    {:else}
        <main class="reader-scroll">
            <div class="reader-content">

                {#if loading}
                    <div class="state-loading">
                        <span class="loading loading-spinner loading-lg"></span>
                    </div>

                {:else if error}
                    <div class="state-error">
                        <p>{error}</p>
                        {#if meta?.link}
                            <a href={meta.link} target="_blank" rel="noopener noreferrer" class="ghost-btn">
                                {$t('article.openOriginalSite')} <ExternalLink size={14} />
                            </a>
                        {/if}
                    </div>

                {:else if readerData}
                    <article class="article-header">

          <div class="meta-row">
            <a
              href={meta?.feed_sha256 ? `/f/${meta.feed_sha256}` : undefined}
              class="meta-feed-link"
            >
              {#if meta?.feed_icon}
                <img src={meta.feed_icon} alt={meta.feed_title ?? ''} class="meta-feed-icon" onerror={(e: Event) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }} />
              {/if}
              <span class="meta-feed-title">{meta?.feed_title ?? ''}</span>
            </a>
            {#if meta?.author}
              <span class="meta-sep">·</span>
              <span class="meta-author">{meta.author}</span>
            {/if}
            {#if meta?.pub_date}
              <span class="meta-date">{formatDate(meta.pub_date)}</span>
            {/if}
          </div>

          <h1 class="article-title">{readerData.title}</h1>

          <div class="article-actions">
            <button
              class="action-btn"
              class:action-active={liked}
              onclick={() => sendVote('like')}
              title="{$t('article.like')}"
              disabled={likeLoading}
            >
              {#if likeLoading}
                <span class="loading loading-spinner loading-xs"></span>
              {:else}
                <Heart size={15} fill={liked ? 'currentColor' : 'none'} />
              {/if}
            </button>

            <button
              class="action-btn"
              class:action-active={disliked}
              onclick={() => sendVote('dislike')}
              title="{$t('article.dislike')}"
              disabled={dislikeLoading}
            >
              {#if dislikeLoading}
                <span class="loading loading-spinner loading-xs"></span>
              {:else}
                <ThumbsDown size={15} fill={disliked ? 'currentColor' : 'none'} />
              {/if}
            </button>

		<button
			class="action-btn action-save"
			class:action-save-active={saved}
			onclick={toggleSave}
			title="{$t('article.save')}"
			disabled={saveLoading}
		>
			{#if saveLoading}
				<span class="loading loading-spinner loading-xs"></span>
			{:else}
				<Bookmark size={15} fill={saved ? 'currentColor' : 'none'} />
			{/if}
		</button>

		<div class="tag-assign-wrap">
			<button
				class="action-btn"
				onclick={toggleTagDropdown}
				title="{$t('article.tagArticle')}"
				aria-expanded={tagDropdownOpen}
				aria-haspopup="listbox"
			>
				<Tag size={15} />
			</button>
			{#if tagDropdownOpen}
				<div class="tag-dropdown" onclick={(e) => e.stopPropagation()}>
					{#if userTags.filter(ut => !articleTags.some(at => at.tag_id === ut.id)).length === 0}
						<p class="tag-dropdown-empty">{$t('article.allTagsAssigned')}</p>
					{:else}
						{#each userTags.filter(ut => !articleTags.some(at => at.tag_id === ut.id)) as ut (ut.id)}
							<button
								class="tag-dropdown-item"
								onclick={() => assignTag(ut.id)}
								disabled={tagAssignLoading}
							>
								<span class="tag-dot" style="background: {ut.color || '#3b82f6'}"></span>
								{ut.name}
							</button>
						{/each}
					{/if}
				</div>
			{/if}
		</div>
	</div>

	{#if articleTags.length > 0}
		<div class="article-tag-chips">
			{#each articleTags as at (at.tag_id)}
				<span class="article-tag-chip" style="--chip-color: {at.color || '#3b82f6'}">
					{at.name}
					<span class="chip-source">{$t(`tags.source_${at.source}`)}</span>
					{#if at.source === 'manual'}
						<button
							class="chip-remove"
							onclick={() => unassignTag(at.tag_id)}
							disabled={tagAssignLoading}
							title="{$t('tags.removeTag')}"
							aria-label="{$t('tags.removeTag')}: {at.name}"
						>
							<X size={10} />
						</button>
					{/if}
				</span>
			{/each}
		</div>
	{/if}

          <!-- ── Caixa de resumo (AI) ─────────────────── -->
                        <button
                            class="resume-toggle"
                            onclick={fetchResume}
                            disabled={resumeLoading}
                        >
                            {#if resumeLoading && !resumeText}
                                <span class="loading loading-spinner loading-xs"></span>
                            {:else}
                                <Sparkles size={14} />
                            {/if}
                            <span>{resumeVisible && resumeText ? $t('article.hideSummary') : $t('article.summarizeText')}</span>
                        </button>

                        {#if resumeVisible}
                            <div class="resume-box">
                                {#if resumeLoading && !resumeText}
                                    <div class="resume-skeleton">
                                        <span class="sk-line" style="width: 92%"></span>
                                        <span class="sk-line" style="width: 78%"></span>
                                        <span class="sk-line" style="width: 85%"></span>
                                        <span class="sk-line" style="width: 60%"></span>
                                    </div>
                                {:else if resumeError}
                                    <p class="resume-error-text">{resumeError}</p>
                                {:else}
                                    <p class="resume-text">
                                        {resumeText}
                                        {#if resumeLoading}<span class="resume-cursor"></span>{/if}
                                    </p>
                                {/if}
                            </div>
                        {/if}

                    </article>

                    <div class="article-body">
                        {@html readerData.content_html}
                    </div>

                    <!-- ── Find Similars Section ─────────────────────── -->
                    {#if readerData.similar_articles && readerData.similar_articles.length > 0}
                        <section class="similar-section">
                            <div class="similar-header">
                                <Layers size={18} />
                                <h2 class="similar-title">{$t('article.findSimilars')}</h2>
                            </div>
                            <div class="similar-list">
                                {#each readerData.similar_articles as sim}
                                    <a href="/a/{sim.item_id}" class="similar-item" title={sim.title}>
                                        <div class="similar-item-left">
                                            {#if sim.feed_icon}
                                                <img src={sim.feed_icon} alt={sim.feed_title} class="similar-source-icon" />
                                            {/if}
                                            <div class="similar-item-text">
                                                {#if sim.feed_title}
                                                    <span class="similar-source-name">{sim.feed_title}</span>
                                                {/if}
                                                <h3 class="similar-item-title">{sim.title}</h3>
                                            </div>
                                        </div>
                                        {#if sim.similarity_score}
                                            <span class="similar-score">{(sim.similarity_score * 100).toFixed(0)}%</span>
                                        {/if}
                                    </a>
                                {/each}
                            </div>
                        </section>
                    {/if}

                {/if}

            </div>
        </main>
    {/if}

</div>

<style>
    /* ── Page Shell ──────────────────────────────────────────── */
.reader-page {
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  background: var(--color-base-100);
  padding-bottom: calc(64px + env(safe-area-inset-bottom, 8px));
}
    .reader-page.web-mode {
        height: 100dvh;
        overflow: hidden;
        padding-bottom: 0;
    }
    @media (min-width: 768px) {
        .reader-page { padding-bottom: 0; }
    }

    /* ── Top Bar (Ghost Toolbar) ─────────────────────────────── */
    .top-bar-wrap {
        position: sticky;
        top: 0;
        z-index: 20;
        background: var(--color-base-100);
        border-bottom: 1px solid var(--color-base-300);
    }

    .top-bar {
        display: flex;
        align-items: center;
        gap: 4px;
        padding: 8px 16px;
        max-width: 42rem;
        width: 100%;
        margin: 0 auto;
    }
    @media (min-width: 768px) {
        .top-bar {
            margin-left: max(240px, calc(50vw - 21rem));
            margin-right: auto;
            padding-left: 0;
            padding-right: 0;
        }
    }

    .ghost-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        background: transparent;
        border: none;
        padding: 6px 8px;
        border-radius: 6px;
        color: color-mix(in oklch, var(--color-base-content) 60%, transparent);
        cursor: pointer;
        text-decoration: none;
        transition: background 140ms, color 140ms;
        font-size: 13px;
        font-weight: 500;
    }
    .ghost-btn:hover {
        background: var(--color-base-200);
        color: var(--color-base-content);
    }
    .ghost-btn:disabled { opacity: 0.4; cursor: default; }

/* Active view state */
.ghost-btn.active-view { color: var(--color-accent); }

    .back-btn { margin-right: 8px; }
    .back-label { display: none; }
    @media (min-width: 768px) { .back-label { display: inline; } }

.top-spacer { flex: 1; }

.top-actions { display: flex; align-items: center; gap: 2px; }

    /* ── Content Centralizer ─────────────────────────────────── */
    .reader-content {
        max-width: 42rem;
        margin: 0 auto;
        padding: 2rem 16px 5rem;
    }
    @media (min-width: 768px) {
        .reader-content {
            padding: 2rem 0 5rem;
            margin-left: max(240px, calc(50vw - 21rem));
            margin-right: auto;
        }
    }

    /* ── Article Header ──────────────────────────────────────── */
    .article-header {
        margin-bottom: 3rem;
    }

.meta-row {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-bottom: 16px;
  min-width: 0;
}
.meta-feed-link {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  min-width: 0;
  flex: 0 1 auto;
  text-decoration: none;
  color: inherit;
}
.meta-feed-icon { width: 15px; height: 15px; border-radius: 50%; object-fit: contain; flex-shrink: 0; }
.meta-feed-title {
  font-size: 11.5px;
  font-weight: 700;
  color: var(--color-accent);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 0 1 auto;
  min-width: 0;
}
.meta-author {
  font-size: 11.5px;
  color: color-mix(in oklch, var(--color-base-content) 45%, transparent);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 0 1 auto;
  min-width: 0;
}
.meta-sep { font-size: 11px; color: color-mix(in oklch, var(--color-base-content) 25%, transparent); flex-shrink: 0; }
.meta-date {
  margin-left: auto;
  font-size: 11px;
  color: color-mix(in oklch, var(--color-base-content) 35%, transparent);
  white-space: nowrap;
  flex-shrink: 0;
  padding-left: 8px;
}

    /* Título em Serifa (Georgia), pesamento e espaçamento de jornal */
.article-title {
  font-family: var(--font-post-title);
  font-size: clamp(1.8rem, 5vw, 2.5rem);
  font-weight: 500;
  line-height: 1.2;
  letter-spacing: -0.02em;
  color: var(--color-base-content);
  margin: 0 0 12px;
}

.article-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  margin-bottom: 16px;
}

.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 6px;
  border: none;
  background: transparent;
  color: color-mix(in oklch, var(--color-base-content) 40%, transparent);
  cursor: pointer;
  transition: background 120ms, color 120ms;
}
.action-btn:hover {
  background: color-mix(in oklch, var(--color-base-content) 8%, transparent);
  color: var(--color-base-content);
}
.action-btn:active { transform: scale(0.88); }
.action-btn:disabled { opacity: 0.5; cursor: default; }
.action-btn.action-active { color: var(--color-error); }
.action-btn.action-save { margin-left: auto; }
.action-btn.action-save-active { color: var(--color-accent); }

.tag-assign-wrap { position: relative; margin-left: 4px; }
.tag-dropdown {
	position: absolute;
	top: 100%;
	left: 0;
	z-index: 30;
	min-width: 180px;
	max-height: 220px;
	overflow-y: auto;
	background: var(--color-base-100);
	border: 1px solid var(--color-base-300);
	border-radius: 8px;
	box-shadow: 0 4px 16px rgba(0,0,0,.12);
	padding: 4px;
	margin-top: 4px;
}
.tag-dropdown-empty { font-size: 12px; color: color-mix(in oklch, var(--color-base-content) 50%, transparent); padding: 8px; margin: 0; }
.tag-dropdown-item {
	display: flex;
	align-items: center;
	gap: 8px;
	width: 100%;
	padding: 7px 10px;
	border: none;
	border-radius: 6px;
	background: transparent;
	color: var(--color-base-content);
	font-size: 13px;
	cursor: pointer;
	text-align: left;
	transition: background 100ms;
}
.tag-dropdown-item:hover { background: color-mix(in oklch, var(--color-base-content) 8%, transparent); }
.tag-dropdown-item:disabled { opacity: .5; cursor: default; }
.tag-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }

.article-tag-chips { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }
.article-tag-chip {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	font-size: 11px;
	font-weight: 600;
	padding: 3px 8px;
	border-radius: 999px;
	background: color-mix(in oklch, var(--chip-color) 14%, transparent);
	color: var(--chip-color);
	white-space: nowrap;
	line-height: 1.5;
}
.chip-source {
	font-size: 9px;
	font-weight: 500;
	opacity: .7;
	text-transform: lowercase;
}
.chip-remove {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	width: 14px;
	height: 14px;
	border: none;
	border-radius: 50%;
	background: color-mix(in oklch, var(--chip-color) 25%, transparent);
	color: inherit;
	cursor: pointer;
	padding: 0;
	margin-left: 2px;
	transition: background 100ms;
}
.chip-remove:hover { background: color-mix(in oklch, var(--chip-color) 40%, transparent); }

    /* ── AI Resume ───────────────────────────────────────────── */
    .resume-toggle {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: transparent;
        border: 1px solid var(--color-base-300);
        color: var(--color-accent);
        font-size: 13px;
        font-weight: 500;
        padding: 6px 12px;
        border-radius: 6px;
        cursor: pointer;
        transition: background 140ms, border-color 140ms;
    }
    .resume-toggle:hover {
        background: color-mix(in oklch, var(--color-accent) 8%, transparent);
        border-color: var(--color-accent);
    }
    .resume-toggle:disabled { opacity: 0.5; cursor: default; }

    .resume-box {
        margin-top: 16px;
        padding: 16px;
        background: var(--color-base-200);
        border-left: 3px solid var(--color-accent); /* Smart insertion highlight */
        border-radius: 0 8px 8px 0;
        min-height: 4rem;
    }

    .resume-text {
        font-size: 0.95rem;
        line-height: 1.7;
        color: var(--color-base-content);
        margin: 0;
        white-space: pre-wrap;
    }
    .resume-cursor {
        display: inline-block;
        width: 2px;
        height: 0.95em;
        background: var(--color-accent);
        margin-left: 2px;
        vertical-align: text-bottom;
        border-radius: 1px;
        animation: blink 0.9s step-end infinite;
    }
    @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }

    .resume-skeleton { display: flex; flex-direction: column; gap: 8px; }
    .sk-line {
        display: block; height: 12px; border-radius: 4px;
        background: color-mix(in oklch, var(--color-base-content) 12%, transparent);
        animation: shimmer 1.4s ease-in-out infinite;
    }
    @keyframes shimmer { 0%, 100% { opacity: 0.5; } 50% { opacity: 1; } }
    .resume-error-text { font-size: 14px; color: var(--color-error); margin: 0; }

    /* ── Article Body ────────────────────────────────────────── */
.article-body {
font-family: var(--font-article-body);
font-size: 1.125rem;
        line-height: 1.8;
        color: color-mix(in oklch, var(--color-base-content) 85%, transparent);
    }
    .article-body :global(p) { margin: 0 0 1.5em; }
.article-body :global(h2), .article-body :global(h3), .article-body :global(h4) {
font-family: var(--font-post-title);
        color: var(--color-base-content);
        margin: 2em 0 0.8em; line-height: 1.3;
    }
    .article-body :global(h2) { font-size: 1.5rem; }
    .article-body :global(h3) { font-size: 1.25rem; }
    .article-body :global(a) {
        color: var(--color-accent); text-decoration: underline; text-underline-offset: 3px;
    }
    .article-body :global(img) { max-width: 100%; height: auto; border-radius: 8px; margin: 2em 0; display: block; }
    .article-body :global(blockquote) {
        border-left: 3px solid var(--color-accent);
        margin: 1.5em 0; padding: 0.25em 1em; font-style: italic;
        color: color-mix(in oklch, var(--color-base-content) 65%, transparent);
    }
    .article-body :global(pre) { background: var(--color-base-200); border-radius: 6px; padding: 1em; overflow-x: auto; font-size: 0.9em; margin: 1.5em 0; }
    .article-body :global(hr) { border: none; border-top: 1px solid var(--color-base-300); margin: 3em 0; }

    /* ── Similar Articles ────────────────────────────────────── */
    .similar-section {
        margin-top: 4rem;
        padding-top: 2rem;
        border-top: 1px solid var(--color-base-300);
    }
    .similar-header { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; color: var(--color-base-content); }
    .similar-title { font-size: 1.1rem; font-weight: 700; margin: 0; letter-spacing: -0.01em; }

    .similar-list { display: flex; flex-direction: column; }
    .similar-item {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 12px 0;
        border-bottom: 1px solid var(--color-base-300);
        text-decoration: none;
        color: var(--color-base-content);
        transition: background 120ms;
    }
    .similar-item:last-child { border-bottom: none; }
    .similar-item:hover {
  background: color-mix(in oklch, var(--color-base-content) 4%, transparent);
  margin: 0 -16px;
  padding: 12px 16px;
  border-radius: 6px;
  border-color: transparent;
}
.similar-item:active {
  background: color-mix(in oklch, var(--color-base-content) 8%, transparent);
}

    .similar-item-left { display: flex; align-items: center; gap: 12px; min-width: 0; flex: 1; }
.similar-source-icon { width: 15px; height: 15px; border-radius: 50%; object-fit: contain; flex-shrink: 0; }
.similar-item-text { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.similar-source-name { font-size: 11.5px; font-weight: 700; color: var(--color-accent); }
.similar-item-title {
font-family: var(--font-post-title);
  font-size: 14px;
  font-weight: 500;
  line-height: 1.4;
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--color-base-content);
}
.similar-item:hover .similar-item-title {
  color: var(--color-accent);
  transition: color 140ms;
}
.similar-score {
  font-size: 11px;
  font-weight: 700;
  color: var(--color-accent);
  background: color-mix(in oklch, var(--color-accent) 10%, transparent);
  padding: 2px 8px;
  border-radius: 6px;
  margin-left: 16px;
  flex-shrink: 0;
}

    /* ── States & Webview ────────────────────────────────────── */
    .state-loading { display: flex; justify-content: center; padding: 8rem 0; }
    .state-error { display: flex; flex-direction: column; align-items: center; gap: 1rem; padding: 6rem 0; text-align: center; opacity: 0.7; }

    .web-view { flex: 1; min-height: 0; position: relative; display: flex; flex-direction: column; background: #fff; }
    .web-view iframe { flex: 1; width: 100%; height: 100%; border: none; }
    .web-view iframe.hidden { display: none; }
    .iframe-overlay { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; background: var(--color-base-100); pointer-events: none; }

    .iframe-blocked { flex: 1; display: flex; align-items: center; justify-content: center; padding: 3rem 1.5rem; }
    .blocked-content { display: flex; flex-direction: column; align-items: center; text-align: center; max-width: 24rem; gap: 8px; }
    .blocked-icon { color: var(--color-warning); margin-bottom: 8px; }
    .blocked-title { font-size: 1.1rem; font-weight: 700; color: var(--color-base-content); margin: 0; }
    .blocked-body { font-size: 0.9rem; color: color-mix(in oklch, var(--color-base-content) 60%, transparent); margin: 0; line-height: 1.6; }
    .blocked-link {
        display: inline-flex; align-items: center; gap: 6px; margin-top: 12px;
        padding: 8px 16px; border-radius: 6px; background: var(--color-base-200);
        color: var(--color-accent); font-size: 14px; font-weight: 600;
        text-decoration: none; transition: background 120ms;
    }
    .blocked-link:hover { background: var(--color-base-300); }
</style>