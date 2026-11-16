/**
 * Find-in-page utilities built on the CSS Custom Highlight API.
 * Matches are returned as Ranges so the DOM is never mutated
 * (safe to combine with existing user-highlight <mark> nodes).
 */

const SKIP_TAGS = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEXTAREA', 'INPUT', 'SELECT']);

function collectTextNodes(root: Node): Text[] {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
    const nodes: Text[] = [];
    let node: Text | null;
    while ((node = walker.nextNode() as Text | null)) {
        if (!SKIP_TAGS.has(node.parentElement?.tagName ?? '')) {
            nodes.push(node);
        }
    }
    return nodes;
}

/** Find all case-insensitive occurrences of `query` under `root`, capped at `max`. */
export function findMatches(root: HTMLElement, query: string, max = 500): Range[] {
    const matches: Range[] = [];
    const q = query.toLowerCase();
    if (!q || max <= 0) return matches;

    const textNodes = collectTextNodes(root);
    if (textNodes.length === 0) return matches;

    // Concatenated document text + per-node [start, end) offsets.
    const fullText: string[] = [];
    const offsets: number[] = new Array(textNodes.length);
    let total = 0;
    for (let i = 0; i < textNodes.length; i++) {
        offsets[i] = total;
        const t = textNodes[i].textContent ?? '';
        fullText.push(t);
        total += t.length;
    }
    const haystack = fullText.join('').toLowerCase();

    let from = 0;
    while (matches.length < max) {
        const idx = haystack.indexOf(q, from);
        if (idx === -1) break;

        const end = idx + q.length;

        // Locate the node holding the start of the match.
        let startIdx = -1;
        for (let i = 0; i < textNodes.length; i++) {
            if (offsets[i] <= idx && idx < offsets[i] + (textNodes[i].textContent?.length ?? 0)) {
                startIdx = i;
                break;
            }
        }
        // Locate the node holding the end of the match.
        let endIdx = -1;
        for (let i = startIdx; i < textNodes.length; i++) {
            if (offsets[i] < end && end <= offsets[i] + (textNodes[i].textContent?.length ?? 0)) {
                endIdx = i;
                break;
            }
        }
        if (startIdx === -1 || endIdx === -1) break;

        const range = document.createRange();
        try {
            range.setStart(textNodes[startIdx], idx - offsets[startIdx]);
            range.setEnd(textNodes[endIdx], end - offsets[endIdx]);
            matches.push(range);
        } catch {
            break;
        }
        from = end;
    }

    return matches;
}

/** Smooth-scroll `container` so `range` sits ~1/3 from the top of the viewport. */
export function scrollRangeIntoView(container: HTMLElement, range: Range) {
    const rect = range.getBoundingClientRect();
    const box = container.getBoundingClientRect();
    const target = rect.top - box.top - box.height / 3 + container.scrollTop;
    container.scrollTo({ top: Math.max(0, target), behavior: 'smooth' });
}
