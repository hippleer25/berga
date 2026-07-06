// Returns the pixel coordinates of the caret in a <textarea>, relative to the viewport.
// Uses the mirror-<div> technique: clone the textarea's box model into a hidden div,
// render the text up to the caret inside a marker span, and measure its bounding rect.
export function textareaCaretCoordinates(
	textarea: HTMLTextAreaElement,
	position: number,
): { top: number; left: number; height: number } {
	const style = window.getComputedStyle(textarea);
	const properties = [
		'boxSizing', 'width', 'height',
		'overflowX', 'overflowY',
		'borderTopWidth', 'borderRightWidth', 'borderBottomWidth', 'borderLeftWidth',
		'paddingTop', 'paddingRight', 'paddingBottom', 'paddingLeft',
		'fontStyle', 'fontVariant', 'fontWeight', 'fontStretch', 'fontSize', 'fontSizeAdjust',
		'lineHeight', 'fontFamily',
		'textAlign', 'textTransform', 'textIndent', 'textDecoration',
		'letterSpacing', 'wordSpacing', 'tabSize',
	];

	const mirror = document.createElement('div');
	mirror.classList.add('bergahl-caret-mirror');
	mirror.style.whiteSpace = 'pre-wrap';
	mirror.style.wordWrap = 'break-word';
	mirror.style.position = 'absolute';
	mirror.style.visibility = 'hidden';
	mirror.style.top = '0';
	mirror.style.left = '-9999px';
	for (const prop of properties as string[]) {
		(mirror.style as unknown as Record<string, string>)[prop] = (style as unknown as Record<string, string>)[prop];
	}

	document.body.appendChild(mirror);
	const value = textarea.value;
	const before = value.slice(0, position);
	const atCaret = value.slice(position);
	const marker = '\u200b';
	mirror.textContent = before;
	const span = document.createElement('span');
	span.textContent = marker;
	mirror.appendChild(span);
	mirror.appendChild(document.createTextNode(atCaret));

	const rect = textarea.getBoundingClientRect();
	const spanRect = span.getBoundingClientRect();
	const mirrorRect = mirror.getBoundingClientRect();

	const coords = {
		top: rect.top + (spanRect.top - mirrorRect.top) - textarea.scrollTop,
		left: rect.left + (spanRect.left - mirrorRect.left) - textarea.scrollLeft,
		height: span.getBoundingClientRect().height || parseFloat(style.lineHeight) || 18,
	};

	mirror.remove();
	return coords;
}