<script lang="ts">
    import { onMount } from 'svelte';
import { untrack } from 'svelte';
import { Heart, ThumbsDown, Bookmark, Check, Tag } from '@lucide/svelte';
import { t, locale } from 'svelte-i18n';
 import { get } from 'svelte/store';
 import { apiFetch } from '$lib/api';
	import { clearFeedCache } from '$lib/stores/feedCache';
	import { showCoverImages, coverImagePosition } from '$lib/stores/preferences';

let {
    item,
    server = '',
    selectionMode = false,
    selected = false,
    onToggleSelect,
    tags = [],
    onTagClick,
    userTags = [],
} = $props<{
    item: {
        item_id: string;
        title: string;
        description?: string;
        author?: string;
        link: string;
        pub_date: string;
        feed_title?: string;
        feed_icon?: string;
        feed_sha256?: string;
        liked?: boolean;
        disliked?: boolean;
        saved?: boolean;
        image_url?: string;
    };
    server?: string;
    selectionMode?: boolean;
    selected?: boolean;
    onToggleSelect?: (item: any) => void;
    tags?: Array<{ tag_id: number; name: string; color?: string; source: string }>;
    onTagClick?: (tag: { tag_id: number; name: string; color?: string; source: string }) => void;
    userTags?: Array<{ id: number; name: string; color?: string }>;
}>();

let liked = $state(item.liked ?? false);
let disliked = $state(item.disliked ?? false);
let saved = $state(item.saved ?? false);
$effect(() => {
	item.liked;
	item.disliked;
	item.saved;
	untrack(() => {
		liked = item.liked ?? false;
		disliked = item.disliked ?? false;
		saved = item.saved ?? false;
	});
});
  let likeLoading = $state(false);
  let dislikeLoading = $state(false);
  let saveLoading = $state(false);

    // ── Long press ────────────────────────────────────────────────────────────
    let pressTimer:  ReturnType<typeof setTimeout> | null = null;
    let pressStartX = 0;
    let pressStartY = 0;
    let didLongPress = false;
    let hasToggled   = false;

    function clearTimer() {
        if (pressTimer) { clearTimeout(pressTimer); pressTimer = null; }
    }

    function triggerLongPress() {
        if (hasToggled) return;
        didLongPress = true;
        hasToggled   = true;
        navigator.vibrate?.(40);
        onToggleSelect?.(item);
    }

    // ── Touch (mobile) ────────────────────────────────────────────────────────
    function onTouchStart(e: TouchEvent) {
        pressStartX  = e.touches[0].clientX;
        pressStartY  = e.touches[0].clientY;
        didLongPress = false;
        hasToggled   = false;
        clearTimer();
        pressTimer = setTimeout(triggerLongPress, 400);
    }

    function onTouchMove(e: TouchEvent) {
        const dx = Math.abs(e.touches[0].clientX - pressStartX);
        const dy = Math.abs(e.touches[0].clientY - pressStartY);
        if (dx > 8 || dy > 8) clearTimer();
    }

    function onTouchEnd() { clearTimer(); }

    // ── Mouse long press (desktop, left button) ───────────────────────────────
    function onMouseDown(e: MouseEvent) {
        if (e.button !== 0) return;
        pressStartX  = e.clientX;
        pressStartY  = e.clientY;
        didLongPress = false;
        hasToggled   = false;
        clearTimer();
        pressTimer = setTimeout(triggerLongPress, 500);
    }

    function onMouseMove(e: MouseEvent) {
        const dx = Math.abs(e.clientX - pressStartX);
        const dy = Math.abs(e.clientY - pressStartY);
        if (dx > 6 || dy > 6) clearTimer();
    }

    function onMouseUp()    { clearTimer(); }
    function onMouseLeave() { clearTimer(); }

    // ── Right-click → selection (desktop) ────────────────────────────────────
    function onContextMenu(e: MouseEvent) {
        e.preventDefault();
        clearTimer();
        if (hasToggled) return;
        hasToggled = true;
        onToggleSelect?.(item);
    }

    // ── Card click ────────────────────────────────────────────────────────────
    function handleCardClick(e: MouseEvent) {
        if (didLongPress) {
            didLongPress = false;
            e.preventDefault();
            return;
        }
        if (selectionMode) {
            e.preventDefault();
            onToggleSelect?.(item);
        }
    }

    // ── Checkbox circle ───────────────────────────────────────────────────────
    function handleCheckboxClick(e: MouseEvent) {
        e.preventDefault();
        e.stopPropagation();
        onToggleSelect?.(item);
    }

    // ── Voting ────────────────────────────────────────────────────────────────
    async function sendVote(type: 'like' | 'dislike') {
        if (!item.item_id) return;
        if (type === 'like'    && likeLoading)    return;
        if (type === 'dislike' && dislikeLoading) return;

        if (type === 'like')    likeLoading    = true;
        else                    dislikeLoading = true;

        try {
            const res = await apiFetch(`/api/feed/${item.item_id}/${type}`, {
                method:      'POST',
                credentials: 'include',
                headers:     { 'Content-Type': 'application/json' },
            });

            if (res.status === 401) { window.location.replace('/'); return; }
            if (!res.ok) throw new Error(`Error ${res.status}`);

            if (type === 'like') {
                liked    = !liked;
                if (liked) disliked = false;
            } else {
                disliked = !disliked;
                if (disliked) liked = false;
            }
        } catch (err) {
            console.error(`Vote ${type} failed:`, err);
        } finally {
            if (type === 'like')    likeLoading    = false;
            else                    dislikeLoading = false;
        }
    }

    function handleLike(e: MouseEvent) {
        e.preventDefault();
        e.stopPropagation();
        sendVote('like');
    }
  function handleDislike(e: MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    sendVote('dislike');
  }

