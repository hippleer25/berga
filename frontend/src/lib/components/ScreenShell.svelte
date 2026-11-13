<script lang="ts">
	import { onMount } from 'svelte';
	import { closeScreen, shellOpened, shellClosed, isScreenClosing } from '$lib/utils/screenStack';
	import { stackedScreenOpen, activeTabIdx } from '$lib/stores/swipe';
	import { hrefAtIdx } from '$lib/config/tabs';
	import { get } from 'svelte/store';

	let { children } = $props();

	let shellEl: HTMLElement;

	// ── Edge-swipe-to-close gesture ──────────────────────────────────────────
	const EDGE_PX = 28;
	const FLING_VEL = 0.45;
	const FLING_MIN_PX = 24;

	let gActive = false;
	let gDragging = false;
	let gAxis: 'h' | 'v' | null = null;
	let gStartX = 0;
	let gStartY = 0;
	let gLastX = 0;
	let gLastT = 0;
	let gVel = 0;
	let gFrozenTop = 0;
	let suppressClick = false;
	// Timer ids so pending callbacks can be cancelled on destroy — an orphaned
	// snap-back timer would re-set `stackedScreenOpen` after the shell is gone,
	// freezing the tab layer (pointer-events: none) with no recovery.
	let snapBackTimer: ReturnType<typeof setTimeout> | null = null;
	let suppressClickTimer: ReturnType<typeof setTimeout> | null = null;

	const isDesktop = () => window.matchMedia('(min-width: 768px)').matches;

	function onTouchStart(e: TouchEvent) {
		if (isScreenClosing() || isDesktop() || e.touches.length !== 1) return;
		const touch = e.touches[0];
		if (touch.clientX > EDGE_PX) return;
		const target = e.target as HTMLElement;
		if (target.closest('input, textarea, select, [contenteditable], [data-no-swipe]')) return;
		gActive = true;
		gDragging = false;
		gAxis = null;
		gStartX = gLastX = touch.clientX;
		gStartY = touch.clientY;
		gLastT = e.timeStamp;
		gVel = 0;
		gFrozenTop = 0;
	}

	function onTouchMove(e: TouchEvent) {
		if (!gActive || isScreenClosing()) return;
		const touch = e.touches[0];
		const dx = touch.clientX - gStartX;
		const dy = touch.clientY - gStartY;

		if (!gAxis) {
			if (Math.abs(dx) > 8 || Math.abs(dy) > 8) {
				if (dx > 0 && Math.abs(dx) > Math.abs(dy) * 1.2) {
					gAxis = 'h';
					gDragging = true;
					gFrozenTop = shellEl.scrollTop;
					stackedScreenOpen.set(false); // reveal the app beneath
				} else {
					gAxis = 'v';
				}
			}
			return;
		}
		if (gAxis !== 'h') return;

		// Horizontal axis locked: suppress vertical scrolling for the whole
		// gesture (preventDefault blocks new native scrolls; pinning scrollTop
		// freezes one already in flight).
		e.preventDefault();
		shellEl.scrollTop = gFrozenTop;

		const dt = e.timeStamp - gLastT;
		if (dt > 0) {
			gVel = gVel * 0.3 + ((touch.clientX - gLastX) / dt) * 0.7;
		}
		gLastX = touch.clientX;
		gLastT = e.timeStamp;

		const px = Math.max(0, dx);
		shellEl.style.transition = 'none';
		shellEl.style.transform = `translate3d(${px}px, 0, 0)`;
	}

	async function onTouchEnd() {
		if (!gActive) return;
		gActive = false;
		if (!gDragging) return;
		gDragging = false;
		gAxis = null;

		suppressClick = true;
		if (suppressClickTimer) clearTimeout(suppressClickTimer);
		suppressClickTimer = setTimeout(() => (suppressClick = false), 350);

		const w = window.innerWidth;
		const dx = gLastX - gStartX;
		const isFling = gVel > FLING_VEL && dx > FLING_MIN_PX;

		if (dx > w * 0.35 || isFling) {
			await closeScreen({ animated: true });
		} else {
			shellEl.style.transition = 'transform 240ms cubic-bezier(0.22, 1, 0.36, 1)';
			shellEl.style.transform = 'translate3d(0, 0, 0)';
			if (snapBackTimer) clearTimeout(snapBackTimer);
			snapBackTimer = setTimeout(() => {
				if (!isScreenClosing()) stackedScreenOpen.set(true);
			}, 250);
		}
	}

	function onClickCapture(e: MouseEvent) {
		if (suppressClick) {
			e.stopPropagation();
			e.preventDefault();
		}
	}

	function onKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape' && !isScreenClosing()) closeScreen();
	}

	onMount(() => {
		shellOpened(shellEl, hrefAtIdx(get(activeTabIdx)) || '/home');
		window.addEventListener('keydown', onKeydown);
		// touchmove must be non-passive so the horizontal drag can preventDefault
		// (Svelte 5 marks ontouchmove attributes passive by default).
		shellEl.addEventListener('touchmove', onTouchMove, { passive: false });
		return () => {
			window.removeEventListener('keydown', onKeydown);
			shellEl.removeEventListener('touchmove', onTouchMove);
			if (snapBackTimer) clearTimeout(snapBackTimer);
			if (suppressClickTimer) clearTimeout(suppressClickTimer);
			shellClosed();
		};
	});
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	class="screen-shell"
	bind:this={shellEl}
	ontouchstart={onTouchStart}
	ontouchend={onTouchEnd}
	ontouchcancel={onTouchEnd}
	onclickcapture={onClickCapture}
>
	{@render children()}
</div>

<style>
	.screen-shell {
		background: var(--color-base-100);
		min-height: 100dvh;
		/* Horizontal drag (swipe-to-close) is ours; vertical scroll stays native */
		touch-action: pan-y;
	}

	@media (max-width: 767.98px) {
		.screen-shell {
			position: fixed;
			inset: 0;
			z-index: 55;
			overflow-y: auto;
			overflow-x: hidden;
			scrollbar-width: none;
			-webkit-overflow-scrolling: touch;
			overscroll-behavior-x: none;
			/* No fill-mode/forwards: a lingering transform would become the
			   containing block for position:fixed children (sub-tab bars). */
			animation: shell-enter 280ms cubic-bezier(0.22, 1, 0.36, 1);
		}
		.screen-shell::-webkit-scrollbar {
			width: 0;
			height: 0;
			display: none;
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.screen-shell {
			animation: none;
		}
	}

	@keyframes shell-enter {
		from {
			transform: translate3d(28%, 0, 0);
			opacity: 0;
		}
	}
</style>
