<script lang="ts">
    import { onMount, tick } from 'svelte';
    import Send        from '@lucide/svelte/icons/send';
    import RotateCcw   from '@lucide/svelte/icons/rotate-ccw';
    import Sparkles    from '@lucide/svelte/icons/sparkles';
    import ChevronDown from '@lucide/svelte/icons/chevron-down';
    import MoreVertical from '@lucide/svelte/icons/more-vertical';
    import BookOpen    from '@lucide/svelte/icons/book-open';
    import Globe       from '@lucide/svelte/icons/globe';
    import Database    from '@lucide/svelte/icons/database';
    import Blend       from '@lucide/svelte/icons/blend';
    import Newspaper   from '@lucide/svelte/icons/newspaper';
    import { pendingMotaPosts } from '$lib/stores/swipe';
import { t } from 'svelte-i18n';
 import { get } from 'svelte/store';
 import { apiFetch } from '$lib/api';

    type Message = {
        role: 'user' | 'assistant';
        content: string;
        id: number;
        fromFeed?: boolean;
        feedTitles?: string[];
    };

    type SourceMode = 'local' | 'online' | 'mixed';
    type WaitingPhase = 'thinking' | 'searching' | 'reading' | 'synthesizing' | null;

    // ─── State ────────────────────────────────────────────────────────────────
    let messages      = $state<Message[]>([]);
    let input         = $state('');
    let loading       = $state(false);
    let streaming     = $state(false);
    let error         = $state('');
    let idCounter     = 0;
    let waitingPhase  = $state<WaitingPhase>(null);

    // Settings
    let deepReading  = $state(false);
    let sourceMode   = $state<SourceMode>('local');
    let menuOpen     = $state(false);

    let textareaRef:     HTMLTextAreaElement;
    let scrollContainer: HTMLElement;
    let messagesEnd:     HTMLDivElement;
    let menuRef:         HTMLDivElement;

    let showScrollBtn = $state(false);

    // ─── Waiting message by phase ─────────────────────────────────────────────
let waitingMessages = $derived<Record<string, string>>({
	thinking: $t('motatab.waitThinking'),
	searching: $t('motatab.waitSearching'),
	reading: $t('motatab.waitReading'),
	synthesizing: $t('motatab.waitSynthesizing'),
});

    // ─── Initial greeting (loaded dynamically for i18n) ──────────────────────
onMount(() => {
	messages = [{
            role: 'assistant', id: -1,
            content: get(t)('motatab.greeting'),
        }];

        function onClickOutside(e: MouseEvent) {
            if (menuRef && !menuRef.contains(e.target as Node)) menuOpen = false;
        }
        document.addEventListener('mousedown', onClickOutside);
        return () => document.removeEventListener('mousedown', onClickOutside);
    });

    // ─── Watch for posts sent from the feed ───────────────────────────────────
    $effect(() => {
        const posts = $pendingMotaPosts;
        if (posts.length > 0) {
            const snapshot = [...posts];
            pendingMotaPosts.set([]);
            handleIncomingFeedPosts(snapshot);
        }
    });

    async function handleIncomingFeedPosts(posts: any[]) {
        if (loading) return;

        const feedTitles = posts.map((p: any) => p.title);
        const apiMessage = get(t)('motatab.feedPrompt');

        const userMsgId = idCounter++;
        messages = [
            ...messages,
            {
                role:       'user',
                content:    apiMessage,
                id:         userMsgId,
                fromFeed:   true,
                feedTitles,
            },
        ];

        await scrollToBottom(true);
        await streamResponse(apiMessage, posts);
    }

    // ─── Scroll ───────────────────────────────────────────────────────────────
    function handleScroll() {
        if (!scrollContainer) return;
        const { scrollTop, clientHeight, scrollHeight } = scrollContainer;
        showScrollBtn = scrollHeight - scrollTop - clientHeight > 120;
    }

    async function scrollToBottom(smooth = true) {
        await tick();
        messagesEnd?.scrollIntoView({ behavior: smooth ? 'smooth' : 'instant' });
    }

    function autoResize() {
        if (!textareaRef) return;
        textareaRef.style.height = 'auto';
        textareaRef.style.height = Math.min(textareaRef.scrollHeight, 120) + 'px';
    }

    // ─── Source mode label ────────────────────────────────────────────────────
