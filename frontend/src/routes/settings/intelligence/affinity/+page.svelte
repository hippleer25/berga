<script lang="ts">
	import { onMount } from 'svelte';
	import Sparkles from '@lucide/svelte/icons/sparkles';
	import Search from '@lucide/svelte/icons/search';
	import ThumbsUp from '@lucide/svelte/icons/thumbs-up';
	import ThumbsDown from '@lucide/svelte/icons/thumbs-down';
	import Plus from '@lucide/svelte/icons/plus';
	import Minus from '@lucide/svelte/icons/minus';
	import ListOrdered from '@lucide/svelte/icons/list-ordered';
	import X from '@lucide/svelte/icons/x';
	import RotateCcw from '@lucide/svelte/icons/rotate-ccw';
	import { t } from 'svelte-i18n';
	import { get } from 'svelte/store';
  import { ripple } from '$lib/actions/ripple';
  import { apiFetch } from '$lib/api';

	let term = $state('');

	type AnalyzeStatus = 'idle' | 'loading' | 'done' | 'error';
	type BoostStatus = 'idle' | 'loading' | 'success' | 'error';

	let analyzeStatus = $state<AnalyzeStatus>('idle');
	let analyzeError = $state('');
	let boostStatus = $state<BoostStatus>('idle');
	let boostError = $state('');

	interface AffinityResult {
		term: string;
		affinity: number;
		sim_pos: number;
		sim_neg: number;
		boost_pos: number;
		boost_neg: number;
	}
	let result = $state<AffinityResult | null>(null);

	interface HistoryEntry extends AffinityResult {
		boostedPositive: boolean;
		boostedNegative: boolean;
	}
	let history = $state<HistoryEntry[]>([]);

	interface RankedTerm {
		term: string;
		affinity: number;
		sim_pos: number;
		sim_neg: number;
	}
	let ranked = $state<RankedTerm[]>([]);
	let rankedStatus = $state<'idle' | 'loading' | 'done'>('idle');

	onMount(() => {
		const stored = localStorage.getItem('affinity-history');
		if (stored) {
			try { history = JSON.parse(stored); } catch { history = []; }
		}
		loadRanking();
	});

	function persistHistory() {
		const capped = history.slice(0, 50);
		history = capped;
		localStorage.setItem('affinity-history', JSON.stringify(capped));
	}

	function affinityLabel(score: number): { text: string; color: string } {
		if (score >= 0.82) return { text: get(t)('affinity.veryHigh'), color: 'var(--color-success)' };
		if (score >= 0.65) return { text: get(t)('affinity.high'), color: 'var(--color-success)' };
		if (score >= 0.50) return { text: get(t)('affinity.moderate'), color: 'var(--color-warning)' };
		if (score >= 0.35) return { text: get(t)('affinity.low'), color: 'var(--color-error)' };
		return { text: get(t)('affinity.veryLow'), color: 'var(--color-error)' };
	}

	function pct(score: number) { return Math.round(score * 100); }

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
			syncHistory(result);
		} catch (err: any) {
			analyzeError = err.message;
			analyzeStatus = 'error';
		}
	}

	function syncHistory(entry: AffinityResult) {
		const existing = history.findIndex(h => h.term === entry.term);
		if (existing >= 0) {
			history[existing] = {
				...history[existing],
				...entry,
				boostedPositive: history[existing].boostedPositive || entry.boost_pos > 0,
				boostedNegative: history[existing].boostedNegative || entry.boost_neg > 0,
			};
			history = [...history];
		} else {
			history = [{ ...entry, boostedPositive: entry.boost_pos > 0, boostedNegative: entry.boost_neg > 0 }, ...history];
		}
		persistHistory();
	}

	async function adjustBoost(direction: 'positive' | 'negative', delta: number) {
		if (!result) return;
		boostStatus = 'loading';
		boostError = '';
		try {
			const res = await apiFetch('/api/affinity/boost', {
				method: 'POST',
				credentials: 'include',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ term: result.term, direction, strength: delta }),
			});
			const data = await res.json();
			if (!res.ok) throw new Error(data.error || `${get(t)('affinity.errorStatus')} ${res.status}`);
			const weight = data.weight ?? 0;
			result = direction === 'positive'
				? { ...result, boost_pos: weight }
				: { ...result, boost_neg: weight };
			syncHistory(result);
			boostStatus = 'idle';
			loadRanking();
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
		loadRanking();
	}

	async function loadRanking() {
		rankedStatus = 'loading';
		try {
			const res = await apiFetch('/api/affinity/terms?limit=10', { credentials: 'include' });
			if (!res.ok) throw new Error();
			const data = await res.json();
			ranked = (data.terms ?? []) as RankedTerm[];
			rankedStatus = 'done';
		} catch {
			ranked = [];
			rankedStatus = 'done';
		}
	}

	let resetConfirm = $state(false);
	let resetStatus = $state<'idle' | 'busy' | 'error'>('idle');
	let resetError = $state('');

	async function resetAllAffinity() {
		resetStatus = 'busy';
		resetError = '';
		try {
			const res = await apiFetch('/api/affinity/reset', {
				method: 'POST',
				credentials: 'include',
			});
			const data = await res.json();
			if (!res.ok) throw new Error(data.error || `${get(t)('affinity.errorStatus')} ${res.status}`);
			resetConfirm = false;
			history = [];
			localStorage.removeItem('affinity-history');
			if (result) {
				result = { ...result, boost_pos: 0, boost_neg: 0 };
			}
			await loadRanking();
			resetStatus = 'idle';
		} catch (err: any) {
			resetError = err.message;
			resetStatus = 'error';
			setTimeout(() => (resetStatus = 'idle'), 4000);
		}
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
					<div class="gauge-fill" class:fill-high={result.affinity >= 0.65} class:fill-moderate={result.affinity >= 0.50 && result.affinity < 0.65} class:fill-low={result.affinity < 0.50} style="width: {pct(result.affinity)}%"></div>
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

			<div class="boost-row positive">
				<div class="boost-info">
					<span class="boost-label"><ThumbsUp size={13} /> {$t('affinity.moreInterest')}</span>
					<span class="boost-weight">{pct(result.boost_pos)}%</span>
				</div>
				<div class="boost-actions">
					<button
						class="step-btn"
						onclick={() => adjustBoost('positive', -0.10)}
						aria-label="{$t('affinity.decreaseWeight')}"
						disabled={boostStatus === 'loading'}
					><Minus size={13} /></button>
					<button
						class="step-btn accent"
						onclick={() => adjustBoost('positive', 0.10)}
						aria-label="{$t('affinity.increaseWeight')}"
						disabled={boostStatus === 'loading'}
					><Plus size={13} /></button>
				</div>
			</div>

			<div class="boost-row negative">
				<div class="boost-info">
					<span class="boost-label"><ThumbsDown size={13} /> {$t('affinity.lessInterest')}</span>
					<span class="boost-weight">{pct(result.boost_neg)}%</span>
				</div>
				<div class="boost-actions">
					<button
						class="step-btn"
						onclick={() => adjustBoost('negative', -0.10)}
						aria-label="{$t('affinity.decreaseWeight')}"
						disabled={boostStatus === 'loading'}
					><Minus size={13} /></button>
					<button
						class="step-btn danger"
						onclick={() => adjustBoost('negative', 0.10)}
						aria-label="{$t('affinity.increaseWeight')}"
						disabled={boostStatus === 'loading'}
					><Plus size={13} /></button>
				</div>
			</div>
			{#if boostStatus === 'error'}<p class="error-text">{boostError}</p>{/if}
		</div>
	{/if}

	{#if rankedStatus === 'done' && ranked.length > 0}
		<div class="ranking-section">
			<div class="ranking-header">
				<ListOrdered size={15} class="ranking-icon" />
				<p class="history-title">{$t('affinity.rankingTitle')}</p>
			</div>
			<div class="history-list">
				{#each ranked as entry, i (entry.term)}
					{@const lbl = affinityLabel(entry.affinity)}
					<div class="history-item">
						<div class="history-left">
							<span class="ranking-pos">{i + 1}</span>
							<button class="history-term" onclick={() => { term = entry.term; analyze(); }}>
								{entry.term}
							</button>
						</div>
						<div class="history-right">
							<div class="ranking-gauge">
								<div
									class="ranking-gauge-fill"
									class:fill-high={entry.affinity >= 0.65}
									class:fill-moderate={entry.affinity >= 0.50 && entry.affinity < 0.65}
									class:fill-low={entry.affinity < 0.50}
									style="width: {pct(entry.affinity)}%"
								></div>
							</div>
							<span class="history-score affinity-{lbl.text.toLowerCase().replace(' ', '-')}">{pct(entry.affinity)}%</span>
						</div>
					</div>
				{/each}
			</div>
		</div>
	{:else if rankedStatus === 'done' && ranked.length === 0}
		<p class="ranking-empty">{$t('affinity.rankingEmpty')}</p>
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

	{#if history.length > 0 || ranked.length > 0}
		<div class="reset-section">
			<button class="action-btn danger" use:ripple onclick={() => (resetConfirm = true)} disabled={resetStatus === 'busy'}>
				<RotateCcw size={14} />
				<span>{$t('affinity.resetAll')}</span>
			</button>
			{#if resetStatus === 'error'}<p class="error-text">{resetError}</p>{/if}
			{#if resetConfirm}
				<div class="confirm-card">
					<p class="confirm-text">{$t('affinity.resetConfirm')}</p>
					<div class="confirm-actions">
						<button class="action-btn" use:ripple onclick={() => (resetConfirm = false)} disabled={resetStatus === 'busy'}>
							{$t('affinity.resetCancel')}
						</button>
						<button class="action-btn danger" use:ripple onclick={resetAllAffinity} disabled={resetStatus === 'busy'}>
							{#if resetStatus === 'busy'}<span class="spinner"></span>{:else}<RotateCcw size={13} />{/if}
							<span>{$t('affinity.resetConfirmBtn')}</span>
						</button>
					</div>
				</div>
			{/if}
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
  border-radius: var(--ui-radius-sm);
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
	.affinity-input:focus,
	.affinity-input:focus-visible { outline: none !important; box-shadow: none !important; }
	.affinity-input::placeholder { color: color-mix(in oklch, var(--color-base-content) 35%, transparent); }
	.search-icon-sm { flex-shrink: 0; color: color-mix(in oklch, var(--color-base-content) 40%, transparent); }

.result-card {
  background: color-mix(in oklch, var(--color-base-200) 70%, transparent);
  border: 1px solid var(--color-base-300);
  border-radius: var(--ui-radius-lg);
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
	.gauge-track { width: 100%; background: var(--color-base-300); border-radius: var(--ui-radius-full); height: 8px; overflow: hidden; }
	.gauge-fill { height: 8px; border-radius: var(--ui-radius-full); transition: width 0.4s ease, background 0.3s ease; }
	.gauge-fill.fill-high { background: var(--color-success); }
	.gauge-fill.fill-moderate { background: var(--color-warning); }
	.gauge-fill.fill-low { background: var(--color-error); }
	.gauge-labels { display: flex; justify-content: space-between; font-size: 10px; color: color-mix(in oklch, var(--color-base-content) 35%, transparent); }
	.gauge-labels.tight { margin-top: 2px; }
	.gauge-center { font-weight: 600; }

	.score-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.score-box {
  background: color-mix(in oklch, var(--color-base-100) 80%, transparent);
  border-radius: var(--ui-radius-sm);
  padding: 8px 12px;
}
	.score-val { font-size: 14px; font-weight: 600; font-family: monospace; margin: 2px 0 0; }
	.score-val.positive { color: var(--color-success); }
	.score-val.negative { color: var(--color-error); }

	.divider-label { font-size: 10px; text-transform: uppercase; letter-spacing: 0.06em; text-align: center; color: color-mix(in oklch, var(--color-base-content) 30%, transparent); margin: 0; }

	.boost-row {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 12px;
		padding: 10px 12px;
		border: 1px solid var(--color-base-300);
		border-radius: var(--ui-radius-sm);
		background: color-mix(in oklch, var(--color-base-100) 80%, transparent);
	}
	.boost-info { display: flex; align-items: center; gap: 8px; min-width: 0; }
	.boost-label { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 600; color: var(--color-base-content); }
	.boost-row.positive .boost-label { color: var(--color-success); }
	.boost-row.negative .boost-label { color: var(--color-error); }
	.boost-weight { font-size: 12px; font-family: monospace; color: color-mix(in oklch, var(--color-base-content) 60%, transparent); }
	.boost-actions { display: flex; gap: 6px; flex-shrink: 0; }
	.step-btn {
		display: inline-flex; align-items: center; justify-content: center;
		width: 30px; height: 30px;
		border: 1px solid var(--ui-border-color, var(--color-base-300));
		border-radius: var(--ui-radius-sm);
		background: transparent;
		color: var(--color-base-content);
		cursor: pointer;
		transition: all var(--ui-dur-1, 130ms) var(--ui-ease, ease);
	}
	.step-btn:hover { background: var(--color-base-200); border-color: var(--color-base-content); }
	.step-btn:active { transform: scale(0.93); }
	.step-btn:disabled { opacity: 0.5; cursor: not-allowed; }
	.step-btn.accent { color: var(--color-success); }
	.step-btn.accent:hover { background: color-mix(in oklch, var(--color-success) 10%, transparent); border-color: var(--color-success); }
	.step-btn.danger { color: var(--color-error); }
	.step-btn.danger:hover { background: color-mix(in oklch, var(--color-error) 10%, transparent); border-color: var(--color-error); }

	.ranking-section { margin-top: 8px; }
	.ranking-header { display: flex; align-items: center; gap: 6px; margin-bottom: 8px; }
	.ranking-icon { color: var(--color-accent); flex-shrink: 0; }
	.ranking-header .history-title { margin: 0; }
	.ranking-pos {
		font-size: 10px;
		font-weight: 700;
		font-family: monospace;
		color: color-mix(in oklch, var(--color-base-content) 45%, transparent);
		width: 18px;
		text-align: right;
		flex-shrink: 0;
	}
	.ranking-gauge {
		width: 64px;
		height: 5px;
		background: var(--color-base-300);
		border-radius: var(--ui-radius-full);
		overflow: hidden;
	}
	.ranking-gauge-fill { height: 100%; border-radius: var(--ui-radius-full); transition: width 0.4s ease, background 0.3s ease; }
	.ranking-gauge-fill.fill-high { background: var(--color-success); }
	.ranking-gauge-fill.fill-moderate { background: var(--color-warning); }
	.ranking-gauge-fill.fill-low { background: var(--color-error); }
	.ranking-empty {
		font-size: 12px;
		text-align: center;
		color: color-mix(in oklch, var(--color-base-content) 45%, transparent);
		padding: 16px 0 4px;
		margin: 0;
	}

	.action-btn {
		display: inline-flex; align-items: center; justify-content: center; gap: 6px;
		padding: 10px 16px; border-radius: var(--ui-radius-sm); border: 1px solid var(--color-base-300);
		background: transparent; color: var(--color-base-content); cursor: pointer;
		font-size: 13px; font-weight: 600; transition: all 130ms ease;
		position: relative; overflow: hidden;
	}
	.action-btn:hover { background: var(--color-base-200); }
	.action-btn:active { transform: scale(0.97); }
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

	.history-section { margin-top: 24px; }
	.history-title { font-size: 12px; font-weight: 700; letter-spacing: 0.06em; opacity: 0.5; margin: 0 0 8px; }
.history-list {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--color-base-300);
  border-radius: var(--ui-radius-lg);
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
	.mini-badge { display: inline-flex; align-items: center; gap: 2px; font-size: 9px; font-weight: 700; padding: 1px 4px; border-radius: var(--ui-radius-xs); flex-shrink: 0; }
	.mini-badge.positive { background: color-mix(in oklch, var(--color-success) 15%, transparent); color: var(--color-success); }
	.mini-badge.negative { background: color-mix(in oklch, var(--color-error) 15%, transparent); color: var(--color-error); }
	.history-right { display: flex; align-items: center; gap: 10px; flex-shrink: 0; margin-left: 8px; }
	.history-score { font-size: 11px; font-family: monospace; font-weight: 600; }
	.history-remove { background: transparent; border: none; cursor: pointer; color: color-mix(in oklch, var(--color-base-content) 30%, transparent); transition: color 150ms; padding: 2px; }
	.history-remove:hover { color: var(--color-error); }
	.history-remove:active { transform: scale(0.9); }

	.reset-section { display: flex; flex-direction: column; gap: 8px; margin-top: 8px; align-items: flex-start; }
	.action-btn.danger { border-color: var(--color-error); color: var(--color-error); }
	.action-btn.danger:hover { background: color-mix(in oklch, var(--color-error) 10%, transparent); }
	.confirm-card {
		width: 100%;
		background: var(--color-base-100);
		border: 1px solid var(--color-base-300);
		border-radius: var(--ui-radius-lg);
		padding: 16px;
		box-shadow: var(--ui-shadow-2, 0 4px 12px rgb(0 0 0 / 0.08));
	}
	.confirm-text { font-size: 13px; color: var(--color-base-content); margin: 0 0 12px; line-height: 1.5; }
	.confirm-actions { display: flex; gap: 8px; justify-content: flex-end; }
</style>
