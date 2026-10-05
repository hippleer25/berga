<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import HeartPulse from '@lucide/svelte/icons/heart-pulse';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import Wrench from '@lucide/svelte/icons/wrench';
	import UserMinus from '@lucide/svelte/icons/user-minus';
	import X from '@lucide/svelte/icons/x';
	import Check from '@lucide/svelte/icons/check';
	import Rss from '@lucide/svelte/icons/rss';
	import Tag from '@lucide/svelte/icons/tag';
	import { t, locale } from 'svelte-i18n';
	import { get } from 'svelte/store';
	import { ripple } from '$lib/actions/ripple';
	import { apiFetch } from '$lib/api';

	type Status = 'ok' | 'failing' | 'dead' | 'silent' | 'unknown';

	interface WeekdayTag {
		tag_id: number;
		name: string;
		color: string | null;
		counts: number[];
		total: number;
	}

	interface FeedStats {
		posts_4w: number | null;
		posts_per_week: number | null;
		weekday_counts: number[];
		weekday_by_tag: WeekdayTag[];
		weekly_trend: number[];
		avg_gap_hours: number | null;
		last_item_at: string | null;
		classified_auto: number | null;
		classified_manual: number | null;
		classified_pct: number | null;
		updated_at?: string | null;
	}

	interface MonitorFeed {
		feed_sha256: string;
		url: string;
		title: string;
		icon?: string | null;
		status: Status;
		last_error?: string | null;
		last_error_at?: string | null;
		consecutive_errors: number;
		last_success_at?: string | null;
		last_parsed_at?: string | null;
		last_http_status?: number | null;
		last_fetch_ms?: number | null;
		entries_count?: number | null;
		stats?: FeedStats | null;
	}

	interface FixCandidate {
		url: string;
		title: string;
		entries: number;
		http_status?: number;
		is_current?: boolean;
		last_title?: string;
		last_pub?: string | null;
	}

	interface FixData {
		feed_sha256: string;
		url: string;
		title: string;
		diagnosis: { code: string; reason: string; source: string };
		candidates: FixCandidate[];
	}

	interface TagCoverage {
		tag_id: number;
		name: string;
		color: string | null;
		manual_count: number;
		auto_count: number;
		total_count: number;
		auto_pct: number | null;
		avg_confidence: number | null;
	}

	let feeds = $state<MonitorFeed[]>([]);
	let summary = $state<Record<Status, number>>({ ok: 0, failing: 0, dead: 0, silent: 0, unknown: 0 });
	let loading = $state(true);
	let loadError = $state('');
	let hasSmartTags = $state(false);
	let refreshing = $state(false);
	let refreshPolls = 0;

	let recomputeStatus: 'idle' | 'loading' | 'success' | 'error' = $state('idle');
	let recomputeError = $state('');

	let retryingSha = $state<string | null>(null);
	let expandedSha = $state<string | null>(null);

	let unsubConfirm = $state<MonitorFeed | null>(null);
	let unsubBusy = $state<string | null>(null);
	let unsubError = $state('');

	// Fix flow
	let fixTarget = $state<MonitorFeed | null>(null);
	let fixPhase: 'loading' | 'pick' | 'applying' | 'done' | 'error' = $state('loading');
	let fixData = $state<FixData | null>(null);
	let fixError = $state('');
	let fixPick = $state('');
	let fixManualUrl = $state('');

	// Tag coverage
	let tags = $state<TagCoverage[] | null>(null);
	let tagsLoading = $state(true);
	let tagsError = $state('');

	const DAY_KEYS = ['dayMon', 'dayTue', 'dayWed', 'dayThu', 'dayFri', 'daySat', 'daySun'];

	let problems = $derived(feeds.filter((f) => f.status !== 'ok'));

	onMount(() => {
		load();
		loadTags();
		// Cross-link from feed error badges: /settings/feeds-health?feed=<sha>
		const sha = get(page).url.searchParams.get('feed');
		if (sha) expandedSha = sha;
	});

	async function load(silent = false) {
		if (!silent) loadError = '';
		try {
			const res = await apiFetch('/api/feed-monitor', { credentials: 'include' });
			const data = await res.json().catch(() => ({}));
			if (!res.ok) throw new Error(data.detail || get(t)('monitor.error'));
			feeds = data.feeds || [];
			summary = data.summary || summary;
			hasSmartTags = !!data.has_smart_tags;
			refreshing = !!data.refreshing;
			if (refreshing) scheduleRefreshPoll();
		} catch (err: any) {
			if (!silent) loadError = err.message || String(err);
		} finally {
			loading = false;
		}
	}

	function scheduleRefreshPoll() {
		if (refreshPolls >= 8) return;
		refreshPolls += 1;
		setTimeout(async () => {
			await load(true);
			if (refreshing && refreshPolls < 8) scheduleRefreshPoll();
		}, 4000);
	}

	async function loadTags() {
		tagsError = '';
		try {
			const res = await apiFetch('/api/feed-monitor/tag-coverage', { credentials: 'include' });
			const data = await res.json().catch(() => ({}));
			if (!res.ok) throw new Error(data.detail || get(t)('monitor.error'));
			tags = data.tags || [];
		} catch (err: any) {
			tagsError = err.message || String(err);
		} finally {
			tagsLoading = false;
		}
	}

	async function recompute() {
		recomputeStatus = 'loading';
		recomputeError = '';
		try {
			const res = await apiFetch('/api/feed-monitor/recompute', {
				method: 'POST',
				credentials: 'include',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({})
			});
			const data = await res.json().catch(() => ({}));
			if (!res.ok) throw new Error(data.detail || get(t)('monitor.error'));
			recomputeStatus = 'success';
			await load();
		} catch (err: any) {
			recomputeStatus = 'error';
			recomputeError = err.message || String(err);
		} finally {
			setTimeout(() => { recomputeStatus = 'idle'; }, 2500);
		}
	}

	async function retryNow(f: MonitorFeed) {
		retryingSha = f.feed_sha256;
		try {
			await apiFetch('/api/following_structure/', {
				method: 'POST',
				credentials: 'include',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ task: 'refresh_feed', feed: f.feed_sha256 })
			});
			// Parse runs in the background — give it a beat, then reload.
			await new Promise((r) => setTimeout(r, 2500));
			await load();
		} catch {
			// surfaced on next load via health fields
		} finally {
			retryingSha = null;
		}
	}

	async function confirmUnsubscribe(f: MonitorFeed) {
		const target = f;
		unsubConfirm = null;
		unsubBusy = target.feed_sha256;
		unsubError = '';
		try {
			await apiFetch('/api/feed-remove', {
				method: 'POST',
				credentials: 'include',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ url: target.url })
			});
			await Promise.all([load(), loadTags()]);
		} catch (err: any) {
			unsubError = err.message || String(err);
		} finally {
			unsubBusy = null;
		}
	}

	async function openFix(f: MonitorFeed) {
		fixTarget = f;
		fixPhase = 'loading';
		fixData = null;
		fixError = '';
		fixPick = '';
		fixManualUrl = '';
		try {
			const res = await apiFetch(`/api/feed-monitor/${f.feed_sha256}/fix/analyze`, {
				method: 'POST',
				credentials: 'include'
			});
			const data = await res.json().catch(() => ({}));
			if (!res.ok) throw new Error(data.detail || get(t)('monitor.error'));
			fixData = data;
			fixPhase = 'pick';
		} catch (err: any) {
			fixError = err.message || String(err);
			fixPhase = 'error';
		}
	}

	async function applyFix() {
		if (!fixTarget) return;
		const newUrl = (fixPick || fixManualUrl).trim();
		if (!newUrl) return;
		fixPhase = 'applying';
		fixError = '';
		try {
			const res = await apiFetch(`/api/feed-monitor/${fixTarget.feed_sha256}/fix/apply`, {
				method: 'POST',
				credentials: 'include',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ new_url: newUrl })
			});
			const data = await res.json().catch(() => ({}));
			if (!res.ok) throw new Error(data.detail || get(t)('monitor.error'));
			fixPhase = 'done';
			const unchanged = (data as any).unchanged === true;
			if (!unchanged) {
				await new Promise((r) => setTimeout(r, 1800));
				await Promise.all([load(), loadTags()]);
				closeFix();
			}
		} catch (err: any) {
			fixError = err.message || String(err);
			fixPhase = 'pick';
		}
	}

	function closeFix() {
		fixTarget = null;
		fixData = null;
		fixPhase = 'loading';
		fixError = '';
		fixPick = '';
		fixManualUrl = '';
	}

	function toggleExpand(f: MonitorFeed) {
		expandedSha = expandedSha === f.feed_sha256 ? null : f.feed_sha256;
	}

	function fmtDate(iso: string | null | undefined): string {
		if (!iso) return get(t)('monitor.never');
		try {
			return new Intl.DateTimeFormat(get(locale) || 'en', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(iso));
		} catch {
			return iso;
		}
	}

	function fmtMs(ms: number | null | undefined): string {
		if (ms == null) return '—';
		return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`;
	}

	function host(url: string): string {
		try {
			return new URL(url).host.replace(/^www\./, '');
		} catch {
			return url;
		}
	}

	function gaugeFillClass(p: number): string {
		if (p >= 62) return 'fill-high';
		if (p >= 45) return 'fill-moderate';
		return 'fill-low';
	}

	// ── Spider/radar geometry for the publishing-days chart ──────────────────
	// Size has margin so weekday labels never spill outside the SVG viewBox
	// (spilled labels were causing a stray horizontal scrollbar).
	const RADAR = { size: 216, cx: 108, cy: 108, r: 70, labelR: 84 };

	function radarPoint(i: number, r: number): [number, number] {
		const a = -Math.PI / 2 + (i * 2 * Math.PI) / 7;
		return [RADAR.cx + r * Math.cos(a), RADAR.cy + r * Math.sin(a)];
	}

	function radarRing(r: number): string {
		return Array.from({ length: 7 }, (_, i) => radarPoint(i, r).map((n) => n.toFixed(1)).join(',')).join(' ');
	}

	/** Closed polygon points through 7 radius-scaled values (axis order kept). */
	function radarPolygon(values: number[], max: number): string {
		return values
			.map((v, i) => {
				const rr = (Math.max(0, v) / max) * RADAR.r;
				const [x, y] = radarPoint(i, rr);
				return `${x.toFixed(1)},${y.toFixed(1)}`;
			})
			.join(' ');
	}

	interface RadarLayer { key: string; color: string; points: string; tag?: string; base?: boolean }
	interface RadarView {
		max: number;
		layers: RadarLayer[];
		legend: { name: string; color: string; total: number }[];
		distinctDays: number;
	}

	function radarView(f: MonitorFeed): RadarView {
		const totalsRaw = f.stats?.weekday_counts || [];
		const totals = Array.from({ length: 7 }, (_, d) => totalsRaw[d] || 0);
		const tags = f.stats?.weekday_by_tag || [];
		const max = Math.max(1, ...totals);
		const distinctDays = totals.filter((v) => v > 0).length;

		// Cumulative boundaries: boundaries[k][d] = count of the first k tags
		// on day d (tags are already sorted by total desc). Clamped to totals.
		const boundaries: number[][] = [Array(7).fill(0)];
		for (const tg of tags) {
			const prev = boundaries[boundaries.length - 1];
			boundaries.push(prev.map((v, d) => Math.min(totals[d], v + (tg.counts?.[d] || 0))));
		}
		const taggedLast = boundaries[boundaries.length - 1];

		// Painter's algorithm: paint the total polygon first, then each
		// cumulative tag polygon from outermost to innermost. The visible ring
		// between boundary[k-1] and boundary[k] then keeps tag k's colour.
		// Solid nonzero polygons (no even-odd inner loop) so a feed with zero
		// weekdays still renders a visible web instead of cancelling to empty.
		const layers: RadarLayer[] = [
			{ key: 'total', color: 'var(--radar-untagged)', points: radarPolygon(totals, max), base: true }
		];
		const legend: { name: string; color: string; total: number }[] = [];

		for (let k = tags.length; k >= 1; k--) {
			const tg = tags[k - 1];
			layers.push({
				key: `tag-${tg.tag_id}`,
				color: tg.color || 'var(--color-accent)',
				points: radarPolygon(boundaries[k], max),
				tag: tg.name
			});
			legend.push({ name: tg.name, color: tg.color || 'var(--color-accent)', total: tg.total });
		}
		if (legend.length && totals.some((v, d) => v - taggedLast[d] > 0)) {
			legend.push({ name: get(t)('monitor.radarOther'), color: 'var(--radar-untagged)', total: -1 });
		}
		return { max, layers, legend, distinctDays };
	}

	const statsUpdated = $derived.by(() => {
		const dates = feeds.map((f) => f.stats?.updated_at).filter(Boolean) as string[];
		return dates.length ? dates.sort().at(-1)! : null;
	});
</script>

<div class="tab-panel">
	<div class="tags-header">
		<HeartPulse size={18} class="header-icon" />
		<div>
			<h2 class="section-title">{$t('monitor.title')}</h2>
			<p class="section-desc tight">{$t('monitor.subtitle')}</p>
		</div>
	</div>

	{#if loading}
		<div class="loading-state"><span class="spinner"></span></div>
	{:else if loadError}
		<p class="error-text">{loadError}</p>
	{:else if feeds.length === 0}
		<div class="empty-state">
			<Rss size={32} class="empty-icon" />
			<p>{$t('monitor.noFeeds')}</p>
			<p class="empty-desc">{$t('monitor.noFeedsDesc')}</p>
		</div>
	{:else}
		<div class="summary-row">
			<span class="summary-chip ok"><span class="status-dot dot-ok"></span>{summary.ok} {$t('monitor.statusOk')}</span>
			<span class="summary-chip"><span class="status-dot dot-failing"></span>{summary.failing} {$t('monitor.statusFailing')}</span>
			<span class="summary-chip"><span class="status-dot dot-dead"></span>{summary.dead} {$t('monitor.statusDead')}</span>
			<span class="summary-chip"><span class="status-dot dot-silent"></span>{summary.silent} {$t('monitor.statusSilent')}</span>
		</div>
		<div class="tags-actions">
			<button class="action-btn" use:ripple onclick={recompute} disabled={recomputeStatus === 'loading'}>
				{#if recomputeStatus === 'loading'}
					<span class="spinner"></span>
					<span>{$t('monitor.recomputing')}</span>
				{:else if recomputeStatus === 'success'}
					<Check size={14} />
					<span>{$t('monitor.recomputed')}</span>
				{:else}
					<RefreshCw size={14} />
					<span>{$t('monitor.recompute')}</span>
				{/if}
			</button>
			{#if recomputeStatus === 'error'}
				<span class="error-text">{recomputeError}</span>
			{/if}
			{#if statsUpdated}
				<span class="stats-updated">{$t('monitor.statsUpdated', { values: { date: fmtDate(statsUpdated) } })}</span>
			{/if}
		</div>

		{#if refreshing}
			<div class="refresh-banner">
				<span class="spinner"></span>
				<span>{$t('monitor.computingStats')}</span>
			</div>
		{/if}

		<div class="section-block">
			<h3 class="section-divider-label">{$t('monitor.problemsTitle')}</h3>
			<p class="section-desc tight">{$t('monitor.problemsDesc')}</p>
		</div>

		{#if problems.length === 0}
			<div class="ok-banner">
				<Check size={16} />
				<div>
					<p>{$t('monitor.noProblems')}</p>
					<p class="banner-sub">{$t('monitor.noProblemsDesc')}</p>
				</div>
			</div>
		{:else}
			<div class="problems-list">
				{#each problems as f (f.feed_sha256)}
					<div class="problem-item">
						<div class="problem-head">
							<span class="status-dot {f.status === 'dead' ? 'dot-dead' : f.status === 'silent' ? 'dot-silent' : 'dot-failing'}"></span>
							{#if f.icon}
								<img src={f.icon} alt="" class="feed-favicon" />
							{:else}
								<span class="feed-favicon-fallback"><Rss size={13} /></span>
							{/if}
							<span class="feed-title">{f.title || f.url}</span>
							<span class="status-chip {f.status}">{$t('monitor.status' + f.status.charAt(0).toUpperCase() + f.status.slice(1))}</span>
						</div>
						{#if f.last_error}
							<p class="problem-error" title={f.last_error}>{$t('monitor.lastError')}: {f.last_error}</p>
						{:else if f.status === 'silent'}
							<p class="problem-error muted">{$t('monitor.statusSilent')} — {$t('monitor.lastPost')}: {fmtDate(f.stats?.last_item_at)}</p>
						{/if}
						<div class="problem-meta">
							{#if f.consecutive_errors}
								<span class="meta-chip warn">{$t('monitor.consecutiveErrors', { values: { count: f.consecutive_errors } })}</span>
							{/if}
							<span class="meta-chip">
								{$t('monitor.lastSuccess')}: {fmtDate(f.last_success_at ?? f.last_parsed_at)}
							</span>
							{#if f.last_http_status}
								<span class="meta-chip mono">{$t('monitor.fetchStats', { values: { status: f.last_http_status, ms: fmtMs(f.last_fetch_ms) } })}</span>
							{/if}
						</div>
						<div class="problem-actions">
							<button class="action-btn" use:ripple onclick={() => retryNow(f)} disabled={retryingSha === f.feed_sha256}>
								{#if retryingSha === f.feed_sha256}
									<span class="spinner"></span>
								{:else}
									<RefreshCw size={13} />
								{/if}
								<span>{$t('monitor.actions.retryNow')}</span>
							</button>
							<button class="action-btn accent" use:ripple onclick={() => openFix(f)}>
								<Wrench size={13} />
								<span>{$t('monitor.actions.fix')}</span>
							</button>
							<button class="action-btn danger" use:ripple onclick={() => { unsubConfirm = f; unsubError = ''; }}>
								<UserMinus size={13} />
								<span>{$t('monitor.actions.unsubscribe')}</span>
							</button>
						</div>
					</div>
				{/each}
			</div>
		{/if}

		<div class="section-block">
			<h3 class="section-divider-label">{$t('monitor.statsTitle')}</h3>
			<p class="section-desc tight">{$t('monitor.statsDesc')}</p>
		</div>

		<div class="feeds-list">
			{#each feeds as f (f.feed_sha256)}
				<button class="feed-row" use:ripple onclick={() => toggleExpand(f)}>
					<span class="status-dot {f.status === 'dead' ? 'dot-dead' : f.status === 'silent' ? 'dot-silent' : f.status === 'failing' ? 'dot-failing' : f.status === 'unknown' ? 'dot-unknown' : 'dot-ok'}"></span>
					{#if f.icon}
						<img src={f.icon} alt="" class="feed-favicon" />
					{:else}
						<span class="feed-favicon-fallback"><Rss size={13} /></span>
					{/if}
					<span class="feed-row-title">{f.title || f.url}</span>
					<span class="feed-row-action">
						{#if f.stats?.posts_per_week != null}
							<span class="feed-ppw">{$t('monitor.perWeek', { values: { count: f.stats.posts_per_week } })}</span>
						{/if}
						{#if expandedSha === f.feed_sha256}
							<ChevronDown size={15} />
						{:else}
							<ChevronRight size={15} />
						{/if}
					</span>
				</button>
				{#if expandedSha === f.feed_sha256}
					<div class="feed-detail">
						{#if f.stats}
							{@const view = radarView(f)}
							{@const trendMax = Math.max(1, ...(f.stats.weekly_trend || [0]))}
							<div class="detail-grid">
								<div class="detail-cell radar-cell">
									<p class="detail-label">{$t('monitor.weekdayTitle')}</p>
									<div class="radar-wrap">
										<svg class="radar" viewBox="0 0 {RADAR.size} {RADAR.size}" role="img" aria-label={$t('monitor.weekdayTitle')}>
											{#each view.layers as l (l.key)}
												<polygon
													class="radar-layer"
													class:radar-layer--base={l.base}
													points={l.points}
													fill={l.color}
												>
													<title>{l.tag ?? $t('monitor.radarOther')}</title>
												</polygon>
											{/each}
											{#each [0.25, 0.5, 0.75, 1] as frac}
												<polygon class="radar-ring" points={radarRing(RADAR.r * frac)} />
											{/each}
											{#each Array.from({ length: 7 }) as _, i}
												{@const p = radarPoint(i, RADAR.r)}
												<line class="radar-spoke" x1={RADAR.cx} y1={RADAR.cy} x2={p[0]} y2={p[1]} />
											{/each}
											{#each Array.from({ length: 7 }) as _, i}
												{@const lp = radarPoint(i, RADAR.labelR)}
												<text
													class="radar-label"
													x={lp[0]}
													y={lp[1]}
													text-anchor="middle"
													dominant-baseline="middle"
												>{$t('monitor.' + DAY_KEYS[i])}</text>
											{/each}
										</svg>
										<div class="radar-side">
											<p class="radar-max mono">{$t('monitor.perWeek', { values: { count: view.max } })}<span class="radar-max-unit"> {$t('monitor.peakDay')}</span></p>
											{#if view.legend.length > 0}
												<div class="radar-legend">
													{#each view.legend as lg, i (i)}
														<span class="radar-legend-item">
															<span class="radar-legend-dot" style="background: {lg.color}"></span>
															{lg.name}{#if lg.total >= 0}<span class="radar-legend-n mono">{lg.total}</span>{/if}
														</span>
													{/each}
												</div>
											{:else}
												<p class="radar-hint">{$t('monitor.radarNoTags')}</p>
											{/if}
											{#if view.distinctDays > 0 && view.distinctDays < 7}
												<p class="radar-history">{$t('monitor.radarHistory', { values: { days: view.distinctDays } })}</p>
											{/if}
										</div>
									</div>
								</div>
								<div class="detail-cell chart-cell">
									<p class="detail-label">
										{$t('monitor.trendTitle')}
										<span class="detail-label-peak mono">{$t('monitor.trendPeak', { values: { count: trendMax } })}</span>
									</p>
									<div class="trend-chart">
										<div class="trend-grid" aria-hidden="true">
											<span></span><span></span><span></span><span></span>
										</div>
										{#each (f.stats.weekly_trend || []) as count, i}
											<div class="trend-col" title={`${count}`}>
												<div class="trend-bar" style="height: {Math.max(count > 0 ? 4 : 0, Math.round((count / trendMax) * 100))}%"></div>
											</div>
										{/each}
									</div>
								</div>
								<div class="detail-cell">
									<p class="detail-label">{$t('monitor.postsPerWeek')}</p>
									<p class="detail-value mono">{f.stats.posts_per_week ?? '—'}</p>
									<p class="detail-sub">
										{#if f.stats.posts_4w != null}
											{$t('monitor.postsLast4w', { values: { count: f.stats.posts_4w } })}
										{:else}
											{$t('monitor.noData')}
										{/if}
									</p>
									{#if f.stats.avg_gap_hours != null}
										<p class="detail-sub">{$t('monitor.everyGap', { values: { hours: f.stats.avg_gap_hours } })}</p>
									{/if}
									{#if f.stats.last_item_at}
										<p class="detail-sub">{$t('monitor.lastPost')}: {fmtDate(f.stats.last_item_at)}</p>
									{/if}
								</div>
								<div class="detail-cell">
									<p class="detail-label">{$t('monitor.autoClassified')}</p>
									<div class="mini-gauge">
										<div class="gauge-track">
											<div
												class="gauge-fill {gaugeFillClass(f.stats.classified_pct ?? 0)}"
												style="width: {f.stats.classified_pct ?? 0}%"
											></div>
										</div>
										<span class="gauge-val mono">{f.stats.classified_pct ?? 0}%</span>
									</div>
									<p class="detail-sub">
										{$t('monitor.autoClassifiedHint', {
											values: { pct: f.stats.classified_pct ?? 0, manual: f.stats.classified_manual ?? 0 }
										})}
									</p>
								</div>
							</div>
						{:else}
							<p class="detail-sub no-data">{$t('monitor.noData')}</p>
						{/if}
					</div>
				{/if}
			{/each}
		</div>

		<div class="section-block">
			<h3 class="section-divider-label">{$t('monitor.tagCoverageTitle')}</h3>
			<p class="section-desc tight">{$t('monitor.tagCoverageDesc')}</p>
		</div>

		{#if tagsLoading}
			<div class="loading-state"><span class="spinner"></span></div>
		{:else if tagsError}
			<p class="error-text">{tagsError}</p>
		{:else if tags && tags.length === 0}
			<div class="tag-empty">
				<p class="detail-sub no-data">
					<Tag size={13} />
					{$t('monitor.tagCoverageEmpty')}
				</p>
				<p class="detail-sub subtle">{$t('monitor.tagCoverageCta')}</p>
				<button class="action-btn accent" use:ripple onclick={() => goto('/settings/tags')}>
					<Tag size={13} />
					<span>{$t('monitor.createTags')}</span>
				</button>
			</div>
		{:else}
			<div class="tag-table">
				{#each tags as tg (tg.tag_id)}
					<div class="tag-row">
						<span class="tag-dot" style="background: {tg.color || '#3b82f6'}"></span>
						<span class="tag-row-name">{tg.name}</span>
						<div class="tag-gauge">
							<div class="gauge-track">
								<div class="gauge-fill {gaugeFillClass(tg.auto_pct ?? 0)}" style="width: {tg.auto_pct ?? 0}%"></div>
							</div>
							<span class="gauge-val mono">{tg.auto_pct ?? 0}%</span>
						</div>
						<span class="tag-counts mono">{tg.auto_count}/{tg.total_count}</span>
						{#if tg.avg_confidence != null}
							<span class="tag-conf mono">{tg.avg_confidence}%</span>
						{:else}
							<span class="tag-conf muted">—</span>
						{/if}
					</div>
				{/each}
			</div>
		{/if}
	{/if}

	{#if unsubConfirm}
		<!-- svelte-ignore a11y_no_static_element_interactions, a11y_click_events_have_key_events -->
		<div class="form-overlay" onclick={() => { unsubConfirm = null; }}>
			<!-- svelte-ignore a11y_no_static_element_interactions, a11y_click_events_have_key_events -->
			<div class="form-card confirm-card" onclick={(e) => { e.stopPropagation(); }}>
				<p class="confirm-text">{$t('monitor.unsubscribeConfirm', { values: { title: unsubConfirm.title || unsubConfirm.url } })}</p>
				{#if unsubError}<p class="error-text">{unsubError}</p>{/if}
				<div class="confirm-actions">
					<button class="action-btn" use:ripple onclick={() => { unsubConfirm = null; }}>{$t('tags.cancel')}</button>
					<button class="action-btn danger" use:ripple onclick={() => confirmUnsubscribe(unsubConfirm!)} disabled={!!unsubBusy}>
						{#if unsubBusy}<span class="spinner"></span>{/if}
						<span>{$t('monitor.actions.unsubscribe')}</span>
					</button>
				</div>
			</div>
		</div>
	{/if}

	{#if fixTarget}
		<!-- svelte-ignore a11y_no_static_element_interactions, a11y_click_events_have_key_events -->
		<div class="form-overlay" onclick={closeFix}>
			<!-- svelte-ignore a11y_no_static_element_interactions, a11y_click_events_have_key_events -->
			<div class="form-card fix-card" onclick={(e) => { e.stopPropagation(); }}>
				<div class="form-header">
					<h3>{$t('monitor.fixTitle')}</h3>
					<button class="close-btn" onclick={closeFix}><X size={18} /></button>
				</div>

				<div class="form-body">
					<div class="fix-feed-line">
						{#if fixTarget.icon}
							<img src={fixTarget.icon} alt="" class="feed-favicon" />
						{/if}
						<span class="feed-title">{fixTarget.title || fixTarget.url}</span>
					</div>
					<div class="fix-current">
						<span class="fix-current-label">{$t('monitor.currentUrl')}</span>
						<span class="fix-current-url mono">{fixTarget.url}</span>
					</div>

					{#if fixPhase === 'loading' || (fixPhase === 'pick' && !fixData)}
						<div class="fix-diagnosis loading">
							<span class="spinner"></span>
							<span>{$t('monitor.diagnosing')}<br /><span class="fix-diagnosis-note">{$t('monitor.diagnosingHint')}</span></span>
						</div>
					{:else if fixData}
						<div class="fix-diagnosis">
							<p class="fix-diagnosis-title">{$t('monitor.diagnosis')} · {fixData.diagnosis.source === 'llm' ? $t('monitor.diagnosisSourceAi') : $t('monitor.diagnosisSourceRegex')}</p>
							<p class="fix-diagnosis-text">{$t('monitor.diag.' + fixData.diagnosis.code)}</p>
							{#if fixData.diagnosis.reason && fixData.diagnosis.source === 'llm'}
								<p class="fix-diagnosis-note">{fixData.diagnosis.reason}</p>
							{/if}
						</div>

						{#if fixData.candidates.length > 0}
							<p class="divider-label">{$t('monitor.candidates', { values: { count: fixData.candidates.length } })}</p>
							<div class="candidate-list">
								{#each fixData.candidates as cand, i (cand.url)}
									<label class="candidate-item" class:selected={fixPick === cand.url}>
										<input
											type="radio"
											name="fix-candidate"
											checked={fixPick === cand.url}
											onchange={() => { fixPick = cand.url; fixManualUrl = ''; }}
										/>
										<div class="candidate-info">
											<span class="candidate-head">
												<span class="candidate-title">{cand.title || host(cand.url)}</span>
												{#if i === 0 && !cand.is_current}<span class="candidate-tag best">{$t('monitor.candidateBest')}</span>{/if}
												{#if cand.is_current}<span class="candidate-tag current">{$t('monitor.candidateCurrent')}</span>{/if}
											</span>
											<span class="candidate-url mono">{cand.url}</span>
											<span class="candidate-desc">
												<span class="candidate-badge">{$t('monitor.candidateEntries', { values: { count: cand.entries } })}</span>
												{#if cand.last_pub}<span class="candidate-badge">{$t('monitor.candidateLastPost', { values: { date: cand.last_pub } })}</span>{/if}
											</span>
											{#if cand.last_title}
												<span class="candidate-last">“{cand.last_title}”</span>
											{/if}
										</div>
									</label>
								{/each}
							</div>
						{:else}
							<div class="no-candidates">
								<p class="detail-sub">{$t('monitor.noCandidates')}</p>
								<p class="detail-sub subtle">{$t('monitor.noCandidatesHint')}</p>
							</div>
						{/if}

						<label class="form-label">
							<span>{$t('monitor.candidateUrlLabel')}</span>
							<input
								type="url"
								class="form-input mono"
								placeholder="https://example.com/feed.xml"
								bind:value={fixManualUrl}
								oninput={() => { fixPick = ''; }}
							/>
						</label>
					{:else if fixPhase === 'done'}
						<div class="fix-diagnosis ok"><Check size={15} /> {$t('monitor.applied')}</div>
					{:else if fixPhase === 'error'}
						<p class="error-text">{fixError}</p>
					{/if}

					{#if fixError}<p class="error-text">{fixError}</p>{/if}

					{#if fixPhase === 'pick' || fixPhase === 'applying'}
						<button
							class="action-btn accent full-width"
							use:ripple
							onclick={applyFix}
							disabled={fixPhase === 'applying' || (!fixPick && !fixManualUrl.trim())}
						>
							{#if fixPhase === 'applying'}<span class="spinner"></span>{:else}<Check size={14} />{/if}
							<span>{fixPhase === 'applying' ? $t('monitor.applying') : $t('monitor.apply')}</span>
						</button>
					{/if}
				</div>
			</div>
		</div>
	{/if}
</div>

<style>
	.tab-panel { display: flex; flex-direction: column; gap: 16px; padding-top: 12px; --radar-untagged: color-mix(in oklch, var(--color-base-content) 45%, transparent); }
	.section-title { font-size: 16px; font-weight: 700; color: var(--color-base-content); margin: 0; }
	.section-desc { font-size: 13px; line-height: 1.45; color: color-mix(in oklch, var(--color-base-content) 50%, transparent); margin: -8px 0 0; }
	.section-desc.tight { margin-top: 2px; }
	.error-text { font-size: 12px; color: var(--color-error); margin-top: 4px; }

	.tags-header { display: flex; align-items: flex-start; gap: 12px; }
	.tags-header :global(.header-icon) { color: var(--color-accent); margin-top: 2px; flex-shrink: 0; }

	.section-block { margin-top: 8px; }
	.section-divider-label {
		font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em;
		color: color-mix(in oklch, var(--color-base-content) 45%, transparent); margin: 0 0 2px;
	}

	.spinner {
		width: 15px; height: 15px; flex-shrink: 0;
		border: 2px solid color-mix(in oklch, var(--color-base-content) 20%, transparent);
		border-top-color: currentColor; border-radius: 50%;
		animation: spin 0.6s linear infinite;
	}
	@keyframes spin { to { transform: rotate(360deg); } }

	.loading-state { display: flex; justify-content: center; padding: 32px; color: color-mix(in oklch, var(--color-base-content) 50%, transparent); }

	.empty-state { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 32px; text-align: center; }
	.empty-state :global(.empty-icon) { color: color-mix(in oklch, var(--color-base-content) 25%, transparent); }
	.empty-state p { font-size: 13px; color: color-mix(in oklch, var(--color-base-content) 50%, transparent); margin: 0; }
	.empty-desc { font-size: 12px; }

	.action-btn {
		display: inline-flex; align-items: center; justify-content: center; gap: 6px;
		padding: 9px 14px; border-radius: var(--ui-radius-sm); border: 1px solid var(--color-base-300);
		background: transparent; color: var(--color-base-content); cursor: pointer;
		font-size: 13px; font-weight: 600; transition: all 130ms ease;
		position: relative; overflow: hidden;
	}
	.action-btn:hover { background: var(--color-base-200); }
	.action-btn:active { transform: scale(0.97); }
	.action-btn.accent { border-color: var(--color-accent); color: var(--color-accent); }
	.action-btn.accent:hover { background: color-mix(in oklch, var(--color-accent) 10%, transparent); }
	.action-btn.danger { border-color: var(--color-error); color: var(--color-error); }
	.action-btn.danger:hover { background: color-mix(in oklch, var(--color-error) 10%, transparent); }
	.action-btn:disabled { opacity: 0.6; cursor: not-allowed; }
	.action-btn.full-width { width: 100%; }

	.tags-actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }

	/* summary chips */
	.summary-row { display: flex; gap: 8px; flex-wrap: wrap; }
	.summary-chip {
		display: inline-flex; align-items: center; gap: 7px;
		font-size: 12px; font-weight: 600; color: var(--color-base-content);
		padding: 6px 12px; border-radius: var(--ui-radius-full);
		background: color-mix(in oklch, var(--color-base-content) 5%, transparent);
		border: 1px solid var(--color-base-300);
	}
	.summary-chip.ok { color: var(--color-success); border-color: color-mix(in oklch, var(--color-success) 40%, transparent); }
	.status-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
	.dot-ok { background: var(--color-success); }
	.dot-failing { background: var(--color-warning); }
	.dot-dead { background: var(--color-error); }
	.dot-silent { background: color-mix(in oklch, var(--color-base-content) 45%, transparent); }
	.dot-unknown { background: color-mix(in oklch, var(--color-accent) 60%, transparent); }

	/* problems */
	.problems-list { display: flex; flex-direction: column; gap: 10px; }
	.problem-item {
		border: 1px solid color-mix(in oklch, var(--color-error) 25%, transparent);
		border-radius: var(--ui-radius-lg);
		padding: 12px 14px;
		display: flex; flex-direction: column; gap: 8px;
		background: color-mix(in oklch, var(--color-error) 4%, transparent);
	}
	.problem-head { display: flex; align-items: center; gap: 8px; min-width: 0; }
	.feed-title { font-size: 13px; font-weight: 600; color: var(--color-base-content); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.status-chip {
		font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em;
		padding: 2px 7px; border-radius: var(--ui-radius-full); flex-shrink: 0;
	}
	.status-chip.failing { background: color-mix(in oklch, var(--color-warning) 15%, transparent); color: var(--color-warning); }
	.status-chip.dead { background: color-mix(in oklch, var(--color-error) 15%, transparent); color: var(--color-error); }
	.status-chip.silent { background: color-mix(in oklch, var(--color-base-content) 10%, transparent); color: color-mix(in oklch, var(--color-base-content) 60%, transparent); }
	.status-chip.unknown { background: color-mix(in oklch, var(--color-accent) 15%, transparent); color: var(--color-accent); }
	.problem-error {
		font-size: 12px; color: var(--color-error); margin: 0;
		overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
	}
	.problem-error.muted { color: color-mix(in oklch, var(--color-base-content) 55%, transparent); }
	.problem-meta { display: flex; gap: 6px; flex-wrap: wrap; }
	.meta-chip {
		font-size: 10px; padding: 3px 8px; border-radius: var(--ui-radius-full);
		background: color-mix(in oklch, var(--color-base-content) 7%, transparent);
		color: color-mix(in oklch, var(--color-base-content) 60%, transparent);
	}
	.meta-chip.warn { background: color-mix(in oklch, var(--color-warning) 15%, transparent); color: var(--color-warning); }
	.meta-chip.mono { font-family: monospace; }
	.problem-actions { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 2px; }

	.problem-item :global(.action-btn) { padding: 7px 12px; font-size: 12px; }

	.ok-banner {
		display: flex; align-items: center; gap: 10px;
		border: 1px solid color-mix(in oklch, var(--color-success) 30%, transparent);
		background: color-mix(in oklch, var(--color-success) 8%, transparent);
		border-radius: var(--ui-radius-lg); padding: 14px 16px;
		color: var(--color-success);
	}
	.ok-banner p { margin: 0; font-size: 13px; font-weight: 600; }
	.banner-sub { font-size: 12px !important; font-weight: 400 !important; color: color-mix(in oklch, var(--color-base-content) 50%, transparent); }

	/* all feeds */
	.feeds-list {
		display: flex; flex-direction: column;
		border: 1px solid var(--color-base-300); border-radius: var(--ui-radius-lg); overflow: hidden;
	}
	.feed-row {
		display: flex; align-items: center; gap: 10px; width: 100%;
		padding: 11px 14px; border-bottom: 1px solid var(--color-base-300);
		background: transparent; border-left: none; border-right: none; border-top: none;
		cursor: pointer; text-align: left; font-family: inherit; color: var(--color-base-content);
		transition: background 120ms ease;
	}
	.feed-row:last-of-type { border-bottom: none; }
	.feed-row:hover { background: color-mix(in oklch, var(--color-base-content) 4%, transparent); }
	.feed-row-title { flex: 1; min-width: 0; font-size: 13px; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.feed-row-action { display: flex; align-items: center; gap: 8px; flex-shrink: 0; color: color-mix(in oklch, var(--color-base-content) 35%, transparent); }
	.feed-ppw { font-size: 11px; font-variant-numeric: tabular-nums; color: color-mix(in oklch, var(--color-base-content) 55%, transparent); }
	.feed-favicon { width: 16px; height: 16px; border-radius: 3px; flex-shrink: 0; }
	.feed-favicon-fallback { width: 16px; height: 16px; display: flex; align-items: center; justify-content: center; color: color-mix(in oklch, var(--color-base-content) 30%, transparent); flex-shrink: 0; }

	.feed-detail {
		padding: 14px 16px; border-bottom: 1px solid var(--color-base-300);
		background: color-mix(in oklch, var(--color-base-content) 3%, transparent);
	}
	.feeds-list .feed-detail:first-child { border-bottom: none; }
	.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
	@media (max-width: 560px) { .detail-grid { grid-template-columns: 1fr; } }
	.detail-cell { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
	.detail-label {
		display: flex; align-items: center; gap: 8px;
		font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;
		color: color-mix(in oklch, var(--color-base-content) 40%, transparent); margin: 0;
	}
	.detail-label-peak {
		margin-left: auto; text-transform: none; letter-spacing: 0; font-weight: 600;
		color: color-mix(in oklch, var(--color-base-content) 50%, transparent);
	}
	.detail-value { font-size: 15px; font-weight: 700; margin: 0; }
	.detail-sub { font-size: 11px; color: color-mix(in oklch, var(--color-base-content) 50%, transparent); margin: 0; }
	.detail-sub.no-data { display: flex; align-items: center; gap: 6px; }
	.no-data { color: color-mix(in oklch, var(--color-base-content) 35%, transparent); font-size: 12px; }
	.subtle { font-weight: 500; }
	.mono { font-family: monospace; font-variant-numeric: tabular-nums; }

	/* charts */
	.radar-cell { grid-column: span 2; }
	@media (max-width: 560px) { .radar-cell { grid-column: span 1; } }
	.radar-wrap { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
	.radar { width: 100%; max-width: 216px; height: auto; aspect-ratio: 1 / 1; flex-shrink: 0; overflow: hidden; }
	.radar-ring { fill: none; stroke: var(--color-base-300); stroke-width: 1; }
	.radar-spoke { stroke: color-mix(in oklch, var(--color-base-content) 18%, transparent); stroke-width: 1; }
	.radar-label { font-size: 9px; fill: color-mix(in oklch, var(--color-base-content) 45%, transparent); }
	.radar-layer { fill-opacity: 1; stroke: var(--color-base-100); stroke-width: 1; transition: fill-opacity 130ms ease; }
	.radar-layer--base { fill-opacity: 0.5; stroke-width: 1.4; }
	.radar-layer:hover { fill-opacity: 0.85; }
	.radar-history { font-size: 10px; color: color-mix(in oklch, var(--color-base-content) 38%, transparent); margin: 2px 0 0; }
	.radar-side { display: flex; flex-direction: column; gap: 6px; min-width: 0; flex: 1; }
	.radar-max { font-size: 11px; font-weight: 700; margin: 0; color: var(--color-base-content); }
	.radar-max-unit { font-weight: 400; color: color-mix(in oklch, var(--color-base-content) 45%, transparent); }
	.radar-legend { display: flex; flex-direction: column; gap: 3px; }
	.radar-legend-item { display: flex; align-items: center; gap: 6px; font-size: 11px; color: color-mix(in oklch, var(--color-base-content) 70%, transparent); }
	.radar-legend-dot { width: 9px; height: 9px; border-radius: 2px; flex-shrink: 0; }
	.radar-legend-n { margin-left: auto; color: color-mix(in oklch, var(--color-base-content) 40%, transparent); }
	.radar-hint { font-size: 11px; color: color-mix(in oklch, var(--color-base-content) 38%, transparent); margin: 0; }

	.trend-chart { position: relative; display: flex; align-items: flex-end; gap: 3px; height: 72px; overflow: hidden; }
	.trend-grid { position: absolute; inset: 0; z-index: 0; display: flex; flex-direction: column; justify-content: space-between; pointer-events: none; }
	.trend-grid span { border-top: 1px dashed color-mix(in oklch, var(--color-base-content) 12%, transparent); }
	.trend-col { position: relative; z-index: 1; flex: 1; min-width: 0; height: 100%; display: flex; align-items: flex-end; }
	.trend-bar {
		width: 100%; border-radius: var(--ui-radius-xs) var(--ui-radius-xs) 0 0;
		background: color-mix(in oklch, var(--color-success) 65%, transparent);
		min-height: 2px; transition: height 0.3s ease;
	}

	/* gauges */
	.mini-gauge { display: flex; align-items: center; gap: 10px; }
	.gauge-track { flex: 1; background: var(--color-base-300); border-radius: var(--ui-radius-full); height: 8px; overflow: hidden; }
	.gauge-fill { height: 8px; border-radius: var(--ui-radius-full); transition: width 0.4s ease, background 0.3s ease; }
	.gauge-fill.fill-high { background: var(--color-success); }
	.gauge-fill.fill-moderate { background: var(--color-warning); }
	.gauge-fill.fill-low { background: var(--color-error); }
	.gauge-val { font-size: 11px; font-weight: 700; min-width: 38px; text-align: right; }

	/* tag coverage */
	.tag-table {
		display: flex; flex-direction: column;
		border: 1px solid var(--color-base-300); border-radius: var(--ui-radius-lg); overflow: hidden;
	}
	.tag-row { display: flex; align-items: center; gap: 10px; padding: 10px 14px; border-bottom: 1px solid var(--color-base-300); }
	.tag-row:last-child { border-bottom: none; }
	.tag-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
	.tag-row-name { flex: 0 0 22%; min-width: 0; font-size: 12px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.tag-gauge { flex: 1; display: flex; align-items: center; gap: 8px; min-width: 0; }
	.tag-gauge .gauge-val { min-width: 42px; font-size: 10px; }
	.tag-counts { font-size: 11px; color: color-mix(in oklch, var(--color-base-content) 55%, transparent); flex-shrink: 0; }
	.tag-conf { font-size: 11px; color: color-mix(in oklch, var(--color-base-content) 55%, transparent); flex-shrink: 0; width: 46px; text-align: right; }
	.tag-conf.muted { color: color-mix(in oklch, var(--color-base-content) 25%, transparent); }

	/* modal */
	.form-overlay {
		position: fixed; inset: 0; background: rgba(0, 0, 0, 0.4); z-index: 100;
		display: flex; align-items: center; justify-content: center; padding: 16px;
	}
	.form-card {
		background: var(--color-base-100); border-radius: var(--ui-radius-lg);
		width: 100%; max-width: 480px; max-height: 90vh; overflow-y: auto;
		box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
	}
	.confirm-card { max-width: 340px; padding: 24px; text-align: center; }
	.confirm-text { font-size: 14px; color: var(--color-base-content); margin: 0 0 20px; }
	.confirm-actions { display: flex; gap: 8px; justify-content: center; }
	.form-header { display: flex; align-items: center; justify-content: space-between; padding: 16px 20px; border-bottom: 1px solid var(--color-base-300); }
	.form-header h3 { margin: 0; font-size: 15px; font-weight: 700; }
	.close-btn { background: transparent; border: none; cursor: pointer; color: color-mix(in oklch, var(--color-base-content) 50%, transparent); padding: 4px; border-radius: var(--ui-radius-xs); }
	.close-btn:hover { background: var(--color-base-200); color: var(--color-base-content); }
	.form-body { padding: 16px 20px 20px; display: flex; flex-direction: column; gap: 14px; }
	.form-label { display: flex; flex-direction: column; gap: 4px; font-size: 12px; font-weight: 600; color: color-mix(in oklch, var(--color-base-content) 60%, transparent); }
	.form-input {
		padding: 8px 12px; border: 1px solid var(--color-base-300); border-radius: var(--ui-radius-sm);
		background: var(--color-base-100); color: var(--color-base-content); font-size: 13px;
		outline: none; transition: border-color 150ms;
	}
	.form-input:focus { border-color: var(--color-accent); }
	.form-input.mono { font-family: monospace; font-size: 12px; }
	.form-input.mono::placeholder { font-family: system-ui, sans-serif; }
	.divider-label { font-size: 10px; text-transform: uppercase; letter-spacing: 0.06em; text-align: center; color: color-mix(in oklch, var(--color-base-content) 30%, transparent); margin: 0 0 8px; }

	.fix-feed-line { display: flex; align-items: center; gap: 8px; min-width: 0; }
	.fix-diagnosis {
		display: flex; flex-direction: column; gap: 6px;
		border: 1px solid var(--color-base-300); border-radius: var(--ui-radius-sm);
		padding: 10px 12px; background: color-mix(in oklch, var(--color-base-content) 4%, transparent);
	}
	.fix-diagnosis.loading { flex-direction: row; align-items: center; font-size: 13px; color: color-mix(in oklch, var(--color-base-content) 55%, transparent); }
	.fix-diagnosis.ok { flex-direction: row; align-items: center; color: var(--color-success); border-color: color-mix(in oklch, var(--color-success) 35%, transparent); font-size: 13px; font-weight: 600; }
	.fix-diagnosis-title { margin: 0; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: color-mix(in oklch, var(--color-base-content) 40%, transparent); }
	.fix-diagnosis-text { margin: 0; font-size: 13px; line-height: 1.45; color: var(--color-base-content); }
	.fix-diagnosis-note { margin: 0; font-size: 11px; color: color-mix(in oklch, var(--color-base-content) 45%, transparent); font-style: italic; }

	.candidate-list { display: flex; flex-direction: column; gap: 6px; max-height: 260px; overflow-y: auto; }
	.candidate-item {
		display: flex; align-items: flex-start; gap: 9px; padding: 9px 11px;
		border: 1px solid var(--color-base-300); border-radius: var(--ui-radius-sm);
		cursor: pointer; transition: border-color 130ms, background 130ms;
	}
	.candidate-item:hover { background: color-mix(in oklch, var(--color-base-content) 4%, transparent); }
	.candidate-item:has(input:checked) { border-color: var(--color-accent); background: color-mix(in oklch, var(--color-accent) 6%, transparent); }
	.candidate-item input { accent-color: var(--color-accent); margin-top: 2px; flex-shrink: 0; }
	.candidate-info { display: flex; flex-direction: column; gap: 3px; min-width: 0; flex: 1; }
	.candidate-head { display: flex; align-items: center; gap: 7px; flex-wrap: wrap; }
	.candidate-title { font-size: 13px; font-weight: 600; color: var(--color-base-content); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 100%; }
	.candidate-url { font-size: 11px; color: color-mix(in oklch, var(--color-base-content) 55%, transparent); word-break: break-all; }
	.candidate-desc { font-size: 11px; color: color-mix(in oklch, var(--color-base-content) 50%, transparent); display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
	.candidate-badge {
		font-size: 10px; font-weight: 600;
		padding: 1px 7px; border-radius: var(--ui-radius-full);
		background: color-mix(in oklch, var(--color-base-content) 8%, transparent);
		color: color-mix(in oklch, var(--color-base-content) 60%, transparent);
	}
	.candidate-last { font-size: 11px; font-style: italic; color: color-mix(in oklch, var(--color-base-content) 40%, transparent); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.candidate-tag {
		font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em;
		padding: 1px 6px; border-radius: var(--ui-radius-full);
	}
	.candidate-tag.best { background: color-mix(in oklch, var(--color-accent) 15%, transparent); color: var(--color-accent); }
	.candidate-tag.current { background: color-mix(in oklch, var(--color-base-content) 10%, transparent); color: color-mix(in oklch, var(--color-base-content) 55%, transparent); }
	.no-candidates { display: flex; flex-direction: column; gap: 4px; padding: 4px 0; }

	.fix-current {
		display: flex; flex-direction: column; gap: 2px;
		padding: 7px 10px; border-radius: var(--ui-radius-sm);
		background: color-mix(in oklch, var(--color-error) 6%, transparent);
	}
	.fix-current-label { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: color-mix(in oklch, var(--color-error) 75%, transparent); }
	.fix-current-url { font-size: 11px; color: color-mix(in oklch, var(--color-base-content) 60%, transparent); word-break: break-all; }

	.refresh-banner {
		display: flex; align-items: center; gap: 9px;
		padding: 9px 13px; border-radius: var(--ui-radius-sm);
		background: color-mix(in oklch, var(--color-accent) 8%, transparent);
		border: 1px solid color-mix(in oklch, var(--color-accent) 25%, transparent);
		font-size: 12px; color: var(--color-accent);
	}
	.tag-empty { display: flex; flex-direction: column; gap: 8px; align-items: flex-start; }
	.stats-updated { font-size: 11px; color: color-mix(in oklch, var(--color-base-content) 45%, transparent); align-self: center; }
</style>
