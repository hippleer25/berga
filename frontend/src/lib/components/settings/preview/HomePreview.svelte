<script lang="ts">
	import Bookmark from '@lucide/svelte/icons/bookmark';
	import FolderOpen from '@lucide/svelte/icons/folder-open';
	import Rss from '@lucide/svelte/icons/rss';
	import Tag from '@lucide/svelte/icons/tag';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import { t } from 'svelte-i18n';
</script>

<div class="home-preview">
	<div class="welcome-section">
		<h1 class="welcome-title">{$t('navbar.home')}</h1>
	</div>

	<div class="filter-bar">
		<span class="mode-pill">
			<button class="mode-btn" class:active={true} type="button">
				<span class="mode-ic"><Bookmark size={13} /></span>
				<span class="mode-t">All</span>
			</button>
			<button class="mode-btn" type="button">
				<span class="mode-ic"><Bookmark size={13} /></span>
				<span class="mode-t">Saved</span>
			</button>
			<button class="mode-btn" type="button">
				<span class="mode-ic"><Bookmark size={13} /></span>
				<span class="mode-t">Liked</span>
			</button>
		</span>

		<button class="filter-chip chip-active" type="button">
			<span class="chip-ic"><FolderOpen size={13} /></span>
			<span class="chip-label">Folder</span>
			<span class="chip-clear"><ChevronDown size={12} /></span>
		</button>
		<button class="filter-chip" type="button">
			<span class="chip-ic"><Rss size={13} /></span>
			<span class="chip-label">Feed</span>
			<span class="chip-clear"><ChevronDown size={12} /></span>
		</button>
		<button class="filter-chip" type="button">
			<span class="chip-ic"><Tag size={13} /></span>
			<span class="chip-label">Tag</span>
			<span class="chip-clear"><ChevronDown size={12} /></span>
		</button>
	</div>

	<div class="preview-cards">
		<span class="pv-line"></span>
		<span class="pv-line"></span>
		<span class="pv-line short"></span>
	</div>
</div>

<style>
	.home-preview {
		position: relative;
		display: flex;
		flex-direction: column;
		gap: 12px;
		max-width: 30rem;
	}
	/* Welcome replica — reacts to --font-page-title + data-welcome-style */
	.welcome-section {
		padding-top: var(--welcome-space-top, 0rem);
	}
	.welcome-title {
		margin: 0;
		font-family: var(--font-page-title);
		font-size: 1.7rem;
		font-weight: 600;
		letter-spacing: -0.02em;
		line-height: 1.1;
		color: var(--color-base-content);
	}
	:global([data-welcome-style='regular']) .welcome-title { font-weight: 400; }
	:global([data-welcome-style='bold']) .welcome-title { font-weight: 800; }
	:global([data-welcome-style='italic']) .welcome-title { font-style: italic; font-weight: 500; }

	/* Filter chips replica — reuses .mode-btn/.filter-chip class names so the
	   global [data-chip-icons] rules in app.css hide icons for free. */
	.filter-bar {
		display: flex;
		align-items: center;
		gap: 6px;
		overflow: hidden;
	}
	.mode-pill { display: inline-flex; border: var(--ui-border-width, 1px) solid var(--ui-border-color); border-radius: var(--ui-radius-chip, var(--ui-radius-sm)); overflow: hidden; }
	.mode-btn {
		display: inline-flex; align-items: center; gap: 5px;
		padding: 6px 10px; border: none; background: transparent;
		font-size: 12px; font-weight: 600; font-family: inherit;
		color: color-mix(in oklch, var(--color-base-content) 65%, transparent);
		cursor: pointer;
	}
	.mode-btn.active { color: var(--color-accent); background: color-mix(in oklch, var(--color-accent) 10%, transparent); }
	.mode-ic { display: flex; }

	.filter-chip {
		display: inline-flex; align-items: center; gap: 5px;
		padding: 6px 10px;
		border: var(--ui-border-width, 1px) solid var(--btn-border-color, var(--ui-border-color));
		border-radius: var(--ui-radius-chip, var(--ui-radius-sm));
		background: var(--btn-fill, transparent);
		font-size: 12px; font-weight: 600; font-family: inherit;
		color: color-mix(in oklch, var(--color-base-content) 70%, transparent);
		cursor: pointer; white-space: nowrap;
	}
	.filter-chip.chip-active { color: var(--color-accent); border-color: color-mix(in oklch, var(--color-accent) 45%, transparent); }
	.chip-ic { display: flex; }
	.chip-clear { display: flex; color: color-mix(in oklch, var(--color-base-content) 40%, transparent); }

	.preview-cards { display: flex; flex-direction: column; gap: 7px; padding-top: 2px; }
	.pv-line {
		display: block;
		width: 94%;
		height: 9px;
		border-radius: var(--ui-radius-full);
		background: color-mix(in oklch, var(--color-base-content) 12%, transparent);
	}
	.pv-line.short { width: 62%; }
</style>
