<script lang="ts">
    import { Rss, ChevronRight, ChevronDown, X, MoreHorizontal, FolderPlus, Trash2, Share2, FolderOpen, Folder } from '@lucide/svelte';
    import { t } from 'svelte-i18n';
    import { get } from 'svelte/store';
import { notifySubscriptionChanged } from '$lib/stores/subscription';

    // ── Props ────────────────────────────────────────────
    let { open = $bindable(false) } = $props();

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
    let subsLoading     = $state(false);
    let subsError       = $state('');
    let expandedFolders = $state<Record<string, boolean>>({});

    let contextMenu = $state<{
        type: 'feed' | 'folder';
        id: string;
        name: string;
        x: number;
        y: number;
        url?: string;
        folderId?: number | null;
    } | null>(null);

    let dragItem = $state<{
        type: 'feed' | 'folder';
        id: string;
        fromKey: number | string;
    } | null>(null);
    let dragOverKey = $state<number | string | null>(null);

    let newFolderDialog = $state<{ parentFolderKey: number | null; parentFolderName: string | null; name: string } | null>(null);

    // ── Load ─────────────────────────────────────────────
    $effect(() => {
        if (open && subsData.length === 0 && !subsLoading) loadSubscriptions();
    });

    $effect(() => {
        if (contextMenu) {
            const handler = (e: MouseEvent) => {
                if (!(e.target as HTMLElement).closest('.ctx-menu')) contextMenu = null;
            };
            document.addEventListener('mousedown', handler);
            return () => document.removeEventListener('mousedown', handler);
        }
    });

    async function loadSubscriptions() {
        subsLoading = true;
        subsError = '';
        try {
            const res = await fetch('/api/list-subscriptions', { credentials: 'include' });
            if (!res.ok) throw new Error(`${get(t)('leftpanel.loadError')} (${res.status})`);
            const raw = await res.json();
            const feeds: Feed[] = Array.isArray(raw) ? raw : (raw.feeds ?? []);
            subsData = feeds;
            const init: Record<string, boolean> = {};
            for (const f of feeds) init[String(f.folder?.id ?? '__root__')] = true;
            expandedFolders = init;
        } catch (err: any) {
            subsError = err.message || get(t)('leftpanel.loadError');
        }
        subsLoading = false;
    }

    function closePanel() { open = false; }

    function toggleFolder(key: number | string) {
        const k = String(key);
        expandedFolders = { ...expandedFolders, [k]: !(expandedFolders[k] !== false) };
    }

    function isExpanded(key: number | string): boolean {
        return expandedFolders[String(key)] !== false;
    }

    // ── Grouped folders (keyed by folder ID, supports nesting) ───────────
    let groupedFolders = $derived.by((): FolderGroup[] => {
        const map = new Map<number | string, FolderGroup>();

        for (const feed of subsData) {
            const key: number | string = feed.folder?.id ?? '__root__';
            if (!map.has(key)) {
                map.set(key, { folder: feed.folder ?? null, feeds: [], depth: 0 });
            }
            if (!feed._empty_folder) {
                map.get(key)!.feeds.push(feed);
            }
        }

        const byId = new Map<number, { name: string; parent_id: number | null }>();
        for (const group of map.values()) {
            if (group.folder?.id != null) {
                byId.set(group.folder.id, {
                    name:      group.folder.name,
                    parent_id: group.folder.parent_id ?? null,
                });
            }
        }

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

        return withPath
            .sort((a, b) => a.sortKey.localeCompare(b.sortKey))
            .map(({ group }) => group);
    });

    let visibleGroups = $derived.by(() => {
        const parentOf = new Map<number, number | null>();
        for (const g of groupedFolders) {
            if (g.folder?.id != null)
                parentOf.set(g.folder.id, g.folder.parent_id ?? null);
        }
        return groupedFolders.filter(group => {
            let pid: number | null = group.folder?.parent_id ?? null;
            while (pid !== null) {
                if (expandedFolders[String(pid)] === false) return false;
                pid = parentOf.get(pid) ?? null;
            }
            return true;
        });
    });

    function feedDisplayTitle(feed: Feed): string {
        if (feed.title && feed.title !== 'No title') return feed.title;
        try { return new URL(feed.url!).hostname; } catch { return feed.url ?? ''; }
    }

    // ── Navigation ────────────────────────────────────────
    function navigateToFeed(sha: string) {
        window.location.href = `/f/${sha}`;
    }
    function navigateToFolder(folderId: number) {
        window.location.href = `/c/${folderId}`;
    }

    // ── API helpers ───────────────────────────────────────
    async function callStructureApi(task: string, payload: Record<string, any>) {
        const res = await fetch('/api/following_structure/', {
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
                await callStructureApi('move_feed', {
                    feed:   dragItem.id,
                    folder: targetFolderId,
                });
                subsData = subsData.map(f =>
                    f.feed_sha256 === dragItem!.id
                        ? { ...f, folder: targetGroup.folder ?? null }
                        : f
                );
            } else {
                await callStructureApi('move_folder', {
                    folder:        Number(dragItem.id),
                    parent_folder: targetFolderId,
                });
                await loadSubscriptions();
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
        contextMenu = { type, id, name, x: e.clientX, y: e.clientY, url, folderId };
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
      await fetch('/api/feed-remove', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: snap.url }),
      });
      await callStructureApi('delete_feed', { feed: snap.id });
      subsData = subsData.filter(f => f.feed_sha256 !== snap.id);
      notifySubscriptionChanged();
            } catch (err) {
                console.error('Delete feed failed:', err);
            }
        } else {
            try {
                await callStructureApi('delete_folder', { folder: Number(snap.id) });
                await loadSubscriptions();
            } catch (err) {
                console.error('Delete folder failed:', err);
            }
        }
    }

    // ── Create Folder ─────────────────────────────────────
    function openNewFolderDialog(parentFolderId: number | null = null, parentFolderName: string | null = null) {
        newFolderDialog = { parentFolderKey: parentFolderId, parentFolderName, name: '' };
        contextMenu = null;
    }

    async function confirmCreateFolder() {
        if (!newFolderDialog?.name.trim()) return;
        const name = newFolderDialog.name.trim();
        const parentId = newFolderDialog.parentFolderKey;
        try {
            await callStructureApi('create_folder', { name, parent_folder: parentId });
            await loadSubscriptions();
        } catch (err) {
            console.error('Create folder failed:', err);
        }
        newFolderDialog = null;
    }
