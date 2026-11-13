<script lang="ts">
import LogOut from '@lucide/svelte/icons/log-out';
import Globe from '@lucide/svelte/icons/globe';
import Check from '@lucide/svelte/icons/check';
import Download from '@lucide/svelte/icons/download';
import Upload from '@lucide/svelte/icons/upload';
import RefreshCw from '@lucide/svelte/icons/refresh-cw';
import ArrowUpRight from '@lucide/svelte/icons/arrow-up-right';
import { t } from 'svelte-i18n';
import { get } from 'svelte/store';
import { onMount } from 'svelte';
import { goto } from '$app/navigation';
import { apiFetch, clearNativeToken } from '$lib/api';
import { instance } from '$lib/stores/instance';
import { version } from '$lib/stores/version';
import { setSessionLoggedOut } from '$lib/stores/session';
import { ripple } from '$lib/actions/ripple';

let instanceUrl = $state(instance.getInstance());

onMount(() => {
	version.load();
});

function fmtVersion(v: string): string {
	if (!v) return '';
	if (v === 'dev') return 'dev';
	return v.startsWith('v') ? v : `v${v}`;
}

function saveInstance() {
	instance.setInstance(instanceUrl);
}

async function logout() {
	try {
		await apiFetch('/api/logout', { method: 'POST', credentials: 'include' });
	} finally {
		clearNativeToken();
		setSessionLoggedOut();
		goto('/', { replaceState: true });
	}
}

/* ── Subscriptions (migrated from /settings/data) ── */
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
			throw new Error(data.detail || data.message || get(t)('settings.serverError', { values: { status: res.status } }));
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

/* ── Recommendation profile (bergapack) ── */
let profileStatus = $state<'idle' | 'loading' | 'success' | 'partial' | 'error'>('idle');
let profileError = $state('');
let profileInput: HTMLInputElement;

async function exportProfile() {
	const res = await apiFetch('/api/profile-export', { credentials: 'include' });
	if (!res.ok) return;
	const blob = await res.blob();
	const url = URL.createObjectURL(blob);
	const a = document.createElement('a');
	a.href = url;
	a.download = 'bergapack.json';
	a.click();
	URL.revokeObjectURL(url);
}

async function importProfile(e: Event) {
	const file = (e.target as HTMLInputElement).files?.[0];
	if (!file) return;
	profileStatus = 'loading';
	profileError = '';
	const formData = new FormData();
	formData.append('file', file);
	try {
		const res = await apiFetch('/api/profile-import', { method: 'POST', credentials: 'include', body: formData });
		const data = await res.json().catch(() => ({}));
		if (!res.ok) {
			throw new Error(data.detail || data.message || get(t)('settings.serverError', { values: { status: res.status } }));
		}
		profileStatus = data.status === 'partial' ? 'partial' : 'success';
		setTimeout(() => (profileStatus = 'idle'), 6000);
	} catch (err: any) {
		profileStatus = 'error';
		profileError = err.message;
	} finally {
		profileInput.value = '';
	}
}

/* ── User data export (notes / highlights / saves) ── */
let exportFormat = $state<'json' | 'csv' | 'md'>('json');
let exportStatus = $state<'idle' | 'loading' | 'error'>('idle');
let exportError = $state('');

async function exportUserData() {
	exportStatus = 'loading';
	exportError = '';
	try {
		const res = await apiFetch(`/api/export/user-data?fmt=${exportFormat}`, { credentials: 'include' });
		if (!res.ok) {
			const data = await res.json().catch(() => ({}));
			throw new Error(data.detail || data.message || get(t)('settings.serverError', { values: { status: res.status } }));
		}
		const blob = await res.blob();
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = `berga-export.${exportFormat === 'md' ? 'md' : exportFormat}`;
		a.click();
		URL.revokeObjectURL(url);
	} catch (err: any) {
		exportStatus = 'error';
		exportError = err.message;
	} finally {
		exportStatus = 'idle';
	}
}

