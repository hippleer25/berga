export function ripple(node: HTMLElement) {
	function handleClick(e: MouseEvent) {
		const circle = document.createElement('span');
		const rect = node.getBoundingClientRect();
		const size = Math.max(rect.width, rect.height);
		circle.style.cssText = `
			position:absolute;border-radius:50%;pointer-events:none;
			width:${size}px;height:${size}px;
			left:${e.clientX - rect.left - size / 2}px;
			top:${e.clientY - rect.top - size / 2}px;
			background:color-mix(in oklch, var(--color-base-content) 12%, transparent);
			transform:scale(0);opacity:1;
			animation:ripple-anim 480ms cubic-bezier(0.4,0,0.2,1) forwards;
		`;
		node.appendChild(circle);
		circle.addEventListener('animationend', () => circle.remove());
	}
	node.addEventListener('click', handleClick);
	return { destroy: () => node.removeEventListener('click', handleClick) };
}
