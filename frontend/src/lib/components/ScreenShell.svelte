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
	let suppressClick = false;

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
					stackedScreenOpen.set(false); // reveal the app beneath
				} else {
					gAxis = 'v';
				}
			}
			return;
		}
		if (gAxis !== 'h') return;

		e.preventDefault();
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
		setTimeout(() => (suppressClick = false), 350);

		const w = window.innerWidth;
		const dx = gLastX - gStartX;
		const isFling = gVel > FLING_VEL && dx > FLING_MIN_PX;

		if (dx > w * 0.35 || isFling) {
			await closeScreen({ animated: true });
		} else {
			shellEl.style.transition = 'transform 240ms cubic-bezier(0.22, 1, 0.36, 1)';
			shellEl.style.transform = 'translate3d(0, 0, 0)';
			setTimeout(() => {
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
		return () => {
			window.removeEventListener('keydown', onKeydown);
			shellClosed();
		};
	});
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	class="screen-shell"
	bind:this={shellEl}
	ontouchstart={onTouchStart}
	ontouchmove={onTouchMove}
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
	}

	@media (max-width: 767.98px) {
		.screen-shell {
			position: fixed;
			inset: 0;
			z-index: 55;
			overflow-y: auto;
			overflow-x: hidden;
			-webkit-overflow-scrolling: touch;
			overscroll-behavior-x: none;
			/* No fill-mode/forwards: a lingering transform would become the
			   containing block for position:fixed children (sub-tab bars). */
			animation: shell-enter 280ms cubic-bezier(0.22, 1, 0.36, 1);
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
