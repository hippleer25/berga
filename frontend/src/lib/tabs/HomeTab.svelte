<script lang="ts">
import { onMount } from 'svelte';
   import { page } from '$app/stores';
 import { goto, beforeNavigate, afterNavigate } from '$app/navigation';
   import { slide } from 'svelte/transition';
   import { get } from 'svelte/store';
   import PostCard from '$lib/components/PostCard.svelte';
   import Portal from '$lib/components/Portal.svelte';
 import {
   selectionMode,
   selectedPosts,
   pendingMotaPosts,
   activeTabIdx,
 } from '$lib/stores/swipe';
 import { subscriptionChanged } from '$lib/stores/subscription';
 import { onViewed, flushPending, destroyViewTracker } from '$lib/stores/viewTracker';
import {
		Rss, FolderOpen, ChevronDown,
		X, Check, Settings, Share2, Sparkles, Bookmark, Tag, RotateCw,
	} from '@lucide/svelte';
import LoaderCircle from '@lucide/svelte/icons/loader-circle';
 import { t } from 'svelte-i18n';
 import { apiFetch } from '$lib/api';
 import {
 	feedCacheKey,
 	loadFeedCache,
 	saveFeedCache,
 	clearFeedCache,
	feedBustNeeded,
	clearBustFlag,
 	loadSubsCache,
 	saveSubsCache,
 	clearSubsCache,
 } from '$lib/stores/feedCache';

const TAB_ROUTES = ['/followers', '/home', '/events', '/mota'];

type Mode = 'recommendations' | 'recents' | 'saved';

    // Mode & filter
    let mode               = $state<Mode>('recommendations');
    let selectedFolderId   = $state<string | null>(null);
    let selectedFolderName = $state<string | null>(null);
let selectedFeedSha = $state<string | null>(null);
let selectedFeedName = $state<string | null>(null);
let selectedTagId = $state<number | null>(null);
let selectedTagName = $state<string | null>(null);
let tagList = $state<Array<{ id: number; name: string; color?: string }>>([]);

    // Feed
let feed = $state<any[]>([]);
let loading = $state<boolean>(true);
let refreshing = $state<boolean>(false);
let loadingMore = $state<boolean>(false);
    let hasMore     = $state<boolean>(true);
    let error       = $state<string>('');
let pageNum = $state<number>(0);
    let subsData    = $state<any[]>([]);

    // Share feedback
    let shareCopied = $state(false);

    // Sentinel element for IntersectionObserver
    let sentinelEl: HTMLDivElement | null = $state(null);
    let observer:   IntersectionObserver | null = null;

// Filter bar touch tracking
let filterBarAxis: 'h' | 'v' | null = null;
let filterBarStartX = 0;
let filterBarStartY = 0;

// Dropdowns
let showFolderPicker = $state<boolean>(false);
let showFeedPicker = $state<boolean>(false);
let showTagPicker = $state<boolean>(false);
let folderDropStyle = $state<string>('');
let feedDropStyle = $state<string>('');
let tagDropStyle = $state<string>('');
let folderBtnEl = $state<HTMLButtonElement | null>(null);
let feedBtnEl = $state<HTMLButtonElement | null>(null);
let tagBtnEl = $state<HTMLButtonElement | null>(null);

// Bulk tag
let bulkTagPickerOpen = $state<boolean>(false);
let bulkTagLoading = $state<boolean>(false);

