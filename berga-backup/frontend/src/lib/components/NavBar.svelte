<script lang="ts">
 import { House, Search, Sparkles, Rss } from '@lucide/svelte';
 import { activeTabIdx, navVisible } from '$lib/stores/swipe';
 import { t } from 'svelte-i18n';
 import { ripple } from '$lib/actions/ripple';

 const tabs = [
 { key: 'followers', href: '/followers', icon: Rss },
 { key: 'home', href: '/home', icon: House },
 { key: 'events', href: '/events', icon: Search },
 { key: 'mota', href: '/mota', icon: Sparkles }
 ];

 const tabIdx = $derived($activeTabIdx);
</script>

<!-- ── Mobile Bottom Nav ─────────────────────────────────── -->
<nav
    class="mobile-nav"
    class:nav-hidden={!$navVisible}
    aria-label="{$t('navbar.mainNav')}"
>
    {#each tabs as tab, i}
        {@const active = tabIdx === i}

        <a
            href={tab.href}
            class="nav-item"
            class:active
            aria-current={active ? 'page' : undefined}
            use:ripple
        >
            <span class="icon-wrap">
                <tab.icon size={22} strokeWidth={active ? 2.2 : 1.8} />
            </span>
            <span class="nav-label">{$t(`navbar.${tab.key}`)}</span>
        </a>
    {/each}
</nav>

<!-- ── Desktop Sidebar ───────────────────────────────────── -->
<aside class="sidebar" aria-label="{$t('navbar.mainNav')}">
    <div class="sidebar-inner">
        <div class="brand"></div>
        <nav class="sidebar-nav">
            {#each tabs as tab, i}
                {@const active = tabIdx === i}
                <a
                    href={tab.href}
                    class="sidebar-item"
                    class:active
                    aria-current={active ? 'page' : undefined}
                    use:ripple
                    title={$t(`navbar.${tab.key}`)}
                >
                    <tab.icon size={20} strokeWidth={active ? 2.2 : 1.6} />
                    <span class="s-label">{$t(`navbar.${tab.key}`)}</span>
                </a>
            {/each}
        </nav>
    </div>
</aside>

<style>
    @keyframes ripple-anim { to { transform: scale(2.8); opacity: 0; } }

    /* ── Mobile Nav ──────────────────────────────────────── */
    .mobile-nav {
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
        transition: transform 320ms cubic-bezier(0.4, 0, 0.2, 1);
    }
    .mobile-nav.nav-hidden {
        transform: translateY(calc(100% + env(safe-area-inset-bottom, 0px)));
    }

    @media (min-width: 768px) { .mobile-nav { display: none; } }

    .nav-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 4px;
        flex: 1;
        padding: 8px 4px;
        position: relative;
        overflow: hidden;
        border-radius: 8px;
        text-decoration: none;
        -webkit-tap-highlight-color: transparent;

        /* Contraste melhorado: 60% em vez de 40% */
        color: color-mix(in oklch, var(--color-base-content) 60%, transparent);
        transition: color 180ms ease;
    }

    .icon-wrap {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 40px;
        height: 28px;
    }

    .nav-label {
        font-size: 11px;
        font-weight: 500;
        letter-spacing: 0.02em;
    }

    /* Estado Ativo: Forte e Accent */
    .nav-item.active {
        color: var(--color-accent-content);
    }
    .nav-item.active .nav-label {
        font-weight: 700;
    }

    /* ── Desktop sidebar ─────────────────────────────── */
    .sidebar { display: none; }
    @media (min-width: 768px) {
        .sidebar {
            display: flex;
            position: fixed;
            top: 0; left: 0; bottom: 0;
            z-index: 50;
            width: 240px; /* Ligeiramente mais largo para caber o texto confortavelmente */
            flex-direction: column;
            background: var(--color-base-100); /* Fundo base igual ao conteúdo principal */
            border-right: 1px solid var(--color-base-200); /* Borda real que separa */
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
        gap: 2px; /* Mais compacto */
    }

    .sidebar-item {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 10px 16px;
        border-radius: 6px; /* Menos arredondado = mais robusto */
        border-left: 3px solid transparent; /* Prepara a borda para o estado ativo */
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

    /* Estado Ativo: Contraste Forte com Borda e Accent */
    .sidebar-item.active {
        color: var(--color-accent-content);
        background: color-mix(in oklch, var(--color-accent-content) 8%, transparent);
        border-left-color: var(--color-accent-content); /* A barra lateral de destaque */
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