<script lang="ts">
	import { onMount } from 'svelte';
	import Sparkles from '@lucide/svelte/icons/sparkles';
	import Search from '@lucide/svelte/icons/search';
	import ThumbsUp from '@lucide/svelte/icons/thumbs-up';
	import ThumbsDown from '@lucide/svelte/icons/thumbs-down';
	import X from '@lucide/svelte/icons/x';
	import { t } from 'svelte-i18n';
	import { get } from 'svelte/store';
 import { ripple } from '$lib/actions/ripple';
 import { apiFetch } from '$lib/api';

	let term = $state('');
	let strength = $state(0.25);

	type AnalyzeStatus = 'idle' | 'loading' | 'done' | 'error';
	type BoostStatus = 'idle' | 'loading' | 'success' | 'error';

	let analyzeStatus = $state<AnalyzeStatus>('idle');
	let analyzeError = $state('');
	let boostStatus = $state<BoostStatus>('idle');
	let boostDirection = $state<'positive' | 'negative' | null>(null);
	let boostError = $state('');

	interface AffinityResult {
		term: string;
		affinity: number;
		sim_pos: number;
		sim_neg: number;
	}
	let result = $state<AffinityResult | null>(null);

	interface HistoryEntry extends AffinityResult {
		boostedPositive: boolean;
		boostedNegative: boolean;
	}
	let history = $state<HistoryEntry[]>([]);

	onMount(() => {
		const stored = localStorage.getItem('affinity-history');
		if (stored) {
			try { history = JSON.parse(stored); } catch { history = []; }
		}
	});

	function persistHistory() {
		const capped = history.slice(0, 50);
		history = capped;
		localStorage.setItem('affinity-history', JSON.stringify(capped));
	}

	function affinityLabel(score: number): { text: string; color: string } {
		if (score >= 0.80) return { text: get(t)('affinity.veryHigh'), color: 'var(--color-success)' };
		if (score >= 0.62) return { text: get(t)('affinity.high'), color: 'var(--color-success)' };
		if (score >= 0.52) return { text: get(t)('affinity.moderate'), color: 'var(--color-warning)' };
		if (score >= 0.42) return { text: get(t)('affinity.low'), color: 'var(--color-error)' };
		return { text: get(t)('affinity.veryLow'), color: 'var(--color-error)' };
	}

	function pct(score: number) { return Math.round(score * 100); }

	function gaugeColor(score: number): string {
		if (score >= 0.62) return 'var(--color-success)';
		if (score >= 0.45) return 'var(--color-warning)';
		return 'var(--color-error)';
	}

	async function analyze() {
		const query = term.trim();
		if (!query) return;
		analyzeStatus = 'loading';
		analyzeError = '';
		result = null;
		boostStatus = 'idle';
		try {
			const res = await apiFetch(`/api/affinity/analyze?term=${encodeURIComponent(query)}`, { credentials: 'include' });
			const data = await res.json();
			if (!res.ok) throw new Error(data.error || `${get(t)('affinity.errorStatus')} ${res.status}`);
			result = data as AffinityResult;
			analyzeStatus = 'done';
		} catch (err: any) {
			analyzeError = err.message;
			analyzeStatus = 'error';
		}
	}

	async function boost(direction: 'positive' | 'negative') {
		if (!result) return;
		boostStatus = 'loading';
		boostDirection = direction;
		boostError = '';
		try {
const res = await apiFetch('/api/affinity/boost', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ term: result.term, direction, strength }),
  });
			const data = await res.json();
			if (!res.ok) throw new Error(data.error || `${get(t)('affinity.errorStatus')} ${res.status}`);
			boostStatus = 'success';
			const existing = history.findIndex(h => h.term === result!.term);
			if (existing >= 0) {
				history[existing] = {
					...history[existing],
					boostedPositive: history[existing].boostedPositive || direction === 'positive',
					boostedNegative: history[existing].boostedNegative || direction === 'negative',
				};
			} else {
				history = [{ ...result, boostedPositive: direction === 'positive', boostedNegative: direction === 'negative' }, ...history];
			}
			persistHistory();
			await analyze();
			boostStatus = 'idle';
		} catch (err: any) {
			boostError = err.message;
			boostStatus = 'error';
			setTimeout(() => (boostStatus = 'idle'), 4000);
		}
	}

  async function removeFromHistory(termKey: string) {
    const entry = history.find(h => h.term === termKey);
    if (entry) {
      const directions: Array<'positive' | 'negative'> = [];
      if (entry.boostedPositive) directions.push('positive');
      if (entry.boostedNegative) directions.push('negative');
      for (const dir of directions) {
        try {
await apiFetch('/api/affinity/boost', {
      method: 'DELETE',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ term: termKey, direction: dir }),
    });
        } catch { /* best-effort */ }
      }
    }
    history = history.filter(h => h.term !== termKey);
    persistHistory();
  }

	function handleKey(e: KeyboardEvent) {
		if (e.key === 'Enter') analyze();
	}
