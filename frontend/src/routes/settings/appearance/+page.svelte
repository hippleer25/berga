<script lang="ts">
  import { onMount } from 'svelte';
  import Check from '@lucide/svelte/icons/check';
  import ChevronDown from '@lucide/svelte/icons/chevron-down';
  import { t, locale } from 'svelte-i18n';
  import { setLocale, SUPPORTED_LOCALES } from '$lib/i18n';
  import type { SupportedLocale } from '$lib/i18n';
  import {
    applyFont,
    applyTheme,
    convertDaisyuiPluginToDataTheme,
    extractThemeNames,
    FONT_LIST,
    FONT_LABELS,
    getSavedFont,
    migrateOldFontPref,
  } from '$lib/utils/appearance';
  import type { FontCategory, FontName } from '$lib/utils/appearance';
  import { get } from 'svelte/store';
  import { ripple } from '$lib/actions/ripple';
  import Portal from '$lib/components/Portal.svelte';
  import { showCoverImages, coverImagePosition, type CoverPosition } from '$lib/stores/preferences';

  const LOCALE_LABELS: Record<SupportedLocale, string> = {
    pt: 'Português',
    en: 'English',
    es: 'Español',
    de: 'Deutsch',
    fr: 'Français',
  };

  const fontCategories: { key: FontCategory; labelKey: string }[] = [
    { key: 'page-title', labelKey: 'settings.pageTitleFont' },
    { key: 'post-title', labelKey: 'settings.postTitleFont' },
    { key: 'article-body', labelKey: 'settings.articleBodyFont' },
    { key: 'ui', labelKey: 'settings.uiFont' },
  ];

  let activeFonts = $state<Record<FontCategory, string>>({
    'page-title': 'Newsreader',
    'post-title': 'PT Serif',
    'article-body': 'Inter',
    'ui': 'Inter',
  });
  let activeTheme = $state('berga');
  let langDropdownOpen = $state(false);
  let langBtnEl: HTMLButtonElement | null = $state(null);
  let langDropStyle = $state('');
  let openFontDropdown = $state<FontCategory | null>(null);
  let fontBtnEls = $state<Record<string, HTMLButtonElement | null>>({});
  let fontDropStyles = $state<Record<string, string>>({});
  let customCss = $state('');
  let cssSaveStatus = $state<'idle' | 'saving' | 'saved'>('idle');
  let showCover = $state(false);
  let coverPos = $state<CoverPosition>('right');
  let coverDropdownOpen = $state(false);
  let coverBtnEl: HTMLButtonElement | null = $state(null);
  let coverDropStyle = $state('');

  $effect(() => {
    console.log('[settings] $locale changed to:', $locale);
    console.log('[settings] $t("settings.language") =', $t('settings.language'));
  });

  onMount(() => {
    migrateOldFontPref();
    for (const cat of fontCategories.map(c => c.key)) {
      activeFonts[cat] = getSavedFont(cat);
    }
    activeTheme = localStorage.getItem('preferred-theme') || 'berga';
    customCss = localStorage.getItem('custom-css') || '';
    showCover = get(showCoverImages);
    coverPos = get(coverImagePosition);

    if (customCss.trim()) {
      const converted = convertDaisyuiPluginToDataTheme(customCss);
      const existing = document.getElementById('user-custom-css');
      if (existing) existing.remove();
      const style = document.createElement('style');
      style.id = 'user-custom-css';
      style.textContent = converted;
      document.head.appendChild(style);
    }

    function onClickOutside(e: MouseEvent) {
      const target = e.target as Node;
	if (langBtnEl && !langBtnEl.contains(target)) {
			const langDropdown = document.querySelector('.lang-dropdown');
			if (!langDropdown || !langDropdown.contains(target)) {
				langDropdownOpen = false;
			}
		}
      if (openFontDropdown) {
        const btnEl = fontBtnEls[openFontDropdown];
        if (!btnEl || !btnEl.contains(target)) {
          const dropdown = document.querySelector(`.font-dropdown-${openFontDropdown}`);
          if (!dropdown || !dropdown.contains(target)) {
            openFontDropdown = null;
          }
        }
      }
      if (coverDropdownOpen) {
        if (!coverBtnEl || !coverBtnEl.contains(target)) {
          const dropdown = document.querySelector('.cover-dropdown');
          if (!dropdown || !dropdown.contains(target)) {
            coverDropdownOpen = false;
          }
        }
      }
    }
    document.addEventListener('mousedown', onClickOutside);
    return () => document.removeEventListener('mousedown', onClickOutside);
  });

  function toggleShowCover() {
    showCover = !showCover;
    showCoverImages.setEnabled(showCover);
  }

  function toggleCoverDropdown() {
    coverDropdownOpen = !coverDropdownOpen;
    if (coverDropdownOpen && coverBtnEl) {
      const r = coverBtnEl.getBoundingClientRect();
      const maxH = window.innerHeight - r.bottom - 12;
      coverDropStyle = `top:${r.bottom + 6}px;left:${r.left}px;min-width:${r.width}px;max-height:${Math.max(maxH, 120)}px;overflow-y:auto`;
    }
  }

  function selectCoverPos(pos: CoverPosition) {
    coverPos = pos;
    coverImagePosition.setPosition(pos);
    coverDropdownOpen = false;
  }

  function selectFont(category: FontCategory, fontName: string) {
    applyFont(category, fontName, true);
    activeFonts[category] = fontName;
    openFontDropdown = null;
  }

  const BUILTIN_THEME_LABELS: Record<string, string> = {
    'berga': 'Berga Dark Theme',
    'berga-black': 'Berga Light Theme',
  };

  function getThemeLabel(name: string): string {
    if (BUILTIN_THEME_LABELS[name]) return BUILTIN_THEME_LABELS[name];
    return name.charAt(0).toUpperCase() + name.slice(1);
  }

  function toggleTheme() {
    if (activeTheme === 'berga-black') {
      activeTheme = 'berga';
    } else {
      activeTheme = 'berga-black';
    }
    applyTheme(activeTheme, true);
  }

  function handleLocaleChange(lang: SupportedLocale) {
    console.log('[settings] handleLocaleChange:', lang, '| current $locale:', $locale);
    setLocale(lang);
    console.log('[settings] after setLocale, $locale:', $locale);
    langDropdownOpen = false;
  }

  function toggleLangDropdown() {
    langDropdownOpen = !langDropdownOpen;
    if (langDropdownOpen && langBtnEl) {
      const r = langBtnEl.getBoundingClientRect();
      langDropStyle = `top:${r.bottom + 6}px;left:${r.left}px;min-width:${r.width}px`;
    }
  }

  function toggleFontDropdown(category: FontCategory) {
    if (openFontDropdown === category) {
      openFontDropdown = null;
      return;
    }
    openFontDropdown = category;
    const btnEl = fontBtnEls[category];
    if (btnEl) {
      const r = btnEl.getBoundingClientRect();
      const maxH = window.innerHeight - r.bottom - 12;
      fontDropStyles[category] = `top:${r.bottom + 6}px;left:${r.left}px;min-width:${r.width}px;max-height:${Math.max(maxH, 120)}px;overflow-y:auto`;
    }
  }

  function saveCustomCss() {
    cssSaveStatus = 'saving';
    const el = document.getElementById('user-custom-css');
    if (el) el.remove();
    if (customCss.trim()) {
      const converted = convertDaisyuiPluginToDataTheme(customCss);
      const style = document.createElement('style');
      style.id = 'user-custom-css';
      style.textContent = converted;
      document.head.appendChild(style);
      localStorage.setItem('custom-css', customCss);

      const detectedThemes = extractThemeNames(customCss);
      if (detectedThemes.length > 0 && !detectedThemes.includes(activeTheme)) {
        activeTheme = detectedThemes[0];
        applyTheme(activeTheme, true);
      }
    } else {
      localStorage.removeItem('custom-css');
    }
    cssSaveStatus = 'saved';
    setTimeout(() => (cssSaveStatus = 'idle'), 2000);
  }
