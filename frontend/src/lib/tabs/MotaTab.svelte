<script lang="ts">
  import { onMount, tick } from 'svelte';
  import { goto } from '$app/navigation';
  import Send from '@lucide/svelte/icons/send';
  import ChevronDown from '@lucide/svelte/icons/chevron-down';
  import ChevronUp from '@lucide/svelte/icons/chevron-up';
  import Settings from '@lucide/svelte/icons/settings';
  import Globe from '@lucide/svelte/icons/globe';
  import Database from '@lucide/svelte/icons/database';
  import Blend from '@lucide/svelte/icons/blend';
  import Newspaper from '@lucide/svelte/icons/newspaper';
  import Brain from '@lucide/svelte/icons/brain';
  import Check from '@lucide/svelte/icons/check';
  import MessageSquare from '@lucide/svelte/icons/message-square';
  import Plus from '@lucide/svelte/icons/plus';
  import X from '@lucide/svelte/icons/x';
  import Pencil from '@lucide/svelte/icons/pencil';
  import Trash2 from '@lucide/svelte/icons/trash-2';
  import History from '@lucide/svelte/icons/history';
  import { pendingMotaPosts, navVisible } from '$lib/stores/swipe';
  import {
    chatSessions,
    currentSessionId,
    sessionsOpen,
    type ChatSession,
  } from '$lib/stores/chatSessions';
  import { t, locale } from 'svelte-i18n';
  import { get } from 'svelte/store';
  import { apiFetch } from '$lib/api';

  type Source = {
    id: number;
    outlet: string;
    title: string;
    url: string;
    date?: string;
  };

  type Message = {
    role: 'user' | 'assistant';
    content: string;
    id: number;
    fromFeed?: boolean;
    feedTitles?: string[];
    sources?: Source[];
    sourcesOpen?: boolean;
    queries?: string[];
    thinking?: string;
    thinkingCollapsed?: boolean;
  };

  type SourceMode = 'local' | 'online' | 'mixed';
  type SourcesPreset = 'feeds' | 'web' | 'both';
  type WaitingPhase = 'thinking' | 'planning' | 'searching' | 'reading' | 'synthesizing' | 'refining' | null;

  let messages = $state<Message[]>([]);
  let input = $state('');
  let loading = $state(false);
  let streaming = $state(false);
  let error = $state('');
  let idCounter = 0;
  let waitingPhase = $state<WaitingPhase>(null);

  let sourcesPreset = $state<SourcesPreset>('both');
  let dropdownOpen = $state(false);

  let sessionsLoading = $state(false);
  let sessionsFailed = $state(false);
  let renamingSessionId = $state<number | null>(null);
  let renameDraft = $state('');
  let confirmDeleteId = $state<number | null>(null);

  let textareaRef: HTMLTextAreaElement;
  let scrollContainer: HTMLElement;
  let messagesEnd: HTMLDivElement;
  let dropdownRef = $state<HTMLElement>();

  let chatAbort: AbortController | null = null;

  let showScrollBtn = $state(false);
  let inputButtonsMultiLine = $state(false);

  let hasStarted = $derived(messages.some(m => m.role === 'user'));

  let waitingMessages = $derived.by(() => ({
    thinking: get(t)('motatab.waitThinking'),
    planning: get(t)('motatab.waitPlanning'),
    searching: get(t)('motatab.waitSearching'),
    reading: get(t)('motatab.waitReading'),
    synthesizing: get(t)('motatab.waitSynthesizing'),
    refining: get(t)('motatab.waitRefining'),
  }));

  let sourceOptions = $derived.by(() => [
    { value: 'feeds' as SourcesPreset, label: get(t)('motatab.sourceLocal'), labelShort: get(t)('motatab.sourceLocalShort'), Icon: Database, mode: 'local' as SourceMode, scope: 'mine' as const },
    { value: 'web' as SourcesPreset, label: get(t)('motatab.sourceOnline'), labelShort: get(t)('motatab.sourceOnlineShort'), Icon: Globe, mode: 'online' as SourceMode, scope: 'all' as const },
    { value: 'both' as SourcesPreset, label: get(t)('motatab.sourceMixed'), labelShort: get(t)('motatab.sourceMixedShort'), Icon: Blend, mode: 'mixed' as SourceMode, scope: 'mine' as const },
  ]);

  let currentSourceLabel = $derived.by(() => {
    const opt = sourceOptions.find(o => o.value === sourcesPreset);
    return opt ? opt.labelShort : get(t)('motatab.sourceMixedShort');
  });

  const STORAGE_KEY = 'mota:messages';
  const SESSION_KEY = 'mota:session';
  const SESSION_ID_KEY = 'mota:session-id';

  function saveMessages() {
    try {
      const trimmed = messages.slice(-30);
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
    } catch {}
  }

  function loadMessages() {
    try {
      const raw = sessionStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed) && parsed.length > 0) {
          messages = parsed;
          idCounter = Math.max(...parsed.map((m: Message) => m.id)) + 1;
        }
      }
    } catch {}
  }

  // A brand-new browser session starts a fresh chat: locally-stored
  // messages are cleared, but durable sessions stay available via the
  // Sessions overlay (MySQL, server-side).
  function ensureFreshSession() {
    try {
      if (sessionStorage.getItem(SESSION_KEY)) return;
      sessionStorage.setItem(SESSION_KEY, '1');
      sessionStorage.removeItem(STORAGE_KEY);
      sessionStorage.removeItem(SESSION_ID_KEY);
    } catch {}
  }

  function persistSessionId(id: number | null) {
    try {
      if (id != null) sessionStorage.setItem(SESSION_ID_KEY, String(id));
      else sessionStorage.removeItem(SESSION_ID_KEY);
    } catch {}
  }

  onMount(() => {
    ensureFreshSession();
    try {
      const sid = sessionStorage.getItem(SESSION_ID_KEY);
      if (sid) currentSessionId.set(parseInt(sid, 10) || null);
    } catch {}
    if ($currentSessionId != null) loadMessages();

    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef && !dropdownRef.contains(e.target as Node)) {
        dropdownOpen = false;
      }
    }
    document.addEventListener('click', handleClickOutside);

    // Escape closes the sessions overlay
    function handleKeydown(e: KeyboardEvent) {
      if (e.key === 'Escape' && $sessionsOpen) {
        e.stopPropagation();
        sessionsOpen.set(false);
      }
    }
    document.addEventListener('keydown', handleKeydown);

    // bfcache eligibility: abort in-flight chat stream only on real page
    // unload — hiding the tab (switching windows) must NOT kill the stream.
    const onPageHide = () => abortChat();
    window.addEventListener('pagehide', onPageHide);

    return () => {
      document.removeEventListener('click', handleClickOutside);
      document.removeEventListener('keydown', handleKeydown);
      window.removeEventListener('pagehide', onPageHide);
      abortChat();
    };
  });

  $effect(() => {
    persistSessionId($currentSessionId);
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
    const maxHeight = parseFloat(getComputedStyle(textareaRef).maxHeight) || 135;
    textareaRef.style.height = Math.min(textareaRef.scrollHeight, maxHeight) + 'px';
    inputButtonsMultiLine = textareaRef.scrollHeight > 46;
  }

  async function sendMessage() {
    const text = input.trim();
    if (!text || loading) return;

    input = '';
    dropdownOpen = false;
    if (textareaRef) textareaRef.style.height = 'auto';
    inputButtonsMultiLine = false;

    messages = [...messages, { role: 'user', content: text, id: idCounter++ }];
    saveMessages();
    await scrollToBottom(true);

    await streamResponse(text);
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  }

  function newChat() {
    abortChat();
    messages = [];
    error = '';
    idCounter = 0;
    waitingPhase = null;
    currentSessionId.set(null);
    try { sessionStorage.removeItem(STORAGE_KEY); } catch {}
  }

  // ── Sessions manager ─────────────────────────────────────
  function sessionTitle(s: ChatSession): string {
    return s.title || s.fallback_title || get(t)('motatab.untitledSession');
  }

  function formatSessionDate(dateStr: string | null): string {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return '';
    const now = Date.now();
    const min = Math.floor((now - date.getTime()) / 60000);
    const h = Math.floor(min / 60);
    const d = Math.floor(h / 24);
    if (min < 1) return get(t)('postcard.now');
    if (min < 60) return `${min}${get(t)('postcard.minutesShort')}`;
    if (h < 24) return `${h}${get(t)('postcard.hoursShort')}`;
    if (d < 7) return `${d}${get(t)('postcard.daysShort')}`;
    const loc = get(locale) ?? 'en';
    return date.toLocaleDateString(loc, {
      day: '2-digit',
      month: 'short',
      year: new Date().getFullYear() !== date.getFullYear() ? 'numeric' : undefined,
    });
  }

  async function openSessions() {
    sessionsOpen.set(true);
    await refreshSessions();
  }

  function closeSessions() {
    sessionsOpen.set(false);
    renamingSessionId = null;
    confirmDeleteId = null;
  }

  async function refreshSessions() {
    sessionsLoading = true;
    sessionsFailed = false;
    try {
      const res = await apiFetch('/api/chat/sessions');
      if (!res.ok) throw new Error(`Error ${res.status}`);
      const data = await res.json();
      chatSessions.set(Array.isArray(data.sessions) ? data.sessions : []);
    } catch {
      sessionsFailed = true;
    } finally {
      sessionsLoading = false;
    }
  }

  async function resumeSession(s: ChatSession) {
    closeSessions();
    abortChat();
    try {
      const res = await apiFetch(`/api/chat/sessions/${s.id}/messages`);
      if (!res.ok) throw new Error(`Error ${res.status}`);
      const data = await res.json();
      const loaded: Message[] = (Array.isArray(data.messages) ? data.messages : [])
        .map((m: any) => {
          const msg: Message = { role: m.role, content: m.content || '', id: idCounter++ };
          if (m.role === 'assistant') {
            if (Array.isArray(m.sources) && m.sources.length) msg.sources = m.sources;
          }
          return msg;
        });
      messages = loaded;
      error = '';
      currentSessionId.set(s.id);
      persistSessionId(s.id);
      saveMessages();
      await scrollToBottom(false);
    } catch (e: any) {
      error = e?.message || String(e);
    }
  }

  function startRename(s: ChatSession) {
    renamingSessionId = s.id;
    renameDraft = s.title || s.fallback_title || '';
    confirmDeleteId = null;
  }

  async function submitRename() {
    const id = renamingSessionId;
    const title = renameDraft.trim();
    if (id == null || !title) { renamingSessionId = null; return; }
    try {
      const res = await apiFetch(`/api/chat/sessions/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title }),
      });
      if (res.ok) {
        chatSessions.update(list =>
          list.map(s => (s.id === id ? { ...s, title } : s))
        );
      }
    } catch {}
    renamingSessionId = null;
  }

  function askDelete(id: number) {
    renamingSessionId = null;
    confirmDeleteId = id;
  }

  async function removeSession(id: number) {
    confirmDeleteId = null;
    try {
      const res = await apiFetch(`/api/chat/sessions/${id}`, { method: 'DELETE' });
      if (res.ok) {
        chatSessions.update(list => list.filter(s => s.id !== id));
        if (id === $currentSessionId) newChat();
      }
    } catch {}
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

      const preset = sourceOptions.find(o => o.value === sourcesPreset) ?? sourceOptions[2];

      const res = await apiFetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          source_mode: preset.mode,
          scope: preset.scope,
          session_id: $currentSessionId,
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

          if (parsed.session?.id != null) {
            // Brand-new session created server-side on the first message
            currentSessionId.set(parsed.session.id);
          }
          if (parsed.status) {
            waitingPhase = parsed.status;
          } else if (parsed.thinking) {
            const msg = messages.find((m: Message) => m.id === assistantId);
            if (msg) msg.thinking = (msg.thinking || '') + parsed.thinking;
          } else if (parsed.content) {
            const msg = messages.find((m: Message) => m.id === assistantId);
            if (msg) {
              msg.content += parsed.content;
              // Auto-collapse the thinking panel once the answer starts
              if (msg.thinking && !msg.thinkingCollapsed && msg.content.trim()) {
                msg.thinkingCollapsed = true;
              }
            }
          } else if (parsed.sources && Array.isArray(parsed.sources)) {
            const msg = messages.find((m: Message) => m.id === assistantId);
            if (msg) msg.sources = parsed.sources;
          } else if (parsed.queries && Array.isArray(parsed.queries)) {
            const msg = messages.find((m: Message) => m.id === assistantId);
            if (msg) msg.queries = parsed.queries;
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

    // Inline numbered citations → clickable badge (safe: n ≤ 99, no user input)
    html = html.replace(/(?<!&)\[(\d{1,2})\](?!\()/g,
      '<sup class="cite-ref">$1</sup>');

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

  <!-- ── Top Header (persistent) ──────────────────────────── -->
  <header class="top-header">
    <div class="main-content top-header-inner">
      <div class="top-header-actions">
        <button class="header-icon-btn" onclick={openSessions} title="{$t('motatab.sessionsTitle')}" aria-label="{$t('motatab.sessions')}">
          <History size={20} />
        </button>
        <button class="header-icon-btn" onclick={() => { closeSessions(); newChat(); }} title="{$t('motatab.newChat')}" aria-label="{$t('motatab.newChat')}">
          <Plus size={20} />
        </button>
        <button class="settings-btn" onclick={() => goto('/settings')} aria-label="Settings">
          <Settings size={20} />
        </button>
      </div>
    </div>
  </header>

  <!-- ── Sessions screen (full-tab, Following-tab pattern) ── -->
  {#if $sessionsOpen}
    <section class="sessions-screen" aria-label="{$t('motatab.sessionsTitle')}">
      <div class="main-content sessions-inner">
        <header class="sessions-header">
          <h2 class="sessions-title">{$t('motatab.sessionsTitle')}</h2>
          <button class="header-icon-btn" onclick={closeSessions} aria-label="{$t('followerstab.close')}">
            <X size={20} />
          </button>
        </header>

        {#if sessionsLoading && $chatSessions.length === 0}
          <ul class="sessions-list" aria-hidden="true">
            {#each Array.from({ length: 6 }) as _, i (i)}
              <li class="sk-row">
                <div class="sk-bar" style="width:46%"></div>
                <div class="sk-bar sk-ml-auto" style="width:44px; opacity:.4"></div>
              </li>
            {/each}
          </ul>
        {:else if sessionsFailed}
          <div class="sessions-state">
            <p class="sessions-state-text">{$t('motatab.sessionsError')}</p>
          </div>
        {:else if $chatSessions.length === 0}
          <div class="state-empty-wrap">
            <MessageSquare size={28} strokeWidth={1.5} class="empty-icon" />
            <p class="state-empty">{$t('motatab.noSessions')}</p>
            <button class="empty-cta" onclick={() => { closeSessions(); newChat(); }}>
              <Plus size={14} />
              <span>{$t('motatab.newChat')}</span>
            </button>
          </div>
        {:else}
          <ul class="sessions-list">
            {#each $chatSessions as s (s.id)}
              <li class="session-row" class:session-row--active={s.id === $currentSessionId}>
                {#if renamingSessionId === s.id}
                  <input
                    class="session-rename-input"
                    type="text"
                    bind:value={renameDraft}
                    placeholder="{$t('motatab.renamePlaceholder')}"
                    maxlength="120"
                    onkeydown={(e) => {
                      if (e.key === 'Enter') submitRename();
                      if (e.key === 'Escape') { renamingSessionId = null; e.stopPropagation(); }
                    }}
                  />
                  <button class="session-action-btn session-action-btn--confirm" onclick={submitRename} title="OK">
                    <Check size={14} />
                  </button>
                {:else if confirmDeleteId === s.id}
                  <span class="session-confirm">{$t('motatab.confirmDelete')}</span>
                  <div class="session-actions">
                    <button class="session-action-btn session-action-btn--confirm" onclick={() => { confirmDeleteId = null; }} aria-label="{$t('motatab.deleteSession')}">
                      <X size={14} />
                    </button>
                    <button class="session-action-btn session-action-btn--danger" onclick={() => removeSession(s.id)} title="{$t('motatab.confirmDelete')}">
                      <Check size={14} />
                    </button>
                  </div>
                {:else}
                  <button class="session-main" onclick={() => resumeSession(s)} title="{$t('motatab.openSession')}">
                    <span class="session-title">{sessionTitle(s)}</span>
                    <time class="session-date" datetime={s.updated_at ?? undefined}>{formatSessionDate(s.updated_at)}</time>
                  </button>
                  <div class="session-actions">
                    <button class="session-action-btn" onclick={() => startRename(s)} title="{$t('motatab.renameSession')}">
                      <Pencil size={13} />
                    </button>
                    <button class="session-action-btn" onclick={() => askDelete(s.id)} title="{$t('motatab.deleteSession')}">
                      <Trash2 size={13} />
                    </button>
                  </div>
                {/if}
              </li>
            {/each}
          </ul>
        {/if}
      </div>
    </section>
  {:else}

  {#if !hasStarted}
  <div class="main-content">
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

        {#if (isWaiting || isStreamingEmpty) && !msg.thinking}
          <p class="getting-data">
            {waitingPhase ? waitingMessages[waitingPhase] ?? $t('motatab.waitThinking') : $t('motatab.waitThinking')}
          </p>
        {:else}
          {#if msg.thinking}
            <div class="thinking-box" class:thinking-box--live={isLast && loading && !msg.thinkingCollapsed}>
              <button
                class="thinking-toggle"
                onclick={() => { msg.thinkingCollapsed = !msg.thinkingCollapsed; }}
                aria-expanded={!msg.thinkingCollapsed}
              >
                <Brain size={13} />
                <span class="thinking-title">
                  {isLast && loading && !msg.content
                    ? $t('motatab.thinkingRunning')
                    : $t('motatab.thinkingTitle')}
                </span>
                <ChevronDown size={13} class="thinking-chevron {msg.thinkingCollapsed ? 'rot' : ''}" />
              </button>
              {#if !msg.thinkingCollapsed}
                <div class="thinking-body">{msg.thinking}</div>
              {/if}
            </div>
          {/if}
          {#if msg.queries?.length}
            <div class="queries-row">
              <span class="queries-label">{msg.queries.length} {msg.queries.length === 1 ? $t('motatab.searchedLabel') : $t('motatab.searchedLabelPlural')}</span>
              {#each msg.queries as q}
                <span class="query-chip" title={q}>{q}</span>
              {/each}
            </div>
          {/if}
          {#if msg.content || !isLast}
            <div class="ai-prose">{@html isStreaming ? renderMarkdownWithCursor(msg.content) : renderMarkdown(msg.content)}</div>
          {/if}
        {/if}

        {#if msg.sources?.length && !isWaiting && !isStreamingEmpty}
          <div class="sources-rail">
            <button
              class="sources-toggle"
              onclick={() => { msg.sourcesOpen = !msg.sourcesOpen; }}
              aria-expanded={!!msg.sourcesOpen}
            >
              <span class="sources-title">{$t('motatab.sourcesTitle')}</span>
              <span class="sources-count">{msg.sources.length}</span>
              <ChevronDown size={13} class="sources-chevron {msg.sourcesOpen ? 'rot' : ''}" />
            </button>
            {#if msg.sourcesOpen}
              <div class="sources-list">
                {#each msg.sources as src (src.id)}
                  <a
                    class="source-chip"
                    href={src.url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <span class="source-num">{src.id}</span>
                    <span class="source-meta">
                      <span class="source-outlet">{src.outlet}</span>
                      <span class="source-headline">{src.title}</span>
                    </span>
                  </a>
                {/each}
              </div>
            {/if}
          </div>
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
    <div class="main-content footer-inner" class:nav-free={!$navVisible}>

    <div class="input-wrap">
      {#if dropdownOpen}
      <div class="dropdown-panel" bind:this={dropdownRef}>
        <div class="dropdown-section">
          <p class="dropdown-section-title">{$t('motatab.sourceMode')}</p>
          {#each sourceOptions as opt (opt.value)}
          <button
            class="dropdown-item"
            class:dropdown-item--active={sourcesPreset === opt.value}
            onclick={() => { sourcesPreset = opt.value; }}
          >
            <opt.Icon size={15} />
            <span class="dropdown-item-label">{opt.label}</span>
            {#if sourcesPreset === opt.value}
            <Check size={14} class="dropdown-check" />
            {/if}
          </button>
          {/each}
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

      <div class="input-buttons" class:pin-bottom={inputButtonsMultiLine}>
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
    </div>
    </div>
  </footer>

  {/if}

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
   margin-left: max(var(--sidebar-w, 240px), calc(50vw - 21rem));
   margin-right: auto;
  }
 }

 /* ── Top Header (persistent) ─────────────────────── */
 .top-header {
  padding-top: 12px;
  padding-bottom: 4px;
 }
 .top-header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
 }
 .top-header-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-left: auto;
 }
 .settings-btn,
 .header-icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: var(--ui-radius-full);
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
 .header-icon-btn:hover {
  background: color-mix(in oklch, var(--color-base-content) 10%, transparent);
  color: var(--color-base-content);
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
 .chat-scroll::-webkit-scrollbar-thumb { background: color-mix(in oklch, var(--color-accent) 20%, transparent); border-radius: var(--ui-radius-xs); }

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
  border-radius: var(--ui-radius-lg) var(--ui-radius-lg) var(--ui-radius-xs) var(--ui-radius-lg);
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
  border-radius: var(--ui-radius-lg) var(--ui-radius-lg) var(--ui-radius-xs) var(--ui-radius-lg);
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

 /* ── Thinking panel (provider reasoning, DeepSeek-web style) ── */
 .thinking-box {
  margin-bottom: 10px;
  border: 1px solid color-mix(in oklch, var(--color-base-300) 70%, transparent);
  border-radius: var(--ui-radius-sm);
  background: color-mix(in oklch, var(--color-base-200) 45%, transparent);
  overflow: hidden;
 }
 .thinking-box--live {
  border-color: color-mix(in oklch, var(--color-accent) 35%, transparent);
 }
 .thinking-toggle {
  display: flex;
  align-items: center;
  gap: 7px;
  width: 100%;
  padding: 7px 10px;
  border: none;
  background: transparent;
  cursor: pointer;
  color: color-mix(in oklch, var(--color-base-content) 55%, transparent);
  font-size: 12px;
  font-weight: 600;
  text-align: left;
 }
 .thinking-toggle:hover {
  color: var(--color-base-content);
 }
 .thinking-box--live .thinking-title {
  color: var(--color-accent);
  animation: fadePulse 1.8s ease-in-out infinite;
 }
 .thinking-box :global(.thinking-chevron) {
  margin-left: auto;
  transition: transform 150ms ease;
  flex-shrink: 0;
 }
 .thinking-box :global(.thinking-chevron.rot) {
  transform: rotate(-90deg);
 }
 .thinking-body {
  padding: 2px 12px 10px 30px;
  font-size: 12.5px;
  line-height: 1.65;
  white-space: pre-wrap;
  word-break: break-word;
  color: color-mix(in oklch, var(--color-base-content) 55%, transparent);
  max-height: 260px;
  overflow-y: auto;
  scrollbar-width: thin;
 }

 /* ── Executed-queries chips ───────────────────────────── */
 .queries-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px 8px;
  margin-bottom: 10px;
 }
 .queries-label {
  font-size: 10.5px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: color-mix(in oklch, var(--color-base-content) 45%, transparent);
 }
 .query-chip {
  display: inline-flex;
  align-items: center;
  max-width: 260px;
  padding: 3px 10px;
  border-radius: 999px;
  background: color-mix(in oklch, var(--color-base-200) 70%, transparent);
  border: 1px solid color-mix(in oklch, var(--color-base-300) 70%, transparent);
  font-size: 11.5px;
  color: color-mix(in oklch, var(--color-base-content) 65%, transparent);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
 }

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
 .ai-prose :global(code) { background: color-mix(in oklch, var(--color-accent) 9%, transparent); border: 1px solid color-mix(in oklch, var(--color-accent) 20%, transparent); border-radius: var(--ui-radius-xs); padding: 1px 6px; font-size: 0.83em; font-family: 'JetBrains Mono', monospace; color: var(--color-accent); }
 .ai-prose :global(pre) { background: var(--color-base-200); border: 1.5px solid color-mix(in oklch, var(--color-base-300) 80%, transparent); border-radius: var(--ui-radius-sm); padding: 1em 1.2em; overflow-x: auto; margin: 0.75em 0; font-size: 0.83em; line-height: 1.6; }
 .ai-prose :global(pre code) { background: transparent; border: none; padding: 0; color: var(--color-base-content); font-size: 1em; }
 .ai-prose :global(.md-table-wrap) { overflow-x: auto; margin: 0.75em 0; border-radius: var(--ui-radius-sm); border: 1.5px solid color-mix(in oklch, var(--color-base-300) 80%, transparent); }
 .ai-prose :global(table) { width: 100%; border-collapse: collapse; font-size: 0.88em; }
 .ai-prose :global(thead) { background: color-mix(in oklch, var(--color-base-200) 80%, transparent); }
 .ai-prose :global(th) { padding: 8px 12px; font-weight: 600; font-size: 0.85em; letter-spacing: 0.02em; text-transform: uppercase; color: color-mix(in oklch, var(--color-base-content) 60%, transparent); border-bottom: 1.5px solid color-mix(in oklch, var(--color-base-300) 80%, transparent); }
 .ai-prose :global(td) { padding: 7px 12px; border-bottom: 1px solid color-mix(in oklch, var(--color-base-300) 50%, transparent); vertical-align: top; }
 .ai-prose :global(tr:last-child td) { border-bottom: none; }
 .ai-prose :global(tbody tr:hover) { background: color-mix(in oklch, var(--color-base-200) 40%, transparent); }

 /* ── Inline citation badge ────────────────────────────── */
 .ai-prose :global(.cite-ref) {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 1.35em;
  height: 1.35em;
  padding: 0 0.25em;
  margin: 0 1px;
  background: color-mix(in oklch, var(--color-accent) 12%, transparent);
  color: var(--color-accent);
  border: 1px solid color-mix(in oklch, var(--color-accent) 25%, transparent);
  border-radius: var(--ui-radius-xs);
  font-size: 0.68em;
  font-weight: 700;
  vertical-align: super;
  line-height: 1;
  user-select: none;
 }

 /* ── Sources rail ─────────────────────────────────────── */
 .sources-rail {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid color-mix(in oklch, var(--color-base-300) 60%, transparent);
 }
 .sources-toggle {
  display: flex;
  align-items: center;
  gap: 7px;
  border: none;
  background: transparent;
  padding: 2px 4px;
  margin-left: -4px;
  cursor: pointer;
  color: color-mix(in oklch, var(--color-base-content) 45%, transparent);
  transition: color 130ms;
 }
 .sources-toggle:hover {
  color: color-mix(in oklch, var(--color-base-content) 75%, transparent);
 }
 .sources-title {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin: 0;
 }
 .sources-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 16px;
  padding: 0 5px;
  border-radius: 999px;
  background: color-mix(in oklch, var(--color-accent) 15%, transparent);
  color: var(--color-accent);
  font-size: 10px;
  font-weight: 700;
 }
 .sources-rail :global(.sources-chevron) {
  transition: transform 150ms ease;
  flex-shrink: 0;
 }
 .sources-rail :global(.sources-chevron.rot) {
  transform: rotate(180deg);
 }
 .sources-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 8px;
  animation: sourcesIn 160ms cubic-bezier(0.16, 1, 0.3, 1) both;
 }
 @keyframes sourcesIn {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: translateY(0); }
 }
 .source-chip {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 6px 8px;
  border-radius: var(--ui-radius-sm);
  border: 1px solid color-mix(in oklch, var(--color-base-300) 70%, transparent);
  background: color-mix(in oklch, var(--color-base-200) 45%, transparent);
  text-decoration: none;
  transition: background 130ms, border-color 130ms;
 }
 .source-chip:hover {
  background: color-mix(in oklch, var(--color-accent) 8%, transparent);
  border-color: color-mix(in oklch, var(--color-accent) 35%, transparent);
 }
 .source-num {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  margin-top: 1px;
  border-radius: var(--ui-radius-xs);
  background: color-mix(in oklch, var(--color-accent) 15%, transparent);
  color: var(--color-accent);
  font-size: 10px;
  font-weight: 700;
 }
 .source-meta {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
 }
 .source-outlet {
  font-size: 10.5px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-accent);
 }
 .source-headline {
  font-size: 12.5px;
  line-height: 1.35;
  color: color-mix(in oklch, var(--color-base-content) 75%, transparent);
 }

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
  border-radius: var(--ui-radius);
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
  appearance: none;
  flex: 1;
  min-width: 0;
  font-size: 15px;
  color: var(--color-base-content);
  max-height: 135px;
  padding: 9px 0;
  overflow-y: auto;
  scrollbar-width: none;
  -ms-overflow-style: none;
}
.chat-textarea::-webkit-scrollbar {
  display: none;
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
  min-height: 46px;
  background: color-mix(in oklch, var(--color-base-200) 50%, transparent);
  border: 1px solid var(--color-base-300);
  border-radius: var(--ui-radius-sm);
  padding: 0 4px 0 16px;
  position: relative;
  transition: background 180ms ease, border-color 180ms ease, box-shadow 180ms ease;
}
.input-wrap:focus-within {
  background: var(--color-base-100);
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px color-mix(in oklch, var(--color-accent) 15%, transparent);
}

/* ── Input buttons (mode trigger + send) ────────────── */
.input-buttons {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}
.input-buttons.pin-bottom {
  align-self: flex-end;
}

/* ── Mode trigger (dropdown button) ─────────────────── */
.mode-trigger {
  display: flex;
  align-items: center;
  gap: 3px;
  flex-shrink: 0;
  padding: 6px 8px;
  border: none;
  border-radius: var(--ui-radius-sm);
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
  border-radius: var(--ui-radius);
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
  border-radius: var(--ui-radius-sm);
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
.dropdown-item :global(.dropdown-check) {
  color: var(--color-accent);
  flex-shrink: 0;
}
/* ── Send button ─────────────────────────────────────── */
.send-btn {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  margin: 5px;
  border-radius: var(--ui-radius-sm);
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
    transition: padding-bottom 320ms cubic-bezier(0.4, 0, 0.2, 1);
  }
  /* Smart navbar hidden (Mota focus mode): the input reclaims the space.
     Padding stays above the 48px reveal zone so it never blocks the meta row */
  .footer-inner.nav-free {
    padding-bottom: calc(52px + env(safe-area-inset-bottom, 0px));
  }
  :global([data-nav-style="deck"]) .footer-inner {
    padding-bottom: calc(12px + var(--deck-height, 16vw) + 20px + env(safe-area-inset-bottom, 0px));
  }
  :global([data-nav-style="deck"]) .footer-inner.nav-free {
    padding-bottom: calc(52px + env(safe-area-inset-bottom, 0px));
  }
}

 @media (min-width: 768px) {
   .footer-inner { padding: 16px 0; }
 }

  /* ── Sessions screen (full tab, Following-tab pattern) ── */
  .sessions-screen {
   flex: 1;
   min-height: 0;
   overflow-y: auto;
   scrollbar-width: thin;
   padding-bottom: 32px;
  }
  .sessions-inner {
   padding-top: 16px;
  }
  .sessions-header {
   display: flex;
   align-items: center;
   justify-content: space-between;
   gap: 12px;
   padding-bottom: 10px;
   border-bottom: 1px solid color-mix(in oklch, var(--color-base-300) 35%, transparent);
  }
  .sessions-title {
   font-family: var(--font-page-title);
   font-size: 1.15rem; font-weight: 400; letter-spacing: -0.01em;
   color: var(--color-base-content); margin: 0;
  }
  .sessions-state {
   display: flex;
   align-items: center;
   justify-content: center;
   padding: 32px 16px;
  }
  .sessions-state-text {
   font-size: 12.5px;
   color: color-mix(in oklch, var(--color-base-content) 50%, transparent);
   margin: 0;
  }

  /* Skeleton rows — FollowersTab conventions */
  .sk-row {
   display: flex;
   align-items: center;
   gap: 8px;
   padding: 9px 2px 9px 6px;
   border-bottom: 1px solid color-mix(in oklch, var(--color-base-300) 35%, transparent);
  }
  .sk-row:last-child { border-bottom: none; }
  .sk-ml-auto { margin-left: auto; }
  .sk-bar {
   height: 10px;
   flex-shrink: 0;
   border-radius: var(--ui-radius-xs);
   background: linear-gradient(
    90deg,
    color-mix(in oklch, var(--color-base-300) 60%, transparent) 0%,
    color-mix(in oklch, var(--color-base-300) 90%, transparent) 40%,
    color-mix(in oklch, var(--color-base-300) 60%, transparent) 80%
   );
   background-size: 200% 100%;
   animation: sk-shimmer 1.6s ease-in-out infinite;
  }
  @keyframes sk-shimmer {
   0% { background-position: 200% center; }
   100% { background-position: -200% center; }
  }

  /* Rows — .feed-row conventions from the Following tab */
  .sessions-list {
   list-style: none;
   margin: 0;
   padding: 2px 0 8px;
  }
  .session-row {
   display: flex;
   align-items: center;
   gap: 6px;
   padding: 9px 2px 9px 6px;
   border-radius: var(--ui-radius-sm);
   border-bottom: 1px solid color-mix(in oklch, var(--color-base-300) 35%, transparent);
   transition: background 150ms ease;
   user-select: none;
  }
  .session-row:last-child { border-bottom: none; }
  .session-row:hover {
   background: color-mix(in oklch, var(--color-base-content) 4%, transparent);
  }
  .session-row:hover .session-actions { opacity: 1; }
  .session-row--active {
   background: color-mix(in oklch, var(--color-accent) 10%, transparent);
  }
  .session-main {
   flex: 1;
   min-width: 0;
   display: flex;
   align-items: center;
   gap: 10px;
   border: none;
   background: transparent;
   cursor: pointer;
   padding: 0;
   text-align: left;
  }
  .session-title {
   flex: 1;
   min-width: 0;
   font-size: 13px;
   font-weight: 500;
   line-height: 1.35;
   color: var(--color-base-content);
   white-space: nowrap;
   overflow: hidden;
   text-overflow: ellipsis;
  }
  /* .pub-date conventions from PostCard */
  .session-date {
   margin-left: auto;
   flex-shrink: 0;
   font-size: 11px;
   white-space: nowrap;
   color: color-mix(in oklch, var(--color-base-content) 35%, transparent);
  }
  .session-row--active .session-title {
   color: var(--color-accent);
  }
  /* .more-btn conventions from the Following tab rows */
  .session-actions {
   display: flex;
   align-items: center;
   gap: 2px;
   flex-shrink: 0;
   opacity: 0;
   transition: opacity 150ms ease;
  }
  .session-row:focus-within .session-actions {
   opacity: 1;
  }
  @media (hover: none) {
   .session-actions { opacity: 1; }
  }
  .session-action-btn {
   display: flex; align-items: center; justify-content: center;
   width: 24px; height: 24px;
   border: none; border-radius: var(--ui-radius-xs);
   background: transparent; cursor: pointer;
   color: color-mix(in oklch, var(--color-base-content) 55%, transparent);
   transition: background 120ms, color 120ms;
  }
  .session-action-btn:hover {
   color: var(--color-base-content);
   background: color-mix(in oklch, var(--color-base-content) 10%, transparent);
  }
  .session-action-btn--confirm {
   color: var(--color-accent);
  }
  .session-action-btn--confirm:hover {
   color: var(--color-accent);
   background: color-mix(in oklch, var(--color-accent) 10%, transparent);
  }
  .session-action-btn--danger {
   color: var(--color-error);
  }
  .session-action-btn--danger:hover {
   color: var(--color-error);
   background: color-mix(in oklch, var(--color-error) 10%, transparent);
  }
  /* Inputs — FollowersTab dialog input conventions */
  .session-rename-input {
   flex: 1;
   min-width: 0;
   font-size: 13.5px;
   color: var(--color-base-content);
   background: color-mix(in oklch, var(--color-base-200) 50%, transparent);
   border: 1px solid var(--color-base-300);
   border-radius: var(--ui-radius-sm);
   padding: 8px 12px;
   outline: none;
   transition: border-color 130ms, background 130ms, box-shadow 130ms;
  }
  .session-rename-input:focus {
   border-color: var(--color-accent);
   background: var(--color-base-100);
   box-shadow: 0 0 0 3px color-mix(in oklch, var(--color-accent) 15%, transparent);
  }
  .session-confirm {
   flex: 1;
   min-width: 0;
   font-size: 12.5px;
   line-height: 1.35;
   color: var(--color-error);
   padding: 0 4px;
  }

  /* Empty state — FollowersTab .state-empty-wrap pattern */
  .state-empty-wrap {
   display: flex;
   flex-direction: column;
   align-items: center;
   justify-content: center;
   padding: 32px 16px 36px;
   text-align: center;
   gap: 10px;
  }
  .state-empty-wrap :global(.empty-icon) {
   color: color-mix(in oklch, var(--color-base-content) 30%, transparent);
  }
  .state-empty {
   font-size: 14px;
   color: color-mix(in oklch, var(--color-base-content) 45%, transparent);
   margin: 0;
  }
  .empty-cta {
   display: flex; align-items: center; gap: 5px;
   margin-top: 6px;
   padding: 7px 14px;
   border-radius: var(--ui-radius-sm);
   border: 1.5px solid var(--color-accent);
   background: var(--color-accent); color: var(--color-base-100);
   font-weight: 700; font-size: 12.5px;
   cursor: pointer;
   transition: opacity 150ms ease;
  }
  .empty-cta:hover { opacity: 0.85; }

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