// ── Save ────────────────────────────────────────────────────────────────
async function toggleSave(e: MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (saveLoading || !item.item_id) return;
    saveLoading = true;
    try {
        const res = await apiFetch(`/api/feed/${item.item_id}/save`, {
            method: saved ? 'DELETE' : 'POST',
            credentials: 'include',
        });
        if (!res.ok) throw new Error(`Error ${res.status}`);
        saved = !saved;
    } catch (err) {
        console.error('Save failed:', err);
    } finally {
        saveLoading = false;
    }
}

// ── Tag assignment ──────────────────────────────────────────────────────
let localTags = $state(tags);
$effect(() => {
	tags;
	untrack(() => { localTags = tags; });
});
let tagDropdownOpen = $state(false);
let tagAssignLoading = $state(false);

function toggleTagDropdown(e: MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    tagDropdownOpen = !tagDropdownOpen;
}

async function assignTag(tagId: number, e: MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (!item.item_id || tagAssignLoading) return;
    tagAssignLoading = true;
    try {
        const res = await apiFetch('/api/tags/assign', {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ item_id: item.item_id, tag_id: tagId }),
        });
if (res.ok) {
				clearFeedCache();
				const ut = userTags.find(ut => ut.id === tagId);
				if (ut && !localTags.some(lt => lt.tag_id === tagId)) {
					localTags = [...localTags, { tag_id: ut.id, name: ut.name, color: ut.color, source: 'manual' }];
				}
			}
    } catch { /* */ }
    finally { tagAssignLoading = false; }
}

async function unassignTag(tagId: number, e: MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (!item.item_id || tagAssignLoading) return;
    tagAssignLoading = true;
    try {
        const res = await apiFetch('/api/tags/assign', {
            method: 'DELETE',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ item_id: item.item_id, tag_id: tagId }),
        });
        if (res.ok) {
            localTags = localTags.filter(lt => lt.tag_id !== tagId);
        }
    } catch { /* */ }
    finally { tagAssignLoading = false; }
}

function handleTagOutsideClick(e: MouseEvent) {
    if (tagDropdownOpen && !(e.target as HTMLElement).closest('.tag-assign-wrap')) {
        tagDropdownOpen = false;
    }
}

