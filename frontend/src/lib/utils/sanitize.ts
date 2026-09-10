// Lightweight sanitizer for rich-text previews (post-card descriptions).
// Keeps only inline emphasis/formatting tags, strips attributes, drops
// interactive/media elements. Output is safe to inject with {@html}.

const INLINE_TAGS = new Set([
	'B',
	'STRONG',
	'I',
	'EM',
	'U',
	'S',
	'DEL',
	'STRIKE',
	'CODE',
	'MARK',
	'SUB',
	'SUP',
	'SMALL',
]);

function plainText(html: string): string {
	return html
		.replace(/<br\s*[\/]?>/gi, ' ')
		.replace(/<[^>]+>/g, '')
		.replace(/\s{2,}/g, ' ')
		.trim();
}

export function sanitizeInlineHtml(html: string): string {
	if (typeof DOMParser === 'undefined') return plainText(html);

	const doc = new DOMParser().parseFromString(html, 'text/html');

	function walk(node: Node): string {
		if (node.nodeType === Node.TEXT_NODE) return node.textContent ?? '';
		if (node.nodeType !== Node.ELEMENT_NODE) return '';
		const el = node as Element;
		const tag = el.tagName.toUpperCase();

		if (tag === 'SCRIPT' || tag === 'STYLE' || tag === 'IFRAME' || tag === 'IMG' || tag === 'VIDEO' || tag === 'SVG') {
			return '';
		}
		// Links: keep the text (previews shouldn't navigate/spam), drop the anchor.
		if (tag === 'A') return el.textContent ?? '';
		if (tag === 'BR') return '<br>';

		const inner = Array.from(el.childNodes).map(walk).join('');
		if (tag === 'P' || tag === 'DIV') return ` ${inner} `;
		if (INLINE_TAGS.has(tag)) return `<${tag.toLowerCase()}>${inner}</${tag.toLowerCase()}>`;
		return inner;
	}

	return Array.from(doc.body.childNodes)
		.map(walk)
		.join('')
		.replace(/[ \t]{2,}/g, ' ')
		.replace(/>\s+</g, '><')
		.trim();
}