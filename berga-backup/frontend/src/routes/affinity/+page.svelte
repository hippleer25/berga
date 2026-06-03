<script lang="ts">
    import { onMount } from 'svelte';
    import ArrowLeft from '@lucide/svelte/icons/arrow-left';
    import Search from '@lucide/svelte/icons/search';
    import ThumbsUp from '@lucide/svelte/icons/thumbs-up';
    import ThumbsDown from '@lucide/svelte/icons/thumbs-down';
    import Sparkles from '@lucide/svelte/icons/sparkles';
    import X from '@lucide/svelte/icons/x';

    import { t } from 'svelte-i18n';
    import { get } from 'svelte/store'; // Necessário para as funções JS

    // ── State ──────────────────────────────────────────────────────────────────

    let term = $state('');
    let strength = $state(0.25);

    type AnalyzeStatus = 'idle' | 'loading' | 'done' | 'error';
    type BoostStatus   = 'idle' | 'loading' | 'success' | 'error';

    let analyzeStatus = $state<AnalyzeStatus>('idle');
    let analyzeError  = $state('');

    let boostStatus    = $state<BoostStatus>('idle');
    let boostDirection = $state<'positive' | 'negative' | null>(null);
    let boostError     = $state('');

    interface AffinityResult {
        term:     string;
        affinity: number;  // 0–1
        sim_pos:  number;
        sim_neg:  number;
    }

    let result = $state<AffinityResult | null>(null);

    // History of analysed terms (session only)
    interface HistoryEntry extends AffinityResult {
        boostedPositive: boolean;
        boostedNegative: boolean;
    }
    let history = $state<HistoryEntry[]>([]);

    // ── Helpers ────────────────────────────────────────────────────────────────

    /** Map 0-1 affinity to a human-readable label + colour class */
    function affinityLabel(score: number): { text: string; cls: string } {
        if (score >= 0.80) return { text: get(t)('affinity.veryHigh'),  cls: 'text-success' };
        if (score >= 0.62) return { text: get(t)('affinity.high'),      cls: 'text-success' };
        if (score >= 0.52) return { text: get(t)('affinity.moderate'),  cls: 'text-warning' };
        if (score >= 0.42) return { text: get(t)('affinity.low'),       cls: 'text-error'   };
        return                    { text: get(t)('affinity.veryLow'),   cls: 'text-error'    };
    }

    /** Percentage (0–100) for the gauge bar */
    function pct(score: number) { return Math.round(score * 100); }

    /** Colour class for the gauge fill */
    function gaugeClass(score: number): string {
        if (score >= 0.62) return 'bg-success';
        if (score >= 0.45) return 'bg-warning';
        return 'bg-error';
    }

    // ── API calls ──────────────────────────────────────────────────────────────

    async function analyze() {
        const query = term.trim();
        if (!query) return;

        analyzeStatus = 'loading';
        analyzeError  = '';
        result        = null;
        boostStatus   = 'idle';

        try {
            const res = await fetch(
                `/api/affinity/analyze?term=${encodeURIComponent(query)}`,
                { credentials: 'include' },
            );
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || `${get(t)('affinity.errorStatus')} ${res.status}`);

            result        = data as AffinityResult;
            analyzeStatus = 'done';
        } catch (err: any) {
            analyzeError  = err.message;
            analyzeStatus = 'error';
        }
    }

    async function boost(direction: 'positive' | 'negative') {
        if (!result) return;

        boostStatus    = 'loading';
        boostDirection = direction;
        boostError     = '';

        try {
            const res = await fetch('/api/affinity/boost', {
                method:      'POST',
                credentials: 'include',
                headers:     { 'Content-Type': 'application/json' },
                body: JSON.stringify({ term: result.term, direction, strength }),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || `${get(t)('affinity.errorStatus')} ${res.status}`);

            boostStatus = 'success';

            // Update history entry or prepend new one
            const existing = history.findIndex(h => h.term === result!.term);
            const entry: HistoryEntry = {
                ...(result as AffinityResult),
                boostedPositive: direction === 'positive',
                boostedNegative: direction === 'negative',
            };
            if (existing >= 0) {
                history[existing] = {
                    ...history[existing],
                    boostedPositive: history[existing].boostedPositive || direction === 'positive',
                    boostedNegative: history[existing].boostedNegative || direction === 'negative',
                };
            } else {
                history = [entry, ...history];
            }

            // Re-analyse so score reflects the boost immediately
            await analyze();
            boostStatus = 'idle';
        } catch (err: any) {
            boostError  = err.message;
            boostStatus = 'error';
        }
    }

    function removeFromHistory(t: string) {
        history = history.filter(h => h.term !== t);
    }

    function handleKey(e: KeyboardEvent) {
        if (e.key === 'Enter') analyze();
    }
</script>

<div class="min-h-screen flex items-center justify-center bg-base-200 px-6 py-10">
    <div class="w-full max-w-lg space-y-4">

        <!-- Card principal -->
        <div class="bg-base-100 border border-primary rounded-2xl shadow-lg overflow-hidden">
            <div class="px-10 py-10 max-w-md mx-auto space-y-6">

                <!-- Header -->
                <div class="space-y-1">
                    <div class="flex items-center gap-2">
                        <Sparkles size={22} class="text-primary" />
                        <h1 class="text-3xl font-semibold">{$t('affinity.title')}</h1>
                    </div>
                    <p class="text-sm text-base-content/50">
                        {$t('affinity.subtitle')}
                    </p>
                </div>

                <!-- Divider -->
                <div class="divider my-0"></div>

                <!-- Search input -->
                <div class="space-y-2">
                    <span class="font-medium block">{$t('affinity.analyzeLabel')}</span>
                    <div class="flex gap-2">
                        <input
                            type="text"
                            class="input input-bordered input-sm flex-1 border-[1.5px] rounded-xl"
                            placeholder="{$t('affinity.analyzePlaceholder')}"
                            bind:value={term}
                            onkeydown={handleKey}
                            disabled={analyzeStatus === 'loading'}
                        />
                        <button
                            class="btn btn-primary btn-sm gap-1.5 rounded-xl px-4
                                   {analyzeStatus === 'loading' ? 'btn-disabled' : ''}"
                            onclick={analyze}
                            disabled={analyzeStatus === 'loading' || !term.trim()}
                        >
                            {#if analyzeStatus === 'loading'}
                                <span class="loading loading-spinner loading-xs"></span>
                            {:else}
                                <Search size={14} />
                            {/if}
                            {$t('affinity.analyzeBtn')}
                        </button>
                    </div>
                    {#if analyzeStatus === 'error'}
                        <p class="text-sm text-error">{analyzeError}</p>
                    {/if}
                </div>

                <!-- Result card -->
                {#if result}
                    {@const label = affinityLabel(result.affinity)}
                    <div class="bg-base-200 rounded-xl p-5 space-y-4">

                        <!-- Term + score label -->
                        <div class="flex items-start justify-between gap-2">
                            <div>
                                <p class="text-xs text-base-content/40 uppercase tracking-widest mb-0.5">{$t('affinity.termLabel')}</p>
                                <p class="font-semibold text-lg leading-tight">"{result.term}"</p>
                            </div>
                            <div class="text-right">
                                <p class="text-xs text-base-content/40 uppercase tracking-widest mb-0.5">{$t('affinity.affinityLabel')}</p>
                                <p class="font-bold text-lg {label.cls}">{label.text}</p>
                            </div>
                        </div>

                        <!-- Gauge bar -->
                        <div class="space-y-1">
                            <div class="w-full bg-base-300 rounded-full h-3 overflow-hidden">
                                <div
                                    class="h-3 rounded-full transition-all duration-500 {gaugeClass(result.affinity)}"
                                    style="width: {pct(result.affinity)}%"
                                ></div>
                            </div>
                            <div class="flex justify-between text-[10px] text-base-content/30">
                                <span>{$t('affinity.gaugeNone')}</span>
                                <span>{pct(result.affinity)}%</span>
                                <span>{$t('affinity.gaugeTotal')}</span>
                            </div>
                        </div>

                        <!-- Raw scores -->
                        <div class="grid grid-cols-2 gap-2 text-sm">
                            <div class="bg-base-100 rounded-lg px-3 py-2">
                                <p class="text-[10px] text-base-content/40 uppercase tracking-widest">{$t('affinity.simPositive')}</p>
                                <p class="font-mono font-semibold text-success">{result.sim_pos.toFixed(3)}</p>
                            </div>
                            <div class="bg-base-100 rounded-lg px-3 py-2">
                                <p class="text-[10px] text-base-content/40 uppercase tracking-widest">{$t('affinity.simNegative')}</p>
                                <p class="font-mono font-semibold text-error">{result.sim_neg.toFixed(3)}</p>
                            </div>
                        </div>

                        <!-- Divider -->
                        <div class="divider my-0 text-xs text-base-content/30">{$t('affinity.adjustProfile')}</div>

                        <!-- Strength slider -->
                        <div class="space-y-1">
                            <div class="flex justify-between items-center">
                                <span class="text-xs text-base-content/50">{$t('affinity.strengthLabel')}</span>
                                <span class="text-xs font-mono text-base-content/60">{Math.round(strength * 100)}%</span>
                            </div>
                            <input
                                type="range"
                                min="0.05"
                                max="0.90"
                                step="0.05"
                                bind:value={strength}
                                class="range range-xs range-primary w-full"
                            />
                            <div class="flex justify-between text-[9px] text-base-content/25">
                                <span>{$t('affinity.strengthSubtle')}</span>
                                <span>{$t('affinity.strengthStrong')}</span>
                            </div>
                        </div>

                        <!-- Boost buttons -->
                        <div class="flex gap-2">
                            <button
                                class="btn btn-outline border-[1.5px] flex-1 gap-2 text-success border-success
                                       hover:bg-success hover:text-white hover:border-success
                                       {boostStatus === 'loading' && boostDirection === 'positive' ? 'btn-disabled' : ''}"
                                onclick={() => boost('positive')}
                                disabled={boostStatus === 'loading'}
                            >
                                {#if boostStatus === 'loading' && boostDirection === 'positive'}
                                    <span class="loading loading-spinner loading-xs"></span>
                                {:else}
                                    <ThumbsUp size={15} />
                                {/if}
                                {$t('affinity.moreInterest')}
                            </button>

                            <button
                                class="btn btn-outline border-[1.5px] flex-1 gap-2 text-error border-error
                                       hover:bg-error hover:text-white hover:border-error
                                       {boostStatus === 'loading' && boostDirection === 'negative' ? 'btn-disabled' : ''}"
                                onclick={() => boost('negative')}
                                disabled={boostStatus === 'loading'}
                            >
                                {#if boostStatus === 'loading' && boostDirection === 'negative'}
                                    <span class="loading loading-spinner loading-xs"></span>
                                {:else}
                                    <ThumbsDown size={15} />
                                {/if}
                                {$t('affinity.lessInterest')}
                            </button>
                        </div>

                        {#if boostStatus === 'error'}
                            <p class="text-sm text-error">{boostError}</p>
                        {/if}
                    </div>
                {/if}

                <!-- Back button -->
                <div class="flex justify-between items-center pt-2">
                    <button
                        class="btn btn-outline bg-base-200 border-[1.5px]"
                        onclick={() => window.location.href = '/settings/affinity'}
                    >
                        <ArrowLeft size={16} />
                        {$t('affinity.back')}
                    </button>
                </div>

            </div>
        </div>

        <!-- History card (session) -->
        {#if history.length > 0}
            <div class="bg-base-100 border border-base-300 rounded-2xl shadow-sm overflow-hidden">
                <div class="px-6 pt-5 pb-1">
                    <p class="font-medium text-sm text-base-content/60 uppercase tracking-widest">
                        {$t('affinity.historyTitle')}
                    </p>
                </div>
                <ul class="divide-y divide-base-200">
                    {#each history as entry (entry.term)}
                        {@const lbl = affinityLabel(entry.affinity)}
                        <li class="flex items-center justify-between px-6 py-3 gap-3 group">
                            <!-- Left: term + badges -->
                            <div class="flex items-center gap-2 min-w-0">
                                <button
                                    class="text-sm font-medium truncate hover:underline text-left"
                                    onclick={() => { term = entry.term; analyze(); }}
                                >
                                    {entry.term}
                                </button>
                                {#if entry.boostedPositive}
                                    <span class="badge badge-success badge-xs gap-0.5">
                                        <ThumbsUp size={9} /> +
                                    </span>
                                {/if}
                                {#if entry.boostedNegative}
                                    <span class="badge badge-error badge-xs gap-0.5">
                                        <ThumbsDown size={9} /> −
                                    </span>
                                {/if}
                            </div>

                            <!-- Right: score + remove -->
                            <div class="flex items-center gap-3 shrink-0">
                                <span class="text-xs font-mono {lbl.cls}">
                                    {pct(entry.affinity)}%
                                </span>
                                <button
                                    class="opacity-0 group-hover:opacity-60 hover:!opacity-100 transition-opacity"
                                    onclick={() => removeFromHistory(entry.term)}
                                    aria-label="{$t('affinity.removeHistoryAria')}"
                                >
                                    <X size={13} />
                                </button>
                            </div>
                        </li>
                    {/each}
                </ul>
            </div>
        {/if}

    </div>
</div>