onMount(() => {
    document.addEventListener('click', handleTagOutsideClick);
    return () => document.removeEventListener('click', handleTagOutsideClick);
});

    // ── Helpers ───────────────────────────────────────────────────────────────
	function formatDate(dateStr: string): string {
        const now  = new Date();
        const date = new Date(dateStr);
        const ms   = now.getTime() - date.getTime();
        const min  = Math.floor(ms / 60_000);
        const h    = Math.floor(ms / 3_600_000);
        const d    = Math.floor(ms / 86_400_000);

        if (min < 1)  return get(t)('postcard.now');
        if (min < 60) return `${min}${get(t)('postcard.minutesShort')}`;
        if (h   < 24) return `${h}${get(t)('postcard.hoursShort')}`;
        if (d   < 7)  return `${d}${get(t)('postcard.daysShort')}`;

        return date.toLocaleDateString(get(locale) ?? 'en', {
            day:   '2-digit',
            month: 'short',
            year:  date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
	});
	}

	let formattedDate = $derived.by(() => formatDate(item.pub_date));

	function getDomain(url: string) {
        try { return new URL(url).hostname.replace('www.', ''); }
        catch { return url; }
    }

    function hideImage(event: Event) {
        (event.currentTarget as HTMLImageElement).style.display = 'none';
    }

    // Strips HTML to ensure CSS line-clamp works perfectly on 2 lines
    function stripHtml(html: string): string {
        let text = html.replace(/<br\s*[\/]?>/gi, ' '); // Converts <br> to space
        text = text.replace(/<[^>]+>/g, ''); // Removes all other tags
        return text.replace(/\s{2,}/g, ' ').trim(); // Removes multiple spaces
    }

	// ── Cover image helpers ─────────────────────────────────────────────────
	let showCover = $derived($showCoverImages && !!item.image_url);
	let coverPos = $derived($coverImagePosition);

	function onCoverError(event: Event) {
		(event.currentTarget as HTMLElement).style.display = 'none';
	}
</script>


<article
    class="post-card"
    class:is-selected={selected}
    class:sel-mode={selectionMode}
    class:cover-right={showCover && coverPos === 'right'}
    class:cover-bottom={showCover && coverPos === 'bottom'}
    ontouchstart={onTouchStart}
    ontouchmove={onTouchMove}
    ontouchend={onTouchEnd}
    onmousedown={onMouseDown}
    onmousemove={onMouseMove}
    onmouseup={onMouseUp}
    onmouseleave={onMouseLeave}
    oncontextmenu={onContextMenu}
    onclick={handleCardClick}
