<script lang="ts">
	import { t } from 'svelte-i18n';
	import { activeTabIdx, navVisible, stackedScreenOpen } from '$lib/stores/swipe';
	import { orderedTabs } from '$lib/config/tabs';

	const tabIdx = $derived($activeTabIdx);
	const covered = $derived($stackedScreenOpen);
</script>

<!-- ── Mobile Bottom Nav ─────────────────────────────────── -->
<nav
	class="mobile-nav"
	class:nav-hidden={!$navVisible}
	class:covered
	aria-label="{$t('navbar.mainNav')}"
>
	{#each $orderedTabs as tab, i (tab.id)}
		{@const active = tabIdx === i}

		<a
			href={tab.href}
			class="nav-item"
			class:active
			aria-current={active ? 'page' : undefined}
		>
			<span class="nav-icon">
				<span class="nav-pill"></span>
				<tab.icon size={21} strokeWidth={active ? 2.2 : 1.8} />
			</span>
			<span class="nav-label">{$t(`navbar.${tab.id}`)}</span>
		</a>
	{/each}
</nav>

<!-- ── Desktop Sidebar ───────────────────────────────────── -->
<aside class="sidebar" class:covered aria-label="{$t('navbar.mainNav')}">
	<div class="sidebar-inner">
		<div class="brand"></div>
		<nav class="sidebar-nav">
			{#each $orderedTabs as tab, i (tab.id)}
				{@const active = tabIdx === i}
				<a
					href={tab.href}
					class="sidebar-item"
					class:active
					aria-current={active ? 'page' : undefined}
					title={$t(`navbar.${tab.id}`)}
				>
					<tab.icon size={20} strokeWidth={active ? 2.2 : 1.6} />
					<span class="s-label">{$t(`navbar.${tab.id}`)}</span>
				</a>
			{/each}
		</nav>
	</div>
</aside>

<style>
	/* ── Mobile Nav ──────────────────────────────────────── */
	.mobile-nav {
		display: flex;
		position: fixed;
		bottom: 0; left: 0; right: 0;
		z-index: 50;
		height: 64px;
		padding: 0 8px env(safe-area-inset-bottom, 8px);
		align-items: center;
		justify-content: center;
		background: var(--glass-bg);
		backdrop-filter: var(--glass-blur);
		-webkit-backdrop-filter: var(--glass-blur);
		border-top: 1px solid var(--glass-border);
		box-shadow: 0 -4px 20px color-mix(in oklch, black 10%, transparent);
		transition: transform 320ms cubic-bezier(0.4, 0, 0.2, 1), opacity 220ms ease;
	}
	.mobile-nav.nav-hidden,
	.mobile-nav.covered {
		transform: translateY(calc(100% + env(safe-area-inset-bottom, 0px)));
	}

	/* ── Floating deck variant ────────────────────────────── */
	:global([data-nav-style="deck"]) .mobile-nav {
		bottom: calc(env(safe-area-inset-bottom, 8px) + 14px);
		width: var(--deck-width, 73vw);
		left: calc(50% - var(--deck-width, 73vw) / 2);
		height: var(--deck-height, 16vw);
		padding: 0 12px;
		background: var(--glass-bg-strong);
		border: var(--ui-border-width, 1px) solid var(--ui-border-color, var(--glass-border));
		border-radius: var(--deck-radius, var(--ui-radius-xl));
		overflow: hidden;
		box-shadow:
			0 10px 30px color-mix(in oklch, black 14%, transparent),
			0 2px 6px color-mix(in oklch, black 8%, transparent);
	}
	:global([data-nav-style="deck"]) .mobile-nav.nav-hidden,
	:global([data-nav-style="deck"]) .mobile-nav.covered {
		transform: translateY(calc(100% + env(safe-area-inset-bottom, 0px) + 26px));
	}

	@media (min-width: 768px) { .mobile-nav { display: none; } }

	/* ── Nav items (shared by bar + deck) ────────────────── */
	.nav-item {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 2px;
		flex: 1;
		max-width: 80px;
		height: 100%;
		padding: 6px 4px;
		border-radius: var(--ui-radius-sm);
		text-decoration: none;
		-webkit-tap-highlight-color: transparent;
		color: color-mix(in oklch, var(--color-base-content) 58%, transparent);
		transition: color 180ms ease, background 180ms ease;
	}
	.nav-item.active {
		color: var(--color-accent);
	}

	/* Modern indicator: the icon sits above a fixed-size pill that
	   pops in accent-tinted behind the active tab's icon only. The pill
	   is a background layer — the icon always stays visible. */
	.nav-icon {
		position: relative;
		display: flex;
		align-items: center;
		justify-content: center;
		width: 52px;
		height: 28px;
	}
	.nav-pill {
		position: absolute;
		inset: 0;
		border-radius: var(--ui-radius-full);
		background: transparent;
		opacity: 0;
		transform: scale(0.5);
		transition:
			background 220ms ease,
			transform 320ms cubic-bezier(0.34, 1.56, 0.64, 1),
			opacity 200ms ease;
	}
	.nav-item.active .nav-pill {
		background: color-mix(in oklch, var(--color-accent) 16%, transparent);
		opacity: 1;
		transform: scale(1);
	}
	.nav-item.active:active .nav-pill {
		transform: scale(0.94);
	}

	/* Classic indicator: the whole item lights up (old look) */
	:global([data-nav-indicator="classic"]) .nav-item.active {
		background: color-mix(in oklch, var(--color-accent) 13%, transparent);
	}
	:global([data-nav-indicator="classic"]) .nav-pill {
		background: transparent;
		opacity: 0;
		transform: none;
	}
	:global([data-nav-style="deck"][data-nav-indicator="classic"]) .nav-item {
		border-radius: var(--ui-radius-full);
	}

	.nav-label {
		font-size: 11px;
		font-weight: 500;
		letter-spacing: 0.02em;
	}
	.nav-item.active .nav-label {
		font-weight: 700;
	}

	@media (prefers-reduced-motion: reduce) {
		.nav-pill {
			transition: none !important;
		}
		.nav-item.active .nav-pill {
			transform: none;
		}
	}

	/* ── Desktop sidebar ───────────────────────────────── */
	.sidebar { display: none; }
	.sidebar.covered { pointer-events: none; }
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
		display: flex;
		flex-direction: column;
		height: 100%;
		padding: 24px 16px 32px;
		gap: 8px;
	}

	.brand { padding: 4px 8px 20px; }

	.sidebar-nav {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.sidebar-item {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 10px 16px;
		border-radius: var(--ui-radius-sm);
		border-left: 3px solid transparent;
		text-decoration: none;
		color: color-mix(in oklch, var(--color-base-content) 60%, transparent);
		position: relative;
		overflow: hidden;
		transition: color 150ms ease, background 150ms ease, border-color 150ms ease;
	}

	.sidebar-item:hover {
		color: var(--color-base-content);
		background: var(--color-base-200);
	}

	/* Active State: Strong Contrast with Border and Accent */
	.sidebar-item.active {
		color: var(--color-accent);
		background: color-mix(in oklch, var(--color-accent) 8%, transparent);
		border-left-color: var(--color-accent);
	}

	.s-label {
		font-size: 14px;
		font-weight: 500;
		letter-spacing: 0.01em;
	}

	.sidebar-item.active .s-label {
		font-weight: 700;
	}
</style>