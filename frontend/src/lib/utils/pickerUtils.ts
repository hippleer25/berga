/** Shared picker-popup helpers (dropdown anchoring + scroll containment).
    Used by the Home filter bar (in-tab and top-bar hosts) and the HomeTab
    bulk-tag picker. */

/** Anchor the popup below (or above) the trigger chip and clamp its
    height to the real viewport space so it is never cut off. The
    inline `max-height` returned here is the single source of truth
    for popup height at every breakpoint (CSS only widens on desktop). */
export function getDropdownStyle(btnEl: HTMLButtonElement, tall = false): string {
	const r          = btnEl.getBoundingClientRect();
	const DROPDOWN_W = 196;
	const PADDING    = 8;
	const GAP        = 6;
	const desktop    = window.matchMedia('(min-width: 768px)').matches;
	const target     = desktop ? (tall ? 520 : 420) : (tall ? 320 : 280);
	const top        = r.bottom + GAP;
	const maxH       = Math.max(Math.floor(Math.min(target, window.innerHeight - top - PADDING)), 160);
	if (r.right + PADDING > window.innerWidth) {
		return `top:${top}px; max-height:${maxH}px; right:${Math.max(window.innerWidth - r.right, PADDING)}px;`;
	}
	const left = Math.max(Math.min(r.left, window.innerWidth - DROPDOWN_W - PADDING), PADDING);
	return `top:${top}px; max-height:${maxH}px; left:${left}px;`;
}

/** Floating selection bar sits at the screen's bottom edge — open its
    dropdown upward so it never fights the viewport. */
export function getDropdownStyleUp(btnEl: HTMLButtonElement, tall = false): string {
	const r          = btnEl.getBoundingClientRect();
	const DROPDOWN_W = 196;
	const PADDING    = 8;
	const GAP        = 6;
	const desktop    = window.matchMedia('(min-width: 768px)').matches;
	const target     = desktop ? (tall ? 520 : 420) : (tall ? 320 : 280);
	const bottom     = window.innerHeight - r.top + GAP;
	const maxH       = Math.max(Math.floor(Math.min(target, r.top - GAP - PADDING)), 160);
	if (r.right + PADDING > window.innerWidth) {
		return `bottom:${bottom}px; max-height:${maxH}px; right:${Math.max(window.innerWidth - r.right, PADDING)}px;`;
	}
	const left = Math.max(Math.min(r.left, window.innerWidth - DROPDOWN_W - PADDING), PADDING);
	return `bottom:${bottom}px; max-height:${maxH}px; left:${left}px;`;
}

/** Svelte action: keeps wheel/touch gestures inside the picker popups.
    Pops are `overflow-y:auto` scroll containers, but once the list is at
    its edge (or the popup has nothing to scroll) the browser chains the
    gesture into the feed behind — this blocks that. Non-passive because
    Svelte 5 marks wheel/touchmove handlers passive by default. */
export function containPickerScroll(node: HTMLElement): { destroy: () => void } {
	const scrollable = () => node.scrollHeight > node.clientHeight + 1;
	const atEdge = (dy: number) => {
		if (!scrollable()) return true;
		const max = node.scrollHeight - node.clientHeight;
		return dy > 0 ? node.scrollTop >= max - 1 : node.scrollTop <= 1;
	};
	const onWheel = (e: WheelEvent) => { if (atEdge(e.deltaY)) e.preventDefault(); };
	let touchY = 0;
	const onTouchStart = (e: TouchEvent) => { touchY = e.touches[0].clientY; };
	const onTouchMove = (e: TouchEvent) => {
		if (e.touches.length !== 1) return;
		if (atEdge(touchY - e.touches[0].clientY)) e.preventDefault();
		touchY = e.touches[0].clientY;
	};
	node.addEventListener('wheel', onWheel, { passive: false });
	node.addEventListener('touchstart', onTouchStart, { passive: true });
	node.addEventListener('touchmove', onTouchMove, { passive: false });
	return {
		destroy() {
			node.removeEventListener('wheel', onWheel);
			node.removeEventListener('touchstart', onTouchStart);
			node.removeEventListener('touchmove', onTouchMove);
		},
	};
}
