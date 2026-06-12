<script lang="ts">
  import { onMount } from 'svelte';
  import Tag from '@lucide/svelte/icons/tag';
import Plus from '@lucide/svelte/icons/plus';
import Pencil from '@lucide/svelte/icons/pencil';
import X from '@lucide/svelte/icons/x';
import Trash2 from '@lucide/svelte/icons/trash-2';
import RefreshCw from '@lucide/svelte/icons/refresh-cw';
  import { t } from 'svelte-i18n';
  import { get } from 'svelte/store';
  import { ripple } from '$lib/actions/ripple';
  import { apiFetch } from '$lib/api';

  interface FeedInfo { feed_sha256: string; feed_title: string; }
  interface FolderInfo { id: string; name: string; }

interface SmartTag {
    id: number;
    name: string;
    color: string | null;
    feed_scope: string[] | string | null;
    folder_scope: string[] | string | null;
    regex_pattern: string | null;
    regex_flags: string | null;
    ai_include_terms: string[] | string | null;
    ai_exclude_terms: string[] | string | null;
    ai_threshold: number;
    ai_negate_threshold: number | null;
    ai_reinforcement_enabled: boolean | number;
    enabled_layers: string | null;
    centroid_manual_count: number;
    created_at: string;
    updated_at: string;
}

  let tags = $state<SmartTag[]>([]);
  let feeds = $state<FeedInfo[]>([]);
  let folders = $state<FolderInfo[]>([]);
  let loading = $state(true);
  let editingTag = $state<SmartTag | null>(null);
  let showForm = $state(false);
  let deleteConfirmId = $state<number | null>(null);

  let formName = $state('');
  let formColor = $state('#3b82f6');
  let formFeedScope = $state<string[]>([]);
  let formFolderScope = $state<string[]>([]);
  let formRegex = $state('');
  let formRegexFlags = $state('');
let formAiInclude = $state('');
let formAiExclude = $state('');
let formAiThreshold = $state(0.65);
let formAiNegateThreshold = $state<number | null>(null);
let formAiReinforcement = $state(true);
  let formLayers = $state<Record<string, boolean>>({ manual: true, feed: false, folder: false, regex: false, ai: false });

  let saving = $state(false);
  let saveError = $state('');
  let evaluating = $state(false);

  onMount(() => {
    loadTags();
    loadStructure();
  });

  async function loadTags() {
    loading = true;
    try {
      const res = await apiFetch('/api/tags', { credentials: 'include' });
      if (!res.ok) throw new Error(`Error ${res.status}`);
      const data = await res.json();
      tags = data.tags || [];
    } catch (err) {
      console.error('Failed to load tags:', err);
    } finally {
      loading = false;
    }
  }

  async function loadStructure() {
    try {
      const res = await apiFetch('/api/list-subscriptions', { credentials: 'include' });
      if (!res.ok) return;
      const raw = await res.json();
      const items: any[] = Array.isArray(raw) ? raw : (raw.feeds ?? []);
      const feedList: FeedInfo[] = [];
      const folderMap = new Map<string, FolderInfo>();
      for (const f of items) {
        if (f._empty_folder) {
          if (f.folder && f.folder.id != null && !folderMap.has(String(f.folder.id))) {
            folderMap.set(String(f.folder.id), { id: String(f.folder.id), name: f.folder.name || `Folder ${f.folder.id}` });
          }
          continue;
        }
        if (f.feed_sha256) {
          feedList.push({ feed_sha256: f.feed_sha256, feed_title: f.title || f.url || f.feed_sha256 });
        }
        if (f.folder && f.folder.id != null && !folderMap.has(String(f.folder.id))) {
          folderMap.set(String(f.folder.id), { id: String(f.folder.id), name: f.folder.name || `Folder ${f.folder.id}` });
        }
      }
      const seen = new Set<string>();
      feeds = feedList.filter(f => { if (seen.has(f.feed_sha256)) return false; seen.add(f.feed_sha256); return true; });
      folders = [...folderMap.values()];
    } catch (err) {
      console.error('Failed to load structure:', err);
    }
  }

