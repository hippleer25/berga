<script lang="ts">
	import { onMount } from 'svelte';
	import { navVisible, navDragOffset, navDragging, stackedScreenOpen } from '$lib/stores/swipe';

	/**
	 * Sensitive bottom-edge zone shown while the mobile NavBar is hidden.
	 * - Swipe up → the bar follows the finger and reveals (commits past a
	 *   distance/fling threshold, springs back otherwise).
	 * - Tap → reveals immediately.
	 * Mounted inside PageTrack's viewport so horizontal drags starting here
	 * keep bubbling to the tab-swipe handlers (they axis-lock to 'v' and
	 * ignore vertical drags).
	 */

	const isDesktop = () => window.matchMedia('(min-width: 768px)').matches;

	const MAX_TRAVEL = 110; // px cap for the finger-follow
	const COMMIT_RATIO = 0.3; // fraction of travel that commits the reveal
	const MAX_AGE_MS = 500; // ignore taps right after an auto-hide on Mota

	let appearedAt = 0;
	let tsX = 0, tsY = 0;
	let axis: 'h' | 'v' | null = null;
	let lastY = 0, lastT = 0, velY = 0;
	let dragged = false;

	onMount(() => {
		appearedAt = Date.now();
	});

	function travel() {
		const el = document.querySelector('.mobile-nav') as HTMLElement | null;
		return el ? Math.min(MAX_TRAVEL, el.getBoundingClientRect().height + 40) : MAX_TRAVEL;
	}

	function reveal() {
		navVisible.set(true);
		navDragOffset.set(0);
		navDragging.set(false);
	}

	function onTouchStart(e: TouchEvent) {
		if (isDesktop()) return;
		const tch = e.touches[0];
		tsX = tch.clientX;
		tsY = tch.clientY;
		axis = null;
		velY = 0;
		lastY = tch.clientY;
		lastT = e.timeStamp;
		dragged = false;
	}

	function onTouchMove(e: TouchEvent) {
		if (isDesktop() || $stackedScreenOpen) return;
		const tch = e.touches[0];
		const dx = tch.clientX - tsX;
		const dy = tch.clientY - tsY;
		if (!axis) {
			if (Math.abs(dx) > 6 || Math.abs(dy) > 6)
				axis = Math.abs(dx) > Math.abs(dy) * 1.2 ? 'h' : 'v';
			if (axis !== 'v') return;
			navDragging.set(true);
		}
		if (axis !== 'v') return;
		e.preventDefault();
		if (dy < -4) dragged = true;
		const dt = e.timeStamp - lastT;
		if (dt > 0) velY = velY * 0.3 + ((tch.clientY - lastY) / dt) * 0.7;
		lastY = tch.clientY;
		lastT = e.timeStamp;
		// Bar is hidden with translateY(100% + safe [+ extras]); a negative
		// offset drags it up toward the resting position.
		navDragOffset.set(Math.max(-travel(), Math.min(0, dy)));
	}

	function onTouchEnd() {
		if (axis !== 'v') {
			navDragOffset.set(0);
			navDragging.set(false);
			axis = null;
			return;
		}
		const dy = lastY - tsY; // negative when swiped up
		const off = $navDragOffset;
		// Fling up or dragged past ~30% of travel commits the reveal
		const commit = off < -20 && (dy < -travel() * COMMIT_RATIO || velY < -0.35);
		navDragging.set(false); // restores the transition
		if (commit) reveal();
		else navDragOffset.set(0); // springs back down (stays hidden)
		axis = null;
	}

	function onTap() {
		if (isDesktop() || dragged) return;
		if (Date.now() - appearedAt < MAX_AGE_MS) return;
		reveal();
	}
</script>

{#if !$stackedScreenOpen}
	<!-- svelte-ignore a11y_no_static_element_interactions, a11y_click_events_have_key_events -->
	<div
		class="reveal-zone"
		ontouchstart={onTouchStart}
		ontouchmove={onTouchMove}
		ontouchend={onTouchEnd}
		onclick={onTap}
	></div>
{/if}

<style>
	.reveal-zone {
		position: fixed;
		left: 0;
		right: 0;
		bottom: 0;
		height: calc(48px + env(safe-area-inset-bottom, 0px));
		z-index: 49; /* just under the NavBar (50) */
		touch-action: none;
		background: transparent;
	}

	@media (min-width: 768px) {
		.reveal-zone {
			display: none;
		}
	}
</style>
