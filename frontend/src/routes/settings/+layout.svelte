<script module lang="ts">
	// True once the settings list ("/settings") has been mounted in the
	// current settings session — lets sub-pages go back to it.
	let settingsListVisited = false;
</script>

<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import ArrowLeft from '@lucide/svelte/icons/arrow-left';
	import Palette from '@lucide/svelte/icons/palette';
	import Database from '@lucide/svelte/icons/database';
	import Sparkles from '@lucide/svelte/icons/sparkles';
	import User from '@lucide/svelte/icons/user';
	import Tag from '@lucide/svelte/icons/tag';
	import Highlighter from '@lucide/svelte/icons/highlighter';
	import { ripple } from '$lib/actions/ripple';
	import { t } from 'svelte-i18n';
	import ScreenShell from '$lib/components/ScreenShell.svelte';
	import { closeScreen } from '$lib/utils/screenStack';

	const { children } = $props();

	const tabs = [
		{ key: 'appearance', href: '/settings/appearance', icon: Palette },
		{ key: 'highlights', href: '/settings/highlights', icon: Highlighter },
		{ key: 'subscriptions', href: '/settings/data', icon: Database },
		{ key: 'affinity', href: '/settings/affinity', icon: Sparkles },
		{ key: 'tags', href: '/settings/tags', icon: Tag },
		{ key: 'account', href: '/settings/account', icon: User },
	];

	function label(key: string): string {
		return key === 'tags'
			? $t('tags.title')
			: $t(`settings.${key === 'subscriptions' ? 'subscriptions' : key}`);
	}

	function isActive(href: string): boolean {
		return $page.url.pathname === href || $page.url.pathname.startsWith(href + '/');
	}

	const onList = $derived($page.url.pathname === '/settings');

	const currentTitle = $derived.by(() => {
		if (onList) return $t('settings.title');
		const tab = tabs.find(t => isActive(t.href));
		return tab ? label(tab.key) : $t('settings.title');
	});

	// Mark the list as visited so sub-pages know "back" means drill-down.
	$effect(() => {
		if (onList) settingsListVisited = true;
	});
	// Leaving the settings route group entirely resets the session flag.
	$effect(() => {
		return () => { settingsListVisited = false; };
	});

	// Sub-navigation: drill-in (push) on mobile; the desktop sidebar keeps
	// replaceState so the whole settings session stays one history entry.
	function openTab(href: string) {
		if (window.matchMedia('(min-width: 768px)').matches) {
			goto(href, { replaceState: true });
		} else {
			goto(href);
		}
	}

	function goBack() {
		if (onList) {
			closeScreen();
			return;
		}
		if (settingsListVisited) {
			history.back();
		} else {
			closeScreen();
		}
	}
</script>

