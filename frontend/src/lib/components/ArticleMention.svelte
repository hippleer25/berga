<script lang="ts">
	import { apiFetch } from '$lib/api';
	import { textareaCaretCoordinates } from '$lib/utils/caret';
	import { t } from 'svelte-i18n';

	type SearchResult = {
		item_id: string;
		title: string;
		description?: string;
		feed_title?: string;
		feed_icon?: string;
		link?: string;
	};

	let {
		textarea,
		onaccept,
	}: {
		textarea: HTMLTextAreaElement | null | undefined;
		onaccept: (snippet: string, start: number, end: number) => void;
	} = $props();

	let open = $state(false);
	let results = $state<SearchResult[]>([]);
	let activeIndex = $state(0);
	let loading = $state(false);
	let position = $state<{ top: number; left: number }>({ top: 0, left: 0 });

	// The `@query` span in the textarea value: [atIndex, caretEnd].
	let mention: { start: number; end: number } | null = null;

	let debounceTimer: ReturnType<typeof setTimeout> | null = null;
	let abortController: AbortController | null = null;
	let blurTimer: ReturnType<typeof setTimeout> | null = null;

	const DROPDOWN_MAX_HEIGHT = 280;

	function close() {
		open = false;
		results = [];
		activeIndex = 0;
		loading = false;
		mention = null;
		if (debounceTimer) {
			clearTimeout(debounceTimer);
			debounceTimer = null;
		}
		if (abortController) {
			abortController.abort();
			abortController = null;
		}
	}

	// Find a valid `@` mention trigger ending at `caret`.
	// Returns { atIndex, query } or null.
	function detectMention(value: string, caret: number): { atIndex: number; query: string } | null {
		// Walk back from caret. The mention ends as soon as we hit a newline.
		let i = caret - 1;
		while (i >= 0 && value[i] !== '\n') {
			if (value[i] === '@') {
				const before = i === 0 ? '' : value[i - 1];
				if (i === 0 || before === ' ' || before === '\t' || before === '\n' || before === '\r') {
					const query = value.slice(i + 1, caret);
					if (query.length <= 80) {
						return { atIndex: i, query };
					}
					return null;
				}
				// `@` preceded by other chars (email) — not a mention trigger.
				return null;
			}
			i--;
		}
		return null;
	}

	function updatePosition() {
		if (!textarea) return;
		const caret = textarea.selectionEnd ?? 0;
		const coords = textareaCaretCoordinates(textarea, caret);
		const rect = textarea.getBoundingClientRect();
		let top = coords.top + coords.height + 2;
		let left = coords.left;
		// Clamp to viewport.
		const dropdownWidth = Math.min(rect.width || 360, 360);
		const maxLeft = window.innerWidth - dropdownWidth - 8;
		if (left > maxLeft) left = maxLeft;
		if (left < 8) left = 8;
		let bottom = top + DROPDOWN_MAX_HEIGHT;
		if (bottom > window.innerHeight - 8) {
			// Flip above the caret if there's no room below.
			top = coords.top - DROPDOWN_MAX_HEIGHT - 2;
			if (top < 8) top = 8;
		}
		position = { top, left };
	}

	async function runSearch(query: string) {
		if (abortController) abortController.abort();
		const ctrl = new AbortController();
		abortController = ctrl;
		loading = true;
		try {
			const res = await apiFetch(
				`/api/search?query=${encodeURIComponent(query)}&limit=8`,
				{ credentials: 'include', signal: ctrl.signal },
			);
			if (ctrl.signal.aborted) return;
			const data = (await res.json()) as SearchResult[];
			results = Array.isArray(data) ? data : [];
			activeIndex = 0;
		} catch (e) {
			if ((e as any)?.name !== 'AbortError') {
				results = [];
				activeIndex = 0;
			}
		} finally {
			if (abortController === ctrl) {
				loading = false;
				abortController = null;
			}
		}
	}

	function onInput() {
		if (!textarea) return;
		const value = textarea.value;
		const caret = textarea.selectionEnd ?? 0;
		const detected = detectMention(value, caret);
		if (!detected) {
			close();
			return;
		}
		mention = { start: detected.atIndex, end: caret };
		const query = detected.query.trim();
		open = true;
		updatePosition();
		if (debounceTimer) clearTimeout(debounceTimer);
		if (query.length === 0) {
			// Show hint with no search fired.
			results = [];
			loading = false;
			if (abortController) {
				abortController.abort();
				abortController = null;
			}
			return;
		}
		debounceTimer = setTimeout(() => {
			void runSearch(query);
		}, 200);
	}

	function onKeyDown(e: KeyboardEvent) {
		if (!open || !mention) return;
		if (e.key === 'ArrowDown') {
			if (results.length === 0) return;
			e.preventDefault();
			activeIndex = (activeIndex + 1) % results.length;
		} else if (e.key === 'ArrowUp') {
			if (results.length === 0) return;
			e.preventDefault();
			activeIndex = (activeIndex - 1 + results.length) % results.length;
		} else if (e.key === 'Enter' || e.key === 'Tab') {
			if (results.length > 0) {
				e.preventDefault();
				accept(activeIndex);
			} else {
				// No results: Enter closes the mention and lets the keystroke through.
				close();
			}
		} else if (e.key === 'Escape') {
			e.preventDefault();
			close();
		}
	}

	function accept(index: number) {
		if (!textarea || !mention) return;
		const item = results[index];
		if (!item) return;
		const snippet = `[[${item.title}^^/a/${item.item_id}]]`;
		onaccept(snippet, mention.start, mention.end);
		close();
	}

	function onBlur() {
		// Delay close so a click on a dropdown item registers first.
		blurTimer = setTimeout(() => {
			close();
		}, 150);
	}

	function onFocus() {
		if (blurTimer) {
			clearTimeout(blurTimer);
			blurTimer = null;
		}
	}

	function onItemClick(e: MouseEvent, index: number) {
		// Prevent the textarea from blurring before the click resolves.
		e.preventDefault();
		accept(index);
	}

	function itemLabel(item: SearchResult): string {
		return item.title || item.link || item.item_id;
	}

	// Attach / detach listeners when the textarea binding resolves.
	$effect(() => {
		const ta = textarea;
		if (!ta) return;
		ta.addEventListener('input', onInput);
		ta.addEventListener('keydown', onKeyDown);
		ta.addEventListener('blur', onBlur);
		ta.addEventListener('focus', onFocus);
		return () => {
			ta.removeEventListener('input', onInput);
			ta.removeEventListener('keydown', onKeyDown);
			ta.removeEventListener('blur', onBlur);
			ta.removeEventListener('focus', onFocus);
		};
	});
