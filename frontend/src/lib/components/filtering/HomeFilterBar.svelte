<script lang="ts">
	import { goto } from '$app/navigation';
	import Portal from '$lib/components/Portal.svelte';
	import {
		Rss, FolderOpen, ChevronDown, Check, Tag, X,
	} from '@lucide/svelte';
	import { t } from 'svelte-i18n';
	import {
		homeFilters, homeSubs, homeTags,
		setHomeMode, selectHomeFolder, selectHomeFeed, selectHomeTag,
	} from '$lib/stores/homeFilters';
	import { activeTabId, type TabId } from '$lib/config/tabs';
	import { stackedScreenOpen } from '$lib/stores/swipe';
	import { getDropdownStyle, containPickerScroll } from '$lib/utils/pickerUtils';

	interface Props {
		/** 'page' = in-tab (HomeTab) rendering, 'bar' = inside the top bar
		    (transparent background, no vertical padding — the bar provides both). */
		variant?: 'page' | 'bar';
	}

	let { variant = 'page' }: Props = $props();

	// Filter-bar horizontal-scroll touch tracking
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

	// Derived lists
	let folders = $derived.by(() => {
		const seen   = new Set<number>();
		const result: Array<{ id: number; name: string }> = [];
		for (const f of $homeSubs) {
			if (f.folder?.id && !seen.has(f.folder.id)) {
				seen.add(f.folder.id);
				result.push({ id: f.folder.id, name: f.folder.name });
			}
		}
		return result.sort((a, b) => a.name.localeCompare(b.name));
	});

	let feedsList = $derived.by(() =>
		$homeSubs
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

	// The top-bar host outlives the home tab: close any open picker when the
	// user leaves home or a stacked screen covers the tab layer.
	$effect(() => {
		const active: TabId = $activeTabId;
		const stacked = $stackedScreenOpen;
		if (active === 'home' && !stacked) return;
		showFolderPicker = false;
		showFeedPicker = false;
		showTagPicker = false;
	});

	function closePickers() {
		showFolderPicker = false;
		showFeedPicker = false;
		showTagPicker = false;
	}

	function toggleFolderPicker() {
		showFolderPicker = !showFolderPicker;
		showFeedPicker = false;
		showTagPicker = false;
		if (showFolderPicker && folderBtnEl) folderDropStyle = getDropdownStyle(folderBtnEl);
	}

	function toggleFeedPicker() {
		showFeedPicker = !showFeedPicker;
		showFolderPicker = false;
		showTagPicker = false;
		if (showFeedPicker && feedBtnEl) feedDropStyle = getDropdownStyle(feedBtnEl, true);
	}

	function toggleTagPicker() {
		showTagPicker = !showTagPicker;
		showFolderPicker = false;
		showFeedPicker = false;
		if (showTagPicker && tagBtnEl) tagDropStyle = getDropdownStyle(tagBtnEl);
	}
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	class="filter-bar"
	class:in-bar={variant === 'bar'}
	ontouchstart={(e) => { filterBarAxis = null; filterBarStartX = e.touches[0].clientX; filterBarStartY = e.touches[0].clientY; }}
	ontouchmove={(e) => {
		if (filterBarAxis === 'v') return;
		const el = e.currentTarget as HTMLElement;
		const dx = e.touches[0].clientX - filterBarStartX;
		const dy = e.touches[0].clientY - filterBarStartY;
		if (!filterBarAxis) {
			if (Math.abs(dx) < 6 && Math.abs(dy) < 6) return;
			filterBarAxis = Math.abs(dx) > Math.abs(dy) * 1.2 ? 'h' : 'v';
			if (filterBarAxis === 'v') return;
		}
		const canScrollLeft = el.scrollLeft > 0;
		const canScrollRight = el.scrollLeft + el.clientWidth < el.scrollWidth - 1;
		const swipingRight = dx > 0;
		const swipingLeft = dx < 0;
		if ((swipingRight && canScrollLeft) || (swipingLeft && canScrollRight)) {
			e.stopPropagation();
		}
	}}
	ontouchend={() => { filterBarAxis = null; }}
>
	<div class="mode-pill" role="group" aria-label="{$t('hometab.filterMode')}">
		<button
			class="mode-btn"
			class:active={$homeFilters.mode === 'recommendations'}
			onclick={() => setHomeMode('recommendations')}
			aria-pressed={$homeFilters.mode === 'recommendations'}
		>
			<span>{$t('hometab.forYou')}</span>
		</button>
		<button
			class="mode-btn"
			class:active={$homeFilters.mode === 'recents'}
			onclick={() => setHomeMode('recents')}
			aria-pressed={$homeFilters.mode === 'recents'}
		>
			<span>{$t('hometab.recent')}</span>
		</button>
		<button
			class="mode-btn"
			class:active={$homeFilters.mode === 'saved'}
			onclick={() => setHomeMode('saved')}
			aria-pressed={$homeFilters.mode === 'saved'}
		>
			<span>{$t('hometab.saved')}</span>
		</button>
	</div>

	<div class="picker-wrap">
		<button
			bind:this={folderBtnEl}
			class="filter-chip"
			class:chip-active={!!$homeFilters.selectedFolderId}
			onclick={toggleFolderPicker}
			aria-expanded={showFolderPicker}
			aria-haspopup="listbox"
		>
			<FolderOpen size={13} strokeWidth={2} />
			<span class="chip-label">{$homeFilters.selectedFolderName ?? $t('hometab.folder')}</span>
			{#if $homeFilters.selectedFolderId}
				<span
					class="chip-clear"
					role="button"
					tabindex="0"
					aria-label="{$t('hometab.clearFolderFilter')}"
					onclick={(e) => { e.stopPropagation(); selectHomeFolder(null, null); }}
					onkeydown={(e) => { if (e.key === 'Enter') selectHomeFolder(null, null); }}
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
			class:chip-active={!!$homeFilters.selectedFeedSha}
			onclick={toggleFeedPicker}
			aria-expanded={showFeedPicker}
			aria-haspopup="listbox"
		>
			<Rss size={13} strokeWidth={2} />
			<span class="chip-label">{$homeFilters.selectedFeedName ?? $t('hometab.feed')}</span>
			{#if $homeFilters.selectedFeedSha}
				<span
					class="chip-clear"
					role="button"
					tabindex="0"
					aria-label="{$t('hometab.clearFeedFilter')}"
					onclick={(e) => { e.stopPropagation(); selectHomeFeed(null, null); }}
					onkeydown={(e) => { if (e.key === 'Enter') selectHomeFeed(null, null); }}
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
			class:chip-active={!!$homeFilters.selectedTagId}
			onclick={toggleTagPicker}
			aria-expanded={showTagPicker}
			aria-haspopup="listbox"
		>
			<Tag size={13} strokeWidth={2} />
			<span class="chip-label">{$homeFilters.selectedTagName ?? $t('hometab.tag')}</span>
			{#if $homeFilters.selectedTagId}
				<span
					class="chip-clear"
					role="button"
					tabindex="0"
					aria-label="{$t('hometab.clearTagFilter')}"
					onclick={(e) => { e.stopPropagation(); selectHomeTag(null, null); }}
					onkeydown={(e) => { if (e.key === 'Enter') selectHomeTag(null, null); }}
				><X size={10} /></span>
			{:else}
				<span class="chevron-wrap" class:rotated={showTagPicker}><ChevronDown size={11} /></span>
			{/if}
		</button>
	</div>
</div>

<!-- Dropdowns e Backdrops (portaled to body to escape overflow:clip) -->
{#if showFolderPicker || showFeedPicker || showTagPicker}
	<Portal>
		<div
			class="picker-backdrop"
			use:containPickerScroll
			onclick={() => closePickers()}
			aria-hidden="true"
		></div>

		{#if showFolderPicker}
			<div
				class="picker-dropdown picker-portal"
				style={folderDropStyle}
				use:containPickerScroll
				role="listbox"
				aria-label="{$t('hometab.folder')}"
			>
				{#if folders.length === 0}
					<p class="picker-empty">{$t('hometab.noFoldersYet')}</p>
				{:else}
					{#each folders as folder (folder.id)}
						<button
							class="picker-item"
							class:picker-selected={$homeFilters.selectedFolderId === String(folder.id)}
							role="option"
							aria-selected={$homeFilters.selectedFolderId === String(folder.id)}
							onclick={() => selectHomeFolder(String(folder.id), folder.name)}
						>
							<FolderOpen size={13} strokeWidth={2} />
							<span class="picker-item-text">{folder.name}</span>
							{#if $homeFilters.selectedFolderId === String(folder.id)}<Check size={12} class="picker-check" />{/if}
						</button>
					{/each}
				{/if}
			</div>
		{/if}

		{#if showFeedPicker}
			<div
				class="picker-dropdown picker-dropdown--tall picker-portal"
				style={feedDropStyle}
				use:containPickerScroll
				role="listbox"
				aria-label="{$t('hometab.feed')}"
			>
				{#if feedsList.length === 0}
					<p class="picker-empty">{$t('hometab.noFeedsYet')}</p>
				{:else}
					{#each feedsList as f (f.sha)}
						<button
							class="picker-item"
							class:picker-selected={$homeFilters.selectedFeedSha === f.sha}
							role="option"
							aria-selected={$homeFilters.selectedFeedSha === f.sha}
							onclick={() => selectHomeFeed(f.sha, f.title)}
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
							{#if $homeFilters.selectedFeedSha === f.sha}<Check size={12} class="picker-check" />{/if}
						</button>
					{/each}
				{/if}
			</div>
		{/if}

		{#if showTagPicker}
			<div
				class="picker-dropdown picker-portal"
				style={tagDropStyle}
				use:containPickerScroll
				role="listbox"
				aria-label="{$t('hometab.tag')}"
			>
				{#if $homeTags.length === 0}
					<p class="picker-empty">{$t('hometab.noTagsYet')}</p>
					<button class="picker-item picker-item--create" onclick={() => { closePickers(); goto('/settings/intelligence/tags'); }}>
						<Tag size={13} strokeWidth={2} />
						<span class="picker-item-text">{$t('hometab.createTag')}</span>
					</button>
				{:else}
					{#each $homeTags as tg (tg.id)}
						<button
							class="picker-item"
							class:picker-selected={$homeFilters.selectedTagId === tg.id}
							role="option"
							aria-selected={$homeFilters.selectedTagId === tg.id}
							onclick={() => selectHomeTag(tg.id, tg.name)}
						>
							<span class="picker-tag-dot" style="background: {tg.color || '#3b82f6'}"></span>
							<span class="picker-item-text">{tg.name}</span>
							{#if $homeFilters.selectedTagId === tg.id}<Check size={12} class="picker-check" />{/if}
						</button>
					{/each}
					<button class="picker-item picker-item--create" onclick={() => { closePickers(); goto('/settings/intelligence/tags'); }}>
						<Tag size={13} strokeWidth={2} />
						<span class="picker-item-text">{$t('hometab.createTag')}</span>
					</button>
				{/if}
			</div>
		{/if}
	</Portal>
{/if}

<style>
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

	/* Top-bar host: the bar itself owns background + vertical rhythm */
	.filter-bar.in-bar {
		background: transparent;
		padding-top: 0;
		padding-bottom: 0;
	}

	.mode-pill {
		display: flex;
		border: var(--ui-border-width, 1px) solid var(--btn-border-color, var(--ui-border-color));
		border-radius: var(--ui-radius-chip, var(--ui-radius-sm));
		padding: 0;
		gap: 0;
		flex-shrink: 0;
		background: var(--btn-fill, transparent);
		overflow: hidden; /* clips hover/active fill to the pill's own curve */
	}
	.mode-btn {
		display: flex;
		align-items: center;
		gap: 5px;
		padding: 7px 14px;
		border-radius: 0;
		border: none;
		background: transparent;
		font-size: 13px;
		font-weight: 500;
		color: var(--ui-text-muted, color-mix(in oklch, var(--color-base-content) 74%, transparent));
		cursor: pointer;
		transition: background 150ms ease, color 150ms ease, box-shadow 150ms ease;
		white-space: nowrap;
	}
	.mode-btn:hover {
		color: var(--color-base-content);
	}
	.mode-btn.active {
		/* Fills its parcel of the big pill edge-to-edge: no gap ring */
		background: color-mix(in oklch, var(--color-accent) 16%, transparent);
		color: var(--color-accent);
		font-weight: 700;
		/* Relief stays inside, since the outer shadow would be clipped */
		box-shadow: inset 0 1px 0 color-mix(in oklch, white 22%, transparent);
	}

	.picker-wrap { position: relative; flex-shrink: 0; }
	.filter-chip {
		display: flex;
		align-items: center;
		gap: 5px;
		padding: 6px 12px;
		border-radius: var(--ui-radius-chip, var(--ui-radius-sm));
		border: var(--ui-border-width, 1px) solid var(--btn-border-color, var(--ui-border-color));
		background: var(--btn-fill, transparent);
		font-size: 13px;
		font-weight: 500;
		color: var(--ui-text-muted, color-mix(in oklch, var(--color-base-content) 74%, transparent));
		cursor: pointer;
		transition: background 130ms, color 130ms, border-color 130ms;
		white-space: nowrap;
		max-width: 140px;
	}
	.filter-chip:hover {
		background: var(--color-base-200);
		color: var(--color-base-content);
		border-color: var(--btn-border-strong, var(--ui-border-strong));
	}
	.filter-chip.chip-active {
		background: transparent;
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
	/* Height is clamped inline by getDropdownStyle()/getDropdownStyleUp()
	   (viewport-aware). CSS only keeps the guard + width. */
	.picker-dropdown {
		z-index: 9999;
		background: var(--color-base-100);
		border: 1px solid var(--color-base-300);
		border-radius: var(--ui-radius-sm);
		box-shadow: 0 8px 24px color-mix(in oklch, black 20%, transparent);
		padding: 4px;
		min-width: 190px;
		max-width: 260px;
		max-height: 280px;
		overflow-x: hidden;
		overflow-y: auto;
		overscroll-behavior: contain;
		scrollbar-width: thin;
		animation: picker-pop 150ms cubic-bezier(0.22, 1, 0.36, 1) both;
	}
	@media (min-width: 768px) {
		.picker-dropdown { min-width: 220px; max-width: 300px; }
	}
	.picker-portal { position: fixed; z-index: 9999; pointer-events: auto; }

	@keyframes picker-pop {
		from { opacity: 0; transform: translateY(-6px) scale(0.97); }
		to   { opacity: 1; transform: translateY(0)    scale(1); }
	}

	.picker-empty {
		padding: 12px;
		font-size: 12px;
		color: var(--ui-text-subtle, color-mix(in oklch, var(--color-base-content) 62%, transparent));
		text-align: center;
	}
	.picker-item {
		display: flex; align-items: center; gap: 8px;
		width: 100%; padding: 8px 10px;
		border: none; background: transparent;
		cursor: pointer; font-size: 13px; font-weight: 500;
		color: var(--color-base-content); border-radius: var(--ui-radius-xs);
		transition: background 110ms; text-align: left;
	}
	.picker-item:hover { background: var(--color-base-200); }
	.picker-item.picker-selected {
		background: color-mix(in oklch, var(--color-accent) 10%, transparent);
		color: var(--color-accent);
	}
	.picker-item-text { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.picker-favicon { width: 14px; height: 14px; border-radius: var(--ui-radius-xs); object-fit: contain; flex-shrink: 0; }
	.picker-tag-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
	.picker-item--create { color: var(--color-accent); font-weight: 600; border-top: 1px solid var(--color-base-300); margin-top: 4px; border-radius: 0 0 var(--ui-radius-xs) var(--ui-radius-xs); }
	.picker-item--create:hover { background: color-mix(in oklch, var(--color-accent) 10%, transparent); }
	:global(.picker-check) { flex-shrink: 0; color: var(--color-accent); }
	:global(.picker-icon-fallback) { color: var(--color-accent); opacity: 0.6; }
	.picker-backdrop { position: fixed; inset: 0; z-index: 9998; pointer-events: auto; }
</style>