</script>

<div class="tab-panel">
	<div class="affinity-header">
		<Sparkles size={18} class="affinity-icon" />
		<div>
			<h2 class="section-title">{$t('affinity.title')}</h2>
			<p class="section-desc tight">{$t('affinity.subtitle')}</p>
		</div>
	</div>

	<div class="affinity-search-row">
		<div class="search-wrap-sm">
			<input
				type="text"
				class="affinity-input"
				placeholder="{$t('affinity.analyzePlaceholder')}"
				bind:value={term}
				onkeydown={handleKey}
				disabled={analyzeStatus === 'loading'}
			/>
			<Search size={16} class="search-icon-sm" />
		</div>
		<button class="action-btn accent" use:ripple onclick={analyze} disabled={analyzeStatus === 'loading' || !term.trim()}>
			{#if analyzeStatus === 'loading'}<span class="spinner"></span>
			{:else}<Search size={14} />{/if}
			<span>{$t('affinity.analyzeBtn')}</span>
		</button>
	</div>
	{#if analyzeStatus === 'error'}<p class="error-text">{analyzeError}</p>{/if}

	{#if result}
		{@const label = affinityLabel(result.affinity)}
		<div class="result-card">
			<div class="result-header">
				<div>
					<p class="result-label">{$t('affinity.termLabel')}</p>
					<p class="result-term">"{result.term}"</p>
				</div>
				<div class="result-right">
					<p class="result-label">{$t('affinity.affinityLabel')}</p>
					<p class="result-value affinity-{label.text.toLowerCase().replace(' ', '-')}">{label.text}</p>
				</div>
			</div>

			<div class="gauge-wrap">
				<div class="gauge-track">
					<div class="gauge-fill" class:fill-high={result.affinity >= 0.62} class:fill-moderate={result.affinity >= 0.45 && result.affinity < 0.62} class:fill-low={result.affinity < 0.45} style="width: {pct(result.affinity)}%"></div>
				</div>
				<div class="gauge-labels">
					<span>{$t('affinity.gaugeNone')}</span>
					<span class="gauge-center">{pct(result.affinity)}%</span>
					<span>{$t('affinity.gaugeTotal')}</span>
				</div>
			</div>

			<div class="score-grid">
				<div class="score-box">
					<p class="result-label">{$t('affinity.simPositive')}</p>
					<p class="score-val positive">{result.sim_pos.toFixed(3)}</p>
				</div>
				<div class="score-box">
					<p class="result-label">{$t('affinity.simNegative')}</p>
					<p class="score-val negative">{result.sim_neg.toFixed(3)}</p>
				</div>
			</div>

			<div class="section-divider"></div>
			<p class="divider-label">{$t('affinity.adjustProfile')}</p>

			<div class="slider-wrap">
				<div class="slider-header">
					<span class="slider-label">{$t('affinity.strengthLabel')}</span>
					<span class="slider-val">{Math.round(strength * 100)}%</span>
				</div>
				<input type="range" min="0.05" max="0.90" step="0.05" bind:value={strength} class="affinity-slider" />
				<div class="gauge-labels tight">
					<span>{$t('affinity.strengthSubtle')}</span>
					<span>{$t('affinity.strengthStrong')}</span>
				</div>
			</div>

			<div class="btn-group spaced">
				<button class="action-btn success full-width" use:ripple onclick={() => boost('positive')} disabled={boostStatus === 'loading'}>
					{#if boostStatus === 'loading' && boostDirection === 'positive'}<span class="spinner"></span>
					{:else}<ThumbsUp size={15} />{/if}
					<span>{$t('affinity.moreInterest')}</span>
				</button>
				<button class="action-btn danger full-width" use:ripple onclick={() => boost('negative')} disabled={boostStatus === 'loading'}>
					{#if boostStatus === 'loading' && boostDirection === 'negative'}<span class="spinner"></span>
					{:else}<ThumbsDown size={15} />{/if}
					<span>{$t('affinity.lessInterest')}</span>
				</button>
			</div>
			{#if boostStatus === 'error'}<p class="error-text">{boostError}</p>{/if}
		</div>
	{/if}

	{#if history.length > 0}
		<div class="history-section">
			<p class="history-title">{$t('affinity.historyTitle')}</p>
			<div class="history-list">
				{#each history as entry (entry.term)}
					{@const lbl = affinityLabel(entry.affinity)}
					<div class="history-item">
						<div class="history-left">
							<button class="history-term" onclick={() => { term = entry.term; analyze(); }}>
								{entry.term}
							</button>
							{#if entry.boostedPositive}
								<span class="mini-badge positive"><ThumbsUp size={8} /> +</span>
							{/if}
							{#if entry.boostedNegative}
								<span class="mini-badge negative"><ThumbsDown size={8} /> &minus;</span>
							{/if}
						</div>
						<div class="history-right">
							<span class="history-score affinity-{lbl.text.toLowerCase().replace(' ', '-')}">{pct(entry.affinity)}%</span>
							<button class="history-remove" onclick={() => removeFromHistory(entry.term)} aria-label="{$t('affinity.removeHistoryAria')}">
								<X size={13} />
							</button>
						</div>
					</div>
				{/each}
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
	.error-text { font-size: 12px; color: var(--color-error); margin-top: 4px; }

	.affinity-header { display: flex; align-items: flex-start; gap: 12px; }
	.affinity-icon { color: var(--color-accent); margin-top: 2px; flex-shrink: 0; }

	.affinity-search-row { display: flex; gap: 8px; align-items: center; }
.search-wrap-sm {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  background: color-mix(in oklch, var(--color-base-200) 50%, transparent);
  border: 1px solid var(--color-base-300);
  border-radius: 10px;
  padding: 0 12px;
  height: 40px;
  transition: background 180ms ease, border-color 180ms ease, box-shadow 180ms ease;
}
	.search-wrap-sm:focus-within { background: var(--color-base-100); border-color: var(--color-accent); box-shadow: 0 0 0 3px color-mix(in oklch, var(--color-accent) 15%, transparent); }
	.affinity-input {
		flex: 1; min-width: 0; background: transparent; border: none; outline: none;
		font-size: 14px; color: var(--color-base-content); line-height: 1;
		-webkit-appearance: none; appearance: none;
	}
	.affinity-input::placeholder { color: color-mix(in oklch, var(--color-base-content) 35%, transparent); }
	.search-icon-sm { flex-shrink: 0; color: color-mix(in oklch, var(--color-base-content) 40%, transparent); }

.result-card {
  background: color-mix(in oklch, var(--color-base-200) 70%, transparent);
  border: 1px solid var(--color-base-300);
  border-radius: 16px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
	.result-header { display: flex; justify-content: space-between; gap: 12px; }
	.result-right { text-align: right; }
	.result-label { font-size: 10px; text-transform: uppercase; letter-spacing: 0.06em; color: color-mix(in oklch, var(--color-base-content) 40%, transparent); margin: 0 0 4px; }
.result-term {
font-size: 16px;
font-weight: 600;
color: var(--color-base-content);
margin: 0;
font-family: var(--font-post-title);
  line-height: 1.4;
}
	.result-value { font-size: 16px; font-weight: 700; margin: 0; }
	.affinity-very-high, .affinity-high { color: var(--color-success); }
	.affinity-moderate { color: var(--color-warning); }
	.affinity-low, .affinity-very-low { color: var(--color-error); }

	.gauge-wrap { display: flex; flex-direction: column; gap: 4px; }
	.gauge-track { width: 100%; background: var(--color-base-300); border-radius: 999px; height: 8px; overflow: hidden; }
	.gauge-fill { height: 8px; border-radius: 999px; transition: width 0.4s ease, background 0.3s ease; }
	.gauge-fill.fill-high { background: var(--color-success); }
	.gauge-fill.fill-moderate { background: var(--color-warning); }
	.gauge-fill.fill-low { background: var(--color-error); }
	.gauge-labels { display: flex; justify-content: space-between; font-size: 10px; color: color-mix(in oklch, var(--color-base-content) 35%, transparent); }
	.gauge-labels.tight { margin-top: 2px; }
	.gauge-center { font-weight: 600; }

	.score-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.score-box {
  background: color-mix(in oklch, var(--color-base-100) 80%, transparent);
  border-radius: 10px;
  padding: 8px 12px;
}
	.score-val { font-size: 14px; font-weight: 600; font-family: monospace; margin: 2px 0 0; }
	.score-val.positive { color: var(--color-success); }
	.score-val.negative { color: var(--color-error); }

	.divider-label { font-size: 10px; text-transform: uppercase; letter-spacing: 0.06em; text-align: center; color: color-mix(in oklch, var(--color-base-content) 30%, transparent); margin: 0; }

	.slider-wrap { display: flex; flex-direction: column; gap: 6px; }
	.slider-header { display: flex; justify-content: space-between; align-items: center; }
	.slider-label { font-size: 12px; color: color-mix(in oklch, var(--color-base-content) 60%, transparent); }
	.slider-val { font-size: 12px; font-family: monospace; color: color-mix(in oklch, var(--color-base-content) 60%, transparent); }
	.affinity-slider { -webkit-appearance: none; appearance: none; width: 100%; height: 4px; background: var(--color-base-300); border-radius: 999px; outline: none; cursor: pointer; }
	.affinity-slider::-webkit-slider-thumb { -webkit-appearance: none; appearance: none; width: 16px; height: 16px; border-radius: 50%; background: var(--color-accent); cursor: pointer; box-shadow: 0 1px 4px rgba(0,0,0,.2); }
	.affinity-slider::-moz-range-thumb { width: 16px; height: 16px; border-radius: 50%; background: var(--color-accent); cursor: pointer; border: none; box-shadow: 0 1px 4px rgba(0,0,0,.2); }

	.btn-group { display: flex; gap: 8px; }
	.btn-group.spaced { margin-top: 12px; }
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
	.action-btn.success { border-color: color-mix(in oklch, var(--color-success) 50%, transparent); color: var(--color-success); }
	.action-btn.success:hover { background: color-mix(in oklch, var(--color-success) 10%, transparent); }
	.action-btn.danger { border-color: color-mix(in oklch, var(--color-error) 50%, transparent); color: var(--color-error); }
	.action-btn.danger:hover { background: color-mix(in oklch, var(--color-error) 10%, transparent); }
	.action-btn:disabled { opacity: 0.6; cursor: not-allowed; }

	.spinner {
		width: 16px; height: 16px;
		border: 2px solid color-mix(in oklch, var(--color-base-content) 20%, transparent);
		border-top-color: var(--color-base-content); border-radius: 50%;
		animation: spin 0.6s linear infinite;
	}
	@keyframes spin { to { transform: rotate(360deg); } }

	.history-section { margin-top: 24px; }
	.history-title { font-size: 12px; font-weight: 700; letter-spacing: 0.06em; opacity: 0.5; margin: 0 0 8px; }
.history-list {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--color-base-300);
  border-radius: 16px;
  overflow: hidden;
}
.history-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border-bottom: 1px solid var(--color-base-300);
  background: transparent;
  transition: background 120ms ease;
}
	.history-item:last-child { border-bottom: none; }
.history-item:hover {
  background: color-mix(in oklch, var(--color-base-content) 4%, transparent);
}
.history-item:active {
  background: color-mix(in oklch, var(--color-base-content) 8%, transparent);
}
	.history-left { display: flex; align-items: center; gap: 8px; min-width: 0; flex: 1; }
	.history-term { font-size: 13px; font-weight: 500; color: var(--color-base-content); background: none; border: none; padding: 0; cursor: pointer; text-align: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.history-term:hover { text-decoration: underline; }
	.mini-badge { display: inline-flex; align-items: center; gap: 2px; font-size: 9px; font-weight: 700; padding: 1px 4px; border-radius: 4px; flex-shrink: 0; }
	.mini-badge.positive { background: color-mix(in oklch, var(--color-success) 15%, transparent); color: var(--color-success); }
	.mini-badge.negative { background: color-mix(in oklch, var(--color-error) 15%, transparent); color: var(--color-error); }
	.history-right { display: flex; align-items: center; gap: 10px; flex-shrink: 0; margin-left: 8px; }
	.history-score { font-size: 11px; font-family: monospace; font-weight: 600; }
	.history-remove { background: transparent; border: none; cursor: pointer; color: color-mix(in oklch, var(--color-base-content) 30%, transparent); transition: color 150ms; padding: 2px; }
	.history-remove:hover { color: var(--color-error); }
	.history-remove:active { transform: scale(0.9); }
</style>
