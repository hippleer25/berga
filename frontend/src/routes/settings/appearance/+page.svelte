<script lang="ts">
  import '$lib/components/settings/settings.css';
  import { onMount } from 'svelte';
  import Check from '@lucide/svelte/icons/check';
  import RotateCcw from '@lucide/svelte/icons/rotate-ccw';
  import {
    applyFont,
    getSavedFont,
    convertDaisyuiPluginToDataTheme,
    extractThemeNames,
    applyTheme,
    FONT_LIST,
    FONT_LABELS,
    migrateOldFontPref,
  } from '$lib/utils/appearance';
  import { ripple } from '$lib/actions/ripple';
  import { apiFetch } from '$lib/api';
  import SettingsPicker from '$lib/components/settings/SettingsPicker.svelte';
  import AppearanceSubNav from '$lib/components/settings/AppearanceSubNav.svelte';
  import {
    resetUiPrefs,
    uiAccent,
    getSavedAccent,
    applyAccent,
    uiPageBg,
    getSavedPageBg,
    applyPageBg,
    type PageBg,
  } from '$lib/stores/uiPrefs';
  import {
    MODE_PRESETS,
    applyDesignMode,
    getSavedDesignMode,
    hasCustomFont,
    uiDesignMode,
    type DesignMode,
  } from '$lib/stores/designMode';
  import { t, locale } from 'svelte-i18n';
  import { setLocale, SUPPORTED_LOCALES } from '$lib/i18n';
  import type { SupportedLocale } from '$lib/i18n';
  import { get } from 'svelte/store';
  import { summaryLanguage, type SummaryLanguage } from '$lib/stores/preferences';

  const LOCALE_LABELS: Record<SupportedLocale, string> = {
    pt: 'Português',
    en: 'English',
    es: 'Español',
    de: 'Deutsch',
    fr: 'Français',
  };

  const SUMMARY_LANG_OPTIONS: { value: string; labelKey?: string; label?: string }[] = [
    { value: 'auto', labelKey: 'settings.summaryLangAuto' },
    { value: 'pt', label: LOCALE_LABELS['pt'] },
    { value: 'en', label: LOCALE_LABELS['en'] },
    { value: 'es', label: LOCALE_LABELS['es'] },
    { value: 'de', label: LOCALE_LABELS['de'] },
    { value: 'fr', label: LOCALE_LABELS['fr'] },
  ];

  const PAGE_BG_OPTIONS: { value: PageBg; labelKey: string; color: string | null }[] = [
    { value: 'theme', labelKey: 'settings.bgColorTheme', color: null },
    { value: 'white', labelKey: 'settings.bgColorWhite', color: '#ffffff' },
    { value: 'berga-white', labelKey: 'settings.bgColorBergaWhite', color: '#fbfaf7' },
    { value: 'berga-gray', labelKey: 'settings.bgColorBergaGray', color: '#f8f7f3' },
    { value: 'dark', labelKey: 'settings.bgColorDark', color: '#17181d' },
    { value: 'amoled', labelKey: 'settings.bgColorAmoled', color: '#000000' },
  ];

  const ACCENT_PRESETS: (string | null)[] = [
    null,
    '#F5B942',
    '#4F9CF9',
    '#4CAF7D',
    '#E5533D',
    '#9B6BF2',
    '#F06BA8',
    '#2DD4BF',
  ];

  const FONT_OPTIONS = FONT_LIST.map((f) => ({
    value: f.name,
    label: FONT_LABELS[f.name] ?? f.name,
    category: f.category === 'serif' ? 'serif' : 'sans',
  }));

  let designModeVal = $state<DesignMode>(getSavedDesignMode());
  let accentVal = $state<string | null>(getSavedAccent());
  let customAccent = $state<string>(getSavedAccent() ?? '#F5B942');
  let pageBgVal = $state<PageBg>(getSavedPageBg());
  let uiFont = $state<string>('Inter');
  let uiFontCustom = $state<boolean>(false);
  let summaryLangVal = $state<SummaryLanguage>(summaryLanguage.getLanguage());

  let customCss = $state('');
  let cssSaveStatus = $state<'idle' | 'saving' | 'saved'>('idle');

  onMount(() => {
    migrateOldFontPref();
    const mode = getSavedDesignMode();
    uiFont = hasCustomFont('ui') ? getSavedFont('ui') : MODE_PRESETS[mode].fonts['ui'];
    uiFontCustom = hasCustomFont('ui');
    customCss = localStorage.getItem('custom-css') || '';

    if (customCss.trim()) {
      const converted = convertDaisyuiPluginToDataTheme(customCss);
      const existing = document.getElementById('user-custom-css');
      if (existing) existing.remove();
      const style = document.createElement('style');
      style.id = 'user-custom-css';
      style.textContent = converted;
      document.head.appendChild(style);
    }
  });

  function setDesignMode(mode: DesignMode) {
    designModeVal = mode;
    applyDesignMode(mode, true);
    uiDesignMode.set(mode);
    if (!hasCustomFont('ui')) {
      uiFont = MODE_PRESETS[mode].fonts['ui'];
      uiFontCustom = false;
    }
  }

  function setAccent(hex: string | null) {
    accentVal = hex;
    applyAccent(hex, true);
    uiAccent.set(hex);
    if (hex) customAccent = hex;
  }

  function setPageBg(v: PageBg) {
    pageBgVal = v;
    applyPageBg(v, true);
    uiPageBg.set(v);
  }

  function selectUiFont(fontName: string) {
    applyFont('ui', fontName, true);
    uiFont = fontName;
    uiFontCustom = true;
  }

  /* Font pickers follow the design-mode preset until the user explicitly
     fixes one — flag that distinction so the dropdown never reads as state
     it doesn't actually have. */
  function fontTrigger(name: string, custom: boolean): string {
    const label = FONT_LABELS[name] ?? name;
    return custom ? label : `${label} ${$t('settings.fontAutoSuffix')}`;
  }

  function handleLocaleChange(lang: SupportedLocale) {
    setLocale(lang);
  }

  function handleSummaryLangChange(lang: string) {
    summaryLangVal = lang as SummaryLanguage;
    summaryLanguage.setLanguage(summaryLangVal);
    apiFetch('/api/settings/summary-language', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ language: lang }),
    }).catch(() => {/* non-fatal: cluster worker keeps previous value */});
  }

  function summaryLangLabel(lang: SummaryLanguage): string {
    if (lang === 'auto') return get(t)('settings.summaryLangAuto');
    return LOCALE_LABELS[lang];
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
      if (detectedThemes.length > 0) {
        const active = document.documentElement.getAttribute('data-theme');
        if (!detectedThemes.includes(active ?? '')) {
          applyTheme(detectedThemes[0], true);
        }
      }
    } else {
      localStorage.removeItem('custom-css');
    }
    cssSaveStatus = 'saved';
    setTimeout(() => (cssSaveStatus = 'idle'), 2000);
  }

  function resetInterface() {
    resetUiPrefs();
    applyDesignMode(designModeVal);
    accentVal = null;
    pageBgVal = 'theme';
    if (!hasCustomFont('ui')) uiFont = MODE_PRESETS[designModeVal].fonts['ui'];
  }
