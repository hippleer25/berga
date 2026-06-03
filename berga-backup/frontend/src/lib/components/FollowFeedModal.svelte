<script lang="ts">
    import { t } from 'svelte-i18n';
    import { get } from 'svelte/store';
import { notifySubscriptionChanged } from '$lib/stores/subscription';

    type ModalStatus = 'loading' | 'confirm' | 'error' | 'success';

    interface Props {
        feed: { title: string; url: string };
        onclose: () => void;
    }

    const { feed, onclose }: Props = $props();

    // ── State ──────────────────────────────────────────────────────────────
    let status      = $state<ModalStatus>('loading');
    let feeds       = $state<string[]>([]);
    let selectedUrl = $state('');
    let error       = $state('');
    let expanded    = $state(false);

    // ── Helpers ────────────────────────────────────────────────────────────
    function getCookie(name: string): string | null {
        const match = document.cookie
            .split('; ')
            .find(row => row.startsWith(name + '='));
        return match ? decodeURIComponent(match.split('=')[1]) : null;
    }

    // ── On mount, start discovering feeds ─────────────────────────────────
    $effect(() => {
        discoverFeeds(feed.url);
    });

    // ── Functions ──────────────────────────────────────────────────────────
    async function discoverFeeds(url: string) {
        status   = 'loading';
        error    = '';
        feeds    = [];
        expanded = false;
        try {
		const res = await fetch(
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
            error  = err.message || get(t)('followfeedmodal.discoverFailed');
            status = 'error';
        }
    }

    async function followFeed() {
        status = 'loading';
        try {
            const token = getCookie('token');

		const res = await fetch(
			`/api/feed-add`,
			{
                    method: 'POST',
                    credentials: 'include',
                    headers: {
                        'Content-Type': 'application/json',
                        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
                    },
                    body: JSON.stringify({ url: selectedUrl })
                }
            );
            if (!res.ok) throw new Error(`${get(t)('followfeedmodal.followFailed')} (${res.status})`);
            const data = await res.json();
    if (data.status === 'error') throw new Error(data.message);
    status = 'success';
    notifySubscriptionChanged();
        } catch (err: any) {
            error  = err.message || get(t)('followfeedmodal.followFailed');
            status = 'error';
        }
    }

    function handleBackdrop(e: MouseEvent) {
        if ((e.target as HTMLElement).classList.contains('overlay')) onclose();
    }
</script>

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="overlay" onclick={handleBackdrop}>
    <div class="box">
        <button class="close" onclick={onclose}>✕</button>

        <!-- Header -->
        <div class="modal-header">
            <span class="modal-icon">📡</span>
            <div class="modal-title-group">
                <p class="modal-label">{$t('followfeedmodal.title')}</p>
                <p class="modal-site-title">{feed.title}</p>
            </div>
        </div>

        <div class="modal-body">

            <!-- Loading -->
            {#if status === 'loading'}
                <div class="state-center">
                    <span class="spinner"></span>
                    <p class="state-hint">{$t('followfeedmodal.discovering')}</p>
                </div>

            <!-- Error -->
            {:else if status === 'error'}
                <div class="state-center">
                    <span class="error-icon">⚠</span>
                    <p class="error-msg">{error}</p>
                    <button class="btn-primary" onclick={() => discoverFeeds(feed.url)}>{$t('followfeedmodal.tryAgain')}</button>
                </div>

            <!-- Success -->
            {:else if status === 'success'}
                <div class="state-center">
                    <span class="success-icon">✓</span>
                    <p class="success-title">{$t('followfeedmodal.followingTitle')}</p>
                    <p class="state-hint">{selectedUrl}</p>
                    <button class="btn-ghost" onclick={onclose}>{$t('followfeedmodal.done')}</button>
                </div>

            <!-- Confirm -->
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

                    <div class="modal-actions">
                        <button class="btn-ghost" onclick={onclose}>{$t('followfeedmodal.cancel')}</button>
                        <button class="btn-primary" onclick={followFeed}>{$t('followfeedmodal.follow')}</button>
                    </div>
                </div>
            {/if}

        </div>
    </div>
</div>

<style>
    .overlay {
        position: fixed;
        inset: 0;
        z-index: 999;
        background: rgba(0, 0, 0, 0.5);
        backdrop-filter: blur(2px);
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 16px;
        animation: fade-in 0.15s ease;
    }

    @keyframes fade-in {
        from { opacity: 0; }
        to   { opacity: 1; }
    }

    .box {
        background: var(--color-base-100, white);
        border: 1px solid color-mix(in oklch, var(--color-base-content, #000) 10%, transparent);
        border-radius: 16px;
        width: 100%;
        max-width: 420px;
        box-shadow: 0 24px 64px rgba(0, 0, 0, 0.2);
        position: relative;
        overflow: hidden;
        animation: slide-up 0.18s ease;
    }

    @keyframes slide-up {
        from { transform: translateY(12px); opacity: 0; }
        to   { transform: translateY(0);    opacity: 1; }
    }

    .close {
        position: absolute;
        top: 12px;
        right: 12px;
        background: none;
        border: none;
        cursor: pointer;
        font-size: 14px;
        color: color-mix(in oklch, var(--color-base-content, #000) 40%, transparent);
        padding: 4px 6px;
        border-radius: 6px;
        transition: background 0.15s, color 0.15s;
        z-index: 1;
    }

    .close:hover {
        background: color-mix(in oklch, var(--color-base-content, #000) 8%, transparent);
        color: var(--color-base-content, #000);
    }

    .modal-header {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 16px 44px 12px 16px;
        border-bottom: 1px solid color-mix(in oklch, var(--color-base-content, #000) 8%, transparent);
    }

    .modal-icon { font-size: 22px; flex-shrink: 0; }

    .modal-title-group { flex: 1; min-width: 0; }

    .modal-label {
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        color: color-mix(in oklch, var(--color-base-content, #000) 40%, transparent);
        margin: 0;
    }

    .modal-site-title {
        font-size: 14px;
        font-weight: 700;
        color: var(--color-base-content, #000);
        margin: 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .modal-body { padding: 16px; }

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
        border-radius: 8px;
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
        border-radius: 8px;
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

    .modal-actions {
        display: flex;
        justify-content: flex-end;
        gap: 8px;
        padding-top: 4px;
    }

    .btn-primary {
        font-size: 13px;
        font-weight: 700;
        padding: 8px 20px;
        border-radius: 999px;
        border: none;
        background: var(--color-primary, #3b82f6);
        color: var(--color-primary-content, #fff);
        cursor: pointer;
        transition: opacity 0.15s;
    }

    .btn-primary:hover { opacity: 0.85; }

    .btn-ghost {
        font-size: 13px;
        font-weight: 600;
        padding: 8px 16px;
        border-radius: 999px;
        border: 1px solid color-mix(in oklch, var(--color-base-content, #000) 15%, transparent);
        background: none;
        color: var(--color-base-content, #000);
        cursor: pointer;
        transition: background 0.15s;
    }

    .btn-ghost:hover {
        background: color-mix(in oklch, var(--color-base-content, #000) 6%, transparent);
    }
</style>