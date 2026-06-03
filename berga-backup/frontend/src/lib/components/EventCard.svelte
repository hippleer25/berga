<script lang="ts">
    import { t } from 'svelte-i18n';
import { get } from 'svelte/store';

    let { event, rank } = $props<{
        rank: number;
        event: {
            summary: string;
            article_count: number;
            unique_feeds: number;
            articles: {
                item_id?: string;
                title: string;
                url: string;
                source: string;
                published_at: string;
            }[];
        };
    }>();

    let publishers = $derived.by(() => {
        const seen = new Set<string>();
        const result: { source: string; icon: string }[] = [];
        for (const a of event.articles) {
            if (a.source && !seen.has(a.source)) {
                seen.add(a.source);
                const domain = (() => {
                    try { return new URL(a.url || '').hostname.replace('www.', ''); }
                    catch { return a.source; }
                })();
                result.push({
                    source: a.source,
                    icon: `https://www.google.com/s2/favicons?domain=${domain}&sz=128`
                });
            }
            if (result.length >= 3) break;
        }
        return result;
    });

    let expanded = $state(false);

    function hideImage(e: Event) {
        (e.currentTarget as HTMLImageElement).style.display = 'none';
    }

    function formatDate(dateStr?: string): string {
        if (!dateStr) return '';
        const d = new Date(dateStr);
        const now = new Date();
        const diff = now.getTime() - d.getTime();
        const h = Math.floor(diff / 3600000);
        if (h < 24) return `${h}${get(t)('eventscard.hoursAgo')}`;
        return d.toLocaleDateString(undefined, { day: '2-digit', month: 'short' });
    }
</script>

<div class="event-card" class:is-expanded={expanded}>
    <!-- Cabeçalho do Cluster (O Rei - Serifado e Escuro) -->
    <div class="event-header" onclick={() => expanded = !expanded} role="button" tabindex="0" onkeydown={(e) => e.key === 'Enter' && (expanded = !expanded)}>
        <h3 class="event-title">{event.summary}</h3>
        <div class="meta-row">
            <span class="article-count">
                {event.article_count} {$t('eventscard.publications')}
            </span>
            <span class="meta-sep">·</span>
            <div class="publishers-group">
	{#each publishers as pub}
                    <div class="publisher-logo-wrap" title={pub.source}>
                        <img src={pub.icon} alt={pub.source} class="publisher-logo" onerror={hideImage} />
                    </div>
                {/each}
            </div>
            {#if event.unique_feeds > 3}
                <span class="more-sources">+{event.unique_feeds - 3}</span>
            {/if}
        </div>
    </div>

    <!-- Lista Expandida (Os Súditos - Indentados, Sans-serif, Agrupados) -->
    {#if expanded}
        <div class="expanded-list">
            {#each event.articles.slice(0, 8) as article}
                <a
                    href={article.item_id ? `/a/${article.item_id}` : article.url}
                    target={article.item_id ? '_self' : '_blank'}
                    rel="noopener noreferrer"
                    class="mini-post"
                    onclick={(e) => e.stopPropagation()}
                >
                    <div class="mini-publisher-row">
                        {#if article.source}
                            <span class="mini-source-name">{article.source}</span>
                        {/if}
                        {#if article.published_at}
                            <span class="mini-sep">·</span>
                            <span class="mini-date">{formatDate(article.published_at)}</span>
                        {/if}
                    </div>
                    <span class="mini-title">{article.title}</span>
                </a>
            {/each}
        </div>
    {/if}
</div>

<style>
    .event-card {
        border-bottom: 1px solid var(--color-base-300);
        transition: background 120ms ease;
    }

    /* Fundo sutil quando expandido */
    .event-card.is-expanded {
        background: color-mix(in oklch, var(--color-base-content) 2%, transparent);
    }

/* ── Header ────────────────────────────────────────── */
.event-header {
  padding: 16px 0;
  cursor: pointer;
  user-select: none;
  transition: background 120ms ease;
}
.event-header:hover {
  background: var(--color-base-200);
  margin: 0 -16px;
  padding-left: 16px;
  padding-right: 16px;
  border-radius: 6px;
}
.event-header:active {
  background: color-mix(in oklch, var(--color-base-content) 8%, transparent);
}

/* Título do Evento em Serifa (Destaque Máximo) */
.event-title {
font-family: var(--font-post-title);
  font-size: 16px;
  font-weight: 500;
  line-height: 1.4;
  color: var(--color-base-content);
  margin: 0 0 8px;
  transition: color 140ms;
}
.event-header:hover .event-title {
  color: var(--color-accent);
}

    .meta-row {
        display: flex;
        align-items: center;
        gap: 6px;
    }

.article-count {
  font-size: 11.5px;
  font-weight: 700;
  color: var(--color-accent);
}

    .meta-sep { color: var(--color-base-300); font-size: 12px; }

    .publishers-group {
        display: flex;
        align-items: center;
        margin-left: 4px;
    }
    .publisher-logo-wrap {
        width: 16px; height: 16px;
        border-radius: 50%; overflow: hidden;
        border: 1.5px solid var(--color-base-100);
        background: var(--color-base-200);
        display: flex; align-items: center; justify-content: center;
        margin-left: -4px;
    }
    .publisher-logo { width: 100%; height: 100%; object-fit: contain; }

    .more-sources {
        font-size: 11px;
        color: color-mix(in oklch, var(--color-base-content) 45%, transparent);
        font-weight: 500;
    }

    /* ── Expanded List (Hierarquia de Informação) ──────── */
    .expanded-list {
        margin-left: 24px; /* Indentação para criar hierarquia visual */
        padding-bottom: 12px;
        border-left: 2px solid color-mix(in oklch, var(--color-accent) 30%, transparent); /* Linha de agrupamento sutil */
    }

    .mini-post {
        display: block;
        padding: 10px 12px; /* Padding interno para isolamento */
        text-decoration: none;
        border-radius: 6px;
        background: transparent;
        transition: background 120ms ease;
    }
    .mini-post:hover {
        background: color-mix(in oklch, var(--color-accent) 6%, transparent); /* Hover sutílimo */
    }

    /* Publisher Row */
    .mini-publisher-row {
        display: flex;
        align-items: center;
        gap: 4px;
        margin-bottom: 3px;
    }
.mini-source-name {
  font-size: 11.5px;
  font-weight: 700;
  color: var(--color-accent);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 150px;
}
.mini-sep { font-size: 11px; color: color-mix(in oklch, var(--color-base-content) 25%, transparent); }
.mini-date { font-size: 11px; color: color-mix(in oklch, var(--color-base-content) 35%, transparent); }

    /* Title (Sans-serif e mais claro para diferenciar do Event Title) */
.mini-title {
font-family: var(--font-post-title);
        font-size: 13.5px;
        font-weight: 500;
        line-height: 1.4;
        color: color-mix(in oklch, var(--color-base-content) 70%, transparent); /* Texto mais claro */
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
</style>