// Pull-to-refresh
let pageRootEl: HTMLElement | null = $state(null);
let ptrContentEl: HTMLElement | null = $state(null);
let pullOffset = $state(0);
let pulling = $state(false);
let pullStartY = 0;
let scrollContainer: HTMLElement | null = null;
let ptrWheelAccum = 0;
let ptrWheelTimer: ReturnType<typeof setTimeout> | null = null;
let ptrSource: 'touch' | 'wheel' | null = null;
const PULL_THRESHOLD = 60;
const PULL_RESISTANCE = 0.4;
const MAX_EXCLUDE_IDS = 80;
const PTR_WHEEL_IDLE_MS = 160;

    // Derived lists
    let folders = $derived.by(() => {
        const seen   = new Set<number>();
        const result: Array<{ id: number; name: string }> = [];
        for (const f of subsData) {
            if (f.folder?.id && !seen.has(f.folder.id)) {
                seen.add(f.folder.id);
                result.push({ id: f.folder.id, name: f.folder.name });
            }
        }
        return result.sort((a, b) => a.name.localeCompare(b.name));
    });

    let feedsList = $derived.by(() =>
        subsData
            .filter((f: any) => !f._empty_folder && f.feed_sha256)
            .map((f: any) => {
                let title = f.title && f.title !== 'No title' ? f.title : '';
                if (!title) {
                    try { title = new URL(f.url).hostname; } catch (_e) { title = f.url || ''; }
                }
                return { sha: f.feed_sha256 as string, title, icon: f.icon as string | undefined };
            })
            .sort((a: any, b: any) => a.title.localeCompare(b.title))
    );

    const SKELETON_INITIAL = Array.from({ length: 6 }, (_, i) => i);
    const SKELETON_MORE    = Array.from({ length: 3 }, (_, i) => i);

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

	onMount(() => {
	observer = new IntersectionObserver(
		(entries) => { if (entries[0].isIntersecting) loadMore(); },
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

	// Desktop / trackpad overscroll pull-to-refresh: listen for wheel events
	// on the scroll container (panel on mobile) or the window (desktop, where
	// panels are overflow:visible and the window scrolls).
	const wheelTarget: EventTarget = scrollContainer ?? window;
	wheelTarget.addEventListener('wheel', onWheelPull as EventListener, { passive: true });

	loadSubscriptions();
		loadFeed(true);
		applyTagFromUrl();

		const unsub = subscriptionChanged.subscribe((val) => {
			if (val > 0) {
				clearFeedCache();
				clearSubsCache();
				loadSubscriptions();
				loadFeed(true);
			}
		});

	beforeNavigate(() => {
		flushPending();
	});

	const navCleanup = afterNavigate(({ from, to }) => {
		if (!from) return;
		const fromIsTab = TAB_ROUTES.some(r => from.url.pathname === r);
		const toIsHome = to.url.pathname === '/home';
		if (toIsHome && !fromIsTab) {
			loadFeed(true);
		}
	});

	return () => {
		observer?.disconnect();
		wheelTarget.removeEventListener('wheel', onWheelPull as EventListener);
		if (ptrWheelTimer) clearTimeout(ptrWheelTimer);
		unsub();
		navCleanup?.destroy();
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

	async function loadSubscriptions() {
		const cached = loadSubsCache<any>();
		if (cached) {
			const raw = cached;
			subsData = Array.isArray(raw) ? raw : (raw.feeds ?? []);
		}

		try {
			const res = await apiFetch('/api/list-subscriptions', { credentials: 'include' });
			if (!res.ok) throw new Error('failed');
			const raw = await res.json();
			subsData = Array.isArray(raw) ? raw : (raw.feeds ?? []);
			saveSubsCache(raw);
		} catch (_e) { /* silently ignore */ }

		try {
			const res = await apiFetch('/api/tags', { credentials: 'include' });
			if (res.ok) {
				const data = await res.json();
				tagList = data.tags ?? [];
			}
		} catch { /* non-critical */ }
	}

	function buildUrl(
		pageNum: number,
		limit: number = 20,
		opts?: { refresh?: boolean; excludeIds?: string[] },
	): string {
		const p = new URLSearchParams({ limit: String(limit) });
		if (selectedFolderId) p.set('folder_id', selectedFolderId);
		if (selectedFeedSha) p.set('feed_sha256', selectedFeedSha);
		if (selectedTagId) p.set('tag_id', String(selectedTagId));
		if (mode === 'recommendations') {
			p.set('page', String(pageNum));
			if (opts?.refresh) p.set('refresh', '1');
			if (opts?.excludeIds && opts.excludeIds.length > 0) {
				p.set('exclude_ids', opts.excludeIds.slice(-MAX_EXCLUDE_IDS).join(','));
			}
			return `/api/feed/recommendations?${p}`;
		}
		if (mode === 'saved') {
			p.set('page', String(pageNum));
			return `/api/feed/saved?${p}`;
		}
		p.set('max_days', '10');
		return `/api/feed/recents?${p}`;
	}

	function loadedItemIds(): string[] {
		return feed.map((x: any) => x.item_id).filter(Boolean);
	}

	function fetchCacheOpt(): RequestInit {
		return feedBustNeeded() ? { credentials: 'include', cache: 'no-store' } : { credentials: 'include' };
	}

	function consumeBust() {
		if (feedBustNeeded()) clearBustFlag();
	}

	async function loadFeed(reset: boolean = false) {
		consumeBust();
		if (reset) {
			const cacheKey = feedCacheKey(mode, selectedFolderId, selectedFeedSha, selectedTagId);
			const cached = loadFeedCache<any[]>(cacheKey);
			if (cached && cached.length > 0) {
				feed = cached;
				loading = false;
				refreshing = true;
				error = '';
				pageNum = 0;
				hasMore = true;
				try {
					const res = await apiFetch(buildUrl(0), fetchCacheOpt());
					if (res.status === 401) { window.location.replace('/login'); return; }
					if (!res.ok) throw new Error(`${get(t)('hometab.loadError')} (${res.status})`);
					const data: any[] = await res.json();
					feed = data;
					hasMore = data.length > 0;
					saveFeedCache(cacheKey, data);
				} catch (e: any) {
				}
				refreshing = false;
				return;
			}
			loading = true;
			feed = [];
			pageNum = 0;
			hasMore = true;
			error = '';
		}
		try {
			const res = await apiFetch(buildUrl(0), fetchCacheOpt());
			if (res.status === 401) { window.location.replace('/login'); return; }
			if (!res.ok) throw new Error(`${get(t)('hometab.loadError')} (${res.status})`);
			const data: any[] = await res.json();
			feed = data;
			hasMore = data.length > 0;
			const cacheKey = feedCacheKey(mode, selectedFolderId, selectedFeedSha, selectedTagId);
			saveFeedCache(cacheKey, data);
		} catch (e: any) {
			error = (e as Error).message || get(t)('hometab.loadError');
		}
		loading = false;
	}

	// Pull-to-refresh / reload entry point. Forces a backend recompute
	// (refresh=1 invalidates the ranking + interaction caches) and, in
	// recommendations mode, asks for a fresh batch that excludes every
	// article currently loaded so scrolled/shown content doesn't resurface.
	async function reloadFeed() {
		if (loading) return;
		refreshing = true;
		error = '';
		pageNum = 0;
		hasMore = true;
		try {
			await flushPending();
			const url = mode === 'recommendations'
				? buildUrl(0, 20, { refresh: true, excludeIds: loadedItemIds() })
				: buildUrl(0);
			const res = await apiFetch(url, fetchCacheOpt());
			if (res.status === 401) { window.location.replace('/login'); return; }
			if (!res.ok) throw new Error(`${get(t)('hometab.loadError')} (${res.status})`);
			const data: any[] = await res.json();
			feed = data;
			hasMore = data.length > 0;
			loading = false;
			const cacheKey = feedCacheKey(mode, selectedFolderId, selectedFeedSha, selectedTagId);
			saveFeedCache(cacheKey, data);
		} catch (e: any) {
			error = (e as Error).message || get(t)('hometab.loadError');
		} finally {
			refreshing = false;
		}
	}

	async function loadMore() {
	if (loadingMore || !hasMore || loading || refreshing) return;
    loadingMore = true;

    try {
      let newItems: any[];

      if (mode === 'recommendations') {
        // Cursor mode: send already-loaded ids so the backend returns the
        // next unseen batch (no skips/duplicates when articles get excluded
        // between pages). Flush pending views first so the DB is current.
        await flushPending();
        const res = await apiFetch(
          buildUrl(0, 20, { excludeIds: loadedItemIds() }),
          { credentials: 'include' },
        );
        if (!res.ok) throw new Error(`${get(t)('hometab.loadError')} (${res.status})`);
        const data: any[] = await res.json();
        if (data.length === 0) { hasMore = false; loadingMore = false; return; }
        const seen = new Set(feed.map((x: any) => x.item_id));
        newItems = data.filter((x: any) => !seen.has(x.item_id));
        if (newItems.length === 0) { hasMore = false; loadingMore = false; return; }
        hasMore = true;
      } else if (mode === 'saved') {
        const nextPage = pageNum + 1;
        const res = await apiFetch(buildUrl(nextPage), { credentials: 'include' });
        if (!res.ok) throw new Error(`${get(t)('hometab.loadError')} (${res.status})`);
        const data: any[] = await res.json();

        if (data.length === 0) { hasMore = false; loadingMore = false; return; }

        const seen = new Set(feed.map((x: any) => x.item_id));
        newItems = data.filter((x: any) => !seen.has(x.item_id));

        if (newItems.length === 0) { hasMore = false; loadingMore = false; return; }

        pageNum = nextPage;
        hasMore = true;
      } else {
        const requestedLimit = feed.length + 20;
        const res = await apiFetch(buildUrl(0, requestedLimit), { credentials: 'include' });
        if (!res.ok) throw new Error(`${get(t)('hometab.loadError')} (${res.status})`);
        const data: any[] = await res.json();
        const seen = new Set(feed.map((x: any) => x.item_id));
        newItems = data.filter((x: any) => !seen.has(x.item_id));
        if (newItems.length === 0) { hasMore = false; loadingMore = false; return; }
      }

		feed = [...feed, ...newItems];

		if (mode === 'recommendations' || mode === 'saved') {
			const cacheKey = feedCacheKey(mode, selectedFolderId, selectedFeedSha, selectedTagId);
			saveFeedCache(cacheKey, feed);
		}
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

	function selectFolder(id: number | null, name: string | null) {
		selectedFolderId = id !== null ? String(id) : null;
		selectedFolderName = name;
		selectedFeedSha = null;
		selectedFeedName = null;
		selectedTagId = null;
		selectedTagName = null;
		showFolderPicker = false;
		loadFeed(true);
	}

	function selectFeed(sha: string | null, name: string | null) {
		selectedFeedSha = sha;
		selectedFeedName = name;
		selectedFolderId = null;
		selectedFolderName = null;
		selectedTagId = null;
		selectedTagName = null;
		showFeedPicker = false;
		loadFeed(true);
	}

	function selectTag(id: number | null, name: string | null) {
		selectedTagId = id;
		selectedTagName = name;
		selectedFolderId = null;
		selectedFolderName = null;
		selectedFeedSha = null;
		selectedFeedName = null;
		showTagPicker = false;
		loadFeed(true);
	}

	function handleTagClick(tag: { tag_id: number; name: string; color?: string; source: string }) {
		selectTag(tag.tag_id, tag.name);
	}

	function applyTagFromUrl() {
		const params = $page.url.searchParams;
		const tid = params.get('tag_id');
		if (tid) {
			const id = Number(tid);
			const found = tagList.find(t => t.id === id);
			if (found) {
				selectedTagId = found.id;
				selectedTagName = found.name;
			}
		}
	}

	function getDropdownStyle(btnEl: HTMLButtonElement): string {
        const r          = btnEl.getBoundingClientRect();
        const DROPDOWN_W = 196;
        const PADDING    = 8;
        const top        = r.bottom + 6;
        if (r.right + PADDING > window.innerWidth) {
            return `top:${top}px; right:${Math.max(window.innerWidth - r.right, PADDING)}px;`;
        }
        const left = Math.max(Math.min(r.left, window.innerWidth - DROPDOWN_W - PADDING), PADDING);
        return `top:${top}px; left:${left}px;`;
    }

function toggleFolderPicker() {
        showFolderPicker = !showFolderPicker;
        showFeedPicker = false;
        showTagPicker = false;
        bulkTagPickerOpen = false;
        if (showFolderPicker && folderBtnEl) folderDropStyle = getDropdownStyle(folderBtnEl);
}

function toggleFeedPicker() {
        showFeedPicker = !showFeedPicker;
        showFolderPicker = false;
        showTagPicker = false;
        bulkTagPickerOpen = false;
        if (showFeedPicker && feedBtnEl) feedDropStyle = getDropdownStyle(feedBtnEl);
}

function toggleTagPicker() {
        showTagPicker = !showTagPicker;
        showFolderPicker = false;
        showFeedPicker = false;
        bulkTagPickerOpen = false;
        if (showTagPicker && tagBtnEl) tagDropStyle = getDropdownStyle(tagBtnEl);
}

	function handleToggleSelect(item: any) {
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

function clearSelection() {
        selectedPosts.set([]);
        selectionMode.set(false);
        bulkTagPickerOpen = false;
}

function toggleBulkTagPicker() {
        bulkTagPickerOpen = !bulkTagPickerOpen;
        showFolderPicker = false;
        showFeedPicker = false;
        showTagPicker = false;
}

async function bulkAssignTag(tagId: number) {
        const posts = get(selectedPosts);
        if (posts.length === 0 || bulkTagLoading) return;
        bulkTagLoading = true;
        try {
                const res = await apiFetch('/api/tags/assign-bulk', {
                        method: 'POST',
                        credentials: 'include',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                                tag_id: tagId,
                                item_ids: posts.map((p: any) => p.item_id),
                        }),
                });
if (res.ok) {
				clearFeedCache();
				const tag = tagList.find(t => t.id === tagId);
                        if (tag) {
                                feed = feed.map((item: any) => {
                                        if (posts.some((p: any) => p.item_id === item.item_id)) {
                                                const existing = item.tags || [];
                                                if (!existing.some((t: any) => t.tag_id === tagId)) {
                                                        return { ...item, tags: [...existing, { tag_id: tag.id, name: tag.name, color: tag.color, source: 'manual' }] };
                                                }
                                        }
                                        return item;
                                });
                        }
                        bulkTagPickerOpen = false;
                }
        } catch { /* */ }
        finally { bulkTagLoading = false; }
}

    async function sendToMota() {
        const posts = get(selectedPosts);
        if (posts.length === 0) return;
        pendingMotaPosts.set([...posts]);
        clearSelection();
        activeTabIdx.set(3);
        await goto('/mota');
    }

    async function shareSelected() {
        const posts = get(selectedPosts);
        if (posts.length === 0) return;

        try {
            if (posts.length === 1) {
                const p = posts[0];
                if (navigator.share) {
                    await navigator.share({ title: p.title, url: p.link });
                } else {
                    await navigator.clipboard.writeText(p.link);
                    showCopiedFeedback();
                }
            } else {
                const text = posts.map((p: any) => `${p.title}\n${p.link}`).join('\n\n');
                if (navigator.share) {
                    await navigator.share({ title: `${posts.length} ${get(t)('hometab.articles')}`, text });
                } else {
                    await navigator.clipboard.writeText(text);
                    showCopiedFeedback();
                }
            }
        } catch (_e) {
            try {
                const text = posts.map((p: any) => p.link).join('\n');
                await navigator.clipboard.writeText(text);
                showCopiedFeedback();
            } catch (_) { /* ignore */ }
        }
    }

    function showCopiedFeedback() {
        shareCopied = true;
        setTimeout(() => { shareCopied = false; }, 2000);
    }

    // ── Pull-to-refresh ─────────────────────────────────────
    function onPullStart(e: TouchEvent) {
        if (loading || refreshing) return;
        if (scrollContainer && scrollContainer.scrollTop > 4) return;
        pullStartY = e.touches[0].clientY;
        pulling = false;
        ptrSource = 'touch';
        pullOffset = 0;
    }

    function onPullMove(e: TouchEvent) {
        if (loading || refreshing) return;
        if (scrollContainer && scrollContainer.scrollTop > 4) return;
        const dy = e.touches[0].clientY - pullStartY;
        if (dy > 0) {
            pulling = true;
            ptrSource = 'touch';
            pullOffset = Math.min(dy * PULL_RESISTANCE, 120);
            if (ptrContentEl) {
                ptrContentEl.style.transition = 'none';
                ptrContentEl.style.transform = `translateY(${pullOffset}px)`;
            }
        } else if (pulling) {
            pulling = false;
            ptrSource = null;
            pullOffset = 0;
            snapPtrBack();
        }
    }

    function onPullEnd(_e: TouchEvent) {
        if (!pulling) return;
        pulling = false;
        ptrSource = null;
        if (pullOffset > PULL_THRESHOLD && !refreshing && !loading) {
            if (ptrContentEl) {
                ptrContentEl.style.transition = 'transform 0.25s ease';
                ptrContentEl.style.transform = 'translateY(55px)';
            }
            pullOffset = 55;
            reloadFeed();
        } else {
            snapPtrBack();
        }
    }

    // Desktop / trackpad overscroll-at-top: accumulate upward wheel deltas
    // into a pull, then commit (reload) or snap back when the wheel goes idle.
    function onWheelPull(e: WheelEvent) {
        if (loading || refreshing) return;
        if (ptrSource === 'touch') return;
        const atTop = scrollContainer
            ? scrollContainer.scrollTop <= 0
            : (typeof window !== 'undefined' && window.scrollY <= 0);
        if (!atTop) {
            if (ptrSource === 'wheel') { ptrSource = null; ptrWheelAccum = 0; snapPtrBack(); }
            return;
        }
        // deltaY < 0 => scrolling up towards the top => overscroll pull
        if (e.deltaY >= 0) {
            if (ptrSource === 'wheel') { ptrSource = null; ptrWheelAccum = 0; snapPtrBack(); }
            return;
        }
        ptrSource = 'wheel';
        pulling = true;
        ptrWheelAccum += -e.deltaY * PULL_RESISTANCE;
        pullOffset = Math.min(ptrWheelAccum, 120);
        if (ptrContentEl) {
            ptrContentEl.style.transition = 'none';
            ptrContentEl.style.transform = `translateY(${pullOffset}px)`;
        }
        if (ptrWheelTimer) clearTimeout(ptrWheelTimer);
        ptrWheelTimer = setTimeout(() => {
            ptrWheelTimer = null;
            if (ptrSource !== 'wheel') return;
            pulling = false;
            if (pullOffset > PULL_THRESHOLD && !refreshing && !loading) {
                if (ptrContentEl) {
                    ptrContentEl.style.transition = 'transform 0.25s ease';
                    ptrContentEl.style.transform = 'translateY(55px)';
                }
                pullOffset = 55;
                ptrSource = null;
                ptrWheelAccum = 0;
                reloadFeed();
            } else {
                ptrSource = null;
                ptrWheelAccum = 0;
                snapPtrBack();
            }
        }, PTR_WHEEL_IDLE_MS);
    }

    $effect(() => {
        if (!refreshing && pullOffset > 0 && !pulling) {
            snapPtrBack();
        }
    });

    function snapPtrBack() {
        pullOffset = 0;
        ptrWheelAccum = 0;
        if (ptrContentEl) {
            ptrContentEl.style.transition = 'transform 0.3s ease';
            ptrContentEl.style.transform = 'translateY(0)';
        }
    }
</script>

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
            <RotateCw size={18} class="ptr-icon-active" />
            <span class="ptr-text">{$t('hometab.releaseToRefresh')}</span>
        {:else}
            <RotateCw size={18} class="ptr-icon" />
            <span class="ptr-text">{$t('hometab.pullToRefresh')}</span>
        {/if}
    </div>

    <!-- Contêiner Centralizador -->
    <div class="main-content" bind:this={ptrContentEl}>
        
        <!-- Top Header (Settings only) -->
        <header class="top-header">
            <button class="settings-btn" onclick={() => goto('/settings/appearance')} aria-label="{$t('hometab.settings')}">
                <Settings size={20} />
            </button>
        </header>

        <!-- Welcome Section -->
        <div class="welcome-section">
            <h1 class="welcome-title">{$t('hometab.welcome')}</h1>
        </div>

        <!-- Selection bar -->
        {#if $selectionMode}
            <div class="selection-bar" transition:slide={{ duration: 220 }} onclick={() => { if (bulkTagPickerOpen) bulkTagPickerOpen = false; }}>
                <button class="sel-cancel-btn" onclick={clearSelection} aria-label="{$t('hometab.cancelSelection')}">
                    <X size={17} />
                </button>
                <span class="sel-count">
                    {$selectedPosts.length}
                    {$selectedPosts.length === 1 ? $t('hometab.selected') : $t('hometab.selectedPlural')}
                </span>
                <div class="sel-bar-actions">
                    <button
                        class="sel-action-btn sel-mota"
                        onclick={sendToMota}
                        disabled={$selectedPosts.length === 0}
                        title="{$t('hometab.sendToMota')}"
                    >
                        <Sparkles size={14} />
                        <span>{$t('hometab.sendToMota')}</span>
                    </button>
<button
        class="sel-action-btn sel-share"
        class:sel-copied={shareCopied}
        onclick={shareSelected}
        disabled={$selectedPosts.length === 0}
        title="{$selectedPosts.length > 1 ? $t('hometab.shareLinks') : $t('hometab.shareLink')}"
        >
        {#if shareCopied}
        <Check size={14} />
        <span>{$t('hometab.copied')}</span>
        {:else}
        <Share2 size={14} />
        {/if}
        </button>
        <div class="picker-wrap picker-wrap--sel">
        <button
        class="sel-action-btn"
        onclick={toggleBulkTagPicker}
        disabled={$selectedPosts.length === 0}
        title={$t('hometab.tagSelected')}
        >
        <Tag size={14} />
        <span>{$t('hometab.tagSelected')}</span>
        </button>
        {#if bulkTagPickerOpen}
        <div class="bulk-tag-dropdown" onclick={(e) => e.stopPropagation()}>
        {#if tagList.length === 0}
        <p class="picker-empty">{$t('hometab.noTagsYet')}</p>
        <button class="picker-item picker-item--create" onclick={() => { bulkTagPickerOpen = false; goto('/settings/tags'); }}>
        <Tag size={13} strokeWidth={2} />
        <span class="picker-item-text">{$t('hometab.createTag')}</span>
        </button>
        {:else}
        {#each tagList as tg (tg.id)}
        <button
        class="picker-item"
        onclick={() => bulkAssignTag(tg.id)}
        disabled={bulkTagLoading}
        >
        <span class="picker-tag-dot" style="background: {tg.color || '#3b82f6'}"></span>
        <span class="picker-item-text">{tg.name}</span>
        </button>
        {/each}
        <button class="picker-item picker-item--create" onclick={() => { bulkTagPickerOpen = false; goto('/settings/tags'); }}>
        <Tag size={13} strokeWidth={2} />
        <span class="picker-item-text">{$t('hometab.createTag')}</span>
        </button>
        {/if}
		</div>
		{/if}
	</div>
	</div>
	</div>
{/if}

<!-- Filter bar -->
        <div class="filter-bar" ontouchstart={(e) => { filterBarAxis = null; filterBarStartX = e.touches[0].clientX; filterBarStartY = e.touches[0].clientY; }} ontouchmove={(e) => { if (filterBarAxis === 'v') return; const el = e.currentTarget as HTMLElement; const dx = e.touches[0].clientX - filterBarStartX; const dy = e.touches[0].clientY - filterBarStartY; if (!filterBarAxis) { if (Math.abs(dx) < 6 && Math.abs(dy) < 6) return; filterBarAxis = Math.abs(dx) > Math.abs(dy) * 1.2 ? 'h' : 'v'; if (filterBarAxis === 'v') return; } const canScrollLeft = el.scrollLeft > 0; const canScrollRight = el.scrollLeft + el.clientWidth < el.scrollWidth - 1; const swipingRight = dx > 0; const swipingLeft = dx < 0; 		if ((swipingRight && canScrollLeft) || (swipingLeft && canScrollRight)) {
				e.stopPropagation();
				e.preventDefault();
			} }} ontouchend={() => { filterBarAxis = null; }}>
    <div class="mode-pill" role="group" aria-label="{$t('hometab.filterMode')}">
      <button
        class="mode-btn"
        class:active={mode === 'recommendations'}
        onclick={() => setMode('recommendations')}
        aria-pressed={mode === 'recommendations'}
      >
        <span>{$t('hometab.forYou')}</span>
      </button>
      <button
        class="mode-btn"
        class:active={mode === 'recents'}
        onclick={() => setMode('recents')}
        aria-pressed={mode === 'recents'}
      >
        <span>{$t('hometab.recent')}</span>
      </button>
      <button
        class="mode-btn"
        class:active={mode === 'saved'}
        onclick={() => setMode('saved')}
        aria-pressed={mode === 'saved'}
      >
        <Bookmark size={13} />
        <span>{$t('hometab.saved')}</span>
      </button>
    </div>

            <div class="picker-wrap">
                <button
                    bind:this={folderBtnEl}
                    class="filter-chip"
                    class:chip-active={!!selectedFolderId}
                    onclick={toggleFolderPicker}
                    aria-expanded={showFolderPicker}
                    aria-haspopup="listbox"
                >
                    <FolderOpen size={13} strokeWidth={2} />
                    <span class="chip-label">{selectedFolderName ?? $t('hometab.folder')}</span>
                    {#if selectedFolderId}
                        <span
                            class="chip-clear"
                            role="button"
                            tabindex="0"
                            aria-label="{$t('hometab.clearFolderFilter')}"
                            onclick={(e) => { e.stopPropagation(); selectFolder(null, null); }}
                            onkeydown={(e) => { if (e.key === 'Enter') selectFolder(null, null); }}
                        ><X size={10} /></span>
                    {:else}
                        <span class="chevron-wrap" class:rotated={showFolderPicker}><ChevronDown size={11} /></span>
                    {/if}
                </button>
            </div>

            <div class="picker-wrap">
                <button
                    bind:this={feedBtnEl}
                    class="filter-chip"
                    class:chip-active={!!selectedFeedSha}
                    onclick={toggleFeedPicker}
                    aria-expanded={showFeedPicker}
                    aria-haspopup="listbox"
                >
                    <Rss size={13} strokeWidth={2} />
                    <span class="chip-label">{selectedFeedName ?? $t('hometab.feed')}</span>
                    {#if selectedFeedSha}
                        <span
                            class="chip-clear"
                            role="button"
                            tabindex="0"
                            aria-label="{$t('hometab.clearFeedFilter')}"
                            onclick={(e) => { e.stopPropagation(); selectFeed(null, null); }}
                            onkeydown={(e) => { if (e.key === 'Enter') selectFeed(null, null); }}
                        ><X size={10} /></span>
                    {:else}
<span class="chevron-wrap" class:rotated={showFeedPicker}><ChevronDown size={11} /></span>
            {/if}
            </button>
            </div>

            <div class="picker-wrap">
            <button
            bind:this={tagBtnEl}
            class="filter-chip"
            class:chip-active={!!selectedTagId}
            onclick={toggleTagPicker}
            aria-expanded={showTagPicker}
            aria-haspopup="listbox"
            >
            <Tag size={13} strokeWidth={2} />
            <span class="chip-label">{selectedTagName ?? $t('hometab.tag')}</span>
            {#if selectedTagId}
            <span
            class="chip-clear"
            role="button"
            tabindex="0"
            aria-label="{$t('hometab.clearTagFilter')}"
            onclick={(e) => { e.stopPropagation(); selectTag(null, null); }}
            onkeydown={(e) => { if (e.key === 'Enter') selectTag(null, null); }}
            ><X size={10} /></span>
            {:else}
            <span class="chevron-wrap" class:rotated={showTagPicker}><ChevronDown size={11} /></span>
            {/if}
            </button>
            </div>
            </div>

<!-- Feed -->
        <div class="feed-wrap">
            {#if loading}
                {#each SKELETON_INITIAL as n (n)}
                    {@render skeletonCard()}
                {/each}
            {:else if error}
                <div class="state-error">
                    <p>{error}</p>
                    <button class="retry-btn" onclick={() => loadFeed(true)}>{$t('hometab.tryAgain')}</button>
                </div>
{:else if feed.length === 0}
      <p class="state-empty">{mode === 'saved' ? $t('hometab.noSavedYet') : $t('hometab.noPostsFound')}</p>
            {:else}
                {#each feed as item (item.item_id)}
                    <div use:trackView={item.item_id}>
<PostCard
    {item}
    server=""
    tags={item.tags || []}
    userTags={tagList}
    selectionMode={$selectionMode}
    selected={$selectedPosts.some((p: any) => p.item_id === item.item_id)}
    onToggleSelect={handleToggleSelect}
    onTagClick={handleTagClick}
    />
                    </div>
                {/each}

                {#if loadingMore}
                    {#each SKELETON_MORE as n (n)}
                        {@render skeletonCard()}
                    {/each}
                {/if}

                {#if !hasMore}
                    <p class="end-label">{$t('hometab.allCaughtUp')}</p>
                {/if}
            {/if}

            <div bind:this={sentinelEl} class="sentinel" aria-hidden="true"></div>
        </div>

    </div> <!-- Fim do main-content -->

<!-- Dropdowns e Backdrops (portaled to body to escape overflow:clip) -->
{#if showFolderPicker || showFeedPicker || showTagPicker}
  <Portal>
	<div
		class="picker-backdrop"
		onclick={() => { showFolderPicker = false; showFeedPicker = false; showTagPicker = false; bulkTagPickerOpen = false; }}
		aria-hidden="true"
	></div>

    {#if showFolderPicker}
      <div class="picker-dropdown picker-portal" style={folderDropStyle} role="listbox" aria-label="{$t('hometab.folder')}">
        {#if folders.length === 0}
          <p class="picker-empty">{$t('hometab.noFoldersYet')}</p>
        {:else}
          {#each folders as folder (folder.id)}
            <button
              class="picker-item"
              class:picker-selected={selectedFolderId === String(folder.id)}
              role="option"
              aria-selected={selectedFolderId === String(folder.id)}
              onclick={() => selectFolder(folder.id, folder.name)}
            >
              <FolderOpen size={13} strokeWidth={2} />
              <span class="picker-item-text">{folder.name}</span>
              {#if selectedFolderId === String(folder.id)}<Check size={12} class="picker-check" />{/if}
            </button>
          {/each}
        {/if}
      </div>
    {/if}

    {#if showFeedPicker}
      <div
        class="picker-dropdown picker-dropdown--tall picker-portal"
        style={feedDropStyle}
        role="listbox"
        aria-label="{$t('hometab.feed')}"
      >
        {#if feedsList.length === 0}
          <p class="picker-empty">{$t('hometab.noFeedsYet')}</p>
        {:else}
          {#each feedsList as f (f.sha)}
            <button
              class="picker-item"
              class:picker-selected={selectedFeedSha === f.sha}
              role="option"
              aria-selected={selectedFeedSha === f.sha}
              onclick={() => selectFeed(f.sha, f.title)}
            >
              {#if f.icon}
                <img
                  src={f.icon}
                  alt=""
                  class="picker-favicon"
                  onerror={(e: Event) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                />
              {:else}
                <Rss size={12} strokeWidth={2} class="picker-icon-fallback" />
              {/if}
              <span class="picker-item-text">{f.title}</span>
              {#if selectedFeedSha === f.sha}<Check size={12} class="picker-check" />{/if}
            </button>
          {/each}
        {/if}
      </div>
	{/if}

{#if showTagPicker}
        <div
        class="picker-dropdown picker-portal"
        style={tagDropStyle}
        role="listbox"
        aria-label="{$t('hometab.tag')}"
        >
        {#if tagList.length === 0}
        <p class="picker-empty">{$t('hometab.noTagsYet')}</p>
        <button class="picker-item picker-item--create" onclick={() => { showTagPicker = false; goto('/settings/tags'); }}>
        <Tag size={13} strokeWidth={2} />
        <span class="picker-item-text">{$t('hometab.createTag')}</span>
        </button>
        {:else}
        {#each tagList as tg (tg.id)}
        <button
        class="picker-item"
        class:picker-selected={selectedTagId === tg.id}
        role="option"
        aria-selected={selectedTagId === tg.id}
        onclick={() => selectTag(tg.id, tg.name)}
        >
        <span class="picker-tag-dot" style="background: {tg.color || '#3b82f6'}"></span>
        <span class="picker-item-text">{tg.name}</span>
        {#if selectedTagId === tg.id}<Check size={12} class="picker-check" />{/if}
        </button>
        {/each}
        <button class="picker-item picker-item--create" onclick={() => { showTagPicker = false; goto('/settings/tags'); }}>
        <Tag size={13} strokeWidth={2} />
        <span class="picker-item-text">{$t('hometab.createTag')}</span>
        </button>
        {/if}
        </div>
        {/if}
	</Portal>
	{/if}
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
    .ptr-icon {
        color: color-mix(in oklch, var(--color-base-content) 40%, transparent);
    }
    .ptr-icon-active {
        color: var(--color-accent);
    }
    .spin {
        animation: rot 0.8s linear infinite;
        color: var(--color-accent);
    }
    @keyframes rot { to { transform: rotate(360deg); } }

/* ── O Contêiner Centralizador ───────────────── */
    .main-content {
        max-width: 42rem;
        margin-left: auto;
        margin-right: auto;
        padding: 0 16px; /* Safe padding on mobile for header and filters */
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
        justify-content: flex-end;
        align-items: center;
        padding-top: 12px;
        padding-bottom: 4px;
    }
    .settings-btn {
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
    .settings-btn:hover {
        background: color-mix(in oklch, var(--color-base-content) 10%, transparent);
        color: var(--color-base-content);
        transform: rotate(8deg);
    }

    /* ── Welcome Section ─────────────────────────────────────── */
    .welcome-section {
        padding-top: 4px;
        padding-bottom: 16px;
    }
.welcome-title {
font-family: var(--font-page-title);
        font-size: 2.25rem;
        font-weight: 400;
        letter-spacing: -0.02em;
        color: var(--color-base-content);
        margin: 0;
        line-height: 1.1;
    }

    /* ── Selection bar ───────────────────────────────────────── */
    .selection-bar {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 14px;
        background: var(--color-base-100);
        border: 1px solid var(--color-accent);
        border-radius: 8px;
        box-shadow: 0 4px 12px color-mix(in oklch, black 10%, transparent);
        margin-bottom: 12px;
        z-index: 60;
    }

    .sel-cancel-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 32px;
        height: 32px;
        border-radius: 50%;
        border: none;
        background: transparent;
        color: color-mix(in oklch, var(--color-base-content) 55%, transparent);
        cursor: pointer;
        flex-shrink: 0;
        transition: background 140ms, color 140ms;
    }
    .sel-cancel-btn:hover {
        background: color-mix(in oklch, var(--color-base-content) 10%, transparent);
        color: var(--color-base-content);
    }

    .sel-count {
        font-size: 13px;
        font-weight: 600;
        color: var(--color-base-content);
        white-space: nowrap;
    }

    .sel-bar-actions {
        display: flex;
        align-items: center;
        gap: 6px;
        margin-left: auto;
    }

    .sel-action-btn {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 7px 12px;
        border-radius: 20px;
        border: none;
        font-size: 12.5px;
        font-weight: 600;
        cursor: pointer;
        transition: background 140ms, color 140ms, transform 100ms;
        white-space: nowrap;
    }
    .sel-action-btn:disabled { opacity: 0.4; cursor: not-allowed; }
    .sel-action-btn:not(:disabled):active { transform: scale(0.96); }

    .sel-mota {
        background: var(--color-accent);
        color: var(--color-base-100);
    }
    .sel-mota:not(:disabled):hover {
        box-shadow: 0 4px 14px color-mix(in oklch, var(--color-accent) 45%, transparent);
    }

    .sel-share {
        background: var(--color-base-200);
        color: var(--color-base-content);
    }
    .sel-share:not(:disabled):hover {
        background: var(--color-base-300);
    }
    .sel-share.sel-copied {
        background: color-mix(in oklch, var(--color-success) 15%, transparent);
        color: var(--color-success);
    }

    /* ── Filter bar ──────────────────────────────────────────── */
.filter-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-top: 8px;
  padding-bottom: 12px;
  background: var(--color-base-100);
  overflow-x: auto;
  scrollbar-width: none;
	touch-action: pan-y pan-x;
}
    .filter-bar::-webkit-scrollbar { display: none; }

    .mode-pill {
        display: flex;
        background: var(--color-base-200);
        border-radius: 13px; /* Borda alterada */
        padding: 3px;
        gap: 2px;
        flex-shrink: 0;
    }
    .mode-btn {
        display: flex;
        align-items: center;
        gap: 5px;
        padding: 6px 14px;
        border-radius: 10px; /* Borda alterada */
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

    .picker-wrap { position: relative; flex-shrink: 0; }
    .filter-chip {
        display: flex;
        align-items: center;
        gap: 5px;
        padding: 6px 12px;
        border-radius: 10px; /* Borda alterada */
        border: 1px solid var(--color-base-300);
        background: transparent;
        font-size: 13px;
        font-weight: 500;
        color: color-mix(in oklch, var(--color-base-content) 70%, transparent);
        cursor: pointer;
        transition: background 130ms, color 130ms, border-color 130ms;
        white-space: nowrap;
        max-width: 140px;
    }
    .filter-chip:hover {
        background: var(--color-base-200);
        color: var(--color-base-content);
    }
    .filter-chip.chip-active {
        background: color-mix(in oklch, var(--color-accent) 12%, transparent);
        border-color: color-mix(in oklch, var(--color-accent) 60%, transparent);
        color: var(--color-accent);
        font-weight: 600;
    }
    .chip-label { overflow: hidden; text-overflow: ellipsis; max-width: 80px; }
    .chip-clear {
        display: flex; align-items: center; justify-content: center;
        width: 14px; height: 14px;
        border-radius: 50%;
        background: color-mix(in oklch, var(--color-accent) 20%, transparent);
        cursor: pointer;
        flex-shrink: 0;
    }
    .chevron-wrap {
        display: flex; align-items: center;
        transition: transform 180ms ease;
        flex-shrink: 0;
    }
    .chevron-wrap.rotated { transform: rotate(180deg); }

    /* ── Pickers ─────────────────────────────────────────────── */
    .picker-dropdown {
        z-index: 9999;
        background: var(--color-base-100);
        border: 1px solid var(--color-base-300);
        border-radius: 8px;
        box-shadow: 0 8px 24px color-mix(in oklch, black 20%, transparent);
        padding: 4px;
        min-width: 190px;
        max-width: 260px;
        max-height: 280px;
        overflow-x: hidden;
        overflow-y: auto;
        scrollbar-width: thin;
        animation: picker-pop 150ms cubic-bezier(0.22, 1, 0.36, 1) both;
    }
  .picker-portal { position: fixed; z-index: 9999; pointer-events: auto; }
    .picker-dropdown--tall { max-height: 320px; }

    @keyframes picker-pop {
        from { opacity: 0; transform: translateY(-6px) scale(0.97); }
        to   { opacity: 1; transform: translateY(0)    scale(1); }
    }

    .picker-empty {
        padding: 12px;
        font-size: 12px;
        color: color-mix(in oklch, var(--color-base-content) 50%, transparent);
        text-align: center;
    }
    .picker-item {
        display: flex; align-items: center; gap: 8px;
        width: 100%; padding: 8px 10px;
        border: none; background: transparent;
        cursor: pointer; font-size: 13px; font-weight: 500;
        color: var(--color-base-content); border-radius: 6px;
        transition: background 110ms; text-align: left;
    }
    .picker-item:hover { background: var(--color-base-200); }
    .picker-item.picker-selected {
        background: color-mix(in oklch, var(--color-accent) 10%, transparent);
        color: var(--color-accent);
    }
.picker-item-text { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.picker-favicon { width: 14px; height: 14px; border-radius: 3px; object-fit: contain; flex-shrink: 0; }
.picker-tag-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.picker-item--create { color: var(--color-accent); font-weight: 600; border-top: 1px solid var(--color-base-300); margin-top: 4px; border-radius: 0 0 6px 6px; }
.picker-item--create:hover { background: color-mix(in oklch, var(--color-accent) 10%, transparent); }
:global(.picker-check) { flex-shrink: 0; color: var(--color-accent); }
:global(.picker-icon-fallback) { color: var(--color-accent); opacity: 0.6; }
.picker-backdrop { position: fixed; inset: 0; z-index: 9998; pointer-events: auto; }

.picker-wrap--sel { position: relative; }
.bulk-tag-dropdown {
        position: absolute;
        top: calc(100% + 6px);
        right: 0;
        z-index: 9999;
        background: var(--color-base-100);
        border: 1px solid var(--color-base-300);
        border-radius: 8px;
        box-shadow: 0 8px 24px color-mix(in oklch, black 20%, transparent);
        padding: 4px;
        min-width: 190px;
        max-width: 260px;
        max-height: 280px;
        overflow-x: hidden;
        overflow-y: auto;
        scrollbar-width: thin;
        animation: picker-pop 150ms cubic-bezier(0.22, 1, 0.36, 1) both;
}

    /* ── Feed ────────────────────────────────────────────────── */
    .feed-wrap {
        border-top: 1px solid var(--color-base-300);
    }


    .sentinel { height: 1px; }

    /* ── Skeleton ────────────────────────────────────────────── */
    .skeleton-card { padding: 12px 20px 10px; border-bottom: 1px solid var(--color-base-300); }
    .sk-row        { display: flex; align-items: center; gap: 6px; }
    .sk-ml-auto    { margin-left: auto; }
    .sk-publisher  { margin-bottom: 10px; }
    .sk-actions    { gap: 6px; }
    .sk-bar, .sk-circle, .sk-dot {
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
    .sk-circle       { width: 16px; height: 16px; border-radius: 50%; flex-shrink: 0; }
    .sk-circle.sk-sm { width: 24px; height: 24px; border-radius: 6px; }
    .sk-dot          { width: 3px;  height: 3px;  border-radius: 50%; flex-shrink: 0; }
    .sk-bar          { height: 10px; flex-shrink: 0; }
    .sk-title        { height: 14px; margin-bottom: 5px; border-radius: 5px; }
    .sk-desc         { height: 11px; margin-bottom: 4px; }
    .skeleton-card:nth-child(1) .sk-bar, .skeleton-card:nth-child(1) .sk-circle { animation-delay: 0s;    }
    .skeleton-card:nth-child(2) .sk-bar, .skeleton-card:nth-child(2) .sk-circle { animation-delay: .15s; }
    .skeleton-card:nth-child(3) .sk-bar, .skeleton-card:nth-child(3) .sk-circle { animation-delay: .3s;  }
    .skeleton-card:nth-child(4) .sk-bar, .skeleton-card:nth-child(4) .sk-circle { animation-delay: .45s; }
    .skeleton-card:nth-child(5) .sk-bar, .skeleton-card:nth-child(5) .sk-circle { animation-delay: .6s;  }
    .skeleton-card:nth-child(6) .sk-bar, .skeleton-card:nth-child(6) .sk-circle { animation-delay: .75s; }
    @keyframes shimmer {
        0%   { background-position:  200% center; }
        100% { background-position: -200% center; }
    }

    /* ── States ──────────────────────────────────────────────── */
    .state-empty {
        text-align: center; padding: 48px 16px;
        color: color-mix(in oklch, var(--color-base-content) 50%, transparent);
        font-size: 15px;
    }
    .state-error {
        display: flex; flex-direction: column; align-items: center;
        gap: 12px; padding: 48px 16px;
        color: color-mix(in oklch, var(--color-error, #e74c3c) 80%, transparent);
        font-size: 14px; text-align: center;
    }
    .retry-btn {
        padding: 7px 18px; border-radius: 6px;
        border: 1px solid color-mix(in oklch, var(--color-error, #e74c3c) 40%, transparent);
        background: transparent; color: var(--color-error, #e74c3c);
        font-size: 13px; font-weight: 600; cursor: pointer; transition: background 130ms;
    }
    .retry-btn:hover { background: color-mix(in oklch, var(--color-error, #e74c3c) 10%, transparent); }
    .end-label {
        text-align: center; padding: 28px 16px 40px;
        font-size: 12px; font-weight: 500;
        color: color-mix(in oklch, var(--color-base-content) 35%, transparent);
        letter-spacing: 0.03em;
    }
</style>
