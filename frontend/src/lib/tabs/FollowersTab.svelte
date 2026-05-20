<script lang="ts">
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import FollowFeedModal from '$lib/components/FollowFeedModal.svelte';
import {
  Rss, ChevronRight, ChevronDown, X, MoreHorizontal, FolderPlus,
  Trash2, Folder, Plus, Search, MoveRight,
  Link, GripVertical
} from '@lucide/svelte';
    import { t, locale } from 'svelte-i18n';
    import { get } from 'svelte/store';
import { notifySubscriptionChanged } from '$lib/stores/subscription';
 import { apiFetch } from '$lib/api';

    // ── Types ────────────────────────────────────────────
    type Feed = {
        feed_sha256: string | null;
        url: string | null;
        title?: string;
        icon?: string;
        folder?: { id: number; name: string; parent_id?: number | null } | null;
        _empty_folder?: boolean;
    };

    type FolderGroup = {
        folder: { id: number; name: string; parent_id?: number | null } | null;
        feeds: Feed[];
        depth: number;
    };

    // ── State ────────────────────────────────────────────
    let subsData        = $state<Feed[]>([]);
    let subsLoading     = $state(true);
    let subsError       = $state('');
    let expandedFolders = $state<Record<string, boolean>>({});
    let searchQuery     = $state('');
    let isRefreshing    = $state(false);

	// Add feed modal
	let showAddModal = $state(false);
	let addFeedUrl = $state('');
	let addFeedInput = $state<HTMLInputElement | null>(null);
	let feedToAdd: { title: string; url: string } | null = $state(null);
	let showFollowModal = $state(false);
	let addFeedMode = $state<'discover' | 'search'>('discover');

    // Context menu
    let contextMenu = $state<{
        type: 'feed' | 'folder';
        id: string;
        name: string;
        x: number;
        y: number;
        url?: string;
        folderId?: number | null;
    } | null>(null);

    // Move-to-folder picker
    let movePicker = $state<{
        feedId: string;
        currentFolderId: number | null;
    } | null>(null);

    // Drag & Drop
    let dragItem    = $state<{ type: 'feed' | 'folder'; id: string; fromKey: number | string } | null>(null);
    let dragOverKey = $state<number | string | null>(null);

    // New folder dialog
    let newFolderDialog = $state<{ parentFolderKey: number | null; parentFolderName: string | null; name: string } | null>(null);

// ── Mount ─────────────────────────────────────────────
onMount(() => {
	loadSubscriptions();

	const handler = (e: MouseEvent) => {
		if (!(e.target as HTMLElement).closest('.ctx-menu') &&
			!(e.target as HTMLElement).closest('.move-picker')) {
			contextMenu = null;
			movePicker = null;
		}
	};
	document.addEventListener('mousedown', handler);
	return () => document.removeEventListener('mousedown', handler);
});