</script>

{#if langDropdownOpen}
  <Portal>
    <div class="picker-backdrop" onclick={() => langDropdownOpen = false} aria-hidden="true"></div>
    <div class="picker-dropdown lang-dropdown" style={langDropStyle} role="listbox">
      {#each SUPPORTED_LOCALES as lang}
        <button class="picker-item" class:picker-selected={$locale === lang} role="option" aria-selected={$locale === lang} onclick={() => handleLocaleChange(lang)}>
          <span class="picker-item-text">{LOCALE_LABELS[lang]}</span>
          {#if $locale === lang}<Check size={12} class="picker-check" />{/if}
        </button>
      {/each}
    </div>
  </Portal>
{/if}

{#if openFontDropdown}
  {@const currentCat = openFontDropdown}
  <Portal>
    <div class="picker-backdrop" onclick={() => openFontDropdown = null} aria-hidden="true"></div>
    <div class="picker-dropdown font-dropdown-{currentCat}" style={fontDropStyles[currentCat]} role="listbox">
      {#each FONT_LIST as font}
        <button
          class="picker-item"
          class:picker-selected={activeFonts[currentCat] === font.name}
          role="option"
          aria-selected={activeFonts[currentCat] === font.name}
          onclick={() => selectFont(currentCat, font.name)}
        >
          <span class="picker-item-text" style="font-family: '{font.name}', {font.category};">
            {FONT_LABELS[font.name] ?? font.name}
          </span>
          <span class="font-cat-label">{font.category === 'serif' ? $t('settings.serif') : $t('settings.sans')}</span>
          {#if activeFonts[currentCat] === font.name}<Check size={12} class="picker-check" />{/if}
        </button>
      {/each}
    </div>
  </Portal>
{/if}

{#if coverDropdownOpen}
  <Portal>
    <div class="picker-backdrop" onclick={() => coverDropdownOpen = false} aria-hidden="true"></div>
    <div class="picker-dropdown cover-dropdown" style={coverDropStyle} role="listbox">
      <button
        class="picker-item"
        class:picker-selected={coverPos === 'right'}
        role="option"
        aria-selected={coverPos === 'right'}
        onclick={() => selectCoverPos('right')}
      >
        <span class="picker-item-text">{$t('settings.coverImagePositionRight')}</span>
        {#if coverPos === 'right'}<Check size={12} class="picker-check" />{/if}
      </button>
      <button
        class="picker-item"
        class:picker-selected={coverPos === 'bottom'}
        role="option"
        aria-selected={coverPos === 'bottom'}
        onclick={() => selectCoverPos('bottom')}
      >
        <span class="picker-item-text">{$t('settings.coverImagePositionBottom')}</span>
        {#if coverPos === 'bottom'}<Check size={12} class="picker-check" />{/if}
      </button>
    </div>
  </Portal>
{/if}

<div class="tab-panel">
  <h2 class="section-title">{$t('settings.appearance')}</h2>

  <div class="setting-row">
    <span class="setting-label">{$t('settings.language')}</span>
    <div class="picker-wrap">
      <button bind:this={langBtnEl} class="setting-btn" use:ripple onclick={toggleLangDropdown}>
        <span>{$locale ? LOCALE_LABELS[$locale as SupportedLocale] ?? $locale : ''}</span>
        <span class="chevron-icon" class:rotated={langDropdownOpen}>
          <ChevronDown size={14} />
        </span>
      </button>
    </div>
  </div>

  <div class="setting-row">
    <div class="setting-text">
      <span class="setting-label">{getThemeLabel(activeTheme)}</span>
    </div>
    <button class="pill-toggle" class:on={activeTheme === 'berga-black'} use:ripple onclick={toggleTheme}>
      <div class="pill-thumb"></div>
    </button>
  </div>

  <div class="setting-row">
    <div class="setting-text">
      <span class="setting-label">{$t('settings.showCoverImages')}</span>
    </div>
    <button class="pill-toggle" class:on={showCover} use:ripple onclick={toggleShowCover}>
      <div class="pill-thumb"></div>
    </button>
  </div>

  {#if showCover}
    <div class="setting-row">
      <span class="setting-label">{$t('settings.coverImagePosition')}</span>
      <div class="picker-wrap">
        <button
          bind:this={coverBtnEl}
          class="setting-btn"
          use:ripple
          onclick={toggleCoverDropdown}
        >
          <span>
            {coverPos === 'right' ? $t('settings.coverImagePositionRight') : $t('settings.coverImagePositionBottom')}
          </span>
          <span class="chevron-icon" class:rotated={coverDropdownOpen}>
            <ChevronDown size={14} />
          </span>
        </button>
      </div>
    </div>
  {/if}

  {#each fontCategories as cat}
    <div class="setting-row">
      <span class="setting-label">{$t(cat.labelKey)}</span>
      <div class="picker-wrap">
        <button
          bind:this={fontBtnEls[cat.key]}
          class="setting-btn"
          use:ripple
          onclick={() => toggleFontDropdown(cat.key)}
        >
          <span style="font-family: '{activeFonts[cat.key]}', {FONT_LIST.find(f => f.name === activeFonts[cat.key])?.category ?? 'sans-serif'};">
            {FONT_LABELS[activeFonts[cat.key]] ?? activeFonts[cat.key]}
          </span>
          <span class="chevron-icon" class:rotated={openFontDropdown === cat.key}>
            <ChevronDown size={14} />
          </span>
        </button>
      </div>
    </div>
  {/each}

  <div class="setting-block">
    <span class="setting-label">{$t('settings.customCss')}</span>
    <p class="section-desc">{$t('settings.customCssDesc')}</p>
    <textarea
      class="css-editor"
      bind:value={customCss}
      placeholder={'/* Your custom CSS here */\n.page-root { ... }'}
      spellcheck="false"
      rows="8"
    ></textarea>
    <div class="css-actions">
      <button class="action-btn accent" use:ripple onclick={saveCustomCss} disabled={cssSaveStatus === 'saving'}>
        {#if cssSaveStatus === 'saving'}<span class="spinner"></span><span>{$t('settings.saving')}</span>
        {:else if cssSaveStatus === 'saved'}<Check size={14} /><span>{$t('settings.saved')}</span>
        {:else}<span>{$t('settings.saveCss')}</span>{/if}
      </button>
      <button class="action-btn" use:ripple onclick={() => { customCss = ''; saveCustomCss(); }} disabled={!customCss.trim()}>
        <span>{$t('settings.resetCss')}</span>
      </button>
    </div>
  </div>
</div>

<style>
  .tab-panel { display: flex; flex-direction: column; gap: 16px; padding-top: 12px; }
  .section-title { font-size: 16px; font-weight: 700; color: var(--color-base-content); margin: 0; }
  .section-desc { font-size: 13px; line-height: 1.45; color: color-mix(in oklch, var(--color-base-content) 50%, transparent); margin: -8px 0 0; }

  .setting-row { display: flex; align-items: center; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid var(--color-base-300); }
  .setting-block { display: flex; flex-direction: column; gap: 12px; padding: 12px 0; border-bottom: 1px solid var(--color-base-300); }
  .setting-label { font-size: 14px; font-weight: 500; color: var(--color-base-content); }
  .setting-text { display: flex; flex-direction: column; gap: 2px; }

  .setting-btn {
    display: flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 10px;
    border: 1px solid var(--color-base-300); background: transparent;
    font-size: 13px; font-weight: 500; position: relative; overflow: hidden;
    color: color-mix(in oklch, var(--color-base-content) 70%, transparent);
    cursor: pointer; transition: all 130ms; white-space: nowrap;
  }
  .setting-btn:hover { background: var(--color-base-200); color: var(--color-base-content); }
  .setting-btn:active { transform: scale(0.97); }
  .chevron-icon { display: flex; align-items: center; transition: transform 180ms ease; }
  .chevron-icon.rotated { transform: rotate(180deg); }

  .picker-wrap { position: relative; flex-shrink: 0; }
  .picker-backdrop { position: fixed; inset: 0; z-index: 9998; pointer-events: auto; }
  .picker-dropdown {
    z-index: 9999; background: var(--color-base-100); border: 1px solid var(--color-base-300);
    border-radius: 10px; box-shadow: 0 8px 24px color-mix(in oklch, black 20%, transparent);
    padding: 4px; min-width: 180px; overflow-y: auto;
    animation: picker-pop 150ms cubic-bezier(0.22, 1, 0.36, 1) both;
    position: fixed;
  }
  .picker-dropdown, .picker-dropdown * { pointer-events: auto; }
  .picker-item {
    display: flex; align-items: center; justify-content: space-between; width: 100%;
    padding: 8px 10px; border: none; background: transparent; cursor: pointer;
    font-size: 13px; font-weight: 500; color: var(--color-base-content);
    border-radius: 6px; transition: background 110ms; text-align: left; gap: 8px;
  }
  .picker-item:hover { background: var(--color-base-200); }
  .picker-item:active { transform: scale(0.97); }
  .picker-item.picker-selected { background: color-mix(in oklch, var(--color-accent) 10%, transparent); color: var(--color-accent); }
  .picker-item-text { flex: 1; }
  .font-cat-label {
    font-size: 10px; color: color-mix(in oklch, var(--color-base-content) 40%, transparent);
    text-transform: capitalize; flex-shrink: 0; font-family: var(--font-ui);
  }
  :global(.picker-check) { flex-shrink: 0; color: var(--color-accent); }
  @keyframes picker-pop { from { opacity: 0; transform: translateY(-6px) scale(0.97); } to { opacity: 1; transform: translateY(0) scale(1); } }

  .pill-toggle {
    width: 44px; height: 24px; border-radius: 999px;
    background: color-mix(in oklch, var(--color-base-content) 20%, transparent);
    position: relative; border: none; cursor: pointer; transition: background 200ms;
    flex-shrink: 0; overflow: hidden;
  }
  .pill-toggle.on { background: var(--color-accent); }
  .pill-toggle:active .pill-thumb { transform: scale(0.9); }
  .pill-thumb {
    position: absolute; top: 3px; left: 3px; width: 18px; height: 18px; border-radius: 50%;
    background: var(--color-base-100); box-shadow: 0 1px 4px rgba(0,0,0,.2);
    transition: transform 200ms cubic-bezier(0.22, 1, 0.36, 1);
  }
  .pill-toggle.on .pill-thumb { transform: translateX(20px); }



  .css-editor {
    width: 100%; padding: 12px; border-radius: 10px;
    border: 1px solid var(--color-base-300); background: var(--color-base-200);
    color: var(--color-base-content); font-family: 'Fira Code', 'Cascadia Code', monospace;
    font-size: 13px; line-height: 1.5; resize: vertical; outline: none;
    transition: border-color 180ms, box-shadow 180ms;
  }
  .css-editor:focus { border-color: var(--color-accent); box-shadow: 0 0 0 3px color-mix(in oklch, var(--color-accent) 15%, transparent); }
  .css-editor::placeholder { color: color-mix(in oklch, var(--color-base-content) 30%, transparent); }

  .css-actions { display: flex; gap: 8px; }

  .action-btn {
    display: inline-flex; align-items: center; justify-content: center; gap: 6px;
    padding: 10px 16px; border-radius: 10px; border: 1px solid var(--color-base-300);
    background: transparent; color: var(--color-base-content); cursor: pointer;
    font-size: 13px; font-weight: 600; transition: all 130ms ease;
    position: relative; overflow: hidden;
  }
  .action-btn:hover { background: var(--color-base-200); }
  .action-btn:active { transform: scale(0.97); }
  .action-btn.accent { border-color: var(--color-accent); color: var(--color-accent); }
  .action-btn.accent:hover { background: color-mix(in oklch, var(--color-accent) 10%, transparent); }
  .action-btn:disabled { opacity: 0.6; cursor: not-allowed; }

  .spinner {
    width: 16px; height: 16px;
    border: 2px solid color-mix(in oklch, var(--color-base-content) 20%, transparent);
    border-top-color: var(--color-base-content); border-radius: 50%;
    animation: spin 0.6s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
