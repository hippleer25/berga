<script lang="ts">
	import { t } from 'svelte-i18n';
	import { get } from 'svelte/store';
	import { X } from '@lucide/svelte';
	import { notifySubscriptionChanged } from '$lib/stores/subscription';
	import { apiFetch } from '$lib/api';

	type ModalStatus = 'loading' | 'search' | 'confirm' | 'error' | 'success';

	interface SearchResult {
		title: string;
		url: string;
		score: number;
	}

	interface Props {
		feed: { title: string; url: string };
		mode?: 'discover' | 'search';
		onclose: () => void;
	}

	const { feed, mode = 'discover', onclose }: Props = $props();

	let status = $state<ModalStatus>('loading');
	let syncing = $state(false);
	let feeds = $state<string[]>([]);
	let selectedUrl = $state('');
	let error = $state('');
	let expanded = $state(false);
	let searchResults = $state<SearchResult[]>([]);
	let lastSearchQuery = $state('');
	let cameFromSearch = $state(false);

	$effect(() => {
		if (mode === 'search') {
			lastSearchQuery = feed.title;
			searchFeeds(feed.title);
		} else {
			discoverFeeds(feed.url);
		}
	});

	async function discoverFeeds(url: string) {
		status = 'loading';
		error = '';
		feeds = [];
		expanded = false;
		try {
			const res = await apiFetch(
				`/api/discover?url=${encodeURIComponent(url)}`,
				{ credentials: 'include' }
			);
			if (!res.ok) throw new Error(`${get(t)('followfeedmodal.discoverFailed')} (${res.status})`);
			const data = await res.json();
			feeds = data.feeds ?? [];
			if (feeds.length === 0) throw new Error(get(t)('followfeedmodal.noFeedsFound'));
			selectedUrl = feeds[0];
			status = 'confirm';
		} catch (err: any) {
			error = err.message || get(t)('followfeedmodal.discoverFailed');
			if (cameFromSearch && searchResults.length > 0) {
				status = 'search';
			} else {
				status = 'error';
			}
		}
	}

	async function searchFeeds(query: string) {
		status = 'loading';
		error = '';
		searchResults = [];
		lastSearchQuery = query;
		try {
			const res = await apiFetch(
				`/api/online-discover?query=${encodeURIComponent(query)}`,
				{ credentials: 'include' }
			);
			if (!res.ok) throw new Error(`${get(t)('followfeedmodal.searchFailed')} (${res.status})`);
			const data = await res.json();
			searchResults = data.candidates ?? [];
			if (searchResults.length === 0) throw new Error(get(t)('followfeedmodal.noSearchResults'));
			status = 'search';
		} catch (err: any) {
			error = err.message || get(t)('followfeedmodal.searchFailed');
			status = 'error';
		}
	}

	function selectSearchResult(result: SearchResult) {
		cameFromSearch = true;
		discoverFeeds(result.url);
	}

	function fallbackToSearch() {
		let query = lastSearchQuery || feed.title;
		searchFeeds(query);
	}

	async function parseSelectedFeed() {
		// Non-fatal: the subscription already succeeded; content syncs on cron otherwise
		try {
			await apiFetch('/api/feed/parse-single', {
				method: 'POST',
				credentials: 'include',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ url: selectedUrl })
			});
		} catch { /* ignore */ }
	}

	async function followFeed() {
		status = 'loading';
		syncing = true;
		try {
			const res = await apiFetch('/api/feed-add', {
				method: 'POST',
				credentials: 'include',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ url: selectedUrl })
			});
			if (!res.ok) throw new Error(`${get(t)('followfeedmodal.followFailed')} (${res.status})`);
			const data = await res.json();
			if (data.status === 'error') throw new Error(data.message);
			notifySubscriptionChanged();
			await parseSelectedFeed();
			status = 'success';
		} catch (err: any) {
			error = err.message || get(t)('followfeedmodal.followFailed');
			status = 'error';
		}
		syncing = false;
	}

	function handleRetry() {
		if (status === 'error' && searchResults.length > 0) {
			status = 'search';
			error = '';
		} else if (lastSearchQuery && !cameFromSearch) {
			fallbackToSearch();
		} else {
			discoverFeeds(feed.url);
		}
	}

	function handleBackdrop(e: MouseEvent) {
		if ((e.target as HTMLElement).classList.contains('dialog-backdrop')) onclose();
	}
