<script lang="ts">
	import { titleTextAlign, bodyTextAlign } from '$lib/stores/preferences';
	import { MOCK_ARTICLE_BODY } from './previewMocks';

	let titleAlign = $derived($titleTextAlign);
	let bodyAlign = $derived($bodyTextAlign);
</script>

<div class="article-preview">
	<article class="a-header" class:align-justify={titleAlign === 'justify'} class:align-center={titleAlign === 'center'} class:align-right={titleAlign === 'right'}>
		<div class="a-meta">
			<span class="a-feed-dot"></span>
			<span>Workshop Journal</span>
			<span class="a-sep">·</span>
			<span class="a-muted">yesterday</span>
		</div>
		<h1 class="a-title">Reading in the age of algorithmic feeds</h1>
	</article>

	<div
		class="a-body"
		class:align-justify={bodyAlign === 'justify'}
		class:align-center={bodyAlign === 'center'}
		class:align-right={bodyAlign === 'right'}
	>
		{@html MOCK_ARTICLE_BODY}
	</div>
</div>

<style>
	.article-preview { display: flex; flex-direction: column; gap: 14px; }

	/* Mirrors routes/a/[item_id]: widths key off the same vars; alignments via
	   the same class pattern. */
	.a-header { max-width: var(--article-title-max-width, 42rem); }
	.a-meta {
		display: flex; align-items: center; gap: 6px;
		font-size: 11.5px; color: color-mix(in oklch, var(--color-base-content) 60%, transparent);
		margin-bottom: 10px;
	}
	.a-feed-dot {
		width: 14px; height: 14px; border-radius: 50%;
		background: var(--color-accent);
		opacity: 0.8;
	}
	.a-sep { opacity: 0.5; }
	.a-muted { opacity: 0.75; }
	.a-title {
		margin: 0;
		font-family: var(--font-post-title);
		font-size: 1.55rem;
		font-weight: 500;
		line-height: 1.2;
		letter-spacing: -0.02em;
		color: var(--color-base-content);
	}
	.a-header.align-justify { text-align: justify; }
	.a-header.align-center { text-align: center; }
	.a-header.align-right { text-align: right; }

	.a-body {
		max-width: var(--article-body-max-width, var(--article-max-width, 50rem));
		font-family: var(--font-article-body);
		font-size: var(--article-font-size, 1.125rem);
		font-weight: var(--article-font-weight, 400);
		letter-spacing: var(--article-letter-spacing, normal);
		line-height: var(--article-line-height, 1.8);
		color: var(--color-base-content);
	}

	.a-body.align-justify { text-align: justify; }
	.a-body.align-center { text-align: center; }
	.a-body.align-right { text-align: right; }
	.a-body :global(p) { margin: 0 0 1em; }
	.a-body :global(img) {
		max-width: var(--article-image-width, 100%);
		height: auto;
		border-radius: var(--ui-radius-sm);
		margin: 0.6em auto;
		display: block;
	}
</style>
