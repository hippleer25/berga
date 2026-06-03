<script lang="ts">
 import { onMount, tick } from 'svelte';
 import { goto } from '$app/navigation';
 import Send from '@lucide/svelte/icons/send';
 import RotateCcw from '@lucide/svelte/icons/rotate-ccw';
 import Sparkles from '@lucide/svelte/icons/sparkles';
 import ChevronDown from '@lucide/svelte/icons/chevron-down';
 import Settings from '@lucide/svelte/icons/settings';
 import BookOpen from '@lucide/svelte/icons/book-open';
 import Globe from '@lucide/svelte/icons/globe';
 import Database from '@lucide/svelte/icons/database';
 import Blend from '@lucide/svelte/icons/blend';
 import Newspaper from '@lucide/svelte/icons/newspaper';
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

 let messages = $state<Message[]>([]);
 let input = $state('');
 let loading = $state(false);
 let streaming = $state(false);
 let error = $state('');
 let idCounter = 0;
 let waitingPhase = $state<WaitingPhase>(null);

 let deepReading = $state(false);
 let sourceMode = $state<SourceMode>('local');

 let textareaRef: HTMLTextAreaElement;
 let scrollContainer: HTMLElement;
 let messagesEnd: HTMLDivElement;

 let showScrollBtn = $state(false);

 let hasStarted = $derived(messages.some(m => m.role === 'user'));

	let waitingMessages = $derived.by(() => ({
		thinking: get(t)('motatab.waitThinking'),
		searching: get(t)('motatab.waitSearching'),
		reading: get(t)('motatab.waitReading'),
		synthesizing: get(t)('motatab.waitSynthesizing'),
	}));

	let sourceLabels = $derived.by(() => ({
		local: get(t)('motatab.sourceLocal'),
		online: get(t)('motatab.sourceOnline'),
		mixed: get(t)('motatab.sourceMixed'),
	} as Record<SourceMode, string>));

 let suggestions = $derived([
  { key: 'suggestSummarize', Icon: Newspaper },
  { key: 'suggestResearch', Icon: Globe },
  { key: 'suggestTrending', Icon: Blend },
  { key: 'suggestDeepRead', Icon: BookOpen },
 ]);

 onMount(() => {});

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
  if (textareaRef) textareaRef.style.height = 'auto';

  messages = [...messages, { role: 'user', content: text, id: idCounter++ }];
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
 }

 function applySuggestion(text: string) {
  input = text;
  textareaRef?.focus();
 }
</script>