</script>

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="dialog-backdrop" onclick={handleBackdrop} aria-hidden="true"></div>
<div class="dialog" role="dialog" aria-modal="true" aria-label="{$t('followfeedmodal.title')}">
	<div class="dialog-header">
		<p class="dialog-title">{$t('followfeedmodal.title')}</p>
		<button class="dialog-close" onclick={onclose} aria-label="{$t('followfeedmodal.cancel')}">
			<X size={16} strokeWidth={2} />
		</button>
	</div>
	<p class="dialog-sub">{feed.title}</p>

	<div class="modal-body">

			<!-- Loading -->
			{#if status === 'loading'}
				<div class="state-center">
					<span class="spinner"></span>
					<p class="state-hint">
						{#if syncing}
							{$t('followfeedmodal.syncing')}
						{:else}
							{mode === 'search' || cameFromSearch ? $t('followfeedmodal.searching') : $t('followfeedmodal.discovering')}
						{/if}
					</p>
				</div>

			<!-- Error -->
			{:else if status === 'error'}
				<div class="state-center">
					<span class="error-icon">⚠</span>
					<p class="error-msg">{error}</p>
					<div class="error-actions">
						<button class="dialog-btn dialog-btn--primary" onclick={handleRetry}>{$t('followfeedmodal.tryAgain')}</button>
						{#if !cameFromSearch && !lastSearchQuery}
							<button class="dialog-btn dialog-btn--ghost" onclick={fallbackToSearch}>{$t('followfeedmodal.searchInstead')}</button>
						{/if}
					</div>
				</div>

			<!-- Success -->
			{:else if status === 'success'}
				<div class="state-center">
					<span class="success-icon">✓</span>
					<p class="success-title">{$t('followfeedmodal.followingTitle')}</p>
					<p class="state-hint">{selectedUrl}</p>
					<button class="dialog-btn dialog-btn--ghost" onclick={onclose}>{$t('followfeedmodal.done')}</button>
				</div>

			<!-- Search results (online discover) -->
			{:else if status === 'search'}
				<div class="search-body">
					{#if error}
						<div class="search-error-banner">
							<span class="search-error-icon">⚠</span>
							<span class="search-error-text">{error}</span>
						</div>
					{:else}
						<p class="search-hint">{$t('followfeedmodal.searchHint')}</p>
					{/if}
					<ul class="search-list" role="listbox">
						{#each searchResults as result}
							<li>
								<button
									class="search-option"
									role="option"
									aria-selected="false"
									onclick={() => selectSearchResult(result)}
								>
									<span class="search-option-dot"></span>
									<div class="search-option-info">
										<span class="search-option-title">{result.title}</span>
										<span class="search-option-url">{result.url}</span>
									</div>
								</button>
							</li>
						{/each}
					</ul>
				</div>

			<!-- Confirm (discovered feeds) -->
			{:else}
				<div class="confirm-body">
					<p class="confirm-hint">{$t('followfeedmodal.confirmHint')}</p>

					<div class="selected-url-box">
						<span class="rss-dot"></span>
						<span class="selected-url-text">{selectedUrl}</span>
					</div>

					{#if feeds.length > 1}
						<button
							class="change-toggle"
							onclick={() => (expanded = !expanded)}
							aria-expanded={expanded}
						>
							<span>{$t('followfeedmodal.changeRssUrl')}</span>
							<span class="chevron" class:rotated={expanded}>›</span>
						</button>

						{#if expanded}
							<ul class="feed-list" role="listbox">
								{#each feeds as f}
									<li>
										<button
											class="feed-option"
											class:selected={f === selectedUrl}
											role="option"
											aria-selected={f === selectedUrl}
											onclick={() => { selectedUrl = f; expanded = false; }}
										>
											<span class="feed-option-dot" class:active={f === selectedUrl}></span>
											<span class="feed-option-url">{f}</span>
										</button>
									</li>
								{/each}
							</ul>
						{/if}
					{/if}

					<div class="dialog-actions">
						{#if cameFromSearch && searchResults.length > 0}
							<button class="dialog-btn dialog-btn--ghost" onclick={() => { status = 'search'; error = ''; }}>{$t('followfeedmodal.backToResults')}</button>
						{/if}
						<button class="dialog-btn dialog-btn--ghost" onclick={onclose}>{$t('followfeedmodal.cancel')}</button>
						<button class="dialog-btn dialog-btn--primary" onclick={followFeed}>{$t('followfeedmodal.follow')}</button>
					</div>
				</div>
			{/if}

		</div>
</div>

<style>
	/* ── App dialog pattern (matches FollowersTab dialogs) ───── */
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
		border-radius: var(--ui-radius-lg);
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
		border-radius: var(--ui-radius-sm);
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
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.dialog-actions {
		display: flex;
		justify-content: flex-end;
		gap: 8px;
	}

	.dialog-btn {
		padding: 8px 18px;
		border-radius: var(--ui-radius-sm);
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

	.modal-body { padding: 0; }

	.state-center {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 10px;
		padding: 20px 0;
	}

	.state-hint {
		font-size: 12px;
		color: color-mix(in oklch, var(--color-base-content, #000) 45%, transparent);
		margin: 0;
		text-align: center;
		word-break: break-all;
	}

	.spinner {
		display: block;
		width: 28px;
		height: 28px;
		border: 3px solid color-mix(in oklch, var(--color-base-content, #000) 12%, transparent);
		border-top-color: var(--color-primary, #3b82f6);
		border-radius: 50%;
		animation: spin 0.7s linear infinite;
	}

	@keyframes spin { to { transform: rotate(360deg); } }

	.error-icon { font-size: 24px; color: var(--color-error, #ef4444); }

	.error-msg {
		font-size: 13px;
		color: var(--color-error, #ef4444);
		text-align: center;
		margin: 0;
	}

	.error-actions {
		display: flex;
		gap: 8px;
		flex-wrap: wrap;
		justify-content: center;
	}

	.success-icon {
		width: 44px;
		height: 44px;
		border-radius: 50%;
		background: color-mix(in oklch, var(--color-success, #22c55e) 15%, transparent);
		color: var(--color-success, #22c55e);
		font-size: 22px;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.success-title {
		font-size: 16px;
		font-weight: 700;
		color: var(--color-base-content, #000);
		margin: 0;
	}

	/* ── Search results ──────────────────────────────────────── */
	.search-body { display: flex; flex-direction: column; gap: 12px; }

	.search-error-banner {
		display: flex;
		align-items: center;
		gap: 8px;
		background: color-mix(in oklch, var(--color-error, #ef4444) 8%, transparent);
		border: 1px solid color-mix(in oklch, var(--color-error, #ef4444) 20%, transparent);
		border-radius: var(--ui-radius-sm);
		padding: 8px 12px;
	}

	.search-error-icon {
		color: var(--color-error, #ef4444);
		flex-shrink: 0;
		font-size: 14px;
	}

	.search-error-text {
		font-size: 12px;
		color: var(--color-error, #ef4444);
	}

	.search-hint {
		font-size: 13px;
		color: color-mix(in oklch, var(--color-base-content, #000) 60%, transparent);
		margin: 0;
	}

	.search-list {
		list-style: none;
		margin: 0;
		padding: 0;
		border: 1px solid color-mix(in oklch, var(--color-base-content, #000) 10%, transparent);
		border-radius: var(--ui-radius-sm);
		overflow: hidden;
		max-height: 280px;
		overflow-y: auto;
	}

	.search-option {
		display: flex;
		align-items: flex-start;
		gap: 10px;
		width: 100%;
		background: none;
		border: none;
		border-bottom: 1px solid color-mix(in oklch, var(--color-base-content, #000) 6%, transparent);
		padding: 10px 12px;
		cursor: pointer;
		text-align: left;
		transition: background 0.13s;
	}

	.search-option:last-child { border-bottom: none; }

	.search-option:hover {
		background: color-mix(in oklch, var(--color-base-content, #000) 5%, transparent);
	}

	.search-option-dot {
		width: 7px;
		height: 7px;
		border-radius: 50%;
		background: var(--color-primary, #3b82f6);
		flex-shrink: 0;
		margin-top: 5px;
	}

	.search-option-info {
		display: flex;
		flex-direction: column;
		gap: 2px;
		min-width: 0;
	}

	.search-option-title {
		font-size: 13px;
		font-weight: 600;
		color: var(--color-base-content, #000);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.search-option-url {
		font-size: 11px;
		color: color-mix(in oklch, var(--color-base-content, #000) 50%, transparent);
		word-break: break-all;
	}

	/* ── Confirm ─────────────────────────────────────────────── */
	.confirm-body { display: flex; flex-direction: column; gap: 12px; }

	.confirm-hint {
		font-size: 13px;
		color: color-mix(in oklch, var(--color-base-content, #000) 60%, transparent);
		margin: 0;
	}

	.selected-url-box {
		display: flex;
		align-items: center;
		gap: 8px;
		background: color-mix(in oklch, var(--color-base-content, #000) 5%, transparent);
		border: 1px solid color-mix(in oklch, var(--color-base-content, #000) 10%, transparent);
		border-radius: var(--ui-radius-sm);
		padding: 10px 12px;
	}

	.rss-dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background: var(--color-primary, #3b82f6);
		flex-shrink: 0;
	}

	.selected-url-text {
		font-size: 12px;
		color: var(--color-base-content, #000);
		word-break: break-all;
	}

	.change-toggle {
		display: flex;
		align-items: center;
		justify-content: space-between;
		width: 100%;
		background: none;
		border: none;
		cursor: pointer;
		font-size: 12px;
		font-weight: 600;
		color: var(--color-primary, #3b82f6);
		padding: 4px 0;
	}

	.chevron {
		font-size: 16px;
		display: inline-block;
		transition: transform 0.18s;
	}

	.chevron.rotated { transform: rotate(90deg); }

	.feed-list {
		list-style: none;
		margin: 0;
		padding: 0;
		border: 1px solid color-mix(in oklch, var(--color-base-content, #000) 10%, transparent);
		border-radius: var(--ui-radius-sm);
		overflow: hidden;
	}

	.feed-option {
		display: flex;
		align-items: center;
		gap: 10px;
		width: 100%;
		background: none;
		border: none;
		border-bottom: 1px solid color-mix(in oklch, var(--color-base-content, #000) 6%, transparent);
		padding: 10px 12px;
		cursor: pointer;
		text-align: left;
		transition: background 0.13s;
	}

	.feed-option:last-child { border-bottom: none; }

	.feed-option:hover {
		background: color-mix(in oklch, var(--color-base-content, #000) 5%, transparent);
	}

	.feed-option.selected {
		background: color-mix(in oklch, var(--color-primary, #3b82f6) 8%, transparent);
	}

	.feed-option-dot {
		width: 7px;
		height: 7px;
		border-radius: 50%;
		border: 2px solid color-mix(in oklch, var(--color-base-content, #000) 25%, transparent);
		flex-shrink: 0;
		transition: background 0.13s, border-color 0.13s;
	}

	.feed-option-dot.active {
		background: var(--color-primary, #3b82f6);
		border-color: var(--color-primary, #3b82f6);
	}

	.feed-option-url {
		font-size: 11px;
		color: var(--color-base-content, #000);
		word-break: break-all;
	}
</style>
