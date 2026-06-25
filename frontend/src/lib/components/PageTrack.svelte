<script lang="ts">
import { afterNavigate, replaceState } from '$app/navigation';
import { swipeOffset, swipeDragging, activeTabIdx, navVisible } from '$lib/stores/swipe';
import { onMount } from 'svelte';
import type { Component } from 'svelte';

type TabLoader = () => Promise<{ default: Component }>;

const TABS = ['/followers', '/home', '/events', '/mota'] as const;
const N = TABS.length;
const HOME_IDX = 1;

const tabLoaders: TabLoader[] = [
  () => import('$lib/tabs/FollowersTab.svelte'),
  () => import('$lib/tabs/HomeTab.svelte'),
  () => import('$lib/tabs/EventsTab.svelte'),
  () => import('$lib/tabs/MotaTab.svelte'),
];

let tabComponents = $state<(Component | null)[]>(Array(N).fill(null));
let tabReady = $state<boolean[]>(Array(N).fill(false));

async function loadTab(idx: number) {
  if (tabReady[idx]) return;
  const mod = await tabLoaders[idx]();
  tabComponents[idx] = mod.default;
  tabReady[idx] = true;
}

function prefetchAdjacent(idx: number) {
  if (idx > 0 && !tabReady[idx - 1]) loadTab(idx - 1);
  if (idx < N - 1 && !tabReady[idx + 1]) loadTab(idx + 1);
}

let trackEl: HTMLElement;

let activeIdx = $state(0);
let isDragging = $state(false);
let dragPx = $state(0);
let locked = false;
let swipeNav = false;

const DUR = 320;
const EASE = 'cubic-bezier(0.25, 0.46, 0.45, 0.94)';
const W = () => window.innerWidth;
const wait = (ms: number) => new Promise<void>(r => setTimeout(r, ms));

const FLING_VEL = 0.4;
const FLING_MIN_PX = 30;

function tabTx(pos: number) {
  return `translateX(${(-pos * 100) / N}%)`;
}

function snapTo(idx: number, animated: boolean) {
  if (!trackEl) return;
  trackEl.style.transition = animated ? `transform ${DUR}ms ${EASE}` : 'none';
  trackEl.style.transform = tabTx(idx);
}

onMount(async () => {
  const path = window.location.pathname;
  const idx = TABS.findIndex(t => path === t || path.startsWith(t + '/'));
  activeIdx = Math.max(0, idx);
  activeTabIdx.set(activeIdx);
  snapTo(activeIdx, false);
  await loadTab(activeIdx);
  prefetchAdjacent(activeIdx);
});

afterNavigate(async ({ to }) => {
  if (swipeNav) { swipeNav = false; return; }
  if (!to) return;
  const idx = TABS.findIndex(
    t => to.url.pathname === t || to.url.pathname.startsWith(t + '/')
  );
  if (idx >= 0) {
    await loadTab(idx);
    if (idx !== activeIdx) {
      activeIdx = idx;
      activeTabIdx.set(idx);
      snapTo(idx, true);
    }
  }
});

    // Keep shared stores in sync with local drag state
    $effect(() => {
        swipeOffset.set(dragPx / W());
        swipeDragging.set(isDragging);
    });

    // Restore NavBar when leaving Home tab
    $effect(() => {
        if (activeIdx !== HOME_IDX) navVisible.set(true);
    });

    // ── Touch handlers ────────────────────────────────────────────────────────

let startX = 0, startY = 0;
let axis: 'h' | 'v' | null = null;
let lastX = 0;
let lastT = 0;
let velPxMs = 0;
let filterBarTouch = false;

function onTouchStart(e: TouchEvent) {
	if (locked) return;
	const t = e.target as HTMLElement;
	filterBarTouch = !!t.closest('.filter-bar');
	startX = e.touches[0].clientX;
	startY = e.touches[0].clientY;
	lastX = startX;
	lastT = e.timeStamp;
	velPxMs = 0;
	axis = null;
	isDragging = false;
	dragPx = 0;
}

