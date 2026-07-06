<script lang="ts">
  import { onMount, tick } from 'svelte';
  import { goto } from '$app/navigation';
  import Send from '@lucide/svelte/icons/send';
  import RotateCcw from '@lucide/svelte/icons/rotate-ccw';
  import ChevronDown from '@lucide/svelte/icons/chevron-down';
  import ChevronUp from '@lucide/svelte/icons/chevron-up';
  import Settings from '@lucide/svelte/icons/settings';
  import BookOpen from '@lucide/svelte/icons/book-open';
  import Globe from '@lucide/svelte/icons/globe';
  import Database from '@lucide/svelte/icons/database';
  import Blend from '@lucide/svelte/icons/blend';
  import Newspaper from '@lucide/svelte/icons/newspaper';
  import Check from '@lucide/svelte/icons/check';
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
  type Scope = 'mine' | 'all';
  type WaitingPhase = 'thinking' | 'searching' | 'reading' | 'synthesizing' | null;

  let messages = $state<Message[]>([]);
  let input = $state('');
  let loading = $state(false);
  let streaming = $state(false);
  let error = $state('');
  let idCounter = 0;
  let waitingPhase = $state<WaitingPhase>(null);

  let deepReading = $state(true);
  let sourceMode = $state<SourceMode>('mixed');
  let scope = $state<Scope>('mine');
  let dropdownOpen = $state(false);

  let textareaRef: HTMLTextAreaElement;
  let scrollContainer: HTMLElement;
  let messagesEnd: HTMLDivElement;
  let dropdownRef: HTMLElement;

  let chatAbort: AbortController | null = null;

  let showScrollBtn = $state(false);

  let hasStarted = $derived(messages.some(m => m.role === 'user'));

  let waitingMessages = $derived.by(() => ({
    thinking: get(t)('motatab.waitThinking'),
    searching: get(t)('motatab.waitSearching'),
    reading: get(t)('motatab.waitReading'),
    synthesizing: get(t)('motatab.waitSynthesizing'),
  }));

  let sourceOptions = $derived.by(() => [
    { value: 'local' as SourceMode, label: get(t)('motatab.sourceLocal'), Icon: Database },
    { value: 'online' as SourceMode, label: get(t)('motatab.sourceOnline'), Icon: Globe },
    { value: 'mixed' as SourceMode, label: get(t)('motatab.sourceMixed'), Icon: Blend },
  ]);

  let currentSourceLabel = $derived.by(() => {
    const opt = sourceOptions.find(o => o.value === sourceMode);
    return opt ? opt.label : get(t)('motatab.sourceMixed');
  });

  const STORAGE_KEY = 'mota:messages';

  function saveMessages() {
    try {
      const trimmed = messages.slice(-30);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
    } catch {}
  }

  function loadMessages() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed) && parsed.length > 0) {
          messages = parsed;
          idCounter = Math.max(...parsed.map((m: Message) => m.id)) + 1;
        }
      }
    } catch {}
  }

  onMount(() => {
    loadMessages();

    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef && !dropdownRef.contains(e.target as Node)) {
        dropdownOpen = false;
      }
    }
    document.addEventListener('click', handleClickOutside);

    // bfcache eligibility: abort in-flight chat stream when the page is hidden.
    const onVisibilityHidden = () => {
      if (document.visibilityState === 'hidden') abortChat();
    };
    const onPageHide = () => abortChat();
    document.addEventListener('visibilitychange', onVisibilityHidden);
    window.addEventListener('pagehide', onPageHide);

    return () => {
      document.removeEventListener('click', handleClickOutside);
      document.removeEventListener('visibilitychange', onVisibilityHidden);
      window.removeEventListener('pagehide', onPageHide);
      abortChat();
    };
  });

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
        role: 'user',
        content: apiMessage,
        id: userMsgId,
        fromFeed: true,
        feedTitles,
      },
    ];

    await scrollToBottom(true);
    await streamResponse(apiMessage, posts);
  }

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

  async function sendMessage() {
    const text = input.trim();
    if (!text || loading) return;

    input = '';
    dropdownOpen = false;
    if (textareaRef) textareaRef.style.height = 'auto';

    messages = [...messages, { role: 'user', content: text, id: idCounter++ }];
    saveMessages();
    await scrollToBottom(true);

    await streamResponse(text);
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  }

  function clearChat() {
    messages = [];
    error = '';
    idCounter = 0;
    waitingPhase = null;
    try { localStorage.removeItem(STORAGE_KEY); } catch {}
    apiFetch('/api/chat/clear', { method: 'POST' }).catch(() => {});
  }

  function toggleDropdown(e: MouseEvent) {
    e.stopPropagation();
    dropdownOpen = !dropdownOpen;
  }

  async function streamResponse(text: string, posts?: any[]) {
    loading = true;
    streaming = true;
    waitingPhase = null;
    error = '';

    const assistantId = idCounter++;
    messages = [...messages, { role: 'assistant', content: '', id: assistantId }];

    chatAbort = new AbortController();

    try {
      const articles = (posts || []).map((p: any) => ({
        item_id: p.item_id || '',
        title: p.title || '',
        description: p.description || '',
        link: p.link || '',
        feed_title: p.feed_title || '',
        pub_date: p.pub_date || '',
        author: p.author || '',
      }));

      const res = await apiFetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          source_mode: sourceMode,
          deep_reading: deepReading,
          scope,
          articles,
        }),
        signal: chatAbort.signal,
      });

      if (!res.ok) {
        const errText = await res.text().catch(() => '');
        throw new Error(errText || `Error ${res.status}`);
      }

      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith('data: ')) continue;

          const data = trimmed.slice(6);
          if (data === '[DONE]') continue;

          let parsed: any;
          try { parsed = JSON.parse(data); } catch { continue; }

          if (parsed.status) {
            waitingPhase = parsed.status;
          } else if (parsed.content) {
            const msg = messages.find((m: Message) => m.id === assistantId);
            if (msg) msg.content += parsed.content;
          } else if (parsed.error) {
            error = parsed.error;
          }
        }
      }
    } catch (e: any) {
      if (e?.name !== 'AbortError') {
        error = e.message || String(e);
      }
    } finally {
      loading = false;
      streaming = false;
      waitingPhase = null;
      chatAbort = null;

      const lastMsg = messages[messages.length - 1];
      if (lastMsg?.role === 'assistant' && !lastMsg.content.trim()) {
        messages = messages.filter((m: Message) => m.id !== assistantId);
      }
      saveMessages();
    }
  }

  function abortChat() {
    if (chatAbort) {
      chatAbort.abort();
      chatAbort = null;
    }
  }

  function renderMarkdown(content: string): string {
    let html = content
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, (_m, _lang, code) =>
      `<pre><code>${code.trim()}</code></pre>`
    );
    html = html.replace(/`([^`\n]+)`/g, '<code>$1</code>');
    html = html.replace(/^#### (.+)$/gm, '<h4>$1</h4>');
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
    html = html.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>');
    html = html.replace(/___(.+?)___/g, '<strong><em>$1</em></strong>');
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/__(.+?)__/g, '<strong>$1</strong>');
    html = html.replace(/(?<!\w)\*(.+?)\*(?!\w)/g, '<em>$1</em>');
    html = html.replace(/(?<!\w)_(.+?)_(?!\w)/g, '<em>$1</em>');
    html = html.replace(/~~(.+?)~~/g, '<del>$1</del>');
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g,
      '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
    html = html.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>');
    html = html.replace(/^---+$/gm, '<hr>');
    html = html.replace(/^\*\*\*+$/gm, '<hr>');

    html = html.replace(/((?:^\|.+\|(?:\n|$))+)/gm, (block) => {
      const rows = block.trim().split('\n').map(l => l.trim()).filter(Boolean);
      if (rows.length < 2) return block;
      if (!/^\|[\s\-:]+\|?$/.test(rows[1])) return block;

      const parseCells = (line: string) => {
        const cells = line.split('|').map(c => c.trim());
        if (cells[0] === '') cells.shift();
        if (cells[cells.length - 1] === '') cells.pop();
        return cells;
      };

      const headers = parseCells(rows[0]);
      const bodyRows = rows.slice(2);

      let t = '<div class="md-table-wrap"><table><thead><tr>';
      t += headers.map(h => `<th>${h}</th>`).join('');
      t += '</tr></thead><tbody>';
      for (const row of bodyRows) {
        const cells = parseCells(row);
        t += '<tr>' + cells.map(c => `<td>${c}</td>`).join('') + '</tr>';
      }
      t += '</tbody></table></div>';
      return t;
    });

    const lines = html.split('\n');
    const out: string[] = [];
    let inUl = false;
    let inOl = false;

    for (const ln of lines) {
      const ulMatch = ln.match(/^[*\-] (.+)$/);
      const olMatch = ln.match(/^\d+\. (.+)$/);

      if (ulMatch) {
        if (!inUl) { out.push('<ul>'); inUl = true; }
        out.push(`<li>${ulMatch[1]}</li>`);
      } else if (olMatch) {
        if (!inOl) { out.push('<ol>'); inOl = true; }
        out.push(`<li>${olMatch[1]}</li>`);
      } else {
        if (inUl) { out.push('</ul>'); inUl = false; }
        if (inOl) { out.push('</ol>'); inOl = false; }
        out.push(ln);
      }
    }
    if (inUl) out.push('</ul>');
    if (inOl) out.push('</ol>');

    html = out.join('\n');
    html = html.replace(/\n{2,}/g, '</p><p>');
    html = html.replace(/\n/g, '<br>');
    return '<p>' + html + '</p>';
  }

  function renderMarkdownWithCursor(content: string): string {
    return renderMarkdown(content) + '<span class="stream-cursor"></span>';
  }
</script>


<div class="page-root mota-page">

  <!-- ── Top Header + Welcome (in scrollable flow) ─────────── -->
  {#if !hasStarted}
  <div class="main-content">

    <header class="top-header">
      <button class="settings-btn" onclick={() => goto('/settings/appearance')} aria-label="Settings">
        <Settings size={20} />
      </button>
    </header>

    <div class="welcome-section">
      <h1 class="welcome-title">Mota</h1>
      <p class="welcome-subtitle">{$t('motatab.subtitle')}</p>
    </div>

    <div class="feed-wrap"></div>
  </div>
  {/if}

 <!-- ── Scrollable messages ────────────────────────────────────────── -->
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
       {@const isLast = msg === messages[messages.length - 1]}
       {@const isWaiting = isLast && loading && !streaming && msg.content === ''}
       {@const isStreaming = isLast && loading && streaming}
       {@const isStreamingEmpty = isLast && loading && streaming && msg.content === ''}

       <div class="msg-in ai-block">
        <div class="ai-header">
         <span class="ai-label">Mota</span>
        </div>

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

  <button
   class="scroll-btn {showScrollBtn ? 'visible' : 'hidden'}"
   onclick={() => scrollToBottom(true)}
   title="{$t('motatab.scrollToBottom')}"
  >
   <ChevronDown size={18} />
  </button>
 </div>

  <!-- ── Footer ─────────────────────────────────────────────────────── -->
  <footer class="chat-footer">
    <div class="main-content footer-inner">

    <div class="input-wrap">
      {#if dropdownOpen}
      <div class="dropdown-panel" bind:this={dropdownRef}>
        <div class="dropdown-section">
          <p class="dropdown-section-title">{$t('motatab.sourceMode')}</p>
          {#each sourceOptions as opt (opt.value)}
          <button
            class="dropdown-item"
            class:dropdown-item--active={sourceMode === opt.value}
            onclick={() => { sourceMode = opt.value; }}
          >
            <opt.Icon size={15} />
            <span class="dropdown-item-label">{opt.label}</span>
            {#if sourceMode === opt.value}
            <Check size={14} class="dropdown-check" />
            {/if}
          </button>
          {/each}
        </div>

        <div class="dropdown-divider"></div>

        <button
          class="dropdown-item"
          onclick={() => { deepReading = !deepReading; }}
        >
          <BookOpen size={15} />
          <span class="dropdown-item-label">{$t('motatab.deepReading')}</span>
          <span class="dropdown-toggle {deepReading ? 'dropdown-toggle--on' : 'dropdown-toggle--off'}">
            {deepReading ? $t('motatab.on') : $t('motatab.off')}
          </span>
        </button>

        <div class="dropdown-divider"></div>

        <div class="dropdown-section">
          <p class="dropdown-section-title">{$t('motatab.scope')}</p>
          <button
            class="dropdown-item"
            class:dropdown-item--active={scope === 'mine'}
            onclick={() => { scope = 'mine'; }}
          >
            <Database size={15} />
            <span class="dropdown-item-label">{$t('motatab.scopeMine')}</span>
            {#if scope === 'mine'}
            <Check size={14} class="dropdown-check" />
            {/if}
          </button>
          <button
            class="dropdown-item"
            class:dropdown-item--active={scope === 'all'}
            onclick={() => { scope = 'all'; }}
          >
            <Globe size={15} />
            <span class="dropdown-item-label">{$t('motatab.scopeAll')}</span>
            {#if scope === 'all'}
            <Check size={14} class="dropdown-check" />
            {/if}
          </button>
        </div>
      </div>
      {/if}

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
        class="mode-trigger"
        onclick={toggleDropdown}
        aria-expanded={dropdownOpen}
        aria-haspopup="listbox"
        title="{$t('motatab.sourceMode')}"
      >
        <span class="mode-trigger-label">{currentSourceLabel}</span>
        <ChevronUp size={14} />
      </button>

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
 /* ── Page layout ────────────────────────────────────────── */
 .mota-page {
  display: flex;
  flex-direction: column;
  height: 100dvh;
  height: 100vh;
  overflow: hidden;
  padding-bottom: 0;
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

 /* ── Top Header (matches HomeTab) ─────────────────── */
 .top-header {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  padding-top: 12px;
  padding-bottom: 4px;
 }
 .settings-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: 40px;
  padding: 8px;
  cursor: pointer;
  color: color-mix(in oklch, var(--color-base-content) 70%, transparent);
  transition: all 0.2s ease;
 }
 .settings-btn:hover {
  background: color-mix(in oklch, var(--color-base-content) 10%, transparent);
  color: var(--color-base-content);
  transform: rotate(8deg);
 }

 /* ── Welcome Section (matches HomeTab) ─────────────── */
 .welcome-section {
  padding-top: 4px;
  padding-bottom: 16px;
 }
 .welcome-title {
  font-family: var(--font-page-title);
  font-size: 2.25rem;
  font-weight: 400;
  letter-spacing: -0.02em;
  color: var(--color-base-content);
  margin: 0;
  line-height: 1.1;
 }
 .welcome-subtitle {
  font-size: 15px;
  font-weight: 400;
  color: color-mix(in oklch, var(--color-base-content) 45%, transparent);
  margin: 6px 0 0;
  line-height: 1.4;
 }

.feed-wrap {
  border-top: 1px solid var(--color-base-300);
 }

 /* ── Scroll Wrap & Chat Scroll ────────────────────────── */
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

 /* ── Messages List ───────────────────────────────────── */
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

 /* ── Feed posts bubble ───────────────────────────────── */
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

 /* ── User bubble ─────────────────────────────────────── */
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

 /* ── AI block ────────────────────────────────────────── */
 .ai-block { padding: 4px 0 8px; max-width: 100%; }
 .ai-header { display: flex; align-items: center; gap: 7px; margin-bottom: 10px; }
 .ai-label { font-size: 11.5px; font-weight: 700; color: var(--color-accent); letter-spacing: 0.04em; text-transform: uppercase; }

 /* ── AI Prose ────────────────────────────────────────── */
 .ai-prose { font-size: 0.925rem; line-height: 1.78; color: var(--color-base-content); }
 .ai-prose :global(p) { margin: 0 0 0.75em; }
 .ai-prose :global(p:last-child) { margin-bottom: 0; }
 .ai-prose :global(h1) { font-size: 1.35em; font-weight: 700; margin: 1.1em 0 0.4em; }
 .ai-prose :global(h2) { font-size: 1.15em; font-weight: 700; margin: 1em 0 0.35em; }
 .ai-prose :global(h3) { font-size: 1em; font-weight: 700; margin: 0.85em 0 0.3em; }
 .ai-prose :global(h4) { font-size: 0.95em; font-weight: 600; margin: 0.8em 0 0.25em; }
 .ai-prose :global(strong) { font-weight: 700; }
 .ai-prose :global(em) { font-style: italic; }
 .ai-prose :global(del) { text-decoration: line-through; opacity: 0.6; }
 .ai-prose :global(ul) { list-style: disc; padding-left: 1.5em; margin: 0.5em 0 0.75em; }
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

 /* ── Streaming cursor ────────────────────────────────── */
 :global(.stream-cursor) {
  display: inline-block; width: 2px; height: 0.9em;
  background: var(--color-accent); border-radius: 1px;
  margin-left: 2px; vertical-align: text-bottom;
  animation: cursorBlink 0.9s step-end infinite;
 }
 @keyframes cursorBlink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }

 /* ── Waiting ─────────────────────────────────────────── */
 .getting-data {
  font-style: italic; font-size: 0.875rem;
  color: color-mix(in oklch, var(--color-base-content) 35%, transparent);
  animation: fadePulse 1.8s ease-in-out infinite;
 }
 @keyframes fadePulse { 0%, 100% { opacity: 0.5; } 50% { opacity: 1; } }

 /* ── Error ──────────────────────────────────────────── */
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

/* ── Textarea ────────────────────────────────────────── */
.chat-textarea {
  resize: none;
  line-height: 1.3;
  outline: none !important;
  box-shadow: none !important;
  border: none;
  background: transparent;
  -webkit-appearance: none;
  flex: 1;
  min-width: 0;
  font-size: 15px;
  color: var(--color-base-content);
  max-height: 120px;
  padding: 0;
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
  }
}

/* ── Input wrap ──────────────────────────────────────── */
.input-wrap {
  display: flex;
  align-items: center;
  gap: 6px;
  height: 46px;
  background: color-mix(in oklch, var(--color-base-200) 50%, transparent);
  border: 1px solid var(--color-base-300);
  border-radius: 10px;
  padding: 0 4px 0 16px;
  position: relative;
  transition: background 180ms ease, border-color 180ms ease, box-shadow 180ms ease;
}
.input-wrap:focus-within {
  background: var(--color-base-100);
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px color-mix(in oklch, var(--color-accent) 15%, transparent);
}

/* ── Mode trigger (dropdown button) ─────────────────── */
.mode-trigger {
  display: flex;
  align-items: center;
  gap: 3px;
  flex-shrink: 0;
  padding: 6px 8px;
  border: none;
  border-radius: 8px;
  background: transparent;
  cursor: pointer;
  color: color-mix(in oklch, var(--color-base-content) 55%, transparent);
  transition: background 140ms, color 140ms;
  white-space: nowrap;
}
.mode-trigger:hover {
  background: color-mix(in oklch, var(--color-base-content) 8%, transparent);
  color: var(--color-base-content);
}
.mode-trigger-label {
  font-size: 13px;
  font-weight: 600;
}

/* ── Dropdown panel ─────────────────────────────────── */
.dropdown-panel {
  position: absolute;
  bottom: calc(100% + 8px);
  right: 0;
  min-width: 220px;
  background: var(--color-base-100);
  border: 1px solid var(--color-base-300);
  border-radius: 12px;
  box-shadow: 0 8px 24px color-mix(in oklch, black 16%, transparent),
              0 2px 6px color-mix(in oklch, black 8%, transparent);
  padding: 6px;
  z-index: 60;
  animation: dropdownIn 150ms cubic-bezier(0.16, 1, 0.3, 1) both;
}
@keyframes dropdownIn {
  from { opacity: 0; transform: translateY(6px) scale(0.97); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.dropdown-section {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.dropdown-section-title {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: color-mix(in oklch, var(--color-base-content) 40%, transparent);
  padding: 6px 10px 4px;
  margin: 0;
}
.dropdown-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border: none;
  border-radius: 8px;
  background: transparent;
  cursor: pointer;
  font-size: 13.5px;
  font-weight: 500;
  color: color-mix(in oklch, var(--color-base-content) 75%, transparent);
  transition: background 120ms, color 120ms;
  width: 100%;
  text-align: left;
}
.dropdown-item:hover {
  background: var(--color-base-200);
  color: var(--color-base-content);
}
.dropdown-item--active {
  color: var(--color-accent);
  font-weight: 600;
}
.dropdown-item--active:hover {
  background: color-mix(in oklch, var(--color-accent) 8%, transparent);
  color: var(--color-accent);
}
.dropdown-item-label {
  flex: 1;
}
.dropdown-check {
  color: var(--color-accent);
  flex-shrink: 0;
}
.dropdown-toggle {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 2px 8px;
  border-radius: 6px;
  flex-shrink: 0;
}
.dropdown-toggle--on {
  background: color-mix(in oklch, var(--color-accent) 15%, transparent);
  color: var(--color-accent);
}
.dropdown-toggle--off {
  background: var(--color-base-200);
  color: color-mix(in oklch, var(--color-base-content) 40%, transparent);
}
.dropdown-divider {
  height: 1px;
  background: var(--color-base-300);
  margin: 4px 6px;
}

/* ── Send button ─────────────────────────────────────── */
.send-btn {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  margin: 5px;
  border-radius: 8px;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 160ms, box-shadow 160ms, transform 100ms;
  cursor: pointer;
}
 .send-btn.ready { background: var(--color-accent); color: var(--color-base-100); }
 .send-btn.ready:hover { box-shadow: 0 4px 12px color-mix(in oklch, var(--color-accent) 35%, transparent); transform: translateY(-1px); }
 .send-btn.ready:active { transform: scale(0.95); }
 .send-btn.idle { background: color-mix(in oklch, var(--color-base-300) 90%, transparent); color: color-mix(in oklch, var(--color-base-content) 40%, transparent); cursor: not-allowed; }

/* ── Footer ──────────────────────────────────────────── */
.chat-footer {
  flex-shrink: 0;
  background: var(--color-base-100);
  border-top: none;
  z-index: 10;
  position: relative;
}

.footer-inner {
  padding-top: 12px;
  padding-bottom: calc(12px + env(safe-area-inset-bottom, 0px));
  position: relative;
}

@media (max-width: 767px) {
  .footer-inner {
    padding-bottom: calc(12px + 64px + env(safe-area-inset-bottom, 0px));
  }
}

@media (min-width: 768px) {
  .footer-inner { padding: 16px 0; }
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
  display: flex; align-items: center; gap: 4px;
  font-size: 11px; font-weight: 500;
  color: color-mix(in oklch, var(--color-base-content) 30%, transparent);
  background: transparent; border: none; cursor: pointer;
  transition: color 130ms;
 }
 .clear-btn:hover {
  color: color-mix(in oklch, var(--color-base-content) 60%, transparent);
 }

 /* ── Scroll button ───────────────────────────────────── */
 .scroll-btn {
  position: absolute;
  bottom: 24px; right: 24px;
  z-index: 10;
  width: 36px; height: 36px; border-radius: 50%;
  border: 1px solid color-mix(in oklch, var(--color-base-300) 80%, transparent);
  background: var(--color-base-100);
  box-shadow: 0 2px 12px color-mix(in oklch, var(--color-base-content) 12%, transparent);
  display: flex; align-items: center; justify-content: center; cursor: pointer;
  color: color-mix(in oklch, var(--color-base-content) 50%, transparent);
  transition: opacity 200ms, transform 200ms, box-shadow 160ms;
 }
 .scroll-btn:hover {
  box-shadow: 0 4px 16px color-mix(in oklch, var(--color-base-content) 18%, transparent);
  transform: translateY(-1px);
  color: var(--color-base-content);
 }
 .scroll-btn.hidden { opacity: 0; pointer-events: none; transform: translateY(6px); }
 .scroll-btn.visible { opacity: 1; pointer-events: auto; transform: translateY(0); }

 @media (min-width: 768px) {
  .scroll-btn {
   right: max(calc(50vw - 21rem - 20px), 260px);
  }
 }
</style>