</script>

{#if open}
    <div class="drawer-backdrop" onclick={closePanel} aria-hidden="true"></div>

    <aside class="drawer-panel" aria-label="{$t('leftpanel.title')}">
        <!-- Header -->
        <div class="drawer-header">
            <div class="drawer-title-row">
                <Rss size={15} strokeWidth={2.5} />
                <span class="drawer-title">{$t('leftpanel.title')}</span>
            </div>
            <div class="header-actions">
                <button class="icon-btn" title="{$t('leftpanel.newFolder')}" onclick={() => openNewFolderDialog(null, null)} aria-label="{$t('leftpanel.newFolder')}">
                    <FolderPlus size={16} strokeWidth={2} />
                </button>
                <button class="icon-btn" onclick={closePanel} aria-label="{$t('leftpanel.closeDrawer')}">
                    <X size={18} strokeWidth={2} />
                </button>
            </div>
        </div>

        <!-- Body -->
        <div class="drawer-body">
            {#if subsLoading}
                <div class="subs-state">
                    <span class="loading loading-spinner loading-md"></span>
                </div>
            {:else if subsError}
                <p class="subs-error">{subsError}</p>
            {:else if groupedFolders.length === 0}
                <p class="subs-empty">{$t('leftpanel.noSubscriptions')}</p>
            {:else}
                {#each visibleGroups as group (group.folder?.id ?? '__root__')}
                    {@const groupKey = group.folder?.id ?? '__root__'}
                    {@const folderExpanded = isExpanded(groupKey)}
                    {@const isOver = dragOverKey === groupKey}
                    {@const indent = group.depth * 14}

                    <div
                        class="folder-block"
                        class:drag-over={isOver}
                        ondragover={(e) => onDragOver(e, groupKey)}
                        ondragleave={onDragLeave}
                        ondrop={(e) => onDrop(e, group)}
                    >
                        <!-- Folder row -->
                        <div
                            class="folder-row"
                            style="padding-left: {10 + indent}px; --indent: {indent}px;"
                            draggable={!!group.folder}
                            ondragstart={(e) => group.folder && onDragStart(e, 'folder', String(group.folder.id), groupKey)}
                            role="button"
                            tabindex="0"
                            aria-expanded={folderExpanded}
                            onclick={() => {
                                if (group.folder?.id) navigateToFolder(group.folder.id);
                                toggleFolder(groupKey);
                            }}
                            onkeydown={(e) => e.key === 'Enter' && toggleFolder(groupKey)}
                        >
                            <span class="folder-chevron" onclick={(e) => { e.stopPropagation(); toggleFolder(groupKey); }}>
                                {#if folderExpanded}
                                    <ChevronDown size={14} strokeWidth={2.5} />
                                {:else}
                                    <ChevronRight size={14} strokeWidth={2.5} />
                                {/if}
                            </span>
                            <span class="folder-icon">
                                {#if folderExpanded}
                                    <FolderOpen size={13} strokeWidth={2} />
                                {:else}
                                    <Folder size={13} strokeWidth={2} />
                                {/if}
                            </span>
                            <span class="folder-name">{group.folder?.name ?? $t('leftpanel.defaultFolder')}</span>
                            <span class="folder-badge">{group.feeds.length}</span>
                            <button
                                class="more-btn"
                                title="{$t('leftpanel.options')}"
                                onclick={(e) => openContextMenu(
                                    e,
                                    'folder',
                                    String(group.folder?.id ?? '__root__'),
                                    group.folder?.name ?? $t('leftpanel.defaultFolder'),
                                    undefined,
                                    group.folder?.id ?? null,
                                )}
                                aria-label="{$t('leftpanel.folderOptions')}"
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
                                        style="padding-left: {28 + indent}px;"
                                        draggable={true}
                                        ondragstart={(e) => onDragStart(e, 'feed', feed.feed_sha256!, groupKey)}
                                        onclick={() => navigateToFeed(feed.feed_sha256!)}
                                        role="button"
                                        tabindex="0"
                                        onkeydown={(e) => e.key === 'Enter' && navigateToFeed(feed.feed_sha256!)}
                                        title={feedDisplayTitle(feed)}
                                    >
                                        <span class="drag-handle" aria-hidden="true">⠿</span>
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
                                            title="{$t('leftpanel.options')}"
                                            onclick={(e) => openContextMenu(
                                                e,
                                                'feed',
                                                feed.feed_sha256!,
                                                feedDisplayTitle(feed),
                                                feed.url ?? undefined,
                                                feed.folder?.id ?? null,
                                            )}
                                            aria-label="{$t('leftpanel.feedOptions')}"
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
    </aside>

    <!-- Context Menu -->
    {#if contextMenu}
        <div
            class="ctx-menu"
            style="top:{contextMenu.y}px; left:{contextMenu.x}px"
            role="menu"
        >
            <div class="ctx-item-label">{contextMenu.name}</div>
            <hr class="ctx-divider" />
            {#if contextMenu.type === 'folder'}
                <button class="ctx-item" onclick={() => openNewFolderDialog(Number(contextMenu!.id), contextMenu!.name)}>
                    <FolderPlus size={14} strokeWidth={2} />
                    <span>{$t('leftpanel.newSubfolder')}</span>
                </button>
            {/if}
            <button class="ctx-item" onclick={shareItem}>
                <Share2 size={14} strokeWidth={2} />
                <span>{$t('leftpanel.copyLink')}</span>
            </button>
            <button class="ctx-item ctx-item--danger" onclick={deleteItem}>
                <Trash2 size={14} strokeWidth={2} />
                <span>{$t('leftpanel.delete')}</span>
            </button>
        </div>
    {/if}

    <!-- New Folder Dialog -->
    {#if newFolderDialog}
        <div class="dialog-backdrop" onclick={() => newFolderDialog = null} aria-hidden="true"></div>
        <div class="dialog" role="dialog" aria-modal="true" aria-label="{$t('leftpanel.dialogTitle')}">
            <p class="dialog-title">{$t('leftpanel.dialogTitle')}</p>
            {#if newFolderDialog.parentFolderName}
                <p class="dialog-sub">{$t('leftpanel.dialogSubInside')}{newFolderDialog.parentFolderName}"</p>
            {/if}
            <!-- svelte-ignore a11y_autofocus -->
            <input
                class="dialog-input"
                type="text"
                placeholder="{$t('leftpanel.folderNamePlaceholder')}"
                bind:value={newFolderDialog.name}
                autofocus
                onkeydown={(e) => {
                    if (e.key === 'Enter') confirmCreateFolder();
                    if (e.key === 'Escape') newFolderDialog = null;
                }}
            />
            <div class="dialog-actions">
                <button class="dialog-btn dialog-btn--ghost" onclick={() => newFolderDialog = null}>{$t('leftpanel.cancel')}</button>
                <button class="dialog-btn dialog-btn--primary" onclick={confirmCreateFolder}>{$t('leftpanel.create')}</button>
            </div>
        </div>
    {/if}
{/if}

<style>
    .drawer-backdrop {
        position: fixed;
        inset: 0;
        background: color-mix(in oklch, var(--color-base-300) 55%, transparent);
        backdrop-filter: blur(3px);
        -webkit-backdrop-filter: blur(3px);
        z-index: 60;
        animation: fade-in 220ms ease both;
    }

    .drawer-panel {
        position: fixed;
        top: 0; left: 0; bottom: 0;
        width: min(300px, 78vw);
        background: var(--color-base-100);
        z-index: 70;
        display: flex;
        flex-direction: column;
        border-right: 1px solid color-mix(in oklch, var(--color-base-300) 70%, transparent);
        box-shadow: 6px 0 36px color-mix(in oklch, black 16%, transparent);
        animation: slide-in 260ms cubic-bezier(0.22, 1, 0.36, 1) both;
    }

    @keyframes fade-in {
        from { opacity: 0 } to { opacity: 1 }
    }
    @keyframes slide-in {
        from { transform: translateX(-100%) } to { transform: translateX(0) }
    }

    .drawer-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 16px 12px 14px 16px;
        border-bottom: 1px solid var(--color-base-200);
        flex-shrink: 0;
    }

    .drawer-title-row {
        display: flex;
        align-items: center;
        gap: 8px;
        color: var(--color-primary);
    }

    .drawer-title {
        font-size: 15px;
        font-weight: 700;
        color: var(--color-base-content);
        letter-spacing: -0.01em;
    }

    .header-actions {
        display: flex;
        align-items: center;
        gap: 4px;
    }

    .icon-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 32px;
        height: 32px;
        border-radius: 8px;
        border: none;
        background: transparent;
        color: var(--color-base-content);
        cursor: pointer;
        transition: background 130ms ease;
    }
    .icon-btn:hover {
        background: color-mix(in oklch, var(--color-base-content) 10%, transparent);
    }

    .drawer-body {
        flex: 1;
        overflow-y: auto;
        padding: 6px 0 20px;
        scrollbar-width: thin;
        scrollbar-color: var(--color-base-300) transparent;
    }

    .subs-state {
        display: flex;
        justify-content: center;
        padding: 40px 16px;
    }

    .subs-error {
        padding: 16px 20px;
        font-size: 13px;
        color: var(--color-error, #e74c3c);
    }

    .subs-empty {
        padding: 16px 20px;
        font-size: 13px;
        color: color-mix(in oklch, var(--color-base-content) 45%, transparent);
    }

    /* ── Folder ── */
    .folder-block {
        margin-bottom: 1px;
        border-radius: 6px;
        transition: background 130ms ease, outline 130ms ease;
    }

    .folder-block.drag-over {
        background: color-mix(in oklch, var(--color-primary) 10%, transparent);
        outline: 2px dashed color-mix(in oklch, var(--color-primary) 50%, transparent);
        outline-offset: -2px;
    }

    .folder-row {
        position: relative;
        display: flex;
        align-items: center;
        gap: 5px;
        width: 100%;
        padding-top: 8px;
        padding-right: 10px;
        padding-bottom: 8px;
        border: none;
        background: transparent;
        cursor: pointer;
        text-align: left;
        transition: background 130ms ease;
        border-radius: 6px;
        user-select: none;
        box-sizing: border-box;
    }
    .folder-row:hover {
        background: color-mix(in oklch, var(--color-primary) 8%, transparent);
    }
    .folder-row:hover .more-btn { opacity: 1; }

    .folder-chevron {
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: calc(10px + var(--indent, 0px) + 21px);
        display: flex;
        align-items: center;
        justify-content: flex-end;
        padding-right: 5px;
        color: color-mix(in oklch, var(--color-base-content) 42%, transparent);
        cursor: pointer;
        z-index: 1;
    }

    .folder-icon {
        display: flex;
        align-items: center;
        color: var(--color-primary);
        opacity: 0.7;
        flex-shrink: 0;
    }

    .folder-name {
        flex: 1;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        color: color-mix(in oklch, var(--color-base-content) 65%, transparent);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .folder-badge {
        font-size: 10.5px;
        font-weight: 600;
        color: var(--color-primary);
        background: color-mix(in oklch, var(--color-primary) 13%, transparent);
        padding: 1px 7px;
        border-radius: 20px;
        line-height: 1.7;
        flex-shrink: 0;
    }

    /* ── Feed list ── */
    .feed-list {
        list-style: none;
        margin: 0;
        padding: 1px 0 4px;
    }

    .feed-row {
        display: flex;
        align-items: center;
        gap: 8px;
        padding-top: 7px;
        padding-right: 10px;
        padding-bottom: 7px;
        cursor: pointer;
        transition: background 120ms ease;
        border-radius: 6px;
        user-select: none;
        position: relative;
        box-sizing: border-box;
    }
    .feed-row:hover {
        background: color-mix(in oklch, var(--color-primary) 6%, transparent);
    }
    .feed-row:hover .drag-handle { opacity: 0.5; }
    .feed-row:hover .more-btn { opacity: 1; }

    .drag-handle {
        font-size: 13px;
        color: var(--color-base-content);
        opacity: 0;
        cursor: grab;
        flex-shrink: 0;
        transition: opacity 120ms ease;
        line-height: 1;
    }
    .drag-handle:active { cursor: grabbing; }

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
        color: var(--color-primary);
        opacity: 0.4;
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
        color: var(--color-base-content);
        cursor: pointer;
        opacity: 0;
        flex-shrink: 0;
        transition: opacity 120ms ease, background 120ms ease;
    }
    .more-btn:hover {
        background: color-mix(in oklch, var(--color-base-content) 12%, transparent);
        opacity: 1 !important;
    }

    /* ── Context menu ── */
    .ctx-menu {
        position: fixed;
        z-index: 200;
        background: var(--color-base-100);
        border: 1px solid var(--color-base-200);
        border-radius: 10px;
        box-shadow:
            0 4px 6px color-mix(in oklch, black 8%, transparent),
            0 10px 30px color-mix(in oklch, black 14%, transparent);
        padding: 4px;
        min-width: 168px;
        animation: ctx-pop 140ms cubic-bezier(0.22, 1, 0.36, 1) both;
    }

    @keyframes ctx-pop {
        from { opacity: 0; transform: scale(0.92) translateY(-4px); }
        to   { opacity: 1; transform: scale(1)    translateY(0);    }
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
        border-radius: 7px;
        transition: background 110ms ease;
        text-align: left;
    }
    .ctx-item:hover {
        background: color-mix(in oklch, var(--color-base-content) 8%, transparent);
    }
    .ctx-item--danger { color: var(--color-error, #e74c3c); }
    .ctx-item--danger:hover {
        background: color-mix(in oklch, var(--color-error, #e74c3c) 10%, transparent);
    }

    /* ── Dialog ── */
    .dialog-backdrop {
        position: fixed;
        inset: 0;
        background: color-mix(in oklch, black 30%, transparent);
        z-index: 100;
        animation: fade-in 160ms ease both;
    }

    .dialog {
        position: fixed;
        top: 50%; left: 50%;
        transform: translate(-50%, -50%);
        z-index: 110;
        background: var(--color-base-100);
        border: 1px solid var(--color-base-200);
        border-radius: 14px;
        padding: 20px 20px 16px;
        min-width: 260px;
        max-width: 90vw;
        box-shadow: 0 20px 60px color-mix(in oklch, black 24%, transparent);
        animation: dialog-in 200ms cubic-bezier(0.22, 1, 0.36, 1) both;
    }

    @keyframes dialog-in {
        from { opacity: 0; transform: translate(-50%, -48%) scale(0.95); }
        to   { opacity: 1; transform: translate(-50%, -50%) scale(1);    }
    }

    .dialog-title {
        font-size: 15px;
        font-weight: 700;
        color: var(--color-base-content);
        margin: 0 0 4px;
    }

    .dialog-sub {
        font-size: 12px;
        color: color-mix(in oklch, var(--color-base-content) 50%, transparent);
        margin: 0 0 14px;
    }

    .dialog-input {
        width: 100%;
        padding: 9px 12px;
        font-size: 14px;
        background: var(--color-base-200);
        border: 1px solid transparent;
        border-radius: 8px;
        color: var(--color-base-content);
        outline: none;
        box-sizing: border-box;
        transition: border-color 140ms ease;
        margin-bottom: 14px;
    }
    .dialog-input:focus {
        border-color: var(--color-primary);
        background: var(--color-base-100);
    }

    .dialog-actions {
        display: flex;
        justify-content: flex-end;
        gap: 8px;
    }

    .dialog-btn {
        padding: 7px 16px;
        border-radius: 8px;
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
        border: none;
        transition: background 120ms ease, opacity 120ms ease;
    }
    .dialog-btn--ghost {
        background: transparent;
        color: color-mix(in oklch, var(--color-base-content) 60%, transparent);
    }
    .dialog-btn--ghost:hover {
        background: color-mix(in oklch, var(--color-base-content) 8%, transparent);
    }
    .dialog-btn--primary {
        background: var(--color-primary);
        color: var(--color-primary-content, #fff);
    }
    .dialog-btn--primary:hover { opacity: 0.88; }
</style>