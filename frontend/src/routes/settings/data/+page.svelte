<script lang="ts">
	import { onMount } from 'svelte';
	import Check from '@lucide/svelte/icons/check';
	import Download from '@lucide/svelte/icons/download';
	import Upload from '@lucide/svelte/icons/upload';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
import { t } from 'svelte-i18n';
 import { get } from 'svelte/store';
 import { apiFetch } from '$lib/api';
 import { ripple } from '$lib/actions/ripple';

	let importStatus = $state<'idle' | 'loading' | 'success' | 'error'>('idle');
	let importError = $state('');
	let fetchStatus = $state<'idle' | 'loading' | 'success' | 'error'>('idle');
	let fetchError = $state('');
	let clusterStatus = $state<'idle' | 'loading' | 'success' | 'error'>('idle');
	let clusterError = $state('');
	let fileInput: HTMLInputElement;

	async function exportOpml() {
		const res = await apiFetch('/api/opml-export', { credentials: 'include' });
		if (!res.ok) return;
		const blob = await res.blob();
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = 'subscriptions.opml';
		a.click();
		URL.revokeObjectURL(url);
	}

	async function importOpml(e: Event) {
		const file = (e.target as HTMLInputElement).files?.[0];
		if (!file) return;
		importStatus = 'loading';
		importError = '';
		const formData = new FormData();
		formData.append('file', file);
		try {
			const res = await apiFetch('/api/opml-import', { method: 'POST', credentials: 'include', body: formData });
			if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || data.message || `${get(t)('settings.serverError').replace('{status}', res.status)}`);
			}
			importStatus = 'success';
			setTimeout(() => (importStatus = 'idle'), 3000);
		} catch (err: any) {
			importStatus = 'error';
			importError = err.message;
		} finally {
			fileInput.value = '';
		}
	}

	async function fetchAllArticles() {
		fetchStatus = 'loading';
		fetchError = '';
		try {
			const res = await apiFetch('/api/parse-user-all', { method: 'POST', credentials: 'include' });
			if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || data.message || `${get(t)('settings.serverError').replace('{status}', res.status)}`);
			}
			fetchStatus = 'success';
			setTimeout(() => (fetchStatus = 'idle'), 3000);
		} catch (err: any) {
			fetchStatus = 'error';
			fetchError = err.message;
		}
	}

	async function refreshClusters() {
		clusterStatus = 'loading';
		clusterError = '';
		try {
			const res = await apiFetch('/api/cluster/refresh', { method: 'POST', credentials: 'include' });
			if (!res.ok) {
				const data = await res.json().catch(() => ({}));
				throw new Error(data.detail || data.message || `${get(t)('settings.serverError').replace('{status}', res.status)}`);
			}
			clusterStatus = 'success';
			setTimeout(() => (clusterStatus = 'idle'), 3000);
		} catch (err: any) {
			clusterStatus = 'error';
			clusterError = err.message;
		}
	}
</script>