function onTouchMove(e: TouchEvent) {
	if (locked) return;
	if (filterBarTouch) return;
	const dx = e.touches[0].clientX - startX;
	const dy = e.touches[0].clientY - startY;

	if (!axis) {
		if (Math.abs(dx) > 6 || Math.abs(dy) > 6)
			axis = Math.abs(dx) > Math.abs(dy) * 1.2 ? 'h' : 'v';
		return;
	}
	if (axis !== 'h') return;

        e.preventDefault();
        isDragging = true;

        const now = e.timeStamp;
        const dt  = now - lastT;
        if (dt > 0) {
            const instantVel = (e.touches[0].clientX - lastX) / dt;
            velPxMs = velPxMs * 0.3 + instantVel * 0.7;
        }
        lastX = e.touches[0].clientX;
        lastT = now;

        const w    = W();
        const canP = activeIdx > 0;
        const canN = activeIdx < N - 1;

        const raw = ((dx > 0 && !canP) || (dx < 0 && !canN))
            ? dx * 0.12
            : Math.max(-w, Math.min(w, dx));

        dragPx = raw;
        trackEl.style.transition = 'none';
        trackEl.style.transform  = tabTx(activeIdx - raw / w);
    }

	async function onTouchEnd() {
		filterBarTouch = false;
		if (!isDragging) {
            snapTo(activeIdx, true);
            dragPx = 0;
            return;
        }

        isDragging = false; // ← $effect fires: swipeDragging=false (removes .dragging),
        locked     = true;  //   swipeOffset stays at current dragPx value for now.
                            //   Pill is at its drag position WITH transition restored.

        const w         = W();
        const finalDrag = dragPx;
        const finalVel  = velPxMs;

        const isFlingLeft  = finalVel < -FLING_VEL && finalDrag < -FLING_MIN_PX;
        const isFlingRight = finalVel >  FLING_VEL && finalDrag >  FLING_MIN_PX;

        const prevIdx = activeIdx;
        let newIdx    = activeIdx;
        if      ((finalDrag < -(w * 0.5) || isFlingLeft)  && activeIdx < N - 1) newIdx = activeIdx + 1;
        else if ((finalDrag >  (w * 0.5) || isFlingRight) && activeIdx > 0)     newIdx = activeIdx - 1;

        // ── Pill fix ──────────────────────────────────────────────────────────
        //
        // The problem:
        //   If we change swipeOffset and activeTabIdx in the same render frame,
        //   the browser sees the pill jump from "drag position, no transition"
        //   to "new tab, transition enabled" — all at once, so no animation.
        //
        // The fix — two-frame approach:
        //   Frame 1 (already happened above when isDragging=false):
        //     • .dragging removed  →  CSS transition is restored on the pill
        //     • swipeOffset still has the drag value
        //     • effectiveIndex = oldTabIdx - dragOffset  (pill is at drag position)
        //
        //   Frame 2 (requestAnimationFrame below):
        //     • activeTabIdx → newIdx
        //     • swipeOffset  → 0  (dragPx = 0)
        //     • effectiveIndex = newIdx - 0 = newIdx
        //     • Browser sees the `left` value change while transition is active
        //       → pill slides smoothly from drag position to destination ✓
        //
  requestAnimationFrame(async () => {
    activeIdx = newIdx;
    activeTabIdx.set(newIdx);
    dragPx = 0; // $effect propagates swipeOffset=0
    await loadTab(newIdx);
  });

  // Animate the page track in parallel
  const dur = (newIdx !== prevIdx && (isFlingLeft || isFlingRight)) ? 240 : DUR;
  trackEl.style.transition = `transform ${dur}ms ${EASE}`;
  trackEl.style.transform = tabTx(newIdx);

  await wait(dur + 30);

  swipeNav = true;
  replaceState(TABS[newIdx], {});
        trackEl.style.transition = 'none';
        locked = false;
    }

    // ── Hide NavBar on scroll-down in Home tab ────────────────────────────────

    const SCROLL_THRESHOLD = 6;
    let lastScrollTop = 0;

    function handleHomeScroll(e: Event) {
        const el    = e.currentTarget as HTMLElement;
        const y     = el.scrollTop;
        const delta = y - lastScrollTop;
        lastScrollTop = y;

        if (y < 40) { navVisible.set(true); return; }

        if      (delta >  SCROLL_THRESHOLD) navVisible.set(false);
        else if (delta < -SCROLL_THRESHOLD) navVisible.set(true);
    }
</script>

<div
    class="viewport"
    ontouchstart={onTouchStart}
    ontouchmove={onTouchMove}
    ontouchend={onTouchEnd}
>
<div class="track" bind:this={trackEl}>
  <div class="panel" class:panel-active={activeIdx === 0}>
{#if tabReady[0] && tabComponents[0]}
			{@const Tab0 = tabComponents[0]}
			<Tab0 />
    {:else}
      <div class="tab-loader"></div>
    {/if}
  </div>
  <div class="panel" class:panel-active={activeIdx === 1} onscroll={handleHomeScroll}>
{#if tabReady[1] && tabComponents[1]}
			{@const Tab1 = tabComponents[1]}
			<Tab1 />
		{:else}
			<div class="tab-loader"></div>
		{/if}
	</div>
	<div class="panel" class:panel-active={activeIdx === 2}>
		{#if tabReady[2] && tabComponents[2]}
			{@const Tab2 = tabComponents[2]}
			<Tab2 />
		{:else}
			<div class="tab-loader"></div>
		{/if}
	</div>
	<div class="panel" class:panel-active={activeIdx === 3}>
		{#if tabReady[3] && tabComponents[3]}
			{@const Tab3 = tabComponents[3]}
			<Tab3 />
    {:else}
      <div class="tab-loader"></div>
    {/if}
  </div>
</div>
</div>

<style>
    .viewport {
        overflow: clip;
        width: 100%;
        height: 100dvh;
    }

    .track {
        display: flex;
        width: calc(100% * 4);
        height: 100%;
    }

    .panel {
        flex-shrink: 0;
        width: calc(100% / 4);
        height: 100%;
        overflow-y: auto;
        overflow-x: hidden;
        scrollbar-width: none;
        will-change: transform;
        background: var(--color-base-100);
        -webkit-overflow-scrolling: touch;
        overscroll-behavior-y: contain;
    }
    .panel::-webkit-scrollbar {
        width: 0;
        height: 0;
        display: none;
    }

    @media (min-width: 768px) {
        .viewport { overflow: visible; height: auto; }
        .track {
            display: block;
            width: 100%;
            height: auto;
            transform: none !important;
            transition: none !important;
        }
        .panel {
            display: none;
            width: 100%;
            height: auto;
            overflow: visible;
            will-change: auto;
            -webkit-overflow-scrolling: auto;
            overscroll-behavior-y: auto;
        }
  .panel.panel-active { display: block; }

  .tab-loader {
    min-height: 100dvh;
    background: var(--color-base-100);
  }
}
</style>