<div class="page-root mota-page">

 <!-- ── Top Header + Welcome + Filter (in scrollable flow) ─────────── -->
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

  <div class="suggestion-cards">
   {#each suggestions as s (s.key)}
    <button class="suggestion-card" onclick={() => applySuggestion($t(`motatab.${s.key}`))}>
     <s.Icon size={15} strokeWidth={1.8} />
     <span>{$t(`motatab.${s.key}`)}</span>
    </button>
   {/each}
  </div>

  <p class="welcome-hint">{$t('motatab.welcomeHint')}</p>

  <!-- ── Filter Bar ──────────────────────────────────────────────── -->
  <div class="filter-bar">
   <div class="mode-pill" role="group" aria-label="Source mode">
    {#each ([
     { value: 'local', label: $t('motatab.sourceLocal'), Icon: Database },
     { value: 'online', label: $t('motatab.sourceOnline'), Icon: Globe },
     { value: 'mixed', label: $t('motatab.sourceMixed'), Icon: Blend },
    ] as const) as opt (opt.value)}
     <button
      class="mode-btn"
      class:active={sourceMode === opt.value}
      onclick={() => sourceMode = opt.value}
      aria-pressed={sourceMode === opt.value}
     >
      <opt.Icon size={13} />
      <span>{opt.label}</span>
     </button>
    {/each}
   </div>

   <button
    class="filter-chip"
    class:chip-active={deepReading}
    onclick={() => deepReading = !deepReading}
    aria-pressed={deepReading}
   >
    <BookOpen size={13} />
    <span>{$t('motatab.deepReading')}</span>
   </button>
  </div>

  <div class="feed-wrap"></div>
 </div>
 {:else}
 <div class="main-content">
  <div class="filter-bar filter-bar--compact">
   <div class="mode-pill" role="group" aria-label="Source mode">
    {#each ([
     { value: 'local', label: $t('motatab.sourceLocal'), Icon: Database },
     { value: 'online', label: $t('motatab.sourceOnline'), Icon: Globe },
     { value: 'mixed', label: $t('motatab.sourceMixed'), Icon: Blend },
    ] as const) as opt (opt.value)}
     <button
      class="mode-btn"
      class:active={sourceMode === opt.value}
      onclick={() => sourceMode = opt.value}
      aria-pressed={sourceMode === opt.value}
     >
      <opt.Icon size={13} />
      <span>{opt.label}</span>
     </button>
    {/each}
   </div>

   <button
    class="filter-chip"
    class:chip-active={deepReading}
    onclick={() => deepReading = !deepReading}
    aria-pressed={deepReading}
   >
    <BookOpen size={13} />
    <span>{$t('motatab.deepReading')}</span>
   </button>
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

 /* ── Suggestion Cards ──────────────────────────────── */
 .suggestion-cards {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
 }
 .suggestion-card {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 9px 14px;
  border-radius: 10px;
  border: 1px solid var(--color-base-300);
  background: transparent;
  font-size: 13px;
  font-weight: 500;
  color: color-mix(in oklch, var(--color-base-content) 70%, transparent);
  cursor: pointer;
  transition: background 140ms, color 140ms, border-color 140ms;
  white-space: nowrap;
 }
 .suggestion-card:hover {
  background: var(--color-base-200);
  color: var(--color-base-content);
  border-color: color-mix(in oklch, var(--color-base-content) 15%, transparent);
 }
 .suggestion-card:active {
  transform: scale(0.97);
 }

 .welcome-hint {
  font-size: 13px;
  color: color-mix(in oklch, var(--color-base-content) 35%, transparent);
  margin: 0 0 20px;
  line-height: 1.4;
 }

 /* ── Filter Bar (matches HomeTab) ──────────────────── */
 .filter-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-top: 8px;
  padding-bottom: 12px;
  background: var(--color-base-100);
  overflow-x: auto;
  scrollbar-width: none;
  touch-action: pan-y pan-x;
 }
 .filter-bar::-webkit-scrollbar { display: none; }

 .filter-bar--compact {
  padding-top: 10px;
  padding-bottom: 10px;
 }

 .mode-pill {
  display: flex;
  background: var(--color-base-200);
  border-radius: 13px;
  padding: 3px;
  gap: 2px;
  flex-shrink: 0;
 }
 .mode-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 6px 14px;
  border-radius: 10px;
  border: none;
  background: transparent;
  font-size: 13px;
  font-weight: 500;
  color: color-mix(in oklch, var(--color-base-content) 65%, transparent);
  cursor: pointer;
  transition: background 150ms ease, color 150ms ease, font-weight 0ms;
  white-space: nowrap;
 }
 .mode-btn.active {
  background: var(--color-base-100);
  color: var(--color-base-content);
  font-weight: 700;
  box-shadow: 0 1px 3px color-mix(in oklch, black 10%, transparent);
 }

 .filter-chip {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 6px 12px;
  border-radius: 10px;
  border: 1px solid var(--color-base-300);
  background: transparent;
  font-size: 13px;
  font-weight: 500;
  color: color-mix(in oklch, var(--color-base-content) 70%, transparent);
  cursor: pointer;
  transition: background 130ms, color 130ms, border-color 130ms;
  white-space: nowrap;
  flex-shrink: 0;
 }
 .filter-chip:hover {
  background: var(--color-base-200);
  color: var(--color-base-content);
 }
 .filter-chip.chip-active {
  background: color-mix(in oklch, var(--color-accent) 12%, transparent);
  border-color: color-mix(in oklch, var(--color-accent) 60%, transparent);
  color: var(--color-accent);
  font-weight: 600;
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

 /* ── Input wrap ──────────────────────────────────────── */
 .input-wrap {
  display: flex; align-items: flex-end; gap: 10px;
  background: color-mix(in oklch, var(--color-base-200) 50%, transparent);
  border: 1px solid var(--color-base-300);
  border-radius: 10px;
  padding: 0 12px;
  transition: background 180ms ease, border-color 180ms ease, box-shadow 180ms ease;
 }
 .input-wrap:focus-within {
  background: var(--color-base-100);
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px color-mix(in oklch, var(--color-accent) 15%, transparent);
 }

 /* ── Send button ─────────────────────────────────────── */
 .send-btn {
  flex-shrink: 0; width: 36px; height: 36px; border-radius: 10px;
  border: none; display: flex; align-items: center; justify-content: center;
  transition: background 160ms, box-shadow 160ms, transform 100ms; cursor: pointer;
 }
 .send-btn.ready { background: var(--color-accent); color: var(--color-base-100); }
 .send-btn.ready:hover { box-shadow: 0 4px 12px color-mix(in oklch, var(--color-accent) 35%, transparent); transform: translateY(-1px); }
 .send-btn.ready:active { transform: scale(0.95); }
 .send-btn.idle { background: color-mix(in oklch, var(--color-base-300) 90%, transparent); color: color-mix(in oklch, var(--color-base-content) 40%, transparent); cursor: not-allowed; }

 /* ── Footer ──────────────────────────────────────────── */
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
  .input-wrap { padding: 0 14px; border-radius: 14px; }
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