>
    <!-- ── Seleção ────────────────────────────────────────────────────────── -->
    <div class="sel-col" aria-hidden={!selectionMode}>
        <button
            class="sel-circle"
            onclick={handleCheckboxClick}
            aria-label={selected ? $t('postcard.deselect') : $t('postcard.select')}
            aria-checked={selected}
            role="checkbox"
            tabindex={selectionMode ? 0 : -1}
        >
            {#if selected}
                <Check size={11} strokeWidth={3.5} />
            {/if}
        </button>
    </div>

    <!-- ── Conteúdo ───────────────────────────────────────────────────────── -->
    <div class="post-content">

    <!-- Publisher row -->
    <header class="publisher-row">
      <a
        href={item.feed_sha256 ? `/f/${item.feed_sha256}` : undefined}
        class="feed-link"
        onclick={(e) => { if (selectionMode) { e.preventDefault(); e.stopPropagation(); } }}
      >
        {#if item.feed_icon}
          <img
            src={item.feed_icon}
            alt={item.feed_title ?? ''}
            class="feed-icon"
            onerror={hideImage}
          />
        {/if}
        <span class="feed-title">{item.feed_title ?? getDomain(item.link)}</span>
      </a>
      {#if item.author}
        <span class="separator" aria-hidden="true">·</span>
        <span class="author">{item.author}</span>
      {/if}
      <time class="pub-date" datetime={item.pub_date}>{formattedDate}</time>
    </header>

        <!-- Title -->
        <a
            href="/a/{item.item_id}"
            class="title-link"
            tabindex={selectionMode ? -1 : 0}
            onclick={(e) => { if (selectionMode) { e.preventDefault(); e.stopPropagation(); } }}
        >
            {item.title}
        </a>

		<!-- Description -->
		{#if item.description}
			<p class="description">{stripHtml(item.description)}</p>
		{/if}

		{#if showCover && coverPos === 'bottom'}
			<img
				src={item.image_url}
				alt=""
				class="cover-image cover-image--bottom"
				onerror={onCoverError}
			/>
		{/if}

<!-- Tag chips -->
{#if localTags.length > 0}
<div class="tag-chips">
{#each localTags as tag (tag.tag_id)}
<button
class="tag-chip"
style="--chip-color: {tag.color || '#3b82f6'}"
onclick={() => onTagClick?.(tag)}
disabled={!onTagClick}
>
{tag.name}
</button>
{/each}
</div>
{/if}

		<!-- Actions -->
    {#if !selectionMode}
      <footer class="actions-row">
        <button
          onclick={handleLike}
          disabled={likeLoading}
          class="action-btn"
          class:action-active={liked}
          aria-label={liked ? $t('postcard.unlike') : $t('postcard.like')}
          aria-pressed={liked}
        >
          {#if likeLoading}
            <span class="loading loading-spinner loading-xs"></span>
          {:else}
            <Heart size={15} fill={liked ? 'currentColor' : 'none'} />
          {/if}
        </button>

<button
    onclick={handleDislike}
    disabled={dislikeLoading}
    class="action-btn"
    class:action-active={disliked}
    aria-label={disliked ? $t('postcard.undoDislike') : $t('postcard.dislike')}
    aria-pressed={disliked}
    >
    {#if dislikeLoading}
    <span class="loading loading-spinner loading-xs"></span>
    {:else}
    <ThumbsDown size={15} fill={disliked ? 'currentColor' : 'none'} />
    {/if}
    </button>

	<div class="tag-assign-wrap" onclick={(e) => e.stopPropagation()}>
		<button
			onclick={toggleTagDropdown}
			disabled={tagAssignLoading}
			class="action-btn"
			class:action-tag-active={localTags.length > 0}
			aria-label={$t('postcard.tag')}
			aria-expanded={tagDropdownOpen}
		>
			{#if tagAssignLoading}
				<span class="loading loading-spinner loading-xs"></span>
			{:else}
				<Tag size={15} />
			{/if}
		</button>
		{#if tagDropdownOpen}
			<div class="tag-dropdown" onclick={(e) => e.stopPropagation()}>
				{#if userTags.length === 0}
					<p class="tag-dropdown-empty">{$t('postcard.noTagsYet')}</p>
				{:else}
					{#each userTags as ut (ut.id)}
						{@const isAssigned = localTags.some(t => t.tag_id === ut.id)}
						<button
							class="tag-dropdown-item"
							class:tag-dropdown-item--assigned={isAssigned}
							onclick={(e) => isAssigned ? unassignTag(ut.id, e) : assignTag(ut.id, e)}
							disabled={tagAssignLoading}
						>
							<span class="tag-dot" style="background: {ut.color || '#3b82f6'}"></span>
							<span class="tag-dropdown-item-text">{ut.name}</span>
							{#if isAssigned}
								<Check size={12} class="tag-check" />
							{/if}
						</button>
					{/each}
				{/if}
			</div>
		{/if}
	</div>

	<button
		onclick={toggleSave}
		disabled={saveLoading}
		class="action-btn action-save"
		class:action-save-active={saved}
		aria-label={saved ? $t('postcard.unsave') : $t('postcard.save')}
		aria-pressed={saved}
	>
		{#if saveLoading}
			<span class="loading loading-spinner loading-xs"></span>
		{:else}
			<Bookmark size={15} fill={saved ? 'currentColor' : 'none'} />
		{/if}
	</button>
	</footer>
    {/if}
    </div>

	<!-- Cover image right -->
	{#if showCover && coverPos === 'right'}
		<img
			src={item.image_url}
			alt=""
			class="cover-image cover-image--right"
			onerror={onCoverError}
		/>
	{/if}
</article>


<style>
    /* ── Card ────────────────────────────────────────────────── */
    .post-card {
        display: flex;
        align-items: flex-start;
        padding: 12px 6px 4px;
        border-bottom: 1px solid var(--color-base-300); /* Cleaner than color-mix */
        transition: background 120ms ease;
        -webkit-tap-highlight-color: transparent;
        user-select: none;
        cursor: default;
    }
.post-card:hover {
  background: var(--color-base-200);
}
.post-card:active:not(.sel-mode) {
  background: color-mix(in oklch, var(--color-base-content) 8%, transparent);
}
    .post-card.is-selected {
        background: color-mix(in oklch, var(--color-accent) 8%, transparent);
        border-left: 3px solid var(--color-accent); /* Yellow highlight border for selection */
        padding-left: 17px; /* Compensates the 3px border to prevent layout shift */
    }
    .post-card.sel-mode {
        cursor: pointer;
    }

    /* ── Selection column ──────────────────────────────────── */
    .sel-col {
        flex-shrink: 0;
        width: 0;
        overflow: hidden;
        display: flex;
        align-items: flex-start;
        padding-top: 2px;
        transition: width 220ms cubic-bezier(0.22, 1, 0.36, 1),
                    margin-right 220ms cubic-bezier(0.22, 1, 0.36, 1);
    }
    .sel-mode .sel-col {
        width: 22px;
        margin-right: 10px;
    }

    .sel-circle {
        flex-shrink: 0;
        width: 22px;
        height: 22px;
        border-radius: 50%;
        border: 2px solid color-mix(in oklch, var(--color-base-content) 28%, transparent);
        background: transparent;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        color: transparent;
        transition: background 150ms, border-color 150ms, color 150ms;
        padding: 0;
    }
    .is-selected .sel-circle {
        background: var(--color-accent);
        border-color: var(--color-accent);
        color: var(--color-base-100); /* Dark icon on yellow button */
    }

    /* ── Body ────────────────────────────────────────────────── */
    .post-content {
        flex: 1;
        min-width: 0;
    }

	/* ── Cover images ────────────────────────────────────────── */
	.cover-image {
		object-fit: cover;
		border-radius: 8px;
		flex-shrink: 0;
	}
	.cover-image--right {
		width: 110px;
		height: 80px;
		margin-left: 10px;
		margin-top: 2px;
	}
	.cover-image--bottom {
		width: 100%;
		max-height: 160px;
		margin-bottom: 8px;
	}

    /* ── Publisher row ───────────────────────────────────────── */
    .publisher-row {
        display: flex;
        align-items: center;
        gap: 5px;
        margin-bottom: 6px;
        min-width: 0;
    }

.feed-icon {
  width: 15px;
  height: 15px;
  border-radius: 50%;
  object-fit: contain;
  flex-shrink: 0;
}

.feed-link {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  min-width: 0;
  flex: 0 1 auto;
  text-decoration: none;
  color: inherit;
}

.feed-title {
  font-size: 11.5px;
  font-weight: 700;
  color: var(--color-accent);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 0 1 auto;
  min-width: 0;
}

    .separator {
        font-size: 11px;
        color: color-mix(in oklch, var(--color-base-content) 25%, transparent);
        flex-shrink: 0;
    }

    .author {
        font-size: 11.5px;
        color: color-mix(in oklch, var(--color-base-content) 45%, transparent);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        flex: 0 1 auto; /* Pode encolher, mas não crescer além do necessário */
        min-width: 0;
    }

    .pub-date {
        margin-left: auto;
        font-size: 11px;
        color: color-mix(in oklch, var(--color-base-content) 35%, transparent);
        white-space: nowrap;
        flex-shrink: 0;
        padding-left: 8px;
    }

    /* ── Title ───────────────────────────────────────────────── */
.title-link {
display: block;
font-family: var(--font-post-title);
        font-size: 16px;
        font-weight: 500; /* Medium: much more legible than 600 in sans-serif */
        line-height: 1.4;
        margin-bottom: 6px;
        color: var(--color-base-content);
        text-decoration: none;
        transition: color 140ms;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
.title-link:hover {
  color: var(--color-accent);
}
.title-link:active {
  opacity: 0.7;
}

	/* ── Description ─────────────────────────────────────────── */
	.description {
		font-family: var(--font-article-body);
		font-size: 13.5px;
		font-weight: 400; /* Regular weight is better for long body text */
		line-height: 1.5;
		color: color-mix(in oklch, var(--color-base-content) 70%, transparent);
		margin-bottom: 8px;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}

	/* ── Tag chips ──────────────────────────────────────────── */
	.tag-chips {
		display: flex;
		flex-wrap: wrap;
		gap: 4px;
		margin-bottom: 6px;
	}
.tag-chip {
	font-size: 10px;
	font-weight: 600;
	letter-spacing: 0.02em;
	padding: 2px 7px;
	border-radius: 999px;
	border: none;
	background: color-mix(in oklch, var(--chip-color) 14%, transparent);
	color: var(--chip-color);
	white-space: nowrap;
	line-height: 1.5;
	cursor: default;
}
.tag-chip:not(:disabled) {
	cursor: pointer;
	transition: background 100ms;
}
.tag-chip:not(:disabled):hover {
	background: color-mix(in oklch, var(--chip-color) 24%, transparent);
}

    /* ── Actions ─────────────────────────────────────────────── */
    .actions-row {
        display: flex;
        align-items: center;
        gap: 2px;
        padding-bottom: 4px;
    }

    .action-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 30px;
        height: 30px;
        border-radius: 6px; /* Less rounded, more robust */
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
.action-btn:active {
  transform: scale(0.88);
}
    .action-btn:disabled { opacity: 0.5; cursor: default; }

/* Like/Dislike colors aligned with DaisyUI without being too loud */
.action-active {
	color: var(--color-error) !important;
}

.action-save-active {
    color: var(--color-accent) !important;
}
.action-tag-active {
    color: var(--color-accent) !important;
}

.tag-assign-wrap { position: relative; display: inline-flex; margin-left: auto; }
.tag-dropdown {
    position: absolute;
    bottom: calc(100% + 6px);
    left: 50%;
    transform: translateX(-50%);
    z-index: 50;
    background: var(--color-base-100);
    border: 1px solid var(--color-base-300);
    border-radius: 8px;
    box-shadow: 0 8px 24px color-mix(in oklch, black 20%, transparent);
    padding: 4px;
    min-width: 170px;
    max-width: 240px;
    max-height: 260px;
    overflow-x: hidden;
    overflow-y: auto;
    scrollbar-width: thin;
    animation: tag-drop-pop 150ms cubic-bezier(0.22, 1, 0.36, 1) both;
}
@keyframes tag-drop-pop {
    from { opacity: 0; transform: translateX(-50%) translateY(4px) scale(0.97); }
    to { opacity: 1; transform: translateX(-50%) translateY(0) scale(1); }
}
.tag-dropdown-empty {
    padding: 12px;
    font-size: 12px;
    color: color-mix(in oklch, var(--color-base-content) 50%, transparent);
    text-align: center;
    margin: 0;
}
.tag-dropdown-item {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    padding: 7px 10px;
    border: none;
    background: transparent;
    cursor: pointer;
    font-size: 12.5px;
    font-weight: 500;
    color: var(--color-base-content);
    border-radius: 6px;
    transition: background 110ms;
    text-align: left;
}
.tag-dropdown-item:hover { background: var(--color-base-200); }
.tag-dropdown-item--assigned { color: var(--color-accent); }
.tag-dropdown-item-text { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tag-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.tag-check { flex-shrink: 0; color: var(--color-accent); }
</style>
