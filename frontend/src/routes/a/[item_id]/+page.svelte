<script lang="ts">
    import { page } from '$app/stores';
    import { goto, beforeNavigate } from '$app/navigation';
    import { onMount } from 'svelte';
    import { Heart, ThumbsDown, Bookmark, ArrowLeft, ExternalLink, FileText, Globe, AlertTriangle, Sparkles, Layers, Tag, X, Highlighter, Trash2 } from '@lucide/svelte';

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
    archived?: boolean;
    similar_articles?: SimilarArticle[];
    highlights?: Highlight[];
};

type Highlight = {
    id: number;
    text: string;
    color: string;
    sort_order: number;
};

const HIGHLIGHT_PRESETS = ['#FFEB3B', '#66BB6A', '#42A5F5', '#F48FB1'] as const;

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

// Highlights
let highlights = $state<Highlight[]>([]);
let highlightMenu = $state<{ x: number; y: number; text: string } | null>(null);
let highlightPopover = $state<{ x: number; y: number; highlightId: number } | null>(null);
let highlightLoading = $state(false);
let suppressOutsideClick = false;
let selectionDebounceTimer: ReturnType<typeof setTimeout> | null = null;
let articleBodyEl: HTMLDivElement | undefined = $state();

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

        liked = data.liked ?? false;
        disliked = data.disliked ?? false;
        saved = data.saved ?? false;
        highlights = (data as any).highlights ?? [];

        if (data.title) document.title = `${data.title} — Berga`;
        loadArticleTags(id);

        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                renderHighlights();
            });
        });
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
        if (suppressOutsideClick) return;
        const target = e.target as HTMLElement;
        if (!target.closest('.hl-toolbar') && !target.closest('.hl-popover') && !target.closest('mark.bergahl')) {
            highlightMenu = null;
            highlightPopover = null;
        }
    }

	onMount(() => {
    const id = $page.params.item_id;
    if (id) loadArticle(id);

    document.addEventListener('selectionchange', onSelectionChange);

	beforeNavigate(() => {
		flushPending();
	});

    return () => {
        document.removeEventListener('selectionchange', onSelectionChange);
        if (selectionDebounceTimer) clearTimeout(selectionDebounceTimer);
    };
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

    // ── Highlights ───────────────────────────────────────────────────

    function renderHighlights() {
        if (!articleBodyEl) return;
        clearHighlightMarks();
        if (highlights.length === 0) return;

        const sorted = [...highlights].sort((a, b) => a.sort_order - b.sort_order);
        for (const hl of sorted) {
            wrapTextInMark(articleBodyEl, hl.text, hl.id, hl.color);
        }
    }

    function clearHighlightMarks() {
        if (!articleBodyEl) return;
        const marks = articleBodyEl.querySelectorAll('mark.bergahl');
        marks.forEach(mark => {
            const parent = mark.parentNode;
            if (parent) {
                while (mark.firstChild) {
                    parent.insertBefore(mark.firstChild, mark);
                }
                parent.removeChild(mark);
                parent.normalize();
            }
        });
    }

    function wrapTextInMark(root: Node, searchText: string, highlightId: number, color: string) {
        const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
        const textNodes: Text[] = [];
        let node: Text | null;
        while ((node = walker.nextNode() as Text | null)) {
            if (node.parentElement?.tagName !== 'MARK' || !node.parentElement.classList.contains('bergahl')) {
                textNodes.push(node);
            }
        }

        let fullText = textNodes.map(n => n.textContent ?? '').join('');
        let searchFrom = 0;

        while (searchFrom <= fullText.length) {
            const idx = fullText.indexOf(searchText, searchFrom);
            if (idx === -1) break;

            let charCount = 0;
            let startNodeIdx = -1;
            let startOffset = 0;
            let endNodeIdx = -1;
            let endOffset = 0;

            for (let i = 0; i < textNodes.length; i++) {
                const len = textNodes[i].textContent?.length ?? 0;
                if (startNodeIdx === -1 && charCount + len > idx) {
                    startNodeIdx = i;
                    startOffset = idx - charCount;
                }
                if (charCount + len >= idx + searchText.length) {
                    endNodeIdx = i;
                    endOffset = idx + searchText.length - charCount;
                    break;
                }
                charCount += len;
            }

            if (startNodeIdx === -1 || endNodeIdx === -1) break;

            try {
                const range = document.createRange();
                range.setStart(textNodes[startNodeIdx], startOffset);
                range.setEnd(textNodes[endNodeIdx], endOffset);

                const mark = document.createElement('mark');
                mark.className = 'bergahl';
                mark.dataset.highlightId = String(highlightId);
                mark.style.backgroundColor = color;

                range.surroundContents(mark);

                const newWalker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
                const newTextNodes: Text[] = [];
                let nn: Text | null;
                while ((nn = newWalker.nextNode() as Text | null)) {
                    if (nn.parentElement?.tagName !== 'MARK' || !nn.parentElement.classList.contains('bergahl')) {
                        newTextNodes.push(nn);
                    }
                }
                textNodes.length = 0;
                textNodes.push(...newTextNodes);
                fullText = textNodes.map(n => n.textContent ?? '').join('');
            } catch {
                break;
            }

            searchFrom = idx + searchText.length;
            if (searchFrom >= fullText.length) break;
        }
    }

    function onArticleBodyMouseup(e: MouseEvent) {
        if (webView) return;
        highlightMenu = null;
        highlightPopover = null;

        const sel = window.getSelection();
        if (!sel || sel.isCollapsed || !sel.toString().trim()) return;

        const bodyEl = articleBodyEl;
        if (!bodyEl) return;

        if (!bodyEl.contains(sel.anchorNode)) return;

        const text = sel.toString().trim();
        if (text.length < 1) return;

        const range = sel.getRangeAt(0);
        const rect = range.getBoundingClientRect();

        highlightMenu = {
            x: rect.left + rect.width / 2,
            y: rect.top - 8,
            text,
        };

        suppressOutsideClick = true;
        setTimeout(() => { suppressOutsideClick = false; }, 0);
    }

    function onSelectionChange() {
        if (selectionDebounceTimer) clearTimeout(selectionDebounceTimer);
        selectionDebounceTimer = setTimeout(() => {
            if (webView) return;

            const sel = window.getSelection();
            if (!sel || sel.isCollapsed || !sel.toString().trim()) {
                if (!suppressOutsideClick) {
                    highlightMenu = null;
                }
                return;
            }

            const bodyEl = articleBodyEl;
            if (!bodyEl) return;
            if (!bodyEl.contains(sel.anchorNode)) return;

            const text = sel.toString().trim();
            if (text.length < 1) return;

            const range = sel.getRangeAt(0);
            const rect = range.getBoundingClientRect();

            highlightMenu = {
                x: rect.left + rect.width / 2,
                y: rect.top - 8,
                text,
            };

            suppressOutsideClick = true;
            setTimeout(() => { suppressOutsideClick = false; }, 150);
        }, 150);
    }

    function onArticleBodyClick(e: MouseEvent) {
        const target = e.target as HTMLElement;
        const mark = target.closest('mark.bergahl') as HTMLElement | null;
        if (!mark) {
            highlightPopover = null;
            return;
        }

        e.preventDefault();
        e.stopPropagation();

        const hlId = parseInt(mark.dataset.highlightId ?? '0', 10);
        if (!hlId) return;

        const rect = mark.getBoundingClientRect();
        highlightPopover = {
            x: rect.left + rect.width / 2,
            y: rect.top - 8,
            highlightId: hlId,
        };
        highlightMenu = null;
    }

    async function applyHighlight(color: string) {
        if (!highlightMenu || !loadedItemId || highlightLoading) return;
        highlightLoading = true;
        const text = highlightMenu.text;
        highlightMenu = null;

        try {
            const res = await apiFetch(`/api/highlights/${loadedItemId}`, {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text, color }),
            });
            if (!res.ok) throw new Error();
            const data = await res.json();
            if (data.highlight) {
                highlights = [...highlights, {
                    id: data.highlight.id,
                    text: data.highlight.text,
                    color: data.highlight.color,
                    sort_order: data.highlight.sort_order,
                }];
            }
        } catch {
            console.error('Failed to save highlight');
        } finally {
            highlightLoading = false;
            window.getSelection()?.removeAllRanges();
            requestAnimationFrame(() => renderHighlights());
        }
    }

    async function removeHighlight(highlightId: number) {
        if (highlightLoading) return;
        highlightLoading = true;
        highlightPopover = null;

        try {
            const res = await apiFetch(`/api/highlights/${highlightId}`, {
                method: 'DELETE',
                credentials: 'include',
            });
            if (!res.ok) throw new Error();
            highlights = highlights.filter(h => h.id !== highlightId);
        } catch {
            console.error('Failed to remove highlight');
        } finally {
            highlightLoading = false;
            clearHighlightMarks();
            requestAnimationFrame(() => renderHighlights());
        }
    }

    function onCustomColorInput(e: Event) {
        const input = e.target as HTMLInputElement;
        if (input.value) {
            applyHighlight(input.value);
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
		</button>

		<div class="top-actions top-actions-left">
			<button
				class="ghost-btn"
				class:action-active={liked}
				onclick={() => sendVote('like')}
				title="{$t('article.like')}"
				disabled={likeLoading}
			>
				{#if likeLoading}
					<span class="loading loading-spinner loading-xs"></span>
				{:else}
					<Heart size={16} fill={liked ? 'currentColor' : 'none'} />
				{/if}
			</button>

			<button
				class="ghost-btn"
				class:action-active={disliked}
				onclick={() => sendVote('dislike')}
				title="{$t('article.dislike')}"
				disabled={dislikeLoading}
			>
				{#if dislikeLoading}
					<span class="loading loading-spinner loading-xs"></span>
				{:else}
					<ThumbsDown size={16} fill={disliked ? 'currentColor' : 'none'} />
				{/if}
			</button>

			<div class="tag-assign-wrap">
				<button
					class="ghost-btn"
					class:action-tag-active={articleTags.length > 0}
					onclick={toggleTagDropdown}
					title="{$t('article.tagArticle')}"
					aria-expanded={tagDropdownOpen}
					aria-haspopup="listbox"
				>
					<Tag size={16} />
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

			<button
				class="ghost-btn"
				class:action-save-active={saved}
				onclick={toggleSave}
				title="{$t('article.save')}"
				disabled={saveLoading}
			>
				{#if saveLoading}
					<span class="loading loading-spinner loading-xs"></span>
				{:else}
					<Bookmark size={16} fill={saved ? 'currentColor' : 'none'} />
				{/if}
			</button>
		</div>

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

                <div class="article-body" bind:this={articleBodyEl} onmouseup={onArticleBodyMouseup} onclick={onArticleBodyClick} onkeydown={() => {}} role="application">
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

    <!-- ── Highlight Selection Toolbar ─────────────────────── -->
    {#if highlightMenu}
        <!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
        <div
            class="hl-toolbar"
            style="left: {highlightMenu.x}px; top: {highlightMenu.y}px;"
            onclick={(e) => e.stopPropagation()}
        >
            {#each HIGHLIGHT_PRESETS as color}
                <button
                    class="hl-color-btn"
                    style="background: {color};"
                    onclick={() => applyHighlight(color)}
                    disabled={highlightLoading}
                    title={color}
                ></button>
            {/each}
            <label class="hl-custom-btn" title={$t('article.customColor')}>
                <input type="color" value="#FF9800" oninput={onCustomColorInput} disabled={highlightLoading} />
                <Highlighter size={13} />
            </label>
        </div>
    {/if}

    <!-- ── Highlight Delete Popover ─────────────────────────── -->
    {#if highlightPopover}
        <!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
        <div
            class="hl-popover"
            style="left: {highlightPopover.x}px; top: {highlightPopover.y}px;"
            onclick={(e) => e.stopPropagation()}
        >
            <button
                class="hl-delete-btn"
                onclick={() => removeHighlight(highlightPopover!.highlightId)}
                disabled={highlightLoading}
                title={$t('article.removeHighlight')}
            >
                <Trash2 size={13} />
                <span>{$t('article.removeHighlight')}</span>
            </button>
        </div>
    {/if}
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

.top-spacer { flex: 1; }

.top-actions { display: flex; align-items: center; gap: 2px; }
.top-actions-left { margin-right: 8px; }

.ghost-btn.action-active { color: var(--color-error); }
.ghost-btn.action-save-active { color: var(--color-accent); }
.ghost-btn.action-tag-active { color: var(--color-accent); }

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

.tag-assign-wrap { position: relative; display: inline-flex; }
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

    /* ── Highlights ────────────────────────────────────────── */
    .article-body :global(mark.bergahl) {
        border-radius: 2px;
        padding: 0 1px;
        cursor: pointer;
        transition: opacity 120ms;
    }
    .article-body :global(mark.bergahl:hover) {
        opacity: 0.75;
    }

    .hl-toolbar {
        position: fixed;
        transform: translate(-50%, -100%);
        z-index: 40;
        display: flex;
        align-items: center;
        gap: 6px;
        background: var(--color-base-100);
        border: 1px solid var(--color-base-300);
        border-radius: 8px;
        box-shadow: 0 4px 16px rgba(0,0,0,.15);
        padding: 6px 8px;
    }

    .hl-color-btn {
        width: 22px;
        height: 22px;
        border-radius: 50%;
        border: 2px solid var(--color-base-300);
        cursor: pointer;
        transition: transform 100ms, border-color 100ms;
        flex-shrink: 0;
    }
    .hl-color-btn:hover {
        transform: scale(1.15);
        border-color: var(--color-base-content);
    }
    .hl-color-btn:disabled { opacity: 0.5; cursor: default; }

    .hl-custom-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 22px;
        height: 22px;
        border-radius: 50%;
        border: 2px dashed var(--color-base-300);
        cursor: pointer;
        color: color-mix(in oklch, var(--color-base-content) 60%, transparent);
        background: transparent;
        position: relative;
        overflow: hidden;
        flex-shrink: 0;
        transition: border-color 100ms;
    }
    .hl-custom-btn:hover {
        border-color: var(--color-accent);
        color: var(--color-accent);
    }
    .hl-custom-btn input[type="color"] {
        position: absolute;
        inset: 0;
        width: 100%;
        height: 100%;
        opacity: 0;
        cursor: pointer;
    }

    .hl-popover {
        position: fixed;
        transform: translate(-50%, -100%);
        z-index: 40;
        background: var(--color-base-100);
        border: 1px solid var(--color-base-300);
        border-radius: 8px;
        box-shadow: 0 4px 16px rgba(0,0,0,.15);
        padding: 4px;
    }

    .hl-delete-btn {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 10px;
        border: none;
        border-radius: 6px;
        background: transparent;
        color: var(--color-error);
        font-size: 12px;
        font-weight: 500;
        cursor: pointer;
        transition: background 100ms;
        white-space: nowrap;
    }
    .hl-delete-btn:hover {
        background: color-mix(in oklch, var(--color-error) 10%, transparent);
    }
    .hl-delete-btn:disabled { opacity: 0.5; cursor: default; }

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