function resetForm() {
    formName = '';
    formColor = '#3b82f6';
    formFeedScope = [];
    formFolderScope = [];
    formRegex = '';
    formRegexFlags = '';
    formAiInclude = '';
    formAiExclude = '';
    formAiThreshold = 0.65;
    formAiNegateThreshold = null;
    formAiReinforcement = true;
    formLayers = { manual: true, feed: false, folder: false, regex: false, ai: false };
    editingTag = null;
    saveError = '';
}

  function openCreate() {
    resetForm();
    showForm = true;
  }

  function toArray(val: any): string[] {
    if (Array.isArray(val)) return val;
    if (typeof val === 'string') {
      try { const p = JSON.parse(val); return Array.isArray(p) ? p : []; } catch { return val.split(',').map((s: string) => s.trim()).filter(Boolean); }
    }
    return [];
  }

  function openEdit(tag: SmartTag) {
    editingTag = tag;
    formName = tag.name;
    formColor = tag.color || '#3b82f6';
    formFeedScope = toArray(tag.feed_scope);
    formFolderScope = toArray(tag.folder_scope);
    formRegex = tag.regex_pattern || '';
    formRegexFlags = tag.regex_flags || '';
    formAiInclude = toArray(tag.ai_include_terms).join(', ');
    formAiExclude = toArray(tag.ai_exclude_terms).join(', ');
    formAiThreshold = tag.ai_threshold || 0.65;
    formAiNegateThreshold = tag.ai_negate_threshold ?? null;
    formAiReinforcement = tag.ai_reinforcement_enabled === true || tag.ai_reinforcement_enabled === 1;
    const layers = (tag.enabled_layers || '').split(',').filter(Boolean);
    formLayers = { manual: true, feed: layers.includes('feed'), folder: layers.includes('folder'), regex: layers.includes('regex'), ai: layers.includes('ai') };
    showForm = true;
    saveError = '';
  }

  function parseTerms(str: string): string[] {
    return str.split(',').map(s => s.trim()).filter(Boolean);
  }

  function getEnabledLayers(): string {
    return Object.entries(formLayers).filter(([, v]) => v).map(([k]) => k).join(',');
  }

  function toggleFeedScope(sha256: string) {
    formFeedScope = formFeedScope.includes(sha256)
      ? formFeedScope.filter(s => s !== sha256)
      : [...formFeedScope, sha256];
  }

  function toggleFolderScope(id: string) {
    formFolderScope = formFolderScope.includes(id)
      ? formFolderScope.filter(s => s !== id)
      : [...formFolderScope, id];
  }

  async function saveTag() {
    if (!formName.trim()) { saveError = get(t)('tags.nameRequired'); return; }
    saving = true;
    saveError = '';

    const body: any = {
      name: formName.trim(),
      color: formColor,
      feed_scope: formLayers.feed && formFeedScope.length > 0 ? formFeedScope : null,
      folder_scope: formLayers.folder && formFolderScope.length > 0 ? formFolderScope : null,
      regex_pattern: formRegex || null,
      regex_flags: formRegexFlags || null,
        ai_include_terms: formLayers.ai ? parseTerms(formAiInclude) : null,
        ai_exclude_terms: formLayers.ai ? parseTerms(formAiExclude) : null,
        ai_threshold: formAiThreshold,
        ai_negate_threshold: formLayers.ai ? formAiNegateThreshold : null,
        ai_reinforcement_enabled: formLayers.ai ? formAiReinforcement : true,
        enabled_layers: getEnabledLayers().split(','),
    };

    try {
      const url = editingTag ? `/api/tags/${editingTag.id}` : '/api/tags';
      const method = editingTag ? 'PUT' : 'POST';
      const res = await apiFetch(url, {
        method,
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) {
        saveError = data.detail || `Error ${res.status}`;
        return;
      }
      showForm = false;
      resetForm();
      await loadTags();
    } catch (err: any) {
      saveError = err.message;
    } finally {
      saving = false;
    }
  }

  async function confirmDelete(id: number) {
    deleteConfirmId = id;
  }

  async function doDelete() {
    if (deleteConfirmId === null) return;
    const id = deleteConfirmId;
    deleteConfirmId = null;
    try {
      const res = await apiFetch(`/api/tags/${id}`, { method: 'DELETE', credentials: 'include' });
      if (!res.ok) throw new Error(`Error ${res.status}`);
      tags = tags.filter(t => t.id !== id);
    } catch (err) {
      console.error('Failed to delete tag:', err);
    }
  }

  async function triggerEvaluation() {
    evaluating = true;
    try {
      const res = await apiFetch('/api/tags/evaluate', { method: 'POST', credentials: 'include' });
      if (!res.ok) throw new Error(`Error ${res.status}`);
    } catch (err) {
      console.error('Failed to trigger evaluation:', err);
    } finally {
      setTimeout(() => { evaluating = false; }, 2000);
    }
  }

  function layerIcons(tag: SmartTag): string {
    const layers = (tag.enabled_layers || '').split(',').filter(Boolean);
    const icons: Record<string, string> = { feed: 'F', folder: 'D', regex: 'R', ai: 'A', manual: 'M' };
    return layers.map(l => icons[l] || l).join(' ');
  }
</script>

<div class="tab-panel">
	<div class="tags-header">
		<Tag size={18} class="tags-icon" />
		<div>
			<h2 class="section-title">{$t('tags.title')}</h2>
			<p class="section-desc tight">{$t('tags.subtitle')}</p>
		</div>
	</div>

	<div class="tags-actions">
		<button class="action-btn accent" use:ripple onclick={openCreate}>
			<Plus size={14} />
			<span>{$t('tags.createTag')}</span>
		</button>
		<button class="action-btn" use:ripple onclick={triggerEvaluation} disabled={evaluating}>
			{#if evaluating}<span class="spinner"></span>
			{:else}<RefreshCw size={14} />{/if}
			<span>{$t('tags.evaluateNow')}</span>
		</button>
	</div>

	{#if loading}
		<div class="loading-state"><span class="spinner"></span></div>
	{:else if tags.length === 0 && !showForm}
		<div class="empty-state">
			<Tag size={32} class="empty-icon" />
			<p>{$t('tags.noTags')}</p>
		</div>
	{:else}
		<div class="tags-list">
			{#each tags as tag (tag.id)}
  <div class="tag-item" role="button" tabindex={0}>
          <div class="tag-left">
            <span class="tag-dot" style="background: {tag.color || '#3b82f6'}"></span>
            <span class="tag-name">{tag.name}</span>
            <span class="tag-layers">{layerIcons(tag)}</span>
            {#if tag.centroid_manual_count > 0}
              <span class="tag-reinforcement" title={$t('tags.reinforcementTooltip', { count: tag.centroid_manual_count })}>
                {tag.centroid_manual_count}
              </span>
            {/if}
          </div>
      <div class="tag-right">
        <button class="tag-edit" onclick={(e) => { e.stopPropagation(); openEdit(tag); }} aria-label={$t('tags.edit')}>
          <Pencil size={14} />
        </button>
        <button class="tag-delete" onclick={(e) => { e.stopPropagation(); confirmDelete(tag.id); }} aria-label={$t('tags.delete')}>
          <Trash2 size={14} />
        </button>
      </div>
				</div>
			{/each}
		</div>
	{/if}

	{#if showForm}
		<div class="form-overlay" onclick={() => { showForm = false; resetForm(); }}>
<div class="form-card" onclick={(e) => e.stopPropagation()}>
  <div class="form-header">
					<h3>{editingTag ? $t('tags.editTag') : $t('tags.createTag')}</h3>
					<button class="close-btn" onclick={() => { showForm = false; resetForm(); }}><X size={18} /></button>
				</div>

				<div class="form-body">
					<label class="form-label">
						<span>{$t('tags.nameLabel')}</span>
						<input type="text" bind:value={formName} placeholder={$t('tags.namePlaceholder')} class="form-input" />
					</label>

					<label class="form-label">
						<span>{$t('tags.colorLabel')}</span>
						<input type="color" bind:value={formColor} class="color-input" />
					</label>

					<div class="section-divider"></div>
					<p class="divider-label">{$t('tags.layersLabel')}</p>

					<div class="layer-toggles">
						{#each ['feed', 'folder', 'regex', 'ai'] as layer}
							<label class="layer-toggle">
								<input type="checkbox" bind:checked={formLayers[layer]} />
								<span class="layer-name">{$t(`tags.layer_${layer}`)}</span>
							</label>
						{/each}
					</div>

        {#if formLayers.feed}
          <div class="layer-section">
            <label class="form-label">
              <span>{$t('tags.feedScope')}</span>
            </label>
            <div class="scope-list">
              {#each feeds as f (f.feed_sha256)}
                <label class="scope-item">
                  <input type="checkbox" checked={formFeedScope.includes(f.feed_sha256)} onchange={() => toggleFeedScope(f.feed_sha256)} />
                  <span class="scope-name">{f.feed_title}</span>
                </label>
              {/each}
              {#if feeds.length === 0}<p class="scope-empty">No feeds found.</p>{/if}
            </div>
          </div>
        {/if}

        {#if formLayers.folder}
          <div class="layer-section">
            <label class="form-label">
              <span>{$t('tags.folderScope')}</span>
            </label>
            <div class="scope-list">
              {#each folders as f (f.id)}
                <label class="scope-item">
                  <input type="checkbox" checked={formFolderScope.includes(f.id)} onchange={() => toggleFolderScope(f.id)} />
                  <span class="scope-name">{f.name}</span>
                </label>
              {/each}
              {#if folders.length === 0}<p class="scope-empty">No folders found.</p>{/if}
            </div>
          </div>
        {/if}

        {#if formLayers.regex}
						<div class="layer-section">
							<label class="form-label">
								<span>{$t('tags.regexPattern')}</span>
								<input type="text" bind:value={formRegex} placeholder="e.g. AI|artificial.?intellig" class="form-input mono" />
							</label>
							<label class="form-label inline">
								<span>{$t('tags.regexFlags')}</span>
								<input type="text" bind:value={formRegexFlags} placeholder="i" class="form-input short" maxlength={4} />
							</label>
						</div>
					{/if}

					{#if formLayers.ai}
						<div class="layer-section">
							<label class="form-label">
								<span>{$t('tags.aiInclude')}</span>
								<input type="text" bind:value={formAiInclude} placeholder={$t('tags.aiIncludePlaceholder')} class="form-input" />
							</label>
							<label class="form-label">
								<span>{$t('tags.aiExclude')}</span>
								<input type="text" bind:value={formAiExclude} placeholder={$t('tags.aiExcludePlaceholder')} class="form-input" />
							</label>
                <label class="form-label">
                    <span>{$t('tags.aiThreshold')} ({Math.round(formAiThreshold * 100)}%)</span>
                    <input type="range" min="0.3" max="0.95" step="0.05" bind:value={formAiThreshold} class="threshold-slider" />
                </label>
                <label class="form-label">
                    <span>{$t('tags.aiNegateThreshold')} {#if formAiNegateThreshold != null}({Math.round(formAiNegateThreshold * 100)}%){/if}</span>
                    <div class="negate-row">
                        <input type="range" min="0.5" max="0.99" step="0.01" value={formAiNegateThreshold ?? 0.85} oninput={(e) => { formAiNegateThreshold = parseFloat(e.currentTarget.value); }} disabled={formAiNegateThreshold == null} class="threshold-slider" />
                        <label class="toggle-label">
                            <input type="checkbox" checked={formAiNegateThreshold != null} onchange={() => { formAiNegateThreshold = formAiNegateThreshold == null ? 0.85 : null; }} />
                            <span class="toggle-text">{formAiNegateThreshold != null ? $t('tags.on') : $t('tags.off')}</span>
                        </label>
                    </div>
                </label>
                <label class="form-label inline">
                    <span>{$t('tags.aiReinforcement')}</span>
                    <label class="toggle-label">
                        <input type="checkbox" bind:checked={formAiReinforcement} />
                        <span class="toggle-text">{formAiReinforcement ? $t('tags.on') : $t('tags.off')}</span>
                    </label>
                </label>
						</div>
					{/if}

					{#if saveError}<p class="error-text">{saveError}</p>{/if}

					<button class="action-btn accent full-width" use:ripple onclick={saveTag} disabled={saving}>
						{#if saving}<span class="spinner"></span>{/if}
						<span>{editingTag ? $t('tags.saveTag') : $t('tags.createTag')}</span>
					</button>
				</div>
			</div>
		</div>
	{/if}

{#if deleteConfirmId !== null}
  <div class="form-overlay" onclick={() => { deleteConfirmId = null; }}>
    <div class="form-card confirm-card" onclick={(e) => e.stopPropagation()}>
      <p class="confirm-text">{$t('tags.deleteConfirm')}</p>
      <div class="confirm-actions">
        <button class="action-btn" use:ripple onclick={() => { deleteConfirmId = null; }}>{$t('tags.cancel')}</button>
        <button class="action-btn danger" use:ripple onclick={doDelete}>{$t('tags.delete')}</button>
      </div>
    </div>
  </div>
{/if}
</div>

<style>
	.tab-panel { display: flex; flex-direction: column; gap: 16px; padding-top: 12px; }
	.section-title { font-size: 16px; font-weight: 700; color: var(--color-base-content); margin: 0; }
	.section-desc { font-size: 13px; line-height: 1.45; color: color-mix(in oklch, var(--color-base-content) 50%, transparent); margin: -8px 0 0; }
	.section-desc.tight { margin-top: 2px; }
	.section-divider { height: 1px; background: var(--color-base-300); margin: 12px 0; }
	.divider-label { font-size: 10px; text-transform: uppercase; letter-spacing: 0.06em; text-align: center; color: color-mix(in oklch, var(--color-base-content) 30%, transparent); margin: 0 0 8px; }
	.error-text { font-size: 12px; color: var(--color-error); margin-top: 4px; }

	.tags-header { display: flex; align-items: flex-start; gap: 12px; }
	.tags-icon { color: var(--color-accent); margin-top: 2px; flex-shrink: 0; }

	.tags-actions { display: flex; gap: 8px; flex-wrap: wrap; }
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
	.action-btn.accent { border-color: var(--color-accent); color: var(--color-accent); }
	.action-btn.accent:hover { background: color-mix(in oklch, var(--color-accent) 10%, transparent); }
	.action-btn:disabled { opacity: 0.6; cursor: not-allowed; }

	.spinner {
		width: 16px; height: 16px;
		border: 2px solid color-mix(in oklch, var(--color-base-content) 20%, transparent);
		border-top-color: var(--color-base-content); border-radius: 50%;
		animation: spin 0.6s linear infinite;
	}
	@keyframes spin { to { transform: rotate(360deg); } }

	.loading-state { display: flex; justify-content: center; padding: 32px; }

	.empty-state { display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 32px; text-align: center; }
	.empty-icon { color: color-mix(in oklch, var(--color-base-content) 25%, transparent); }
	.empty-state p { font-size: 13px; color: color-mix(in oklch, var(--color-base-content) 50%, transparent); }

	.tags-list { display: flex; flex-direction: column; border: 1px solid var(--color-base-300); border-radius: 16px; overflow: hidden; }
	.tag-item { display: flex; align-items: center; justify-content: space-between; padding: 10px 14px; border-bottom: 1px solid var(--color-base-300); cursor: pointer; transition: background 120ms ease; }
	.tag-item:last-child { border-bottom: none; }
	.tag-item:hover { background: color-mix(in oklch, var(--color-base-content) 4%, transparent); }
	.tag-left { display: flex; align-items: center; gap: 10px; min-width: 0; flex: 1; }
	.tag-dot { width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; }
	.tag-name { font-size: 13px; font-weight: 500; color: var(--color-base-content); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.tag-layers { font-size: 10px; font-weight: 700; letter-spacing: 0.04em; color: color-mix(in oklch, var(--color-base-content) 40%, transparent); flex-shrink: 0; }
.tag-reinforcement { font-size: 9px; font-weight: 700; line-height: 1; padding: 2px 5px; border-radius: 999px; background: color-mix(in oklch, var(--color-accent) 15%, transparent); color: var(--color-accent); flex-shrink: 0; cursor: default; }
.tag-right { display: flex; align-items: center; gap: 4px; flex-shrink: 0; }
.tag-edit { background: transparent; border: none; cursor: pointer; color: color-mix(in oklch, var(--color-base-content) 30%, transparent); transition: color 150ms; padding: 4px; }
.tag-edit:hover { color: var(--color-accent); }
.tag-delete { background: transparent; border: none; cursor: pointer; color: color-mix(in oklch, var(--color-base-content) 30%, transparent); transition: color 150ms; padding: 4px; }
.tag-delete:hover { color: var(--color-error); }

	.form-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 100; display: flex; align-items: center; justify-content: center; padding: 16px; }
	.form-card { background: var(--color-base-100); border-radius: 16px; width: 100%; max-width: 440px; max-height: 90vh; overflow-y: auto; box-shadow: 0 8px 32px rgba(0,0,0,0.2); }
	.form-header { display: flex; align-items: center; justify-content: space-between; padding: 16px 20px; border-bottom: 1px solid var(--color-base-300); }
	.form-header h3 { margin: 0; font-size: 15px; font-weight: 700; }
	.close-btn { background: transparent; border: none; cursor: pointer; color: color-mix(in oklch, var(--color-base-content) 50%, transparent); padding: 4px; border-radius: 6px; }
	.close-btn:hover { background: var(--color-base-200); color: var(--color-base-content); }

	.form-body { padding: 16px 20px 20px; display: flex; flex-direction: column; gap: 14px; }
	.form-label { display: flex; flex-direction: column; gap: 4px; font-size: 12px; font-weight: 600; color: color-mix(in oklch, var(--color-base-content) 60%, transparent); }
	.form-label.inline { flex-direction: row; align-items: center; gap: 8px; }
	.form-input {
		padding: 8px 12px; border: 1px solid var(--color-base-300); border-radius: 8px;
		background: var(--color-base-100); color: var(--color-base-content); font-size: 13px;
		outline: none; transition: border-color 150ms;
	}
	.form-input:focus { border-color: var(--color-accent); }
	.form-input.mono { font-family: monospace; }
	.form-input.short { width: 56px; text-align: center; }
	.color-input { width: 40px; height: 32px; border: 1px solid var(--color-base-300); border-radius: 6px; cursor: pointer; padding: 2px; background: transparent; }

	.layer-toggles { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
	.layer-toggle { display: flex; align-items: center; gap: 8px; font-size: 13px; cursor: pointer; color: var(--color-base-content); }
	.layer-toggle input { accent-color: var(--color-accent); }
	.layer-name { font-weight: 500; text-transform: capitalize; }

  .layer-section { display: flex; flex-direction: column; gap: 10px; padding-top: 4px; }

.negate-row { display: flex; align-items: center; gap: 10px; }
.negate-row .threshold-slider { flex: 1; }

.toggle-label { display: inline-flex; align-items: center; gap: 6px; cursor: pointer; font-size: 12px; font-weight: 500; color: var(--color-base-content); white-space: nowrap; }
.toggle-label input { accent-color: var(--color-accent); }
.toggle-text { font-size: 11px; color: color-mix(in oklch, var(--color-base-content) 50%, transparent); }

  .scope-list { display: flex; flex-direction: column; gap: 4px; max-height: 160px; overflow-y: auto; border: 1px solid var(--color-base-300); border-radius: 8px; padding: 8px; }
  .scope-item { display: flex; align-items: center; gap: 8px; font-size: 12px; cursor: pointer; color: var(--color-base-content); }
  .scope-item input { accent-color: var(--color-accent); }
  .scope-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .scope-empty { font-size: 12px; color: color-mix(in oklch, var(--color-base-content) 40%, transparent); margin: 0; }

  .confirm-card { max-width: 320px; padding: 24px; text-align: center; }
  .confirm-text { font-size: 14px; color: var(--color-base-content); margin: 0 0 20px; }
  .confirm-actions { display: flex; gap: 8px; justify-content: center; }
  .action-btn.danger { border-color: var(--color-error); color: var(--color-error); }
  .action-btn.danger:hover { background: color-mix(in oklch, var(--color-error) 10%, transparent); }

	.threshold-slider { -webkit-appearance: none; appearance: none; width: 100%; height: 4px; background: var(--color-base-300); border-radius: 999px; outline: none; cursor: pointer; }
	.threshold-slider::-webkit-slider-thumb { -webkit-appearance: none; appearance: none; width: 16px; height: 16px; border-radius: 50%; background: var(--color-accent); cursor: pointer; }
	.threshold-slider::-moz-range-thumb { width: 16px; height: 16px; border-radius: 50%; background: var(--color-accent); cursor: pointer; border: none; }
</style>