async function fetchAllArticles() {
	fetchStatus = 'loading';
	fetchError = '';
	try {
		const res = await apiFetch('/api/parse-user-all', { method: 'POST', credentials: 'include' });
		if (!res.ok) {
			const data = await res.json().catch(() => ({}));
			throw new Error(data.detail || data.message || get(t)('settings.serverError', { values: { status: res.status } }));
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
			throw new Error(data.detail || data.message || get(t)('settings.serverError', { values: { status: res.status } }));
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
<h2 class="section-title">{$t('settings.account')}</h2>

<div class="account-section">
	<div class="instance-section">
		<label for="instance-setting" class="setting-label">{$t('settings.instanceLabel')}</label>
		<div class="instance-row">
			<div class="input-icon-wrap">
				<span class="input-icon"><Globe size={18} /></span>
				<input
					id="instance-setting"
					type="text"
					class="custom-input has-icon-left"
					placeholder={$t('settings.instancePlaceholder')}
					bind:value={instanceUrl}
					oninput={saveInstance}
				/>
			</div>
		</div>
		<p class="setting-desc">{$t('settings.instanceDesc')}</p>
	</div>

	<button class="action-btn danger full-width" use:ripple onclick={logout}>
		<LogOut size={16} /><span>{$t('settings.logOut')}</span>
	</button>
</div>

<div class="section-divider"></div>

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

<h2 class="section-title">{$t('settings.profilePack')}</h2>
<p class="section-desc">{$t('settings.profilePackDesc')}</p>

<div class="btn-group">
	<button class="action-btn" use:ripple onclick={exportProfile}>
		<Download size={16} /><span>{$t('settings.exportProfile')}</span>
	</button>
	<input bind:this={profileInput} type="file" accept=".json,application/json" class="hidden-input" onchange={importProfile} />
	<button class="action-btn" use:ripple class:success={profileStatus === 'success' || profileStatus === 'partial'} onclick={() => profileInput.click()} disabled={profileStatus === 'loading'}>
		{#if profileStatus === 'loading'}<span class="spinner"></span><span>{$t('settings.importing')}</span>
		{:else if profileStatus === 'success' || profileStatus === 'partial'}<Check size={16} /><span>{$t('settings.imported')}</span>
		{:else}<Upload size={16} /><span>{$t('settings.importProfile')}</span>{/if}
	</button>
</div>
{#if profileStatus === 'partial'}<p class="warn-text">{$t('settings.profilePackMismatch')}</p>{/if}
{#if profileStatus === 'error'}<p class="error-text">{profileError}</p>{/if}

<div class="section-divider"></div>

<h2 class="section-title">{$t('settings.userDataExport')}</h2>
<p class="section-desc">{$t('settings.userDataExportDesc')}</p>

<div class="btn-group">
	<div class="format-toggle" role="radiogroup" aria-label={$t('settings.userDataExportFormat')}>
		<button
			class="format-btn" class:active={exportFormat === 'json'}
			onclick={() => (exportFormat = 'json')}>JSON</button>
		<button
			class="format-btn" class:active={exportFormat === 'csv'}
			onclick={() => (exportFormat = 'csv')}>CSV</button>
		<button
			class="format-btn" class:active={exportFormat === 'md'}
			onclick={() => (exportFormat = 'md')}>Markdown</button>
	</div>
	<button class="action-btn" use:ripple onclick={exportUserData} disabled={exportStatus === 'loading'}>
		{#if exportStatus === 'loading'}<span class="spinner"></span><span>{$t('settings.exporting')}</span>
		{:else}<Download size={16} /><span>{$t('settings.userDataExportBtn')}</span>{/if}
	</button>
</div>
{#if exportStatus === 'error'}<p class="error-text">{exportError}</p>{/if}

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

<div class="section-divider"></div>

<h2 class="section-title">{$t('settings.aboutSection')}</h2>

<div class="about-card">
	<div class="about-row">
		<span class="about-label">{$t('settings.versionLabel')}</span>
		<span class="about-version">{fmtVersion($version.version) || '—'}</span>
	</div>
	<div class="about-row">
		<span class="about-label">{$t('settings.updateStatusLabel')}</span>
		{#if !$version.loaded}
			<span class="about-status">—</span>
		{:else if $version.updateAvailable}
			<a
				class="update-badge"
				href={$version.latestUrl || 'https://github.com/hippleer25/berga/releases'}
				target="_blank"
				rel="noopener noreferrer"
			>
				{$t('settings.updateAvailable')}
				<ArrowUpRight size={12} strokeWidth={2.2} />
			</a>
		{:else}
			<span class="about-status up-to-date">
				<Check size={13} strokeWidth={2.2} />
				{$t('settings.upToDate')}
			</span>
		{/if}
	</div>
	<a
		class="action-btn full-width"
		href="{$version.latestUrl || 'https://github.com/hippleer25/berga/releases'}"
		target="_blank"
		rel="noopener noreferrer"
		use:ripple
	>
		<ArrowUpRight size={16} /><span>{$t('settings.viewReleases')}</span>
	</a>
</div>
</div>

<style>
	.tab-panel { display: flex; flex-direction: column; gap: 16px; padding-top: 12px; }
	.section-title { font-size: 16px; font-weight: 700; color: var(--color-base-content); margin: 0; }
	.section-desc { font-size: 13px; line-height: 1.45; color: color-mix(in oklch, var(--color-base-content) 50%, transparent); margin: -8px 0 0; overflow-wrap: anywhere; }
	.section-divider { height: 1px; background: var(--color-base-300); margin: 8px 0; }

	.account-section { display: flex; flex-direction: column; gap: 12px; }

	.btn-group { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
	.format-toggle { display: inline-flex; border: 1px solid var(--color-base-300); border-radius: var(--ui-radius-sm); overflow: hidden; }
	.format-btn {
		padding: 9px 12px; border: none; background: transparent; color: var(--color-base-content);
		font-size: 13px; font-weight: 600; cursor: pointer; transition: background 130ms ease;
	}
	.format-btn + .format-btn { border-left: 1px solid var(--color-base-300); }
	.format-btn:hover { background: var(--color-base-200); }
	.format-btn.active { background: var(--color-base-200); color: var(--color-accent); }
	.action-btn {
		display: inline-flex; align-items: center; justify-content: center; gap: 6px;
		padding: 10px 16px; border-radius: var(--ui-radius-sm); border: 1px solid var(--color-base-300);
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
	.action-btn.danger { border-color: color-mix(in oklch, var(--color-error) 50%, transparent); color: var(--color-error); }
	.action-btn.danger:hover { background: color-mix(in oklch, var(--color-error) 10%, transparent); }
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
	.warn-text { font-size: 12px; color: var(--color-warning, var(--color-accent)); margin-top: 4px; line-height: 1.4; }

	.instance-section { display: flex; flex-direction: column; gap: 8px; margin-bottom: 8px; }

	.about-card { display: flex; flex-direction: column; gap: 10px; }
	.about-row {
		display: flex; align-items: center; justify-content: space-between; gap: 12px;
		padding: 10px 12px;
		border: var(--ui-border-width) solid var(--ui-border-color);
		border-radius: var(--ui-radius-sm);
		background: color-mix(in oklch, var(--color-base-100) 70%, transparent);
	}
	.about-label { font-size: 13px; font-weight: 600; color: var(--ui-text-subtle); }
	.about-version { font-size: 13px; font-weight: 700; color: var(--color-base-content); }
	.about-status {
		display: inline-flex; align-items: center; gap: 5px;
		font-size: 12.5px; font-weight: 600; color: var(--ui-text-subtle);
	}
	.about-status.up-to-date { color: var(--color-success); }
	.update-badge {
		display: inline-flex;
		align-items: center;
		gap: 3px;
		padding: 2px 8px;
		border: var(--ui-border-width) solid color-mix(in oklch, var(--color-accent) 45%, transparent);
		border-radius: 999px;
		background: color-mix(in oklch, var(--color-accent) 12%, transparent);
		color: var(--color-accent);
		font-size: 11px;
		font-weight: 700;
		text-decoration: none;
		transition: background var(--ui-dur-1) var(--ui-ease);
	}
	.update-badge:hover {
		background: color-mix(in oklch, var(--color-accent) 20%, transparent);
	}
	a.action-btn { text-decoration: none; }
	.setting-label { font-size: 13px; font-weight: 600; color: color-mix(in oklch, var(--color-base-content) 80%, transparent); padding-left: 2px; }
	.setting-desc { font-size: 12px; color: color-mix(in oklch, var(--color-base-content) 50%, transparent); margin: 0; line-height: 1.4; }
	.input-icon-wrap { position: relative; display: flex; align-items: center; }
	.custom-input { width: 100%; height: 44px; background: color-mix(in oklch, var(--color-base-200) 50%, transparent); border: 1px solid var(--color-base-300); border-radius: var(--ui-radius-sm); padding: 0 14px; font-size: 14px; color: var(--color-base-content); transition: background 180ms ease, border-color 180ms ease, box-shadow 180ms ease; outline: none; }
	.custom-input::placeholder { color: color-mix(in oklch, var(--color-base-content) 35%, transparent); }
	.custom-input:focus { background: var(--color-base-100); border-color: var(--color-accent); box-shadow: 0 0 0 3px color-mix(in oklch, var(--color-accent) 15%, transparent); }
	.custom-input.has-icon-left { padding-left: 42px; }
	.input-icon { position: absolute; left: 14px; color: var(--color-accent); display: flex; align-items: center; pointer-events: none; z-index: 2; }
</style>