async function loadSubscriptions(quiet = false) {
        if (!quiet) subsLoading = true;
        else isRefreshing = true;
        subsError = '';
        try {
            const res = await apiFetch('/api/list-subscriptions', { credentials: 'include' });
            if (res.status === 401) { window.location.replace('/'); return; }
            if (!res.ok) throw new Error(`${get(t)('followerstab.loadError')} (${res.status})`);
            const raw  = await res.json();
            const feeds: Feed[] = Array.isArray(raw) ? raw : (raw.feeds ?? []);
            subsData = feeds;
            const init: Record<string, boolean> = {};
            for (const f of feeds) init[String(f.folder?.id ?? '__root__')] = true;
            expandedFolders = init;
        } catch (err: any) {
            subsError = err.message || get(t)('followerstab.loadError');
        } finally {
            subsLoading = false;
            isRefreshing = false;
        }
    }

    function toggleFolder(key: number | string) {
        const k = String(key);
        expandedFolders = { ...expandedFolders, [k]: !(expandedFolders[k] !== false) };
    }

    function isExpanded(key: number | string): boolean {
        return expandedFolders[String(key)] !== false;
    }

    // ── Derived ──────────────────────────────────────────
    let groupedFolders = $derived.by((): FolderGroup[] => {
        const map = new Map<number | string, FolderGroup>();
        for (const feed of subsData) {
            const key: number | string = feed.folder?.id ?? '__root__';
            if (!map.has(key)) map.set(key, { folder: feed.folder ?? null, feeds: [], depth: 0 });
            if (!feed._empty_folder) map.get(key)!.feeds.push(feed);
        }
        const byId = new Map<number, { name: string; parent_id: number | null }>();
        for (const group of map.values())
            if (group.folder?.id != null)
                byId.set(group.folder.id, { name: group.folder.name, parent_id: group.folder.parent_id ?? null });

        const memo = new Map<number | null, string[]>();
        function getPath(id: number | null): string[] {
            if (id === null) return [];
            if (memo.has(id)) return memo.get(id)!;
            const f = byId.get(id!);
            if (!f) { memo.set(id, []); return []; }
            const path = [...getPath(f.parent_id), f.name];
            memo.set(id, path);
            return path;
        }

        const withPath: Array<{ group: FolderGroup; sortKey: string }> = [];
        for (const group of map.values()) {
            const path = group.folder ? getPath(group.folder.id) : [];
            group.depth = Math.max(0, path.length - 1);
            withPath.push({ group, sortKey: path.join('\0') || '\0' });
        }
        return withPath.sort((a, b) => a.sortKey.localeCompare(b.sortKey)).map(({ group }) => group);
    });

    let visibleGroups = $derived.by(() => {
        const parentOf = new Map<number, number | null>();
        for (const g of groupedFolders)
            if (g.folder?.id != null) parentOf.set(g.folder.id, g.folder.parent_id ?? null);

        return groupedFolders.filter(group => {
            let pid: number | null = group.folder?.parent_id ?? null;
            while (pid !== null) {
                if (expandedFolders[String(pid)] === false) return false;
                pid = parentOf.get(pid) ?? null;
            }
            return true;
        });
    });

    let filteredGroups = $derived.by(() => {
        if (!searchQuery.trim()) return visibleGroups;
        const q = searchQuery.toLowerCase();
        return visibleGroups
            .map(group => ({
                ...group,
                feeds: group.feeds.filter(f =>
                    feedDisplayTitle(f).toLowerCase().includes(q) ||
                    (f.url ?? '').toLowerCase().includes(q)
                ),
            }))
            .filter(group =>
                group.feeds.length > 0 ||
                (group.folder?.name ?? 'Default').toLowerCase().includes(q)
            );
    });

    let allFolders = $derived(
        groupedFolders
            .filter(g => g.folder !== null)
            .map(g => g.folder!)
    );

    let totalFeeds = $derived(subsData.filter(f => !f._empty_folder).length);

    function feedDisplayTitle(feed: Feed): string {
        if (feed.title && feed.title !== 'No title') return feed.title;
        try { return new URL(feed.url!).hostname; } catch { return feed.url ?? ''; }
    }

    function navigateToFeed(sha: string)        { goto(`/f/${sha}`); }
    function navigateToFolder(folderId: number)  { goto(`/c/${folderId}`); }

    async function callStructureApi(task: string, payload: Record<string, any>) {
        const res = await apiFetch('/api/following_structure/', {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task, ...payload }),
        });
        if (!res.ok) {
            const detail = await res.json().then(j => j.detail).catch(() => res.status);
            throw new Error(`API error: ${detail}`);
        }
        return res.json();
    }

    // ── Add Feed ──────────────────────────────────────────
    function openAddModal() {
        addFeedUrl   = '';
        showAddModal = true;
        setTimeout(() => addFeedInput?.focus(), 50);
    }

    function closeAddModal() {
        showAddModal = false;
        addFeedUrl   = '';
    }

	function submitAddFeed() {
		const raw = addFeedUrl.trim();
		if (!raw) return;

		const looksLikeUrl = /^https?:\/\//i.test(raw) || /^[^\s]+\.[^\s]/.test(raw);

		if (looksLikeUrl) {
			let url = raw;
			if (!/^https?:\/\//i.test(url)) url = 'https://' + url;
			let title = url;
			try { title = new URL(url).hostname; } catch {}
			feedToAdd = { title, url };
			addFeedMode = 'discover';
		} else {
			feedToAdd = { title: raw, url: '' };
			addFeedMode = 'search';
		}

		showAddModal = false;
		showFollowModal = true;
	}

    function closeFollowModal() {
        showFollowModal = false;
        feedToAdd = null;
        loadSubscriptions(true);
    }

    // ── Drag & Drop ───────────────────────────────────────
    function onDragStart(e: DragEvent, type: 'feed' | 'folder', id: string, fromKey: number | string) {
        dragItem = { type, id, fromKey };
        e.dataTransfer!.effectAllowed = 'move';
        e.dataTransfer!.setData('text/plain', id);
    }

    function onDragOver(e: DragEvent, key: number | string) {
        e.preventDefault();
        e.dataTransfer!.dropEffect = 'move';
        dragOverKey = key;
    }

    function onDragLeave(e: DragEvent) {
        const rel = e.relatedTarget as HTMLElement | null;
        if (!rel?.closest('.folder-block')) dragOverKey = null;
    }

    async function onDrop(e: DragEvent, targetGroup: FolderGroup) {
        e.preventDefault();
        dragOverKey = null;
        if (!dragItem) return;

        const targetKey: number | string = targetGroup.folder?.id ?? '__root__';
        if (dragItem.fromKey === targetKey) { dragItem = null; return; }
        const targetFolderId: number | null = targetGroup.folder?.id ?? null;

        try {
            if (dragItem.type === 'feed') {
                await callStructureApi('move_feed', { feed: dragItem.id, folder: targetFolderId });
                subsData = subsData.map(f =>
                    f.feed_sha256 === dragItem!.id ? { ...f, folder: targetGroup.folder ?? null } : f
                );
            } else {
                await callStructureApi('move_folder', { folder: Number(dragItem.id), parent_folder: targetFolderId });
                await loadSubscriptions(true);
            }
        } catch (err) {
            console.error('Drop failed:', err);
        }
        dragItem = null;
    }

    // ── Context Menu ──────────────────────────────────────
    function openContextMenu(
        e: MouseEvent,
        type: 'feed' | 'folder',
        id: string,
        name: string,
        url?: string,
        folderId?: number | null,
    ) {
        e.stopPropagation();
        e.preventDefault();
        movePicker  = null;
        const x = Math.min(e.clientX, window.innerWidth  - 200);
        const y = Math.min(e.clientY, window.innerHeight - 200);
        contextMenu = { type, id, name, x, y, url, folderId };
    }

    function shareItem() {
        if (!contextMenu) return;
        const link = contextMenu.type === 'feed' ? `/f/${contextMenu.id}` : `/c/${contextMenu.id}`;
        navigator.clipboard.writeText(window.location.origin + link).catch(() => {});
        contextMenu = null;
    }

    async function deleteItem() {
        if (!contextMenu) return;
        const snap = { ...contextMenu };
        contextMenu = null;

        if (snap.type === 'feed') {
            try {
        await apiFetch('/api/feed-remove', {
          method: 'POST', credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: snap.url }),
        });
        await callStructureApi('delete_feed', { feed: snap.id });
        subsData = subsData.filter(f => f.feed_sha256 !== snap.id);
        notifySubscriptionChanged();
            } catch (err) { console.error('Delete feed failed:', err); }
        } else {
            try {
                await callStructureApi('delete_folder', { folder: Number(snap.id) });
                await loadSubscriptions(true);
            } catch (err) { console.error('Delete folder failed:', err); }
        }
    }

    function openMovePicker() {
        if (!contextMenu || contextMenu.type !== 'feed') return;
        movePicker = { feedId: contextMenu.id, currentFolderId: contextMenu.folderId ?? null };
        contextMenu = null;
    }

    async function moveToFolder(targetFolder: { id: number; name: string } | null) {
        if (!movePicker) return;
        const { feedId } = movePicker;
        movePicker = null;
        try {
            await callStructureApi('move_feed', { feed: feedId, folder: targetFolder?.id ?? null });
            subsData = subsData.map(f =>
                f.feed_sha256 === feedId ? { ...f, folder: targetFolder ?? null } : f
            );
        } catch (err) { console.error('Move feed failed:', err); }
    }

    // ── Create Folder ─────────────────────────────────────
    function openNewFolderDialog(parentFolderId: number | null = null, parentFolderName: string | null = null) {
        newFolderDialog = { parentFolderKey: parentFolderId, parentFolderName, name: '' };
        contextMenu = null;
    }

    async function confirmCreateFolder() {
        if (!newFolderDialog?.name.trim()) return;
        const name     = newFolderDialog.name.trim();
        const parentId = newFolderDialog.parentFolderKey;
        try {
            await callStructureApi('create_folder', { name, parent_folder: parentId });
            await loadSubscriptions(true);
        } catch (err) { console.error('Create folder failed:', err); }
        newFolderDialog = null;
    }
