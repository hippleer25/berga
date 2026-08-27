<script lang="ts">
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

	const { children } = $props();

	const tabs = [
		{ key: 'appearance', href: '/settings/appearance', icon: Palette },
		{ key: 'highlights', href: '/settings/highlights', icon: Highlighter },
		{ key: 'subscriptions', href: '/settings/data', icon: Database },
		{ key: 'affinity', href: '/settings/affinity', icon: Sparkles },
		{ key: 'tags', href: '/settings/tags', icon: Tag },
		{ key: 'account', href: '/settings/account', icon: User },
	];

	function isActive(href: string): boolean {
		return $page.url.pathname === href || $page.url.pathname.startsWith(href + '/');
	}
</script>

<!-- Mobile Bottom Tab Bar -->
<nav class="mobile-tabs" aria-label="{$t('settings.title')}">
	{#each tabs as tab}
		<a
			href={tab.href}
			class="mobile-tab"
			class:active={isActive(tab.href)}
			aria-current={isActive(tab.href) ? 'page' : undefined}
			use:ripple
		>
			<span class="icon-wrap">
				<tab.icon size={22} strokeWidth={isActive(tab.href) ? 2.2 : 1.8} />
			</span>
			<span class="tab-label">{$t(tab.key === 'tags' ? 'tags.title' : `settings.${tab.key === 'subscriptions' ? 'subscriptions' : tab.key}`)}</span>
		</a>
	{/each}
</nav>

<!-- Desktop Sidebar -->
<aside class="sidebar" aria-label="{$t('settings.title')}">
	<div class="sidebar-inner">
		<div class="brand"></div>
		<nav class="sidebar-nav">
			<a
				href="/home"
				class="sidebar-item"
				use:ripple
				title={$t('settings.back')}
			>
				<ArrowLeft size={20} strokeWidth={1.6} />
				<span class="s-label">{$t('settings.back')}</span>
			</a>
			<div class="sidebar-divider"></div>
			{#each tabs as tab}
				<a
					href={tab.href}
					class="sidebar-item"
					class:active={isActive(tab.href)}
					aria-current={isActive(tab.href) ? 'page' : undefined}
					use:ripple
		title={tab.key === 'tags' ? $t('tags.title') : $t(`settings.${tab.key === 'subscriptions' ? 'subscriptions' : tab.key}`)}
	>
		<tab.icon size={20} strokeWidth={isActive(tab.href) ? 2.2 : 1.6} />
		<span class="s-label">{tab.key === 'tags' ? $t('tags.title') : $t(`settings.${tab.key === 'subscriptions' ? 'subscriptions' : tab.key}`)}</span>
				</a>
			{/each}
		</nav>
	</div>
</aside>

<!-- Mobile Top Bar (Back Button) -->
<header class="mobile-top-bar">
  <button class="ghost-btn back-btn" onclick={() => window.location.href = '/home'} title={$t('settings.back')}>
    <ArrowLeft size={18} />
    <span class="back-label">{$t('settings.back')}</span>
  </button>
</header>

<!-- Content -->
<div class="settings-content">
  {@render children()}
</div>

<style>
	@keyframes ripple-anim { to { transform: scale(2.8); opacity: 0; } }

	/* ── Mobile Top Bar (Back Button) ─────────────────── */
.mobile-top-bar {
  display: flex;
  align-items: center;
  position: sticky;
  top: 0;
  z-index: 20;
  background: var(--color-base-100);
  border-bottom: 1px solid var(--color-base-300);
  padding: 8px 16px;
}
@media (min-width: 768px) {
  .mobile-top-bar { display: none; }
}

.ghost-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  background: transparent;
  border: none;
  padding: 6px 8px;
  border-radius: 6px;
  color: color-mix(in oklch, var(--color-base-content) 60%, transparent);
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition: background 140ms, color 140ms;
}
.ghost-btn:hover {
  background: var(--color-base-200);
  color: var(--color-base-content);
}

.back-btn { margin-right: 8px; }
.back-label { display: none; }
@media (min-width: 768px) {
  .back-label { display: inline; }
}

/* ── Mobile Tab Bar ────────────────────────────────── */
	.mobile-tabs {
		display: flex;
		position: fixed;
		bottom: 0; left: 0; right: 0;
		z-index: 50;
		height: 64px;
		padding: 0 8px env(safe-area-inset-bottom, 8px);
		align-items: center;
		justify-content: space-around;
		background: var(--color-base-100);
		border-top: 1px solid var(--color-base-200);
	}
	@media (min-width: 768px) { .mobile-tabs { display: none; } }

	.mobile-tab {
		display: flex; flex-direction: column; align-items: center; gap: 4px;
		flex: 1; padding: 8px 4px; position: relative; overflow: hidden;
		border-radius: 8px; text-decoration: none; -webkit-tap-highlight-color: transparent;
		color: color-mix(in oklch, var(--color-base-content) 60%, transparent);
		transition: color 180ms ease;
	}
	.icon-wrap { display: flex; align-items: center; justify-content: center; width: 40px; height: 28px; }
	.tab-label { font-size: 11px; font-weight: 500; letter-spacing: 0.02em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 72px; text-align: center; }
	.mobile-tab.active { color: var(--color-accent); }
	.mobile-tab.active .tab-label { font-weight: 700; }

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
		padding: 10px 16px; border-radius: 6px;
		border-left: 3px solid transparent;
		text-decoration: none;
		color: color-mix(in oklch, var(--color-base-content) 60%, transparent);
		position: relative; overflow: hidden;
		transition: color 150ms ease, background 150ms ease, border-color 150ms ease;
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
  padding: 20px 16px 0;
  padding-bottom: calc(64px + env(safe-area-inset-bottom, 8px));
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
</style>