<div class="tab-panel">
	<h2 class="section-title">{$t('settings.subscriptions')}</h2>
	<p class="section-desc">{$t('settings.subscriptionsDesc')}</p>

	<div class="btn-group">
		<button class="action-btn" use:ripple onclick={exportOpml}>
			<Download size={16} /><span>{$t('settings.exportOpml')}</span>
		</button>
		<input bind:this={fileInput} type="file" accept=".opml,text/x-opml,application/xml,text/xml" class="hidden-input" onchange={importOpml} />
		<button class="action-btn" use:ripple class:success={importStatus === 'success'} onclick={() => fileInput.click()} disabled={importStatus === 'loading'}>
			{#if importStatus === 'loading'}<span class="spinner"></span><span>{$t('settings.importing')}</span>
			{:else if importStatus === 'success'}<Check size={16} /><span>{$t('settings.imported')}</span>
			{:else}<Upload size={16} /><span>{$t('settings.importOpml')}</span>{/if}
		</button>
	</div>
	{#if importStatus === 'error'}<p class="error-text">{importError}</p>{/if}

	<div class="section-divider"></div>

	<h2 class="section-title">{$t('settings.fetchNewArticles')}</h2>
	<p class="section-desc">{$t('settings.fetchDesc')}</p>
	<button class="action-btn full-width" use:ripple class:success={fetchStatus === 'success'} class:error={fetchStatus === 'error'} onclick={fetchAllArticles} disabled={fetchStatus === 'loading'}>
		{#if fetchStatus === 'loading'}<span class="spinner"></span><span>{$t('settings.fetching')}</span>
		{:else if fetchStatus === 'success'}<Check size={16} /><span>{$t('settings.done')}</span>
		{:else}<RefreshCw size={16} /><span>{$t('settings.fetchArticles')}</span>{/if}
	</button>
	{#if fetchStatus === 'error'}<p class="error-text">{fetchError}</p>{/if}

	<div class="section-divider"></div>

	<h2 class="section-title">{$t('settings.refreshClusters')}</h2>
	<p class="section-desc">{$t('settings.refreshClustersDesc')}</p>
	<button class="action-btn full-width" use:ripple class:success={clusterStatus === 'success'} class:error={clusterStatus === 'error'} onclick={refreshClusters} disabled={clusterStatus === 'loading'}>
		{#if clusterStatus === 'loading'}<span class="spinner"></span><span>{$t('settings.refreshingClusters')}</span>
		{:else if clusterStatus === 'success'}<Check size={16} /><span>{$t('settings.done')}</span>
		{:else}<RefreshCw size={16} /><span>{$t('settings.refreshClusters')}</span>{/if}
	</button>
	{#if clusterStatus === 'error'}<p class="error-text">{clusterError}</p>{/if}
</div>

<style>
	.tab-panel { display: flex; flex-direction: column; gap: 16px; padding-top: 12px; }
	.section-title { font-size: 16px; font-weight: 700; color: var(--color-base-content); margin: 0; }
	.section-desc { font-size: 13px; line-height: 1.45; color: color-mix(in oklch, var(--color-base-content) 50%, transparent); margin: -8px 0 0; }
	.section-divider { height: 1px; background: var(--color-base-300); margin: 8px 0; }

	.btn-group { display: flex; gap: 8px; }
	.action-btn {
		display: inline-flex; align-items: center; justify-content: center; gap: 6px;
		padding: 10px 16px; border-radius: 10px; border: 1px solid var(--color-base-300);
		background: transparent; color: var(--color-base-content); cursor: pointer;
		font-size: 13px; font-weight: 600; transition: all 130ms ease;
		position: relative; overflow: hidden;
	}
	.action-btn:hover { background: var(--color-base-200); }
	.action-btn:active { transform: scale(0.97); }
	.action-btn.full-width { width: 100%; }
	.action-btn.success { border-color: color-mix(in oklch, var(--color-success) 50%, transparent); color: var(--color-success); }
	.action-btn.success:hover { background: color-mix(in oklch, var(--color-success) 10%, transparent); }
	.action-btn.error { border-color: color-mix(in oklch, var(--color-error) 50%, transparent); color: var(--color-error); }
	.action-btn.error:hover { background: color-mix(in oklch, var(--color-error) 10%, transparent); }
	.action-btn:disabled { opacity: 0.6; cursor: not-allowed; }
	.hidden-input { display: none; }

	.spinner {
		width: 16px; height: 16px;
		border: 2px solid color-mix(in oklch, var(--color-base-content) 20%, transparent);
		border-top-color: var(--color-base-content); border-radius: 50%;
		animation: spin 0.6s linear infinite;
	}
	@keyframes spin { to { transform: rotate(360deg); } }
	.error-text { font-size: 12px; color: var(--color-error); margin-top: 4px; }
</style>