</script>

{#if open}
	<ul
		class="mention-dropdown bg-base-100 text-base-content border-base-300"
		style="top: {position.top}px; left: {position.left}px;"
		role="listbox"
	>
		{#if loading}
			<li class="mention-state">{$t('article.mentionLoading')}</li>
		{:else if results.length === 0}
			<li class="mention-state">{$t('article.mentionNoResults')}</li>
		{:else}
			{#each results as item, i}
				<li
					class="mention-item"
					class:active={i === activeIndex}
					role="option"
					aria-selected={i === activeIndex}
					onmousedown={(e) => onItemClick(e, i)}
				>
					<span class="mention-title">{itemLabel(item)}</span>
					{#if item.feed_title}
						<span class="mention-feed">{item.feed_title}</span>
					{/if}
				</li>
			{/each}
			<li class="mention-hint border-base-300 text-base-content/60">{$t('article.mentionHint')}</li>
		{/if}
	</ul>
{/if}

<style>
	.mention-dropdown {
		position: fixed;
		z-index: 9999;
		list-style: none;
		margin: 0;
		padding: 4px;
		width: min(360px, 92vw);
		max-height: 280px;
		overflow-y: auto;
		border: 1px solid;
		border-radius: 8px;
		box-shadow: 0 6px 24px rgba(0, 0, 0, 0.18);
		font-size: 0.85rem;
		user-select: none;
	}
	.mention-item {
		padding: 6px 8px;
		border-radius: 6px;
		cursor: pointer;
		display: flex;
		flex-direction: column;
		gap: 2px;
	}
	.mention-item:hover {
		background: color-mix(in srgb, currentColor 8%, transparent);
	}
	.mention-item.active {
		background: color-mix(in srgb, currentColor 14%, transparent);
	}
	.mention-title {
		font-weight: 500;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.mention-feed {
		font-size: 0.72rem;
		opacity: 0.6;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.mention-state {
		padding: 6px 8px;
		opacity: 0.6;
		font-style: italic;
	}
	.mention-hint {
		padding: 4px 8px 2px;
		font-size: 0.68rem;
		opacity: 0.55;
		border-top: 1px solid;
		margin-top: 2px;
	}
</style>