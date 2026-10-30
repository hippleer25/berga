<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import Palette from '@lucide/svelte/icons/palette';
	import Sparkles from '@lucide/svelte/icons/sparkles';
	import User from '@lucide/svelte/icons/user';
	import Highlighter from '@lucide/svelte/icons/highlighter';
	import HeartPulse from '@lucide/svelte/icons/heart-pulse';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import { ripple } from '$lib/actions/ripple';
	import { t } from 'svelte-i18n';

	const sections = [
		{ key: 'appearance', href: '/settings/appearance', icon: Palette },
		{ key: 'highlights', href: '/settings/highlights', icon: Highlighter },
		{ key: 'monitor', href: '/settings/monitor', icon: HeartPulse },
		{ key: 'intelligence', href: '/settings/intelligence', icon: Sparkles },
		{ key: 'account', href: '/settings/account', icon: User },
	];

	function label(key: string): string {
		return $t(`settings.${key}`);
	}

	function desc(key: string): string {
		return $t(`settings.${key}Desc`);
	}

	// Desktop has the sidebar in the layout — jump straight to Appearance.
	$effect(() => {
		if ($page.url.pathname !== '/settings') return;
		if (window.matchMedia('(min-width: 768px)').matches) {
			goto('/settings/appearance', { replaceState: true });
		}
	});

	function open(href: string) {
		goto(href);
	}
</script>

<div class="settings-home">
	<header class="hero">
		<div class="ui-kicker hero-kicker">Berga</div>
		<h2 class="hero-title">{$t('settings.title')}</h2>
		<p class="hero-sub">{$t('settings.subtitle')}</p>
	</header>

	<nav class="settings-list" aria-label={$t('settings.title')}>
		{#each sections as s, i (s.key)}
			<button class="cell" use:ripple onclick={() => open(s.href)}>
				<span class="cell-icon">
					<s.icon size={19} strokeWidth={1.9} />
				</span>
				<span class="cell-copy">
					<span class="cell-label">{label(s.key)}</span>
					<span class="cell-desc">{desc(s.key)}</span>
				</span>
				<span class="cell-chevron"><ChevronRight size={17} strokeWidth={1.8} /></span>
			</button>
			{#if i < sections.length - 1}
				<div class="cell-divider" aria-hidden="true"></div>
			{/if}
		{/each}
	</nav>
</div>

<style>
	.settings-home {
		max-width: 42rem;
		margin: 0 auto;
		padding-top: 6px;
	}

	/* ── Hero (desktop hub header) ───────────────────────────── */
	.hero { display: none; }
	@media (min-width: 768px) {
		.hero {
			display: flex;
			flex-direction: column;
			gap: 4px;
			margin: 4px 0 10px;
		}
	}
	.hero-kicker { color: var(--color-accent); }
	.hero-title {
		font-family: var(--font-page-title, var(--font-ui));
		font-size: 26px;
		font-weight: 700;
		letter-spacing: -0.02em;
		color: var(--color-base-content);
		margin: 0;
		line-height: 1.2;
	}
	.hero-sub {
		font-size: 13.5px;
		line-height: 1.45;
		color: var(--ui-text-subtle);
		margin: 0;
	}

	/* ── Section list: rows on mobile, cards on desktop ──────── */
	.settings-list {
		display: flex;
		flex-direction: column;
		background: color-mix(in oklch, var(--color-base-100) 60%, transparent);
		border: var(--ui-border-width) solid var(--ui-border-color);
		border-radius: var(--ui-radius-lg);
		overflow: hidden;
	}

	.cell {
		display: flex;
		align-items: center;
		gap: 14px;
		width: 100%;
		padding: 13px 14px;
		background: transparent;
		border: none;
		cursor: pointer;
		text-align: left;
		font-family: inherit;
		position: relative;
		overflow: hidden;
		color: var(--color-base-content);
		transition: background 130ms ease;
	}
	.cell:hover { background: var(--color-base-200); }
	.cell:active { background: color-mix(in oklch, var(--color-base-content) 7%, transparent); }

	.cell-icon {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 34px;
		height: 34px;
		flex-shrink: 0;
		border-radius: var(--ui-radius-sm);
		background: color-mix(in oklch, var(--color-accent) 14%, transparent);
		color: var(--color-accent);
	}

	.cell-copy {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: 2px;
		min-width: 0;
	}
	.cell-label {
		font-size: 15px;
		font-weight: 600;
		letter-spacing: -0.01em;
	}
	.cell-desc {
		font-size: 12px;
		line-height: 1.4;
		color: var(--ui-text-subtle);
	}

	.cell-chevron {
		display: flex;
		flex-shrink: 0;
		color: color-mix(in oklch, var(--color-base-content) 38%, transparent);
		transition: color 130ms ease;
	}
	.cell:hover .cell-chevron {
		color: color-mix(in oklch, var(--color-base-content) 62%, transparent);
	}

	.cell-divider {
		height: 1px;
		margin-left: 62px;
		background: var(--ui-hairline, var(--color-base-300));
	}

	/* ── Desktop: standalone card grid ───────────────────────── */
	@media (min-width: 768px) {
		.settings-list {
			display: grid;
			grid-template-columns: repeat(2, minmax(0, 1fr));
			gap: 12px;
			background: none;
			border: none;
			border-radius: 0;
			padding: 0;
			overflow: visible;
		}
		.cell-divider { display: none; }
		.cell {
			padding: 14px 16px;
			border: var(--ui-border-width) solid var(--ui-border-color);
			border-radius: var(--ui-radius-lg);
			background: color-mix(in oklch, var(--color-base-100) 70%, transparent);
			transition:
				border-color var(--ui-dur-2) var(--ui-ease),
				transform var(--ui-dur-1) var(--ui-ease),
				box-shadow var(--ui-dur-2) var(--ui-ease),
				background-color var(--ui-dur-2) var(--ui-ease);
		}
		.cell:hover {
			border-color: var(--ui-border-strong, var(--color-base-300));
			transform: translateY(-1px);
			box-shadow: var(--ui-shadow-1);
		}
		.cell:last-child { grid-column: 1 / -1; }
	}
</style>