let sourceLabels = $derived<Record<SourceMode, string>>({
	local: $t('motatab.sourceLocal'),
	online: $t('motatab.sourceOnline'),
	mixed: $t('motatab.sourceMixed'),
});

    // ─── Markdown renderer ────────────────────────────────────────────────────
    function renderMarkdown(raw: string): string {
        if (!raw) return '';
        try {
            const codeBlocks: string[] = [];
            let s = raw.replace(/```([\w]*)\n?([\s\S]*?)```/g, (_, lang, code) => {
                const i = codeBlocks.length;
                const esc = code.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
                const cls = lang ? ` class="language-${lang}"` : '';
                codeBlocks.push(`<pre><code${cls}>${esc}</code></pre>`);
                return `\x02CB${i}\x03`;
            });

            const inlineCodes: string[] = [];
            s = s.replace(/`([^`\n]+)`/g, (_, code) => {
                const i = inlineCodes.length;
                const esc = code.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
                inlineCodes.push(`<code>${esc}</code>`);
                return `\x02IC${i}\x03`;
            });

            s = s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

            function inline(t: string): string {
                return t
                    .replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')
                    .replace(/\*\*(.+?)\*\*/g,     '<strong>$1</strong>')
                    .replace(/\*(.+?)\*/g,          '<em>$1</em>')
                    .replace(/~~(.+?)~~/g,          '<del>$1</del>')
                    .replace(/\[([^\]]+)\]\(([^)]+)\)/g,
                        '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
                    .replace(/\x02IC(\d+)\x03/g, (_, i) => inlineCodes[+i])
                    .replace(/\x02CB(\d+)\x03/g, (_, i) => codeBlocks[+i]);
            }

            function parseTable(block: string): string | null {
                const lines = block.split('\n').filter(Boolean);
                if (lines.length < 2) return null;
                const sepIdx = lines.findIndex(l => /\|/.test(l) && /---/.test(l));
                if (sepIdx < 1) return null;

                const parseRow = (line: string) =>
                    line.split('|').map(c => c.trim())
                        .filter((_, i, a) => !(i===0&&a[0]==='') && !(i===a.length-1&&a[a.length-1]===''));

                const aligns = parseRow(lines[sepIdx]).map(c =>
                    c.startsWith(':')&&c.endsWith(':') ? 'center' : c.endsWith(':') ? 'right' : 'left');
                const headers = parseRow(lines[sepIdx-1]);

                const thead = `<thead><tr>${headers.map((h,i) =>
                    `<th style="text-align:${aligns[i]??'left'}">${inline(h)}</th>`).join('')}</tr></thead>`;

                const tbody = lines.slice(sepIdx+1).length
                    ? `<tbody>${lines.slice(sepIdx+1).map(line => {
                        const cells = parseRow(line);
                        return `<tr>${cells.map((c,i) =>
                            `<td style="text-align:${aligns[i]??'left'}">${inline(c)}</td>`).join('')}</tr>`;
                    }).join('')}</tbody>` : '';

                return `<div class="md-table-wrap"><table>${thead}${tbody}</table></div>`;
            }

            const lines = s.split('\n');

            type Block = { type: string; lines: string[] };
            const blocks: Block[] = [];
            let currentBlock: Block | null = null;

            function pushBlock() {
                if (currentBlock && currentBlock.lines.length > 0) {
                    blocks.push(currentBlock);
                }
                currentBlock = null;
            }

            for (const line of lines) {
                const trimmed = line.trimEnd();

                if (trimmed === '') { pushBlock(); continue; }

                if (/^#{1,6} /.test(trimmed)) {
                    pushBlock(); blocks.push({ type: 'heading', lines: [trimmed] });
                } else if (/^[-*+] /.test(trimmed)) {
                    if (currentBlock && currentBlock.type === 'ul') { currentBlock.lines.push(trimmed); }
                    else { pushBlock(); currentBlock = { type: 'ul', lines: [trimmed] }; }
                } else if (/^\d+\. /.test(trimmed)) {
                    if (currentBlock && currentBlock.type === 'ol') { currentBlock.lines.push(trimmed); }
                    else { pushBlock(); currentBlock = { type: 'ol', lines: [trimmed] }; }
                } else if (/^&gt;/.test(trimmed)) {
                    if (currentBlock && currentBlock.type === 'blockquote') { currentBlock.lines.push(trimmed); }
                    else { pushBlock(); currentBlock = { type: 'blockquote', lines: [trimmed] }; }
                } else if (/^(-{3,}|\*{3,}|_{3,})$/.test(trimmed)) {
                    pushBlock(); blocks.push({ type: 'hr', lines: [trimmed] });
                } else if (trimmed.includes('|')) {
                    if (currentBlock && currentBlock.type === 'table') { currentBlock.lines.push(trimmed); }
                    else { pushBlock(); currentBlock = { type: 'table', lines: [trimmed] }; }
                } else if (/^\x02CB\d+\x03$/.test(trimmed)) {
                    pushBlock(); blocks.push({ type: 'code', lines: [trimmed] });
                } else {
                    if (currentBlock && currentBlock.type === 'paragraph') { currentBlock.lines.push(trimmed); }
                    else { pushBlock(); currentBlock = { type: 'paragraph', lines: [trimmed] }; }
                }
            }
            pushBlock();

            const out = blocks.map(block => {
                switch (block.type) {
                    case 'heading': {
                        const m = block.lines[0].match(/^(#{1,6}) (.+)$/);
                        return m ? `<h${m[1].length}>${inline(m[2])}</h${m[1].length}>` : '';
                    }
                    case 'ul':
                        return `<ul>${block.lines.map(l => `<li>${inline(l.replace(/^[-*+] /, ''))}</li>`).join('')}</ul>`;
                    case 'ol':
                        return `<ol>${block.lines.map(l => `<li>${inline(l.replace(/^\d+\. /, ''))}</li>`).join('')}</ol>`;
                    case 'blockquote':
                        return `<blockquote>${inline(block.lines.map(l => l.replace(/^&gt;\s?/, '')).join('<br/>'))}</blockquote>`;
                    case 'hr':
                        return '<hr/>';
                    case 'table': {
                        const tableHtml = parseTable(block.lines.join('\n'));
                        return tableHtml || `<p>${block.lines.map(l => inline(l)).join('<br/>')}</p>`;
                    }
                    case 'code':
                        return block.lines.map(l => l.replace(/\x02CB(\d+)\x03/g, (_, i) => codeBlocks[+i])).join('');
                    case 'paragraph':
                        return `<p>${block.lines.map(l => inline(l)).join('<br/>')}</p>`;
                    default:
                        return '';
                }
            });

            return out.join('\n');
        } catch (e) {
            console.error("Markdown rendering error:", e);
            return raw.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
        }
    }

    function renderMarkdownWithCursor(raw: string): string {
        const html = renderMarkdown(raw);
        const blockClose = /(<\/(?:p|li|h[1-6]|td|th|tr|thead|tbody|table|pre|code|div|blockquote)>)\s*$/;
        return blockClose.test(html)
            ? html.replace(blockClose, '<span class="stream-cursor"></span>$1')
            : html + '<span class="stream-cursor"></span>';
    }

    // ─── SSE payload extractor ────────────────────────────────────────────────
    function extractSSEPayload(payload: string): {
        content: string;
        isError: boolean;
        status: WaitingPhase;
    } {
        if (!payload || payload === '[DONE]') return { content: '', isError: false, status: null };

        try {
            const json = JSON.parse(payload);

            if (json.error) {
                return { content: json.error, isError: true, status: null };
            }

            if (json.status) {
                return { content: '', isError: false, status: json.status as WaitingPhase };
            }

            const content = json.content
                ?? json.choices?.[0]?.delta?.content
                ?? json.choices?.[0]?.text
                ?? json.message?.content
                ?? json.text
                ?? '';

            return { content, isError: false, status: null };
        } catch {
            return { content: payload, isError: false, status: null };
        }
    }

    // ─── Core streaming logic ─────────────────────────────────────────────────
    async function streamResponse(text: string, articles: any[] = []) {
        error         = '';
        loading       = true;
        streaming     = false;
        waitingPhase  = null;

        const assistantId = idCounter++;
        messages = [...messages, { role: 'assistant', content: '', id: assistantId }];
        await scrollToBottom(false);

        try {
            const body: Record<string, any> = {
                message:      text,
                source_mode:  sourceMode,
                deep_reading: deepReading,
            };

            if (articles.length > 0) {
                body.articles = articles.map((a: any) => ({
                    item_id:     a.item_id    ?? '',
                    title:       a.title      ?? '',
                    description: a.description ?? '',
                    link:        a.link       ?? '',
                    feed_title:  a.feed_title ?? '',
                    pub_date:    a.pub_date   ?? '',
                    author:      a.author     ?? '',
                }));
            }

	const res = await apiFetch('/api/chat', {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
		},
		body: JSON.stringify(body),
		credentials: 'include',
	});

            if (!res.ok) {
                const data = await res.json().catch(() => ({}));
                throw new Error(data.message || data.error || `${get(t)('motatab.serverError').replace('{status}', res.status)}`);
            }
            if (!res.body) throw new Error(get(t)('motatab.noResponseBody'));

            streaming = true;
            const reader  = res.body.getReader();
            const decoder = new TextDecoder();

            let buffer = '';
            let chunkCount = 0;
            let totalChars = 0;
            let streamDone = false;

            const contentType = res.headers.get('Content-Type') || '';
            const isSSE = contentType.includes('text/event-stream');

            while (!streamDone) {
                const { done, value } = await reader.read();

                if (done) {
                    if (buffer.trim()) {
                        processBuffer(buffer);
                        buffer = '';
                    }
                    break;
                }

                const chunk = decoder.decode(value, { stream: true });
                buffer += chunk;
                chunkCount++;

                if (isSSE) {
                    let newlineIdx: number;
                    while ((newlineIdx = buffer.indexOf('\n')) !== -1) {
                        const line = buffer.slice(0, newlineIdx);
                        buffer = buffer.slice(newlineIdx + 1);

                        const trimmed = line.trim();
                        if (!trimmed) continue;

                        if (trimmed.startsWith('data: ')) {
                            const payload = trimmed.slice(6).trim();

                            if (payload === '[DONE]') {
                                streamDone = true;
                                break;
                            }

                            const { content, isError, status } = extractSSEPayload(payload);

                            if (status) {
                                waitingPhase = status;
                                if (!showScrollBtn) {
                                    await tick();
                                    messagesEnd?.scrollIntoView({ behavior: 'instant' });
                                }
                                continue;
                            }

                            if (isError && content) {
                                error = content;
                            } else if (content) {
                                messages = messages.map(m =>
                                    m.id === assistantId ? { ...m, content: m.content + content } : m
                                );
                                totalChars += content.length;

                                if (!showScrollBtn) {
                                    await tick();
                                    messagesEnd?.scrollIntoView({ behavior: 'instant' });
                                }
                            }
                        }
                    }
                } else {
                    if (chunk) {
                        messages = messages.map(m =>
                            m.id === assistantId ? { ...m, content: m.content + chunk } : m
                        );
                        totalChars += chunk.length;
                        buffer = '';

                        if (!showScrollBtn) {
                            await tick();
                            messagesEnd?.scrollIntoView({ behavior: 'instant' });
                        }
                    }
                }
            }

            function processBuffer(remaining: string) {
                if (isSSE) {
                    const lines = remaining.split('\n');
                    for (const line of lines) {
                        const trimmed = line.trim();
                        if (!trimmed || !trimmed.startsWith('data: ')) continue;

                        const payload = trimmed.slice(6).trim();
                        if (payload === '[DONE]') return;

                        const { content, isError, status } = extractSSEPayload(payload);
                        if (status) { waitingPhase = status; continue; }
                        if (isError && content) { error = content; }
                        else if (content) {
                            messages = messages.map(m =>
                                m.id === assistantId ? { ...m, content: m.content + content } : m
                            );
                            totalChars += content.length;
                        }
                    }
                } else if (remaining) {
                    messages = messages.map(m =>
                        m.id === assistantId ? { ...m, content: m.content + remaining } : m
                    );
                    totalChars += remaining.length;
                }
            }

            const finalMsg = messages.find(m => m.id === assistantId);
            if (finalMsg && !finalMsg.content.trim() && !error) {
                messages = messages.map(m =>
                    m.id === assistantId
                        ? { ...m, content: get(t)('motatab.emptyResponse') }
                        : m
                );
            }

        } catch (err: any) {
            const emptyMsg = messages.find(m => m.id === assistantId);
            if (emptyMsg && !emptyMsg.content.trim()) {
                messages = messages.filter(m => m.id !== assistantId);
            }
            error = err.message || get(t)('motatab.connectionError');
        } finally {
            loading      = false;
            streaming    = false;
            waitingPhase = null;
        }
    }

    // ─── Send regular message ─────────────────────────────────────────────────
    async function sendMessage() {
        const text = input.trim();
        if (!text || loading) return;

        input = '';
        if (textareaRef) textareaRef.style.height = 'auto';

        messages = [...messages, { role: 'user', content: text, id: idCounter++ }];
        await scrollToBottom(true);

        await streamResponse(text);
    }

    function handleKeydown(e: KeyboardEvent) {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
    }

    function clearChat() {
        messages      = [{
            role: 'assistant', id: -1,
            content: get(t)('motatab.greeting'),
        }];
        error         = '';
        idCounter     = 0;
        waitingPhase  = null;
}
</script>


<div class="chat-root">

    <!-- ── Header ──────────────────────────────────────────────────────────── -->
    <header class="chat-header">
        <div class="main-content header-inner">
            <div class="header-title">
                <Sparkles size={14} />
                {$t('motatab.headerTitle')}
            </div>

            <div class="header-badges">
                {#if sourceMode === 'online'}
                    <span class="badge badge-online">{$t('motatab.badgeOnline')}</span>
                {:else if sourceMode === 'mixed'}
                    <span class="badge badge-mixed">{$t('motatab.badgeMixed')}</span>
                {/if}
                {#if deepReading}
                    <span class="badge badge-deep">{$t('motatab.badgeDeep')}</span>
                {/if}
            </div>

            <div class="header-right" bind:this={menuRef}>
                <button
                    class="menu-btn"
                    class:active={menuOpen}
                    onclick={() => menuOpen = !menuOpen}
                    title="{$t('motatab.settingsTitle')}"
                    aria-label="{$t('motatab.chatSettings')}"
                >
                    <MoreVertical size={16} />
                </button>

                {#if menuOpen}
                    <div class="dropdown" role="menu">
                        <p class="menu-section-label">{$t('motatab.readingSection')}</p>
                        <div
                            class="toggle-row"
                            role="button"
                            tabindex="0"
                            onclick={() => deepReading = !deepReading}
                            onkeydown={e => e.key === 'Enter' && (deepReading = !deepReading)}
                        >
                            <span class="toggle-label">
                                <BookOpen size={14} />
                                <span>
                                    {$t('motatab.deepReading')}
                                    <span class="toggle-label-sub">{$t('motatab.deepReadingDesc')}</span>
                                </span>
                            </span>
                            <div class="pill {deepReading ? 'on' : 'off'}" aria-label="Toggle deep reading">
                                <div class="pill-thumb"></div>
                            </div>
                        </div>

                        <div class="menu-divider"></div>

                        <p class="menu-section-label">{$t('motatab.sourcesSection')}</p>

                        {#each ([
                            { value: 'local',  label: $t('motatab.sourceLocal'),  Icon: Database },
                            { value: 'online', label: $t('motatab.sourceOnline'), Icon: Globe    },
                            { value: 'mixed',  label: $t('motatab.sourceMixed'),  Icon: Blend   },
                        ] as const) as opt (opt.value)}
                            <div
                                class="source-option"
                                class:selected={sourceMode === opt.value}
                                role="radio"
                                aria-checked={sourceMode === opt.value}
                                tabindex="0"
                                onclick={() => sourceMode = opt.value}
                                onkeydown={e => e.key === 'Enter' && (sourceMode = opt.value)}
                            >
                                <div class="source-dot"><div class="source-dot-inner"></div></div>
                                <opt.Icon size={13} class="source-icon" />
                                {opt.label}
                            </div>
                        {/each}
                    </div>
                {/if}
            </div>
        </div>
    </header>

    <!-- ── Scrollable messages ──────────────────────────────────────────────── -->
    <div class="scroll-wrap">
        <main
            bind:this={scrollContainer}
            onscroll={handleScroll}
            class="chat-scroll"
        >
            <div class="main-content chat-inner">
                <div class="msg-list">
                    {#each messages as msg (msg.id)}
                        {#if msg.role === 'user'}
                            <div class="msg-in msg-user">
                                {#if msg.fromFeed && msg.feedTitles}
                                    <div class="feed-bubble">
                                        <div class="feed-bubble-header">
                                            <Newspaper size={13} />
                                            <span>{msg.feedTitles.length} {msg.feedTitles.length !== 1 ? $t('motatab.articlesSelected') : $t('motatab.articleSelected')}</span>
                                        </div>
                                        <ul class="feed-bubble-list">
                                            {#each msg.feedTitles as title}
                                                <li>{title}</li>
                                            {/each}
                                        </ul>
                                    </div>
                                {:else}
                                    <div class="user-bubble">{msg.content}</div>
                                {/if}
                            </div>
                        {:else}
                            {@const isLast      = msg === messages[messages.length - 1]}
                            {@const isWaiting   = isLast && loading && !streaming && msg.content === ''}
                            {@const isStreaming  = isLast && loading && streaming}
                            {@const isStreamingEmpty = isLast && loading && streaming && msg.content === ''}

                            <div class="msg-in ai-block">
                                {#if msg.id === -1}
                                    <h1 class="greeting-title">Mota</h1>
                                {:else}
                                    <div class="ai-header">
                                        <span class="ai-label">Mota</span>
                                    </div>
                                {/if}

                                {#if isWaiting || isStreamingEmpty}
                                    <p class="getting-data">
                                        {waitingPhase ? waitingMessages[waitingPhase] ?? $t('motatab.waitThinking') : $t('motatab.waitThinking')}
                                    </p>
                                {:else if isStreaming}
                                    <div class="ai-prose">{@html renderMarkdownWithCursor(msg.content)}</div>
                                {:else}
                                    <div class="ai-prose">{@html renderMarkdown(msg.content)}</div>
                                {/if}
                            </div>
                        {/if}
                    {/each}
                </div>

                {#if error}
                    <div class="error-wrap">
                        <p class="error-text">{error}</p>
                    </div>
                {/if}

                <div bind:this={messagesEnd}></div>
            </div>
        </main>

        <div class="scroll-fade"></div>

        <!-- Scroll Button positioned relative to main-content -->
        <button
            class="scroll-btn {showScrollBtn ? 'visible' : 'hidden'}"
            onclick={() => scrollToBottom(true)}
            title="{$t('motatab.scrollToBottom')}"
        >
            <ChevronDown size={18} />
        </button>
    </div>

    <!-- ── Footer ──────────────────────────────────────────────────────────── -->
    <footer class="chat-footer">
        <div class="main-content footer-inner">
            <div class="input-wrap">
                <textarea
                    bind:this={textareaRef}
                    bind:value={input}
                    oninput={autoResize}
                    onkeydown={handleKeydown}
                    placeholder="{$t('motatab.placeholder')}"
                    rows={1}
                    class="chat-textarea"
                ></textarea>

                <button
                    class="send-btn {input.trim() && !loading ? 'ready' : 'idle'}"
                    onclick={sendMessage}
                    disabled={loading || !input.trim()}
                    title="{$t('motatab.send')}"
                >
                    <Send size={15} />
                </button>
            </div>

            <div class="footer-meta">
                <p class="disclaimer-text">
                    {$t('motatab.disclaimer')}
                </p>
                <button
                    class="clear-btn"
                    onclick={clearChat}
                    title="{$t('motatab.newConversation')}"
                >
                    <RotateCcw size={11} />
                    <span>{$t('motatab.clearChat')}</span>
                </button>
            </div>
        </div>
    </footer>

</div>


<style>
/* ── Layout ──────────────────────────────────────────────── */
    .chat-root {
        position: fixed;
        top: 0; left: 0; right: 0;
        bottom: calc(64px + env(safe-area-inset-bottom, 8px));
        display: flex;
        flex-direction: column;
        background: var(--color-base-100);
    }
    @media (min-width: 768px) {
        .chat-root { bottom: 0; }
    }

    /* ── Centralizer Logic ─────────────────────────── */
    .main-content {
        max-width: 42rem;
        margin: 0 auto;
        padding: 0 16px;
        width: 100%;
    }
    @media (min-width: 768px) {
        .main-content {
            padding: 0;
            margin-left: max(240px, calc(50vw - 21rem));
            margin-right: auto;
        }
    }

    /* ── Header ──────────────────────────────────────────────── */
    .chat-header {
        flex-shrink: 0;
        border-bottom: 1px solid var(--color-base-300);
        background: var(--color-base-100);
        position: relative;
        z-index: 20;
    }

    .header-inner {
        display: flex;
        align-items: center;
        justify-content: space-between;
        height: 48px;
    }

    .header-title {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 13px;
        font-weight: 600;
        color: var(--color-base-content);
        letter-spacing: 0.01em;
    }

    .header-badges { display: flex; align-items: center; gap: 5px; }
    .badge {
        font-size: 10px; font-weight: 600;
        padding: 2px 7px; border-radius: 999px;
        letter-spacing: 0.03em; text-transform: uppercase;
    }
    .badge-online { background: color-mix(in oklch, var(--color-info) 15%, transparent);    color: var(--color-info);    border: 1px solid color-mix(in oklch, var(--color-info) 30%, transparent); }
    .badge-mixed  { background: color-mix(in oklch, var(--color-success) 12%, transparent); color: var(--color-success); border: 1px solid color-mix(in oklch, var(--color-success) 25%, transparent); }
    .badge-deep   { background: color-mix(in oklch, var(--color-warning) 12%, transparent); color: var(--color-warning); border: 1px solid color-mix(in oklch, var(--color-warning) 25%, transparent); }

    .header-right { display: flex; align-items: center; gap: 6px; position: relative; }

    /* ── Menu button ─────────────────────────────────────────── */
    .menu-btn {
        width: 32px; height: 32px; border-radius: 8px;
        border: none; background: transparent;
        display: flex; align-items: center; justify-content: center;
        cursor: pointer;
        color: color-mix(in oklch, var(--color-base-content) 45%, transparent);
        transition: background 150ms, color 150ms;
    }
    .menu-btn:hover { background: color-mix(in oklch, var(--color-base-300) 60%, transparent); color: var(--color-base-content); }
    .menu-btn.active { background: color-mix(in oklch, var(--color-base-300) 80%, transparent); color: var(--color-base-content); }

    /* ── Dropdown ────────────────────────────────────────────── */
    .dropdown {
        position: absolute; top: calc(100% + 8px); right: 0;
        width: 240px;
        background: var(--color-base-100);
        border: 1px solid color-mix(in oklch, var(--color-base-300) 80%, transparent);
        border-radius: 14px;
        box-shadow: 0 8px 32px color-mix(in oklch, var(--color-base-content) 12%, transparent);
        padding: 8px; z-index: 100;
        animation: dropIn 0.15s cubic-bezier(0.22, 1, 0.36, 1) both;
    }
    @keyframes dropIn {
        from { opacity: 0; transform: translateY(-6px) scale(0.97); }
        to   { opacity: 1; transform: translateY(0)    scale(1); }
    }

    .menu-section-label {
        font-size: 10px; font-weight: 700; letter-spacing: 0.07em;
        text-transform: uppercase;
        color: color-mix(in oklch, var(--color-base-content) 35%, transparent);
        padding: 6px 10px 4px;
    }
    .menu-divider { height: 1px; background: color-mix(in oklch, var(--color-base-300) 70%, transparent); margin: 6px 4px; }

    .toggle-row {
        display: flex; align-items: center; justify-content: space-between;
        padding: 8px 10px; border-radius: 8px; cursor: pointer;
        transition: background 140ms; gap: 10px;
    }
    .toggle-row:hover { background: color-mix(in oklch, var(--color-base-300) 50%, transparent); }
    .toggle-label { display: flex; align-items: center; gap: 8px; font-size: 13px; font-weight: 500; color: var(--color-base-content); }
    .toggle-label-sub { display: block; font-size: 10.5px; font-weight: 400; color: color-mix(in oklch, var(--color-base-content) 45%, transparent); margin-top: 1px; }

    .pill { flex-shrink: 0; width: 36px; height: 20px; border-radius: 999px; position: relative; transition: background 200ms; cursor: pointer; }
    .pill.off { background: color-mix(in oklch, var(--color-base-300) 90%, transparent); }
    .pill.on  { background: var(--color-accent); }
    .pill-thumb { position: absolute; top: 3px; left: 3px; width: 14px; height: 14px; border-radius: 50%; background: var(--color-base-100); box-shadow: 0 1px 3px rgba(0,0,0,.25); transition: transform 200ms cubic-bezier(0.22, 1, 0.36, 1); }
    .pill.on .pill-thumb { transform: translateX(16px); }

    .source-option {
        display: flex; align-items: center; gap: 10px;
        padding: 8px 10px; border-radius: 8px; cursor: pointer;
        transition: background 140ms; font-size: 13px; font-weight: 500; color: var(--color-base-content);
    }
    .source-option:hover { background: color-mix(in oklch, var(--color-base-300) 50%, transparent); }
    .source-option.selected { background: color-mix(in oklch, var(--color-accent) 12%, transparent); color: var(--color-accent); }
    .source-dot { width: 14px; height: 14px; border-radius: 50%; border: 2px solid color-mix(in oklch, var(--color-base-content) 25%, transparent); display: flex; align-items: center; justify-content: center; flex-shrink: 0; transition: border-color 150ms; }
    .source-option.selected .source-dot { border-color: var(--color-accent); }
    .source-dot-inner { width: 6px; height: 6px; border-radius: 50%; background: var(--color-accent); opacity: 0; transform: scale(0); transition: opacity 150ms, transform 150ms; }
    .source-option.selected .source-dot-inner { opacity: 1; transform: scale(1); }

    :global(.source-icon) { color: color-mix(in oklch, var(--color-base-content) 40%, transparent); }
    :global(.source-option.selected .source-icon) { color: var(--color-accent); }

    /* ── Scroll Wrap & Chat Scroll ────────────────────────────── */
    .scroll-wrap {
        position: relative;
        flex: 1;
        min-height: 0;
        display: flex;
        flex-direction: column;
    }

    .chat-scroll {
        flex: 1;
        overflow-y: auto;
        height: 100%;
        scrollbar-width: thin;
        scrollbar-color: color-mix(in oklch, var(--color-accent) 20%, transparent) transparent;
    }
    .chat-scroll::-webkit-scrollbar { width: 4px; }
    .chat-scroll::-webkit-scrollbar-track { background: transparent; }
    .chat-scroll::-webkit-scrollbar-thumb { background: color-mix(in oklch, var(--color-accent) 20%, transparent); border-radius: 4px; }

    .chat-inner {
        padding-top: 20px;
        padding-bottom: 80px;
    }

    .scroll-fade {
        position: absolute;
        bottom: 0; left: 0; right: 0;
        height: 72px;
        background: linear-gradient(to bottom, transparent, var(--color-base-100));
        pointer-events: none;
        z-index: 1;
    }

    /* ── Messages List ───────────────────────────────────────── */
    .msg-list {
        display: flex;
        flex-direction: column;
        gap: 16px;
    }

    .msg-in { animation: msgSlide 0.2s cubic-bezier(0.22, 1, 0.36, 1) both; }
    @keyframes msgSlide { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }

    .msg-user {
        display: flex;
        justify-content: flex-end;
    }

    /* ── Feed posts bubble ───────────────────────────────────── */
    .feed-bubble {
        max-width: min(85%, 560px);
        background: color-mix(in oklch, var(--color-accent) 8%, transparent);
        border: 1px solid color-mix(in oklch, var(--color-accent) 20%, transparent);
        border-radius: 16px 16px 4px 16px;
        padding: 12px 14px;
        word-break: break-word;
    }

    .feed-bubble-header {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--color-accent);
        margin-bottom: 8px;
    }

    .feed-bubble-list {
        list-style: none;
        padding: 0; margin: 0;
        display: flex; flex-direction: column; gap: 4px;
    }

    .feed-bubble-list li {
        font-size: 13px;
        font-weight: 500;
        color: color-mix(in oklch, var(--color-base-content) 75%, transparent);
        line-height: 1.4;
        padding-left: 10px;
        position: relative;
    }
    .feed-bubble-list li::before {
        content: '·';
        position: absolute;
        left: 0;
        color: var(--color-accent);
        font-weight: 700;
    }

    /* ── User bubble ─────────────────────────────────────────── */
    .user-bubble {
        display: inline-block;
        max-width: min(80%, 520px);
        background: var(--color-base-200);
        color: var(--color-base-content);
        border-radius: 16px 16px 4px 16px;
        padding: 10px 16px;
        font-size: 0.9rem;
        line-height: 1.55;
        word-break: break-word;
        border: 1px solid var(--color-base-300);
    }

    /* ── AI block ────────────────────────────────────────────── */
    .ai-block { padding: 4px 0 8px; max-width: 100%; }
    .ai-header { display: flex; align-items: center; gap: 7px; margin-bottom: 10px; }
    .ai-label { font-size: 11.5px; font-weight: 700; color: var(--color-accent); letter-spacing: 0.04em; text-transform: uppercase; }

.greeting-title {
font-family: var(--font-page-title);
        font-size: 2.25rem;
        font-weight: 400;
        color: var(--color-base-content);
        margin-bottom: 8px;
        text-align: left;
    }

    /* ── AI Prose ────────────────────────────────────────────── */
    .ai-prose { font-size: 0.925rem; line-height: 1.78; color: var(--color-base-content); }
    .ai-prose :global(p)            { margin: 0 0 0.75em; }
    .ai-prose :global(p:last-child) { margin-bottom: 0; }
    .ai-prose :global(h1) { font-size: 1.35em; font-weight: 700; margin: 1.1em 0 0.4em; }
    .ai-prose :global(h2) { font-size: 1.15em; font-weight: 700; margin: 1em 0 0.35em; }
    .ai-prose :global(h3) { font-size: 1em;    font-weight: 700; margin: 0.85em 0 0.3em; }
    .ai-prose :global(h4) { font-size: 0.95em; font-weight: 600; margin: 0.8em 0 0.25em; }
    .ai-prose :global(strong) { font-weight: 700; }
    .ai-prose :global(em)     { font-style: italic; }
    .ai-prose :global(del)    { text-decoration: line-through; opacity: 0.6; }
    .ai-prose :global(ul) { list-style: disc;    padding-left: 1.5em; margin: 0.5em 0 0.75em; }
    .ai-prose :global(ol) { list-style: decimal; padding-left: 1.5em; margin: 0.5em 0 0.75em; }
    .ai-prose :global(li) { margin-bottom: 0.3em; }
    .ai-prose :global(li:last-child) { margin-bottom: 0; }
    .ai-prose :global(blockquote) { border-left: 3px solid var(--color-accent); padding: 0.25em 0 0.25em 1em; color: color-mix(in oklch, var(--color-base-content) 60%, transparent); margin: 0.75em 0; font-style: italic; }
    .ai-prose :global(hr) { border: none; border-top: 1.5px solid color-mix(in oklch, var(--color-base-300) 80%, transparent); margin: 1.1em 0; }
    .ai-prose :global(a) { color: var(--color-accent); text-decoration: underline; text-underline-offset: 2px; }
    .ai-prose :global(a:hover) { opacity: 0.75; }
    .ai-prose :global(code) { background: color-mix(in oklch, var(--color-accent) 9%, transparent); border: 1px solid color-mix(in oklch, var(--color-accent) 20%, transparent); border-radius: 5px; padding: 1px 6px; font-size: 0.83em; font-family: 'JetBrains Mono', monospace; color: var(--color-accent); }
    .ai-prose :global(pre) { background: var(--color-base-200); border: 1.5px solid color-mix(in oklch, var(--color-base-300) 80%, transparent); border-radius: 10px; padding: 1em 1.2em; overflow-x: auto; margin: 0.75em 0; font-size: 0.83em; line-height: 1.6; }
    .ai-prose :global(pre code) { background: transparent; border: none; padding: 0; color: var(--color-base-content); font-size: 1em; }
    .ai-prose :global(.md-table-wrap) { overflow-x: auto; margin: 0.75em 0; border-radius: 10px; border: 1.5px solid color-mix(in oklch, var(--color-base-300) 80%, transparent); }
    .ai-prose :global(table) { width: 100%; border-collapse: collapse; font-size: 0.88em; }
    .ai-prose :global(thead) { background: color-mix(in oklch, var(--color-base-200) 80%, transparent); }
    .ai-prose :global(th) { padding: 8px 12px; font-weight: 600; font-size: 0.85em; letter-spacing: 0.02em; text-transform: uppercase; color: color-mix(in oklch, var(--color-base-content) 60%, transparent); border-bottom: 1.5px solid color-mix(in oklch, var(--color-base-300) 80%, transparent); }
    .ai-prose :global(td) { padding: 7px 12px; border-bottom: 1px solid color-mix(in oklch, var(--color-base-300) 50%, transparent); vertical-align: top; }
    .ai-prose :global(tr:last-child td) { border-bottom: none; }
    .ai-prose :global(tbody tr:hover) { background: color-mix(in oklch, var(--color-base-200) 40%, transparent); }

    /* ── Streaming cursor ────────────────────────────────────── */
    :global(.stream-cursor) {
        display: inline-block; width: 2px; height: 0.9em;
        background: var(--color-accent); border-radius: 1px;
        margin-left: 2px; vertical-align: text-bottom;
        animation: cursorBlink 0.9s step-end infinite;
    }
    @keyframes cursorBlink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }

    /* ── Waiting ─────────────────────────────────────────────── */
    .getting-data {
        font-style: italic; font-size: 0.875rem;
        color: color-mix(in oklch, var(--color-base-content) 35%, transparent);
        animation: fadePulse 1.8s ease-in-out infinite;
    }
    @keyframes fadePulse { 0%, 100% { opacity: 0.5; } 50% { opacity: 1; } }

    /* ── Error ──────────────────────────────────────────────── */
    .error-wrap {
        display: flex;
        justify-content: center;
        margin-top: 16px;
    }
    .error-text {
        font-size: 13px;
        color: var(--color-error);
        background: color-mix(in oklch, var(--color-error) 10%, transparent);
        border: 1px solid color-mix(in oklch, var(--color-error) 20%, transparent);
        border-radius: 12px;
        padding: 8px 16px;
        text-align: center;
    }

    /* ── Textarea ────────────────────────────────────────────── */
    .chat-textarea {
        resize: none;
        line-height: 1.55;
        outline: none !important;
        box-shadow: none !important;
        border: none;
        background: transparent;
        -webkit-appearance: none;
        flex: 1;
        min-width: 0;
        font-size: 15px;
        color: var(--color-base-content);
        min-height: 26px;
        max-height: 120px;
        padding: 6px 0;
    }
    .chat-textarea::placeholder {
        color: color-mix(in oklch, var(--color-base-content) 35%, transparent);
    }
    .chat-textarea:focus, .chat-textarea:focus-visible {
        outline: none !important;
        box-shadow: none !important;
        border: none !important;
    }

    @media (min-width: 768px) {
        .chat-textarea {
            font-size: 0.95rem;
            min-height: 32px;
        }
    }

    /* ── Input wrap ──────────────────────────────────────────── */
    .input-wrap {
        display: flex; align-items: flex-end; gap: 10px;
        background: color-mix(in oklch, var(--color-base-200) 50%, transparent);
        border: 1px solid var(--color-base-300);
        border-radius: 10px; padding: 0 12px;
        transition: background 180ms ease, border-color 180ms ease, box-shadow 180ms ease;
    }
    .input-wrap:focus-within {
        background: var(--color-base-100);
        border-color: var(--color-accent);
        box-shadow: 0 0 0 3px color-mix(in oklch, var(--color-accent) 15%, transparent);
    }

    /* ── Send button ─────────────────────────────────────────── */
    .send-btn {
        flex-shrink: 0; width: 36px; height: 36px; border-radius: 10px;
        border: none; display: flex; align-items: center; justify-content: center;
        transition: background 160ms, box-shadow 160ms, transform 100ms; cursor: pointer;
    }
    .send-btn.ready { background: var(--color-accent); color: var(--color-base-100); }
    .send-btn.ready:hover { box-shadow: 0 4px 12px color-mix(in oklch, var(--color-accent) 35%, transparent); transform: translateY(-1px); }
    .send-btn.ready:active { transform: scale(0.95); }
    .send-btn.idle { background: color-mix(in oklch, var(--color-base-300) 90%, transparent); color: color-mix(in oklch, var(--color-base-content) 40%, transparent); cursor: not-allowed; }

    /* ── Footer ──────────────────────────────────────────────── */
    .chat-footer {
        flex-shrink: 0;
        background: var(--color-base-100);
        border-top: 1px solid var(--color-base-300);
        z-index: 10;
    }

    .footer-inner {
        padding-top: 12px;
        padding-bottom: calc(12px + env(safe-area-inset-bottom, 0px));
    }

    @media (min-width: 768px) {
        .footer-inner { padding: 16px 0; }
        .input-wrap   { padding: 0 14px; border-radius: 14px; }
    }

    .footer-meta {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-top: 8px;
        padding: 0 4px;
    }

    .disclaimer-text {
        font-size: 11px;
        color: color-mix(in oklch, var(--color-base-content) 25%, transparent);
    }

    .clear-btn {
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 11px;
        font-weight: 500;
        color: color-mix(in oklch, var(--color-base-content) 30%, transparent);
        background: transparent;
        border: none;
        cursor: pointer;
        transition: color 130ms;
    }
    .clear-btn:hover {
        color: color-mix(in oklch, var(--color-base-content) 60%, transparent);
    }

    /* ── Scroll button ───────────────────────────────────────── */
    .scroll-btn {
        position: absolute;
        bottom: 24px;
        right: 24px;
        z-index: 10;
        width: 36px; height: 36px;
        border-radius: 50%;
        border: 1px solid color-mix(in oklch, var(--color-base-300) 80%, transparent);
        background: var(--color-base-100);
        box-shadow: 0 2px 12px color-mix(in oklch, var(--color-base-content) 12%, transparent);
        display: flex; align-items: center; justify-content: center;
        cursor: pointer;
        color: color-mix(in oklch, var(--color-base-content) 50%, transparent);
        transition: opacity 200ms, transform 200ms, box-shadow 160ms;
    }
    .scroll-btn:hover { box-shadow: 0 4px 16px color-mix(in oklch, var(--color-base-content) 18%, transparent); transform: translateY(-1px); color: var(--color-base-content); }
    .scroll-btn.hidden  { opacity: 0; pointer-events: none; transform: translateY(6px); }
    .scroll-btn.visible { opacity: 1; pointer-events: auto; transform: translateY(0); }

    @media (min-width: 768px) {
        .scroll-btn {
            right: calc(50vw - 21rem - 20px); /* Adjusted to align with the right edge of main-content */
            right: max(calc(50vw - 21rem - 20px), 260px);
        }
    }
</style>