</script>

<!-- ── Snippets ─────────────────────────────────────── -->

{#snippet skeletonRow()}
    <div class="sk-row" aria-hidden="true">
        <div class="sk-circle"></div>
        <div class="sk-bar" style="width:110px"></div>
        <div class="sk-bar sk-ml-auto" style="width:28px; opacity:.4"></div>
    </div>
{/snippet}

<!-- ── Markup ──────────────────────────────────────── -->

<div class="page-root">
  <div class="main-content">

  <!-- Search bar at top (EventsTab-style) -->
  <header class="page-header">
    <div class="search-wrap">
      <input
        class="search-input"
        type="search"
        placeholder="{$t('followerstab.searchPlaceholder')}"
        bind:value={searchQuery}
        aria-label="{$t('followerstab.searchAria')}"
        autocomplete="off"
        autocorrect="off"
        spellcheck="false"
      />
      {#if searchQuery}
        <button class="search-clear" onclick={() => (searchQuery = '')} aria-label="{$t('followerstab.clearSearch')}">
          <X size={14} strokeWidth={2} />
        </button>
      {/if}
	<Search size={18} class="search-icon" />
	</div>

	<div class="action-row">
		<button
			class="action-btn"
			onclick={() => openNewFolderDialog(null, null)}
			aria-label="{$t('followerstab.newFolder')}"
		>
			<FolderPlus size={15} strokeWidth={2} />
			{$t('followerstab.newFolder')}
		</button>
		<button
			class="action-btn"
			onclick={openAddModal}
			aria-label="{$t('followerstab.addFeed')}"
		>
			<Plus size={15} strokeWidth={2.5} />
			{$t('followerstab.addFeed')}
		</button>
	</div>
	</header>

        <!-- Tree -->
        <div class="tree-body">
            {#if subsLoading}
                {#each Array.from({ length: 8 }) as _, i (i)}
                    {@render skeletonRow()}
                {/each}
            {:else if subsError}
                <div class="header-error">
                    <span class="header-error__icon" aria-hidden="true">⚠</span>
                    {subsError}
                    <button class="header-error__retry" onclick={() => loadSubscriptions()}>
                        {$t('followerstab.tryAgain')}
                    </button>
                </div>
            {:else if groupedFolders.length === 0}
                <div class="state-empty-wrap">
                    <Rss size={28} strokeWidth={1.5} class="empty-icon" />
                    <p class="state-empty">{$t('followerstab.emptyTitle')}</p>
                    <button class="empty-cta" onclick={openAddModal}>
                        <Plus size={14} strokeWidth={2.5} />
                        {$t('followerstab.addFirstFeed')}
                    </button>
                </div>
            {:else if filteredGroups.length === 0}
                <div class="state-empty-wrap">
                    <Search size={24} strokeWidth={1.5} class="empty-icon" />
                    <p class="state-empty">{$t('followerstab.noFeedFound')} "{searchQuery}"</p>
                </div>
            {:else}
                {#each filteredGroups as group (group.folder?.id ?? '__root__')}
                    {@const groupKey      = group.folder?.id ?? '__root__'}
                    {@const folderExpanded = isExpanded(groupKey)}
                    {@const isOver        = dragOverKey === groupKey}
                    {@const indent        = group.depth * 14}

                    <div
                        class="folder-block"
                        class:drag-over={isOver}
                        ondragover={(e) => onDragOver(e, groupKey)}
                        ondragleave={onDragLeave}
                        ondrop={(e) => onDrop(e, group)}
                    >
                        <!-- Folder row — no folder icon -->
                        <div
                            class="folder-row"
                            style="padding-left: {6 + indent}px;"
                            role="button"
                            tabindex="0"
                            aria-expanded={folderExpanded}
                            onclick={() => group.folder?.id && navigateToFolder(group.folder.id)}
                            onkeydown={(e) => e.key === 'Enter' && group.folder?.id && navigateToFolder(group.folder.id)}
                        >
                            <button
                                class="chevron-btn"
                                onclick={(e) => { e.stopPropagation(); toggleFolder(groupKey); }}
                                aria-label={folderExpanded ? $t('followerstab.collapseFolder') : $t('followerstab.expandFolder')}
                                tabindex="0"
                            >
                                {#if folderExpanded}
                                    <ChevronDown size={14} strokeWidth={2.5} />
                                {:else}
                                    <ChevronRight size={14} strokeWidth={2.5} />
                                {/if}
                            </button>

                            <span class="folder-name">{group.folder?.name ?? $t('followerstab.defaultFolder')}</span>

                            <span class="folder-badge">{group.feeds.length}</span>

                            <button
                                class="more-btn"
                                title="{$t('followerstab.options')}"
                                onclick={(e) => openContextMenu(
                                    e, 'folder',
                                    String(group.folder?.id ?? '__root__'),
                                    group.folder?.name ?? $t('followerstab.defaultFolder'),
                                    undefined,
                                    group.folder?.id ?? null,
                                )}
                                aria-label="{$t('followerstab.folderOptions')}"
                            >
                                <MoreHorizontal size={14} strokeWidth={2} />
                            </button>
                        </div>

                        <!-- Feed list -->
                        {#if folderExpanded && group.feeds.length > 0}
                            <ul class="feed-list">
                                {#each group.feeds as feed (feed.feed_sha256)}
                                    <li
                                        class="feed-row"
                                        style="padding-left: {22 + indent}px;"
                                        onclick={() => navigateToFeed(feed.feed_sha256!)}
                                        role="button"
                                        tabindex="0"
                                        onkeydown={(e) => e.key === 'Enter' && navigateToFeed(feed.feed_sha256!)}
                                        title={feedDisplayTitle(feed)}
                                    >
                                        <span
                                            class="drag-handle"
                                            aria-hidden="true"
                                            draggable={true}
                                            ondragstart={(e) => {
                                                e.stopPropagation();
                                                onDragStart(e, 'feed', feed.feed_sha256!, groupKey);
                                            }}
                                        >
                                            <GripVertical size={14} strokeWidth={2} />
                                        </span>

                                        {#if feed.icon}
                                            <img
                                                src={feed.icon}
                                                alt=""
                                                class="feed-favicon"
                                                onerror={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                                            />
                                        {:else}
                                            <span class="feed-favicon-fallback">
                                                <Rss size={11} />
                                            </span>
                                        {/if}

                                        <span class="feed-label">{feedDisplayTitle(feed)}</span>

                                        <button
                                            class="more-btn"
                                            title="{$t('followerstab.options')}"
                                            onclick={(e) => openContextMenu(
                                                e, 'feed',
                                                feed.feed_sha256!,
                                                feedDisplayTitle(feed),
                                                feed.url ?? undefined,
                                                feed.folder?.id ?? null,
                                            )}
                                            aria-label="{$t('followerstab.feedOptions')}"
                                        >
                                            <MoreHorizontal size={14} strokeWidth={2} />
                                        </button>
                                    </li>
                                {/each}
                            </ul>
                        {/if}
                    </div>
                {/each}
            {/if}
        </div>

    </div>
</div>

<!-- ── Context Menu ─────────────────────────────────────── -->
{#if contextMenu}
    <div class="ctx-menu" style="top:{contextMenu.y}px; left:{contextMenu.x}px" role="menu">
        <div class="ctx-item-label">{contextMenu.name}</div>
        <hr class="ctx-divider" />

        {#if contextMenu.type === 'folder'}
            <button class="ctx-item" onclick={() => openNewFolderDialog(Number(contextMenu!.id), contextMenu!.name)}>
                <FolderPlus size={14} strokeWidth={2} />
                <span>{$t('followerstab.newSubfolder')}</span>
            </button>
        {/if}

        {#if contextMenu.type === 'feed'}
            <button class="ctx-item" onclick={openMovePicker}>
                <MoveRight size={14} strokeWidth={2} />
                <span>{$t('followerstab.moveToFolder')}</span>
            </button>
        {/if}

        <button class="ctx-item" onclick={shareItem}>
            <Link size={14} strokeWidth={2} />
            <span>{$t('followerstab.copyLink')}</span>
        </button>
        <button class="ctx-item ctx-item--danger" onclick={deleteItem}>
            <Trash2 size={14} strokeWidth={2} />
            <span>{$t('followerstab.remove')}</span>
        </button>
    </div>
{/if}

<!-- ── Move-to-folder Picker ────────────────────────────── -->
{#if movePicker}
    <div class="move-picker" style="top:160px; left:50%; transform:translateX(-50%);" role="menu">
        <div class="ctx-item-label">{$t('followerstab.moveToLabel')}</div>
        <hr class="ctx-divider" />
        <button
            class="ctx-item"
            class:ctx-item--active={movePicker.currentFolderId === null}
            onclick={() => moveToFolder(null)}
        >
            <Folder size={14} strokeWidth={2} />
            <span>{$t('followerstab.defaultRoot')}</span>
        </button>
        {#each allFolders as folder}
            <button
                class="ctx-item"
                class:ctx-item--active={movePicker.currentFolderId === folder.id}
                onclick={() => moveToFolder(folder)}
            >
                <Folder size={14} strokeWidth={2} />
                <span>{folder.name}</span>
            </button>
        {/each}
    </div>
{/if}

<!-- ── Add Feed Dialog ──────────────────────────────────── -->
{#if showAddModal}
    <div class="dialog-backdrop" onclick={closeAddModal} aria-hidden="true"></div>
    <div class="dialog" role="dialog" aria-modal="true" aria-label="{$t('followerstab.addFeedTitle')}">
        <div class="dialog-header">
            <p class="dialog-title">{$t('followerstab.addFeedTitle')}</p>
            <button class="dialog-close" onclick={closeAddModal} aria-label="{$t('followerstab.close')}">
                <X size={16} strokeWidth={2} />
            </button>
        </div>
        <p class="dialog-sub">{$t('followerstab.addFeedSubtitle')}</p>
        <div class="dialog-input-row">
            <Link size={14} strokeWidth={2} class="dialog-input-icon" />
            <input
                bind:this={addFeedInput}
		class="dialog-input"
		type="text"
		placeholder="https://example.com/feed.xml"
                bind:value={addFeedUrl}
                onkeydown={(e) => {
                    if (e.key === 'Enter') submitAddFeed();
                    if (e.key === 'Escape') closeAddModal();
                }}
            />
        </div>
        <div class="dialog-actions">
            <button class="dialog-btn dialog-btn--ghost" onclick={closeAddModal}>{$t('followerstab.cancel')}</button>
            <button
                class="dialog-btn dialog-btn--primary"
                onclick={submitAddFeed}
                disabled={!addFeedUrl.trim()}
            >
                {$t('followerstab.continue')}
            </button>
        </div>
    </div>
{/if}

<!-- ── New Folder Dialog ────────────────────────────────── -->
{#if newFolderDialog}
    <div class="dialog-backdrop" onclick={() => (newFolderDialog = null)} aria-hidden="true"></div>
    <div class="dialog" role="dialog" aria-modal="true" aria-label="{$t('followerstab.newFolderTitle')}">
        <div class="dialog-header">
            <p class="dialog-title">{$t('followerstab.newFolderTitle')}</p>
            <button class="dialog-close" onclick={() => (newFolderDialog = null)} aria-label="{$t('followerstab.close')}">
                <X size={16} strokeWidth={2} />
            </button>
        </div>
        {#if newFolderDialog.parentFolderName}
            <p class="dialog-sub">{$t('followerstab.insideFolder')} "{newFolderDialog.parentFolderName}"</p>
        {/if}
        <div class="dialog-input-row">
            <Folder size={14} strokeWidth={2} class="dialog-input-icon" />
            <input
                class="dialog-input"
                type="text"
                placeholder="{$t('followerstab.folderNamePlaceholder')}"
                bind:value={newFolderDialog.name}
                autofocus
                onkeydown={(e) => {
                    if (e.key === 'Enter') confirmCreateFolder();
                    if (e.key === 'Escape') newFolderDialog = null;
                }}
            />
        </div>
        <div class="dialog-actions">
            <button class="dialog-btn dialog-btn--ghost" onclick={() => (newFolderDialog = null)}>{$t('followerstab.cancel')}</button>
            <button
                class="dialog-btn dialog-btn--primary"
                onclick={confirmCreateFolder}
                disabled={!newFolderDialog.name.trim()}
            >
                {$t('followerstab.create')}
            </button>
        </div>
    </div>
{/if}

<!-- ── Follow Feed Modal ────────────────────────────────── -->
{#if showFollowModal && feedToAdd}
	<FollowFeedModal feed={feedToAdd} mode={addFeedMode} onclose={closeFollowModal} />
{/if}

<style>
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

/* ── Page Header ─────────────────────────────────────────── */
.page-header {
  padding: 24px 0 0;
}

/* ── Search Input ──────────────────────────────────────── */
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
  background: transparent;
  border: none;
  outline: none;
  font-size: 15px;
  color: var(--color-base-content);
  line-height: 1;
  -webkit-appearance: none;
  appearance: none;
}

    .search-input::placeholder {
        color: color-mix(in oklch, var(--color-base-content) 35%, transparent);
    }

    .search-input::-webkit-search-cancel-button,
    .search-input::-webkit-search-decoration {
        display: none;
    }

    :global(.search-icon) {
        flex-shrink: 0;
        color: color-mix(in oklch, var(--color-base-content) 40%, transparent);
        transition: color 180ms ease;
    }

    .search-wrap:focus-within :global(.search-icon) {
        color: var(--color-accent);
    }

    .search-clear {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 20px;
        height: 20px;
        border-radius: 50%;
        border: none;
        background: color-mix(in oklch, var(--color-base-content) 15%, transparent);
        color: color-mix(in oklch, var(--color-base-content) 60%, transparent);
        cursor: pointer;
        padding: 0;
        flex-shrink: 0;
        transition: background 120ms ease;
    }

    .search-clear:hover {
        background: color-mix(in oklch, var(--color-base-content) 25%, transparent);
    }

/* ── Action Row (Add Folder / Add Feed) ─────────────── */
.action-row {
	display: flex;
	gap: 8px;
	padding: 10px 0 0;
}

.action-btn {
	flex: 1;
	display: flex;
	align-items: center;
	justify-content: center;
	gap: 6px;
	padding: 8px 12px;
	border-radius: 10px;
	border: 1px solid var(--color-base-300);
	background: transparent;
	font-size: 13px;
	font-weight: 500;
	color: color-mix(in oklch, var(--color-base-content) 70%, transparent);
	cursor: pointer;
	transition: background 130ms, color 130ms, border-color 130ms;
	white-space: nowrap;
}

.action-btn:hover {
	background: var(--color-base-200);
	color: var(--color-base-content);
}

/* ── Tree Body ──────────────────────────────────────────── */
.tree-body {
	padding-bottom: 32px;
}

    /* ── Skeleton ────────────────────────────────────────────── */
    .sk-row {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 11px 0;
        border-bottom: 1px solid color-mix(in oklch, var(--color-base-300) 40%, transparent);
    }

    .sk-ml-auto {
        margin-left: auto;
    }

    .sk-circle,
    .sk-bar {
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

    .sk-bar {
        height: 10px;
        flex-shrink: 0;
    }

    @keyframes shimmer {
        0% { background-position: 200% center; }
        100% { background-position: -200% center; }
    }

    /* ── Header Error ────────────────────────────────────────── */
    .header-error {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 16px 0;
        font-size: 12.5px;
        color: color-mix(in oklch, var(--color-error, #e74c3c) 75%, transparent);
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
        border: 1px solid color-mix(in oklch, var(--color-error, #e74c3c) 40%, transparent);
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

    /* ── Empty State ─────────────────────────────────────────── */
    .state-empty-wrap {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 48px 20px;
        text-align: center;
        gap: 10px;
    }

    :global(.empty-icon) {
        color: color-mix(in oklch, var(--color-base-content) 30%, transparent);
    }

    .state-empty {
        font-size: 14px;
        color: color-mix(in oklch, var(--color-base-content) 45%, transparent);
        margin: 0;
    }

    .empty-cta {
        display: flex;
        align-items: center;
        gap: 5px;
        margin-top: 6px;
        padding: 7px 14px;
        border-radius: 10px;
        border: 1.5px solid var(--color-accent);
        background: var(--color-accent);
        color: var(--color-base-100);
        font-weight: 700;
        font-size: 12.5px;
        cursor: pointer;
        transition: opacity 150ms ease;
    }

    .empty-cta:hover {
        opacity: 0.85;
    }

    /* ── Folder Blocks ───────────────────────────────────────── */
    .folder-block {
        border-radius: 0;
        transition: background 130ms ease, outline 130ms ease;
        overflow: hidden;
    }

    .folder-block.drag-over {
        background: color-mix(in oklch, var(--color-accent) 8%, transparent);
        outline: 2px dashed color-mix(in oklch, var(--color-accent) 40%, transparent);
        outline-offset: -2px;
    }

.folder-row {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 9px 2px 9px 0;
        border: none;
        background: transparent;
        cursor: pointer;
        text-align: left;
        transition: background 150ms ease;
        user-select: none;
    }

    .folder-row:hover {
        background: color-mix(in oklch, var(--color-base-content) 4%, transparent);
    }

    .folder-row:hover .more-btn {
        opacity: 1;
    }

    .chevron-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        width: 20px;
        height: 20px;
        border: none;
        background: transparent;
        color: color-mix(in oklch, var(--color-base-content) 38%, transparent);
        cursor: pointer;
        padding: 0;
        border-radius: 4px;
        transition: background 120ms ease, color 120ms ease;
    }

    .chevron-btn:hover {
        background: color-mix(in oklch, var(--color-base-content) 10%, transparent);
        color: var(--color-base-content);
    }

    .folder-name {
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        color: color-mix(in oklch, var(--color-base-content) 55%, transparent);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        min-width: 0;
        flex: 1;
    }

.folder-badge {
  font-size: 10.5px;
        font-weight: 600;
        color: color-mix(in oklch, var(--color-accent) 80%, transparent);
        background: color-mix(in oklch, var(--color-accent) 10%, transparent);
        padding: 1px 7px;
        border-radius: 20px;
        line-height: 1.7;
        flex-shrink: 0;
    }

    /* ── Feed List ───────────────────────────────────────────── */
    .feed-list {
        list-style: none;
        margin: 0;
        padding: 0;
    }

    .feed-row {
        display: flex;
        align-items: center;
        gap: 8px;
  padding: 9px 2px 9px 0;
  cursor: pointer;
  transition: background 150ms ease;
  user-select: none;
  border-bottom: 1px solid color-mix(in oklch, var(--color-base-300) 35%, transparent);
    }

    .feed-row:last-child {
        border-bottom: none;
    }

    .feed-row:hover {
        background: color-mix(in oklch, var(--color-base-content) 4%, transparent);
    }

    .feed-row:hover .more-btn {
        opacity: 1;
    }

    .drag-handle {
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        color: color-mix(in oklch, var(--color-base-content) 28%, transparent);
        cursor: grab;
        transition: opacity 120ms ease, color 120ms ease;
        line-height: 1;
        padding: 2px 0;
        border-radius: 3px;
    }

    .drag-handle:active {
        cursor: grabbing;
    }

    .feed-row:hover .drag-handle {
        color: color-mix(in oklch, var(--color-base-content) 50%, transparent);
    }

    .feed-favicon {
        width: 16px;
        height: 16px;
        border-radius: 3px;
        object-fit: cover;
        flex-shrink: 0;
    }

    .feed-favicon-fallback {
        width: 16px;
        height: 16px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: var(--color-accent);
        opacity: 0.35;
        flex-shrink: 0;
    }

    .feed-label {
        flex: 1;
        font-size: 13px;
        font-weight: 500;
        color: var(--color-base-content);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        line-height: 1.35;
    }

    .more-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 24px;
        height: 24px;
        border-radius: 6px;
        border: none;
        background: transparent;
        color: color-mix(in oklch, var(--color-base-content) 55%, transparent);
        cursor: pointer;
        opacity: 0;
        flex-shrink: 0;
        transition: opacity 120ms ease, background 120ms ease;
    }

    .more-btn:hover {
        background: color-mix(in oklch, var(--color-base-content) 10%, transparent);
        opacity: 1 !important;
    }

    /* ── Context Menu / Move Picker ──────────────────────────── */
    .ctx-menu,
    .move-picker {
        position: fixed;
        z-index: 200;
        background: var(--color-base-100);
        border: 1px solid var(--color-base-200);
        border-radius: 12px;
        box-shadow:
            0 4px 6px color-mix(in oklch, black 8%, transparent),
            0 10px 30px color-mix(in oklch, black 14%, transparent);
        padding: 4px;
        min-width: 180px;
        animation: ctx-pop 140ms cubic-bezier(0.22, 1, 0.36, 1) both;
    }

    @keyframes ctx-pop {
        from { opacity: 0; transform: scale(0.92) translateY(-4px); }
        to   { opacity: 1; transform: scale(1)    translateY(0); }
    }

    .ctx-item-label {
        padding: 6px 10px 4px;
        font-size: 11px;
        font-weight: 600;
        color: color-mix(in oklch, var(--color-base-content) 40%, transparent);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 200px;
    }

    .ctx-divider {
        border: none;
        border-top: 1px solid var(--color-base-200);
        margin: 3px 0;
    }

    .ctx-item {
        display: flex;
        align-items: center;
        gap: 9px;
        width: 100%;
        padding: 8px 10px;
        border: none;
        background: transparent;
        cursor: pointer;
        font-size: 13px;
        font-weight: 500;
        color: var(--color-base-content);
        border-radius: 8px;
        transition: background 110ms ease;
        text-align: left;
    }

    .ctx-item:hover {
        background: color-mix(in oklch, var(--color-base-content) 7%, transparent);
    }

    .ctx-item--danger {
        color: var(--color-error, #e74c3c);
    }

    .ctx-item--danger:hover {
        background: color-mix(in oklch, var(--color-error, #e74c3c) 10%, transparent);
    }

    .ctx-item--active {
        background: color-mix(in oklch, var(--color-accent) 12%, transparent);
    }

    /* ── Dialogs ─────────────────────────────────────────────── */
    .dialog-backdrop {
        position: fixed;
        inset: 0;
        background: color-mix(in oklch, black 30%, transparent);
        z-index: 100;
        animation: fade-in 160ms ease both;
    }

    @keyframes fade-in {
        from { opacity: 0; }
        to   { opacity: 1; }
    }

    .dialog {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        z-index: 110;
        background: var(--color-base-100);
        border: 1px solid var(--color-base-200);
        border-radius: 16px;
        padding: 20px 20px 16px;
        width: min(380px, 92vw);
        box-shadow: 0 20px 60px color-mix(in oklch, black 24%, transparent);
        animation: dialog-in 200ms cubic-bezier(0.22, 1, 0.36, 1) both;
    }

    @keyframes dialog-in {
        from { opacity: 0; transform: translate(-50%, -48%) scale(0.95); }
        to   { opacity: 1; transform: translate(-50%, -50%) scale(1); }
    }

    .dialog-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 6px;
    }

.dialog-title {
font-family: var(--font-page-title);
        font-size: 1.15rem;
        font-weight: 400;
        letter-spacing: -0.01em;
        color: var(--color-base-content);
        margin: 0;
    }

    .dialog-close {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 30px;
        height: 30px;
        border-radius: 8px;
        border: none;
        background: transparent;
        color: color-mix(in oklch, var(--color-base-content) 55%, transparent);
        cursor: pointer;
        transition: background 130ms ease, color 130ms ease;
    }

    .dialog-close:hover {
        background: color-mix(in oklch, var(--color-base-content) 10%, transparent);
        color: var(--color-base-content);
    }

    .dialog-sub {
        font-size: 12.5px;
        color: color-mix(in oklch, var(--color-base-content) 50%, transparent);
        margin: 0 0 14px;
    }

    .dialog-input-row {
        position: relative;
        display: flex;
        align-items: center;
        margin-bottom: 16px;
    }

    :global(.dialog-input-icon) {
        position: absolute;
        left: 12px;
        color: color-mix(in oklch, var(--color-base-content) 40%, transparent);
        pointer-events: none;
        flex-shrink: 0;
    }

    .dialog-input {
        width: 100%;
        padding: 10px 12px 10px 36px;
        font-size: 13.5px;
        background: color-mix(in oklch, var(--color-base-200) 50%, transparent);
        border: 1px solid var(--color-base-300);
        border-radius: 10px;
        color: var(--color-base-content);
        outline: none;
        box-sizing: border-box;
        transition: border-color 140ms ease, background 140ms ease, box-shadow 140ms ease;
    }

    .dialog-input:focus {
        border-color: var(--color-accent);
        background: var(--color-base-100);
        box-shadow: 0 0 0 3px color-mix(in oklch, var(--color-accent) 15%, transparent);
    }

    .dialog-actions {
        display: flex;
        justify-content: flex-end;
        gap: 8px;
    }

    .dialog-btn {
        padding: 8px 18px;
        border-radius: 10px;
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
        border: none;
        transition: background 120ms ease, opacity 120ms ease;
    }

    .dialog-btn:disabled {
        opacity: 0.45;
        cursor: not-allowed;
    }

    .dialog-btn--ghost {
        background: transparent;
        color: color-mix(in oklch, var(--color-base-content) 60%, transparent);
    }

    .dialog-btn--ghost:hover {
        background: color-mix(in oklch, var(--color-base-content) 8%, transparent);
    }

    .dialog-btn--primary {
        background: var(--color-accent);
        color: var(--color-base-100);
    }

    .dialog-btn--primary:not(:disabled):hover {
        opacity: 0.88;
    }
</style>