<ScreenShell>
	<!-- Desktop Sidebar -->
	<aside class="sidebar" aria-label="{$t('settings.title')}">
		<div class="sidebar-inner">
			<div class="brand"></div>
			<nav class="sidebar-nav">
				<button
					class="sidebar-item"
					use:ripple
					title={$t('settings.back')}
					onclick={() => closeScreen()}
				>
					<ArrowLeft size={20} strokeWidth={1.6} />
					<span class="s-label">{$t('settings.back')}</span>
				</button>
				<div class="sidebar-divider"></div>
				{#each tabs as tab}
					<a
						href={tab.href}
						class="sidebar-item"
						class:active={isActive(tab.href)}
						aria-current={isActive(tab.href) ? 'page' : undefined}
						use:ripple
						title={label(tab.key)}
						onclick={(e) => { e.preventDefault(); openTab(tab.href); }}
					>
						<tab.icon size={20} strokeWidth={isActive(tab.href) ? 2.2 : 1.6} />
						<span class="s-label">{label(tab.key)}</span>
					</a>
				{/each}
			</nav>
		</div>
	</aside>

	<!-- Mobile Top Bar (Back + Title) -->
	<header class="mobile-top-bar">
		<button class="ghost-btn back-btn" onclick={() => goBack()} title={$t('settings.back')}>
			<ArrowLeft size={18} />
		</button>
		<span class="top-title">{currentTitle}</span>
		<span class="top-spacer"></span>
	</header>

	<!-- Content -->
	<div class="settings-content" class:on-list={onList}>
		{@render children()}
	</div>
</ScreenShell>

<style>
	@keyframes ripple-anim { to { transform: scale(2.8); opacity: 0; } }

	/* ── Mobile Top Bar (Back Button) ─────────────────── */
.mobile-top-bar {
  display: flex;
  align-items: center;
  gap: 4px;
  position: sticky;
  top: 0;
  z-index: 20;
  background: var(--glass-bg);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
  border-bottom: 1px solid var(--glass-border);
  padding: 10px 12px;
}
@media (min-width: 768px) {
  .mobile-top-bar { display: none; }
}

.top-title {
  flex: 1;
  text-align: center;
  font-size: 15px;
  font-weight: 700;
  color: var(--color-base-content);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.top-spacer { width: 34px; flex-shrink: 0; }

.ghost-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  background: transparent;
  border: none;
  padding: 6px 8px;
  border-radius: var(--ui-radius-sm);
  color: color-mix(in oklch, var(--color-base-content) 60%, transparent);
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition: background 140ms, color 140ms;
  width: 34px;
  flex-shrink: 0;
}
.ghost-btn:hover {
  background: var(--color-base-200);
  color: var(--color-base-content);
}

.back-btn { margin-right: 0; }

/* ── Desktop Sidebar ───────────────────────────────── */
	.sidebar { display: none; }
	@media (min-width: 768px) {
		.sidebar {
			display: flex;
			position: fixed;
			top: 0; left: 0; bottom: 0;
			z-index: 50;
			width: 240px;
			flex-direction: column;
			background: var(--color-base-100);
			border-right: 1px solid var(--color-base-200);
		}
	}

	.sidebar-inner {
		display: flex; flex-direction: column; height: 100%;
		padding: 24px 16px 32px; gap: 8px;
	}
	.brand { padding: 4px 8px 20px; }

	.sidebar-nav {
		display: flex; flex-direction: column; gap: 2px;
	}

	.sidebar-divider {
		height: 1px;
		background: var(--color-base-300);
		margin: 8px 0 4px;
	}

	.sidebar-item {
		display: flex; align-items: center; gap: 12px;
		padding: 10px 16px; border-radius: var(--ui-radius-sm);
		border-left: 3px solid transparent;
		text-decoration: none;
		color: color-mix(in oklch, var(--color-base-content) 60%, transparent);
		position: relative; overflow: hidden;
		transition: color 150ms ease, background 150ms ease, border-color 150ms ease;
		width: 100%;
		background: none;
		border-top: none; border-right: none; border-bottom: none;
		cursor: pointer;
		font-family: inherit;
		text-align: left;
	}
	.sidebar-item:hover {
		color: var(--color-base-content);
		background: var(--color-base-200);
	}
.sidebar-item.active {
  color: var(--color-accent);
  background: color-mix(in oklch, var(--color-accent) 8%, transparent);
  border-left-color: var(--color-accent);
}
	.s-label { font-size: 14px; font-weight: 500; letter-spacing: 0.01em; }
	.sidebar-item.active .s-label { font-weight: 700; }

	/* ── Content Area ──────────────────────────────────── */
.settings-content {
  min-height: 100dvh;
  background: var(--color-base-100);
  padding: 16px 16px 0;
  padding-bottom: calc(env(safe-area-inset-bottom, 8px) + 32px);
}
	@media (min-width: 768px) {
		.settings-content {
			margin-left: max(240px, calc(50vw - 21rem));
			margin-right: auto;
			max-width: 42rem;
			padding: 24px 0;
			padding-bottom: 48px;
		}
	}

	/* The mobile top bar already shows the section name */
	@media (max-width: 767.98px) {
		.settings-content :global(h2.section-title:first-child) {
			display: none;
		}
	}
</style>
