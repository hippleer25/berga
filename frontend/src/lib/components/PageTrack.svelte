<script lang="ts">
import { afterNavigate, replaceState } from '$app/navigation';
import { swipeOffset, swipeDragging, activeTabIdx, navVisible } from '$lib/stores/swipe';
import { orderedTabs, TAB_LOADERS, type TabId } from '$lib/config/tabs';
import { onMount } from 'svelte';
import type { Component } from 'svelte';
import NavRevealZone from '$lib/components/NavRevealZone.svelte';

const HOME_ID: TabId = 'home';

let tabComponents = $state<Record<string, Component | null>>({});
let tabReady = $state<Record<string, boolean>>({});

async function loadTab(id: TabId) {
  if (tabReady[id]) return;
  const mod = await TAB_LOADERS[id]();
  tabComponents[id] = mod.default;
  tabReady[id] = true;
}

let trackEl: HTMLElement;

let activeIdx = $state(0);
let activeTabId = $state<TabId>('home');
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
  const n = $orderedTabs.length || 1;
  return `translateX(${(-pos * 100) / n}%)`;
}

function snapTo(idx: number, animated: boolean) {
  if (!trackEl) return;
  trackEl.style.transition = animated ? `transform ${DUR}ms ${EASE}` : 'none';
  trackEl.style.transform = tabTx(idx);
}

onMount(async () => {
  const tabs = $orderedTabs;
  const path = window.location.pathname;
  const idx = tabs.findIndex(t => path === t.href || path.startsWith(t.href + '/'));
  activeIdx = Math.max(0, idx);
  activeTabId = tabs[activeIdx].id;
  activeTabIdx.set(activeIdx);
  snapTo(activeIdx, false);
  await loadTab(activeTabId);
  for (const t of tabs) {
    if (t.id !== activeTabId) loadTab(t.id);
  }
});

afterNavigate(async ({ to }) => {
  if (swipeNav) { swipeNav = false; return; }
  if (!to) return;
  const tabs = $orderedTabs;
  const idx = tabs.findIndex(
    t => to.url.pathname === t.href || to.url.pathname.startsWith(t.href + '/')
  );
  if (idx >= 0) {
    await loadTab(tabs[idx].id);
    if (idx !== activeIdx) {
      activeIdx = idx;
      activeTabId = tabs[idx].id;
      activeTabIdx.set(idx);
      snapTo(idx, true);
    }
  }
});

// ── Reorder: keep the active panel under the finger when tab order changes ──
$effect(() => {
  const tabs = $orderedTabs;
  if (locked || isDragging || !trackEl) return;
  const newIdx = tabs.findIndex(t => t.id === activeTabId);
  if (newIdx >= 0 && newIdx !== activeIdx) {
    activeIdx = newIdx;
    activeTabIdx.set(newIdx);
    snapTo(newIdx, false);
  }
});

    // Keep shared stores in sync with local drag state
    $effect(() => {
        swipeOffset.set(dragPx / W());
        swipeDragging.set(isDragging);
    });

    // NavBar auto-hide: Home hides on scroll-down; on Mota (mobile) the chat
    // takes the full screen, so the nav is forced away and restored on exit.
    const MOTA_ID: TabId = 'mota';
    const isDesktop = () => window.matchMedia('(min-width: 768px)').matches;
    $effect(() => {
        if (isDesktop()) return;
        if (activeTabId === MOTA_ID) navVisible.set(false);
        else if (activeTabId !== HOME_ID) navVisible.set(true);
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
        const n    = $orderedTabs.length;
        const canP = activeIdx > 0;
        const canN = activeIdx < n - 1;

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
        const n         = $orderedTabs.length;
        const finalDrag = dragPx;
        const finalVel  = velPxMs;

        const isFlingLeft  = finalVel < -FLING_VEL && finalDrag < -FLING_MIN_PX;
        const isFlingRight = finalVel >  FLING_VEL && finalDrag >  FLING_MIN_PX;

        const prevIdx = activeIdx;
        let newIdx    = activeIdx;
        if      ((finalDrag < -(w * 0.5) || isFlingLeft)  && activeIdx < n - 1) newIdx = activeIdx + 1;
        else if ((finalDrag >  (w * 0.5) || isFlingRight) && activeIdx > 0)     newIdx = activeIdx - 1;

        // ── Pill fix ──────────────────────────────────────────────────────────
        //
        // Two-frame approach so the NavBar pill animates from its drag position
        // to the destination tab instead of jumping:
        //   Frame 1 (isDragging=false above): transition restored, offset kept.
        //   Frame 2 (rAF): activeTabIdx → newIdx, offset → 0 → pill slides.
        //
  requestAnimationFrame(async () => {
    activeIdx = newIdx;
    activeTabId = $orderedTabs[newIdx].id;
    activeTabIdx.set(newIdx);
    dragPx = 0; // $effect propagates swipeOffset=0
    await loadTab(activeTabId);
  });

  // Animate the page track in parallel
  const dur = (newIdx !== prevIdx && (isFlingLeft || isFlingRight)) ? 240 : DUR;
  trackEl.style.transition = `transform ${dur}ms ${EASE}`;
  trackEl.style.transform = tabTx(newIdx);

  await wait(dur + 30);

  swipeNav = true;
  replaceState($orderedTabs[newIdx].href, {});
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

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
    class="viewport"
    ontouchstart={onTouchStart}
    ontouchmove={onTouchMove}
    ontouchend={onTouchEnd}
>
<div class="track" style="--n: {$orderedTabs.length}" bind:this={trackEl}>
  {#each $orderedTabs as def, i (def.id)}
    <div class="panel" class:panel-active={activeIdx === i} onscroll={def.id === HOME_ID ? handleHomeScroll : undefined}>
      {#if tabReady[def.id] && tabComponents[def.id]}
        {@const TabComp = tabComponents[def.id]}
        <TabComp />
      {:else}
        <div class="tab-loader"></div>
      {/if}
    </div>
  {/each}
</div>
<NavRevealZone />
</div>

<style>
    .viewport {
        overflow: clip;
        width: 100%;
        height: 100dvh;
    }

    .track {
        display: flex;
        width: calc(100% * var(--n, 4));
        height: 100%;
    }

    .panel {
        flex-shrink: 0;
        width: calc(100% / var(--n, 4));
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