</script>

<div class="tab-panel">
  <h2 class="section-title">{$t('settings.appearance')}</h2>

  <AppearanceSubNav />

  <div class="settings-group">
    <div class="group-label">{$t('settings.designLanguage')}</div>
    <div class="group-card">
      <p class="section-desc">{$t('settings.designLanguageDesc')}</p>
      <div class="mode-picker">
        <button
          class="mode-card"
          class:active={designModeVal === 'elegant'}
          use:ripple
          onclick={() => setDesignMode('elegant')}
          aria-pressed={designModeVal === 'elegant'}
        >
          <span class="mode-preview mode-preview--elegant" aria-hidden="true">
            <span class="mode-aa">Aa</span>
            <span class="mode-lines"><i></i><i></i></span>
          </span>
          <span class="mode-copy">
            <span class="mode-name">{$t('settings.designElegant')}</span>
            <span class="mode-desc">{$t('settings.designElegantDesc')}</span>
          </span>
          {#if designModeVal === 'elegant'}<Check size={15} class="mode-check" />{/if}
        </button>

        <button
          class="mode-card"
          class:active={designModeVal === 'modern'}
          use:ripple
          onclick={() => setDesignMode('modern')}
          aria-pressed={designModeVal === 'modern'}
        >
          <span class="mode-preview mode-preview--modern" aria-hidden="true">
            <span class="mode-aa">Aa</span>
            <span class="mode-lines"><i></i><i></i></span>
          </span>
          <span class="mode-copy">
            <span class="mode-name">{$t('settings.designModern')}</span>
            <span class="mode-desc">{$t('settings.designModernDesc')}</span>
          </span>
          {#if designModeVal === 'modern'}<Check size={15} class="mode-check" />{/if}
        </button>
      </div>
    </div>
  </div>

  <div class="settings-group">
    <div class="group-label">{$t('settings.appearanceGeneral')}</div>
    <div class="group-card">
      <div class="setting-row">
        <span class="setting-label">{$t('settings.language')}</span>
        <SettingsPicker
          value={$locale ?? 'en'}
          options={SUPPORTED_LOCALES.map((lang) => ({ value: lang, label: LOCALE_LABELS[lang] }))}
          onSelect={(v) => handleLocaleChange(v as SupportedLocale)}
          trigger={$locale ? LOCALE_LABELS[$locale as SupportedLocale] ?? $locale : ''}
        />
      </div>

      <div class="setting-row">
        <span class="setting-label">{$t('settings.summaryLanguage')}</span>
        <SettingsPicker
          value={summaryLangVal as string}
          options={SUMMARY_LANG_OPTIONS}
          onSelect={handleSummaryLangChange}
          trigger={summaryLangLabel(summaryLangVal)}
        />
      </div>

      <div class="setting-row">
        <span class="setting-label">{$t('settings.bgColor')}</span>
        <div class="navstyle-picker">
          {#each PAGE_BG_OPTIONS as opt (opt.value)}
            <button
              class="navstyle-card"
              class:active={pageBgVal === opt.value}
              use:ripple
              onclick={() => setPageBg(opt.value)}
              aria-pressed={pageBgVal === opt.value}
            >
              <span
                class="navbg-swatch"
                style:background={opt.color}
                class:navbg-swatch--theme={opt.color === null}
              ></span>
              <span class="navstyle-label">{$t(opt.labelKey)}</span>
            </button>
          {/each}
        </div>
      </div>

      <div class="setting-row accent-row">
        <span class="setting-label">{$t('settings.accentColor')}</span>
        <div class="accent-swatches">
          {#each ACCENT_PRESETS as preset}
            <button
              class="swatch"
              class:selected={accentVal === preset}
              style="background: {preset ?? 'var(--color-accent)'}"
              use:ripple
              onclick={() => setAccent(preset)}
              aria-label={preset ?? $t('settings.accentThemeDefault')}
              aria-pressed={accentVal === preset}
            ></button>
          {/each}
          <label
            class="swatch swatch-custom"
            class:selected={accentVal !== null && !ACCENT_PRESETS.includes(accentVal)}
            title={$t('settings.accentCustom')}
          >
            <input
              type="color"
              value={customAccent}
              oninput={(e) => setAccent((e.target as HTMLInputElement).value)}
            />
          </label>
        </div>
      </div>

      <div class="setting-row">
        <span class="setting-label">{$t('settings.uiFont')}</span>
        <SettingsPicker
          value={uiFont}
          options={FONT_OPTIONS}
          onSelect={selectUiFont}
          trigger={fontTrigger(uiFont, uiFontCustom)}
          fontList
        />
      </div>
    </div>
  </div>

  <div class="settings-group">
    <div class="group-label">{$t('settings.customCss')}</div>
    <div class="group-card">
      <p class="section-desc">{$t('settings.customCssDesc')}</p>
      <textarea
        class="css-editor"
        bind:value={customCss}
        placeholder={'/* Your custom CSS here */\n.page-root { ... }'}
        spellcheck="false"
        rows="8"
      ></textarea>
      <div class="css-actions">
        <button class="settings-action-btn accent" use:ripple onclick={saveCustomCss} disabled={cssSaveStatus === 'saving'}>
          {#if cssSaveStatus === 'saving'}<span class="spinner"></span><span>{$t('settings.saving')}</span>
          {:else if cssSaveStatus === 'saved'}<Check size={14} /><span>{$t('settings.saved')}</span>
          {:else}<span>{$t('settings.saveCss')}</span>{/if}
        </button>
        <button class="settings-action-btn" use:ripple onclick={() => { customCss = ''; saveCustomCss(); }} disabled={!customCss.trim()}>
          <span>{$t('settings.resetCss')}</span>
        </button>
      </div>
    </div>
  </div>

  <div class="settings-group">
    <div class="group-label">{$t('settings.resetInterface')}</div>
    <div class="reset-card">
      <button class="settings-action-btn settings-action-btn--block" use:ripple onclick={resetInterface}>
        <RotateCcw size={14} />
        <span>{$t('settings.resetInterface')}</span>
      </button>
    </div>
  </div>
</div>

<style>
  .mode-picker { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; margin-top: 4px; }
  .mode-card {
    position: relative;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 12px;
    text-align: left;
    background: transparent;
    border: var(--ui-border-width) solid var(--ui-border-color);
    border-radius: var(--ui-radius-lg);
    color: var(--color-base-content);
    cursor: pointer;
    transition:
      border-color var(--ui-dur-2) var(--ui-ease),
      background-color var(--ui-dur-2) var(--ui-ease),
      box-shadow var(--ui-dur-2) var(--ui-ease),
      transform var(--ui-dur-1) var(--ui-ease);
  }
  .mode-card:hover {
    border-color: var(--ui-border-strong);
    background: color-mix(in oklch, var(--color-base-content) 4%, transparent);
    transform: translateY(-1px);
    box-shadow: var(--ui-shadow-1);
  }
  .mode-card.active {
    border-color: var(--color-accent);
    background: var(--color-accent-soft);
    box-shadow: var(--ui-shadow-1), inset 0 0 0 1px var(--color-accent-line);
  }
  .mode-preview {
    display: flex;
    align-items: center;
    gap: 10px;
    height: 46px;
    padding: 0 10px;
    border-radius: var(--ui-radius-sm);
    border: 1px solid var(--ui-hairline);
    background: color-mix(in oklch, var(--color-base-200) 70%, transparent);
    overflow: hidden;
  }
  .mode-aa { font-size: 25px; line-height: 1; color: var(--color-base-content); }
  .mode-preview--elegant .mode-aa { font-family: 'Newsreader', serif; letter-spacing: -0.01em; }
  .mode-preview--modern .mode-aa { font-family: 'Figtree', sans-serif; font-weight: 600; letter-spacing: -0.03em; }
  .mode-lines { display: flex; flex-direction: column; gap: 5px; flex: 1; }
  .mode-lines i { display: block; height: 3px; background: color-mix(in oklch, var(--color-base-content) 24%, transparent); }
  .mode-lines i:first-child { width: 82%; }
  .mode-lines i:last-child { width: 58%; }
  .mode-preview--elegant .mode-lines i { border-radius: 0; background: color-mix(in oklch, var(--color-base-content) 34%, transparent); }
  .mode-preview--modern .mode-lines i { border-radius: 999px; background: var(--color-accent); opacity: 0.55; }
  .mode-copy { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
  .mode-name { font-size: 14px; font-weight: 600; letter-spacing: -0.01em; }
  .mode-desc { font-size: 11.5px; line-height: 1.35; color: var(--ui-text-subtle); }
  .mode-card :global(.mode-check) { position: absolute; top: 9px; right: 9px; color: var(--color-accent); }

  .reset-card {
    border: var(--ui-border-width) solid var(--ui-border-color);
    border-radius: var(--ui-radius-lg);
    padding: 10px 4px;
  }
  .settings-action-btn--block { width: 100%; }

  @media (max-width: 420px) {
    .mode-picker { grid-template-columns: 1fr; }
  }
</style>
