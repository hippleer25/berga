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
    applyFontSize,
    applyFontWeight,
    allowedFontWeights,
    snapFontWeight,
    applyLetterSpacing,
    applyLineHeight,
    applyArticleMaxWidth,
    applyArticleTitleMaxWidth,
    applyArticleImageWidth,
    applyDescLines,
    applyTitleBold,
    applyTitleSize,
    applyDescSize,
    getSavedTitleSize,
    getSavedDescSize,
    applyDensity,
    getSavedDensity,
    ARTICLE_TYPOGRAPHY,
    POSTCARD_PREFS,
    type Density,
  } from '$lib/utils/appearance';
  import type { FontCategory, FontName } from '$lib/utils/appearance';
  import { get } from 'svelte/store';
  import { ripple } from '$lib/actions/ripple';
  import Portal from '$lib/components/Portal.svelte';
  import {
    uiRadiusSurface,
    uiRadiusControl,
    uiNavStyle,
    uiGlass,
    uiAccent,
    uiBorderOn,
    uiBorderWidth,
    uiBorderColor,
    uiNavIndicator,
    uiChipIcons,
    uiDeckWidthPct,
    uiDeckHeightVw,
    uiDeckRadiusPct,
    uiWelcomeBold,
    applyRadiusSurfaces,
    applyRadiusControls,
    applyNavStyle,
    applyGlass,
    applyAccent,
    applyBorder,
    applyNavIndicator,
    applyChipIcons,
    applyDeckWidthPct,
    applyDeckHeightVw,
    applyDeckRadiusPct,
    applyWelcomeBold,
    resetUiPrefs,
    getSavedRadiusSurface,
    getSavedRadiusControl,
    getSavedNavStyle,
    getSavedGlass,
    getSavedAccent,
    getSavedBorderOn,
    getSavedBorderWidth,
    getSavedBorderColor,
    getSavedNavIndicator,
    getSavedChipIcons,
    getSavedDeckWidthPct,
    getSavedDeckHeightVw,
    getSavedDeckRadiusPct,
    getSavedWelcomeBold,
    RADIUS_SURFACE_MIN,
    RADIUS_SURFACE_MAX,
    RADIUS_SURFACE_DEFAULT,
    RADIUS_CONTROL_MIN,
    RADIUS_CONTROL_MAX,
    RADIUS_CONTROL_DEFAULT,
    DECK_WIDTH_PCT_MIN,
    DECK_WIDTH_PCT_MAX,
    DECK_WIDTH_PCT_DEFAULT,
    DECK_HEIGHT_VW_MIN,
    DECK_HEIGHT_VW_MAX,
    DECK_HEIGHT_VW_DEFAULT,
    DECK_RADIUS_PCT_MIN,
    DECK_RADIUS_PCT_MAX,
    DECK_RADIUS_PCT_DEFAULT,
    BORDER_WIDTH_MIN,
    BORDER_WIDTH_MAX,
    type NavStyle,
    type NavIndicator,
  } from '$lib/stores/uiPrefs';
  import { tabOrder, setTabOrder, TAB_DEFS, type TabId } from '$lib/config/tabs';
  import { ChevronUp, RotateCcw } from '@lucide/svelte';
  import {
    showCoverImages,
    coverImagePosition,
    titleTextAlign,
    bodyTextAlign,
    articleFontSize,
    articleFontWeight,
    articleLetterSpacing,
    articleLineHeight,
    articleMaxWidth,
    articleTitleMaxWidth,
    articleImageWidth,
    postcardDescLines,
    postcardTitleBold,
    feedDensity,
    type CoverPosition,
    type TextAlign,
  } from '$lib/stores/preferences';

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
  let titleDropdownOpen = $state(false);
  let titleBtnEl: HTMLButtonElement | null = $state(null);
  let titleDropStyle = $state('');
  let titlePos = $state<TextAlign>('left');
  let bodyDropdownOpen = $state(false);
  let bodyBtnEl: HTMLButtonElement | null = $state(null);
  let bodyDropStyle = $state('');
  let bodyPos = $state<TextAlign>('left');

  // ── Border state ──
  const BORDER_COLOR_PRESETS: (string | null)[] = [
    null,
    '#F5B942',
    '#4F9CF9',
    '#4CAF7D',
    '#E5533D',
    '#9B6BF2',
    '#2DD4BF',
  ];

  // ── Interface state ──
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
  let radiusSurfaceVal = $state<number>(getSavedRadiusSurface());
  let radiusControlVal = $state<number>(getSavedRadiusControl());
  let navStyleVal = $state<NavStyle>(getSavedNavStyle());
  let glassVal = $state<boolean>(getSavedGlass());
  let accentVal = $state<string | null>(getSavedAccent());
  let customAccent = $state<string>(getSavedAccent() ?? '#F5B942');
  let borderOn = $state<boolean>(getSavedBorderOn());
  let borderWidth = $state<number>(getSavedBorderWidth());
  let borderColor = $state<string | null>(getSavedBorderColor());
  let customBorderColor = $state<string>(getSavedBorderColor() ?? '#8f8f96');
  let navIndicatorVal = $state<NavIndicator>(getSavedNavIndicator());
  let chipIcons = $state<boolean>(getSavedChipIcons());
  let deckWidth = $state<number>(getSavedDeckWidthPct());
  let deckHeight = $state<number>(getSavedDeckHeightVw());
  let deckRadius = $state<number>(getSavedDeckRadiusPct());
  let welcomeBold = $state<boolean>(getSavedWelcomeBold());

  // ── Typography state ──
  let fontSize = $state<number>(ARTICLE_TYPOGRAPHY.fontSize.default);
  let fontWeight = $state<number>(ARTICLE_TYPOGRAPHY.fontWeight.default);
  let letterSpacing = $state<number>(ARTICLE_TYPOGRAPHY.letterSpacing.default);
  let lineHeight = $state<number>(ARTICLE_TYPOGRAPHY.lineHeight.default);

  // ── Reading view state ──
  let articleMaxW = $state<number>(ARTICLE_TYPOGRAPHY.maxWidth.default);
  let articleTitleMaxW = $state<number>(ARTICLE_TYPOGRAPHY.titleMaxWidth.default);
  let imageWidth = $state<number>(ARTICLE_TYPOGRAPHY.imageWidth.default);

  // ── Post-card state ──
  let descLines = $state<number>(POSTCARD_PREFS.descLines.default);
  let titleBold = $state<boolean>(POSTCARD_PREFS.titleBold.default);
  let titleSizeVal = $state<number>(getSavedTitleSize());
  let descSizeVal = $state<number>(getSavedDescSize());
  let density = $state<Density>('comfortable');

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
    titlePos = get(titleTextAlign);
    bodyPos = get(bodyTextAlign);

    // Load new prefs
    fontSize = get(articleFontSize);
    fontWeight = snapFontWeight(activeFonts['article-body'], get(articleFontWeight));
    letterSpacing = get(articleLetterSpacing);
    lineHeight = get(articleLineHeight);
    articleMaxW = get(articleMaxWidth);
    articleTitleMaxW = get(articleTitleMaxWidth);
    imageWidth = get(articleImageWidth);
    descLines = get(postcardDescLines);
    titleBold = get(postcardTitleBold);
    density = getSavedDensity();

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
      if (titleDropdownOpen) {
        if (!titleBtnEl || !titleBtnEl.contains(target)) {
          const dropdown = document.querySelector('.title-align-dropdown');
          if (!dropdown || !dropdown.contains(target)) {
            titleDropdownOpen = false;
          }
        }
      }
      if (bodyDropdownOpen) {
        if (!bodyBtnEl || !bodyBtnEl.contains(target)) {
          const dropdown = document.querySelector('.body-align-dropdown');
          if (!dropdown || !dropdown.contains(target)) {
            bodyDropdownOpen = false;
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

  function toggleTitleDropdown() {
    titleDropdownOpen = !titleDropdownOpen;
    if (titleDropdownOpen && titleBtnEl) {
      const r = titleBtnEl.getBoundingClientRect();
      const maxH = window.innerHeight - r.bottom - 12;
      titleDropStyle = `top:${r.bottom + 6}px;left:${r.left}px;min-width:${r.width}px;max-height:${Math.max(maxH, 120)}px;overflow-y:auto`;
    }
  }

  function selectTitleAlign(pos: TextAlign) {
    titlePos = pos;
    titleTextAlign.setPosition(pos);
    titleDropdownOpen = false;
  }

  function toggleBodyDropdown() {
    bodyDropdownOpen = !bodyDropdownOpen;
    if (bodyDropdownOpen && bodyBtnEl) {
      const r = bodyBtnEl.getBoundingClientRect();
      const maxH = window.innerHeight - r.bottom - 12;
      bodyDropStyle = `top:${r.bottom + 6}px;left:${r.left}px;min-width:${r.width}px;max-height:${Math.max(maxH, 120)}px;overflow-y:auto`;
    }
  }

  function selectBodyAlign(pos: TextAlign) {
    bodyPos = pos;
    bodyTextAlign.setPosition(pos);
    bodyDropdownOpen = false;
  }

  // ── Typography setters ──
  function setFontSize(v: number) {
    fontSize = v; applyFontSize(v, true); articleFontSize.setValue(v);
  }
  function setFontWeight(v: number) {
    const snapped = snapFontWeight(activeFonts['article-body'], v);
    fontWeight = snapped; applyFontWeight(snapped, true); articleFontWeight.setValue(snapped);
  }
  function setLetterSpacing(v: number) {
    letterSpacing = v; applyLetterSpacing(v, true); articleLetterSpacing.setValue(v);
  }
  function setLineHeight(v: number) {
    lineHeight = v; applyLineHeight(v, true); articleLineHeight.setValue(v);
  }

  // ── Reading-view setters ──
  function setArticleMaxWidth(v: number) {
    articleMaxW = v; applyArticleMaxWidth(v, true); articleMaxWidth.setValue(v);
  }
  function setArticleTitleMaxWidth(v: number) {
    articleTitleMaxW = v; applyArticleTitleMaxWidth(v, true); articleTitleMaxWidth.setValue(v);
  }
  function setImageWidth(v: number) {
    imageWidth = v; applyArticleImageWidth(v, true); articleImageWidth.setValue(v);
  }

  // ── Post-card setters ──
  function setDescLines(v: number) {
    descLines = v; applyDescLines(v, true); postcardDescLines.setValue(v);
  }
  function toggleTitleBold() {
    titleBold = !titleBold; applyTitleBold(titleBold, true); postcardTitleBold.setValue(titleBold);
  }
  function setTitleSize(v: number) {
    titleSizeVal = v; applyTitleSize(v, true);
  }
  function setDescSize(v: number) {
    descSizeVal = v; applyDescSize(v, true);
  }
  function setDensity(d: Density) {
    density = d; applyDensity(d, true); feedDensity.setValue(d);
  }

  // ── Interface setters ──
  function setRadiusSurface(v: number) {
    radiusSurfaceVal = v; applyRadiusSurfaces(v, true); uiRadiusSurface.set(v);
  }
  function setRadiusControl(v: number) {
    radiusControlVal = v; applyRadiusControls(v, true); uiRadiusControl.set(v);
  }
  function setNavStyle(s: NavStyle) {
    navStyleVal = s; applyNavStyle(s, true); uiNavStyle.set(s);
  }
  function toggleGlass() {
    glassVal = !glassVal; applyGlass(glassVal, true); uiGlass.set(glassVal);
  }
  function setAccent(hex: string | null) {
    accentVal = hex; applyAccent(hex, true); uiAccent.set(hex);
    if (hex) customAccent = hex;
  }
  function setBorderOn(v: boolean) {
    borderOn = v; applyBorder(v, borderWidth, borderColor, true); uiBorderOn.set(v);
  }
  function setBorderWidth(v: number) {
    borderWidth = v; applyBorder(borderOn, v, borderColor, true); uiBorderWidth.set(v);
  }
  function setBorderColor(hex: string | null) {
    borderColor = hex; applyBorder(borderOn, borderWidth, hex, true); uiBorderColor.set(hex);
    if (hex) customBorderColor = hex;
  }
  function setNavIndicator(s: NavIndicator) {
    navIndicatorVal = s; applyNavIndicator(s, true); uiNavIndicator.set(s);
  }
  function toggleChipIcons() {
    chipIcons = !chipIcons; applyChipIcons(chipIcons, true); uiChipIcons.set(chipIcons);
  }
  function setDeckWidth(v: number) {
    deckWidth = v; applyDeckWidthPct(v, true); uiDeckWidthPct.set(v);
  }
  function setDeckHeight(v: number) {
    deckHeight = v; applyDeckHeightVw(v, true); uiDeckHeightVw.set(v);
  }
  function setDeckRadius(v: number) {
    deckRadius = v; applyDeckRadiusPct(v, true); uiDeckRadiusPct.set(v);
  }
  function toggleWelcomeBold() {
    welcomeBold = !welcomeBold; applyWelcomeBold(welcomeBold, true); uiWelcomeBold.set(welcomeBold);
  }
  function moveTab(i: number, dir: -1 | 1) {
    const arr = [...get(tabOrder)];
    const j = i + dir;
    if (j < 0 || j >= arr.length) return;
    [arr[i], arr[j]] = [arr[j], arr[i]];
    setTabOrder(arr);
  }
  function resetInterface() {
    resetUiPrefs();
    radiusSurfaceVal = RADIUS_SURFACE_DEFAULT;
    radiusControlVal = RADIUS_CONTROL_DEFAULT;
    navStyleVal = 'bar';
    glassVal = true;
    accentVal = null;
    borderOn = false;
    borderWidth = 1;
    borderColor = null;
    navIndicatorVal = 'modern';
    chipIcons = true;
    deckWidth = DECK_WIDTH_PCT_DEFAULT;
    deckHeight = DECK_HEIGHT_VW_DEFAULT;
    deckRadius = DECK_RADIUS_PCT_DEFAULT;
    welcomeBold = false;
  }

  function fmtEm(px: number): string {
    return `${(px / 16).toFixed(2)}rem`;
  }

  function selectFont(category: FontCategory, fontName: string) {
    applyFont(category, fontName, true);
    activeFonts[category] = fontName;
    openFontDropdown = null;
    if (category === 'article-body') {
      const snapped = snapFontWeight(fontName, fontWeight);
      if (snapped !== fontWeight) {
        fontWeight = snapped; applyFontWeight(snapped, true); articleFontWeight.setValue(snapped);
      }
    }
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

{#if titleDropdownOpen}
  <Portal>
    <div class="picker-backdrop" onclick={() => titleDropdownOpen = false} aria-hidden="true"></div>
    <div class="picker-dropdown title-align-dropdown" style={titleDropStyle} role="listbox">
      <button class="picker-item" class:picker-selected={titlePos === 'left'} role="option" aria-selected={titlePos === 'left'} onclick={() => selectTitleAlign('left')}>
        <span class="picker-item-text">{$t('settings.textAlignLeft')}</span>
        {#if titlePos === 'left'}<Check size={12} class="picker-check" />{/if}
      </button>
      <button class="picker-item" class:picker-selected={titlePos === 'justify'} role="option" aria-selected={titlePos === 'justify'} onclick={() => selectTitleAlign('justify')}>
        <span class="picker-item-text">{$t('settings.textAlignJustified')}</span>
        {#if titlePos === 'justify'}<Check size={12} class="picker-check" />{/if}
      </button>
      <button class="picker-item" class:picker-selected={titlePos === 'center'} role="option" aria-selected={titlePos === 'center'} onclick={() => selectTitleAlign('center')}>
        <span class="picker-item-text">{$t('settings.textAlignCenter')}</span>
        {#if titlePos === 'center'}<Check size={12} class="picker-check" />{/if}
      </button>
      <button class="picker-item" class:picker-selected={titlePos === 'right'} role="option" aria-selected={titlePos === 'right'} onclick={() => selectTitleAlign('right')}>
        <span class="picker-item-text">{$t('settings.textAlignRight')}</span>
        {#if titlePos === 'right'}<Check size={12} class="picker-check" />{/if}
      </button>
    </div>
  </Portal>
{/if}

{#if bodyDropdownOpen}
  <Portal>
    <div class="picker-backdrop" onclick={() => bodyDropdownOpen = false} aria-hidden="true"></div>
    <div class="picker-dropdown body-align-dropdown" style={bodyDropStyle} role="listbox">
      <button class="picker-item" class:picker-selected={bodyPos === 'left'} role="option" aria-selected={bodyPos === 'left'} onclick={() => selectBodyAlign('left')}>
        <span class="picker-item-text">{$t('settings.textAlignLeft')}</span>
        {#if bodyPos === 'left'}<Check size={12} class="picker-check" />{/if}
      </button>
      <button class="picker-item" class:picker-selected={bodyPos === 'justify'} role="option" aria-selected={bodyPos === 'justify'} onclick={() => selectBodyAlign('justify')}>
        <span class="picker-item-text">{$t('settings.textAlignJustified')}</span>
        {#if bodyPos === 'justify'}<Check size={12} class="picker-check" />{/if}
      </button>
      <button class="picker-item" class:picker-selected={bodyPos === 'center'} role="option" aria-selected={bodyPos === 'center'} onclick={() => selectBodyAlign('center')}>
        <span class="picker-item-text">{$t('settings.textAlignCenter')}</span>
        {#if bodyPos === 'center'}<Check size={12} class="picker-check" />{/if}
      </button>
      <button class="picker-item" class:picker-selected={bodyPos === 'right'} role="option" aria-selected={bodyPos === 'right'} onclick={() => selectBodyAlign('right')}>
        <span class="picker-item-text">{$t('settings.textAlignRight')}</span>
        {#if bodyPos === 'right'}<Check size={12} class="picker-check" />{/if}
      </button>
    </div>
  </Portal>
{/if}

<div class="tab-panel">
  <h2 class="section-title">{$t('settings.appearance')}</h2>

  {#snippet sliderRow(label: string, value: number, min: number, max: number, step: number, suffix: string, onInput: (v: number) => void, fmt: ((v: number) => string) | undefined)}
    <div class="setting-slider-row">
      <div class="slider-head">
        <span class="setting-label">{label}</span>
        <span class="slider-value">{fmt ? fmt(value) : `${value}${suffix ?? ''}`}</span>
      </div>
      <input
        type="range"
        class="range"
        min={min}
        max={max}
        step={step}
        value={value}
        oninput={(e) => onInput(Number((e.target as HTMLInputElement).value))}
      />
    </div>
  {/snippet}

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
    <button class="pill-toggle" class:on={activeTheme === 'berga-black'} use:ripple onclick={toggleTheme} aria-label={$t('settings.lightMode')}>
      <div class="pill-thumb"></div>
    </button>
  </div>

  {#snippet TabIcon(id: TabId)}
    {@const Icon = TAB_DEFS[id].icon}
    <Icon size={18} strokeWidth={1.8} />
  {/snippet}

  <div class="settings-group">
    <div class="group-label">{$t('settings.interface')}</div>
    <div class="group-card">
      <div class="setting-row">
        <span class="setting-label">{$t('settings.bottomNavStyle')}</span>
        <div class="navstyle-picker">
          <button
            class="navstyle-card"
            class:active={navStyleVal === 'bar'}
            use:ripple
            onclick={() => setNavStyle('bar')}
            aria-pressed={navStyleVal === 'bar'}
          >
            <span class="navstyle-preview navstyle-preview--bar"><span></span><span></span><span></span></span>
            <span class="navstyle-label">{$t('settings.navStyleBar')}</span>
          </button>
          <button
            class="navstyle-card"
            class:active={navStyleVal === 'deck'}
            use:ripple
            onclick={() => setNavStyle('deck')}
            aria-pressed={navStyleVal === 'deck'}
          >
            <span class="navstyle-preview navstyle-preview--deck"><span></span><span></span><span></span></span>
            <span class="navstyle-label">{$t('settings.navStyleDeck')}</span>
          </button>
        </div>
      </div>

      <div class="setting-row">
        <span class="setting-label">{$t('settings.navIndicator')}</span>
        <div class="navstyle-picker">
          <button
            class="navstyle-card"
            class:active={navIndicatorVal === 'modern'}
            use:ripple
            onclick={() => setNavIndicator('modern')}
            aria-pressed={navIndicatorVal === 'modern'}
          >
            <span class="navstyle-preview navstyle-preview--modern"><span></span><span></span><span></span></span>
            <span class="navstyle-label">{$t('settings.navIndicatorModern')}</span>
          </button>
          <button
            class="navstyle-card"
            class:active={navIndicatorVal === 'classic'}
            use:ripple
            onclick={() => setNavIndicator('classic')}
            aria-pressed={navIndicatorVal === 'classic'}
          >
            <span class="navstyle-preview navstyle-preview--classic"><span></span><span></span><span></span></span>
            <span class="navstyle-label">{$t('settings.navIndicatorClassic')}</span>
          </button>
        </div>
      </div>

      {#if navStyleVal === 'deck'}
        <div class="setting-slider-row">
          <div class="slider-head">
            <span class="setting-label">{$t('settings.deckWidth')}</span>
            <span class="slider-value">{deckWidth}%</span>
          </div>
          <input
            type="range"
            class="range"
            min={DECK_WIDTH_PCT_MIN}
            max={DECK_WIDTH_PCT_MAX}
            step={1}
            value={deckWidth}
            oninput={(e) => setDeckWidth(Number((e.target as HTMLInputElement).value))}
          />
        </div>

        <div class="setting-slider-row">
          <div class="slider-head">
            <span class="setting-label">{$t('settings.deckHeight')}</span>
            <span class="slider-value">{deckHeight}%</span>
          </div>
          <input
            type="range"
            class="range"
            min={DECK_HEIGHT_VW_MIN}
            max={DECK_HEIGHT_VW_MAX}
            step={0.5}
            value={deckHeight}
            oninput={(e) => setDeckHeight(Number((e.target as HTMLInputElement).value))}
          />
        </div>

        <div class="setting-slider-row">
          <div class="slider-head">
            <span class="setting-label">{$t('settings.deckRadius')}</span>
            <span class="slider-value">{deckRadius}%</span>
          </div>
          <input
            type="range"
            class="range"
            min={DECK_RADIUS_PCT_MIN}
            max={DECK_RADIUS_PCT_MAX}
            step={1}
            value={deckRadius}
            oninput={(e) => setDeckRadius(Number((e.target as HTMLInputElement).value))}
          />
        </div>
      {/if}

      <div class="setting-row">
        <div class="setting-text">
          <span class="setting-label">{$t('settings.frostedGlass')}</span>
        </div>
        <button class="pill-toggle" class:on={glassVal} use:ripple onclick={toggleGlass} aria-label={$t('settings.frostedGlass')}>
          <div class="pill-thumb"></div>
        </button>
      </div>

      <div class="setting-slider-row">
        <div class="slider-head">
          <span class="setting-label">{$t('settings.radiusSurfaces')}</span>
          <span class="slider-value">{radiusSurfaceVal}px</span>
        </div>
        <input
          type="range"
          class="range"
          min={RADIUS_SURFACE_MIN}
          max={RADIUS_SURFACE_MAX}
          step={1}
          value={radiusSurfaceVal}
          oninput={(e) => setRadiusSurface(Number((e.target as HTMLInputElement).value))}
        />
      </div>

      <div class="setting-slider-row">
        <div class="slider-head">
          <span class="setting-label">{$t('settings.radiusControls')}</span>
          <span class="slider-value">{radiusControlVal}px</span>
        </div>
        <input
          type="range"
          class="range"
          min={RADIUS_CONTROL_MIN}
          max={RADIUS_CONTROL_MAX}
          step={1}
          value={radiusControlVal}
          oninput={(e) => setRadiusControl(Number((e.target as HTMLInputElement).value))}
        />
        <p class="row-hint">{$t('settings.radiusHint')}</p>
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
        <div class="setting-text">
          <span class="setting-label">{$t('settings.borders')}</span>
        </div>
        <button class="pill-toggle" class:on={borderOn} use:ripple onclick={() => setBorderOn(!borderOn)} aria-label={$t('settings.borders')}>
          <div class="pill-thumb"></div>
        </button>
      </div>

      {#if borderOn}
        <div class="setting-slider-row">
          <div class="slider-head">
            <span class="setting-label">{$t('settings.borderWidth')}</span>
            <span class="slider-value">{borderWidth}px</span>
          </div>
          <input
            type="range"
            class="range"
            min={BORDER_WIDTH_MIN}
            max={BORDER_WIDTH_MAX}
            step={0.5}
            value={borderWidth}
            oninput={(e) => setBorderWidth(Number((e.target as HTMLInputElement).value))}
          />
        </div>

        <div class="setting-row accent-row">
          <span class="setting-label">{$t('settings.borderColor')}</span>
          <div class="accent-swatches">
            {#each BORDER_COLOR_PRESETS as preset}
              <button
                class="swatch swatch-line"
                class:selected={borderColor === preset}
                style="background: {preset ?? 'var(--ui-border-color)'}"
                use:ripple
                onclick={() => setBorderColor(preset)}
                aria-label={preset ?? $t('settings.borderColorDefault')}
                aria-pressed={borderColor === preset}
              ></button>
            {/each}
            <label
              class="swatch swatch-custom"
              class:selected={borderColor !== null && !BORDER_COLOR_PRESETS.includes(borderColor)}
              title={$t('settings.accentCustom')}
            >
              <input
                type="color"
                value={customBorderColor}
                oninput={(e) => setBorderColor((e.target as HTMLInputElement).value)}
              />
            </label>
          </div>
        </div>
      {/if}

      <div class="setting-row">
        <div class="setting-text">
          <span class="setting-label">{$t('settings.chipIcons')}</span>
        </div>
        <button class="pill-toggle" class:on={chipIcons} use:ripple onclick={toggleChipIcons} aria-label={$t('settings.chipIcons')}>
          <div class="pill-thumb"></div>
        </button>
      </div>

      <div class="setting-row">
        <div class="setting-text">
          <span class="setting-label">{$t('settings.boldWelcome')}</span>
        </div>
        <button class="pill-toggle" class:on={welcomeBold} use:ripple onclick={toggleWelcomeBold} aria-label={$t('settings.boldWelcome')}>
          <div class="pill-thumb"></div>
        </button>
      </div>

      <div class="setting-block">
        <span class="setting-label">{$t('settings.tabOrder')}</span>
        <div class="taborder-list">
          {#each $tabOrder as id, i (id)}
            <div class="taborder-row" class:first={i === 0} class:last={i === $tabOrder.length - 1}>
              <span class="taborder-icon">{@render TabIcon(id)}</span>
              <span class="taborder-label">{$t(`navbar.${id}`)}</span>
              <span class="taborder-controls">
                <button
                  class="taborder-btn"
                  onclick={() => moveTab(i, -1)}
                  disabled={i === 0}
                  aria-label={$t('settings.moveUp')}
                >
                  <ChevronUp size={16} />
                </button>
                <button
                  class="taborder-btn"
                  onclick={() => moveTab(i, 1)}
                  disabled={i === $tabOrder.length - 1}
                  aria-label={$t('settings.moveDown')}
                >
                  <ChevronDown size={16} />
                </button>
              </span>
            </div>
          {/each}
        </div>
      </div>

      <div class="css-actions">
        <button class="action-btn" use:ripple onclick={resetInterface}>
          <RotateCcw size={14} />
          <span>{$t('settings.resetInterface')}</span>
        </button>
      </div>
    </div>
  </div>

  <div class="settings-group">
    <div class="group-label">{$t('settings.sectionTypography')}</div>
    <div class="group-card">
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

      {@render sliderRow($t('settings.fontSize'), fontSize,
        ARTICLE_TYPOGRAPHY.fontSize.min, ARTICLE_TYPOGRAPHY.fontSize.max,
        ARTICLE_TYPOGRAPHY.fontSize.step, '', setFontSize, fmtEm)}

      {@render sliderRow($t('settings.fontWeight'), fontWeight,
        ARTICLE_TYPOGRAPHY.fontWeight.min, ARTICLE_TYPOGRAPHY.fontWeight.max,
        ARTICLE_TYPOGRAPHY.fontWeight.step, '', setFontWeight, undefined)}

      {@render sliderRow($t('settings.letterSpacing'), letterSpacing,
        ARTICLE_TYPOGRAPHY.letterSpacing.min, ARTICLE_TYPOGRAPHY.letterSpacing.max,
        ARTICLE_TYPOGRAPHY.letterSpacing.step, 'em', setLetterSpacing,
        (v) => v === 0 ? $t('settings.normal') : `${v}em`)}

      {@render sliderRow($t('settings.lineHeight'), lineHeight,
        ARTICLE_TYPOGRAPHY.lineHeight.min, ARTICLE_TYPOGRAPHY.lineHeight.max,
        ARTICLE_TYPOGRAPHY.lineHeight.step, '', setLineHeight,
        (v) => v.toFixed(2))}
    </div>
  </div>

  <div class="settings-group">
    <div class="group-label">{$t('settings.sectionReading')}</div>
    <div class="group-card">
      {@render sliderRow($t('settings.bodyWidth'), articleMaxW,
        ARTICLE_TYPOGRAPHY.maxWidth.min, ARTICLE_TYPOGRAPHY.maxWidth.max,
        ARTICLE_TYPOGRAPHY.maxWidth.step, '', setArticleMaxWidth,
        (v) => `${v}px`)}

      {@render sliderRow($t('settings.titleWidth'), articleTitleMaxW,
        ARTICLE_TYPOGRAPHY.titleMaxWidth.min, ARTICLE_TYPOGRAPHY.titleMaxWidth.max,
        ARTICLE_TYPOGRAPHY.titleMaxWidth.step, '', setArticleTitleMaxWidth,
        (v) => `${v}px`)}

      {@render sliderRow($t('settings.imageWidth'), imageWidth,
        ARTICLE_TYPOGRAPHY.imageWidth.min, ARTICLE_TYPOGRAPHY.imageWidth.max,
        ARTICLE_TYPOGRAPHY.imageWidth.step, '%', setImageWidth,
        (v) => v === 0 ? $t('settings.imageWidthAuto') : `${v}%`)}

      <div class="setting-row">
        <span class="setting-label">{$t('settings.titleTextPosition')}</span>
        <div class="picker-wrap">
          <button bind:this={titleBtnEl} class="setting-btn" use:ripple onclick={toggleTitleDropdown}>
            <span>
              {titlePos === 'left' ? $t('settings.textAlignLeft') :
               titlePos === 'justify' ? $t('settings.textAlignJustified') :
               titlePos === 'center' ? $t('settings.textAlignCenter') :
               $t('settings.textAlignRight')}
            </span>
            <span class="chevron-icon" class:rotated={titleDropdownOpen}>
              <ChevronDown size={14} />
            </span>
          </button>
        </div>
      </div>

      <div class="setting-row">
        <span class="setting-label">{$t('settings.bodyTextPosition')}</span>
        <div class="picker-wrap">
          <button bind:this={bodyBtnEl} class="setting-btn" use:ripple onclick={toggleBodyDropdown}>
            <span>
              {bodyPos === 'left' ? $t('settings.textAlignLeft') :
               bodyPos === 'justify' ? $t('settings.textAlignJustified') :
               bodyPos === 'center' ? $t('settings.textAlignCenter') :
               $t('settings.textAlignRight')}
            </span>
            <span class="chevron-icon" class:rotated={bodyDropdownOpen}>
              <ChevronDown size={14} />
            </span>
          </button>
        </div>
      </div>
    </div>
  </div>

  <div class="settings-group">
    <div class="group-label">{$t('settings.sectionPostcards')}</div>
    <div class="group-card">
      <div class="setting-row">
        <div class="setting-text">
          <span class="setting-label">{$t('settings.showCoverImages')}</span>
        </div>
        <button class="pill-toggle" class:on={showCover} use:ripple onclick={toggleShowCover} aria-label={$t('settings.showCoverImages')}>
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

      {@render sliderRow($t('settings.descLines'), descLines,
        POSTCARD_PREFS.descLines.min, POSTCARD_PREFS.descLines.max,
        POSTCARD_PREFS.descLines.step, '', setDescLines,
        (v) => v === 0 ? $t('settings.descLinesHidden') : String(v))}

      <div class="setting-row">
        <div class="setting-text">
          <span class="setting-label">{$t('settings.boldTitle')}</span>
        </div>
        <button class="pill-toggle" class:on={titleBold} use:ripple onclick={toggleTitleBold} aria-label={$t('settings.boldTitle')}>
          <div class="pill-thumb"></div>
        </button>
      </div>

      {@render sliderRow($t('settings.cardTitleSize'), titleSizeVal,
        POSTCARD_PREFS.titleSize.min, POSTCARD_PREFS.titleSize.max,
        POSTCARD_PREFS.titleSize.step, '',
        setTitleSize,
        (v) => `${v}%`)}

      {@render sliderRow($t('settings.cardDescSize'), descSizeVal,
        POSTCARD_PREFS.descSize.min, POSTCARD_PREFS.descSize.max,
        POSTCARD_PREFS.descSize.step, '',
        setDescSize,
        (v) => `${v}%`)}

      <div class="setting-row">
        <span class="setting-label">{$t('settings.density')}</span>
        <div class="picker-wrap density-picker">
          {#each ['compact', 'comfortable', 'spacious'] as d}
            {@const isSel = d === density}
            <button
              class="density-btn"
              class:active={isSel}
              use:ripple
              onclick={() => setDensity(d as Density)}
              aria-pressed={isSel}
            >
              {$t(`settings.density${d.charAt(0).toUpperCase() + d.slice(1)}`)}
            </button>
          {/each}
        </div>
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
</div>

<style>
  .tab-panel { display: flex; flex-direction: column; gap: 16px; padding-top: 12px; }
  .section-title { font-size: 16px; font-weight: 700; color: var(--color-base-content); margin: 0; }
  .section-desc { font-size: 13px; line-height: 1.45; color: color-mix(in oklch, var(--color-base-content) 50%, transparent); margin: 0; overflow-wrap: anywhere; }

  .setting-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 13px 0; border-bottom: 1px solid var(--color-base-300); }
  .setting-row:last-child { border-bottom: none; }
  .setting-block { display: flex; flex-direction: column; gap: 12px; padding: 13px 0; border-bottom: 1px solid var(--color-base-300); }
  .setting-label { font-size: 14px; font-weight: 500; color: var(--color-base-content); }
  .setting-text { display: flex; flex-direction: column; gap: 2px; min-width: 0; overflow-wrap: anywhere; }

  .setting-btn {
    display: flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: var(--ui-radius-sm);
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
    border-radius: var(--ui-radius-sm); box-shadow: 0 8px 24px color-mix(in oklch, black 20%, transparent);
    padding: 4px; min-width: 180px; overflow-y: auto;
    animation: picker-pop 150ms cubic-bezier(0.22, 1, 0.36, 1) both;
    position: fixed;
  }
  .picker-dropdown, .picker-dropdown * { pointer-events: auto; }
  .picker-item {
    display: flex; align-items: center; justify-content: space-between; width: 100%;
    padding: 8px 10px; border: none; background: transparent; cursor: pointer;
    font-size: 13px; font-weight: 500; color: var(--color-base-content);
    border-radius: var(--ui-radius-xs); transition: background 110ms; text-align: left; gap: 8px;
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
    width: 44px; height: 24px; border-radius: var(--ui-radius-full);
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
    width: 100%; box-sizing: border-box; padding: 12px; border-radius: var(--ui-radius-sm);
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
    padding: 10px 16px; border-radius: var(--ui-radius-sm); border: 1px solid var(--color-base-300);
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

  /* ── Flat grouped sections (iOS style) ────────────────────── */
  .settings-group { display: flex; flex-direction: column; gap: 10px; }
  .group-label {
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: color-mix(in oklch, var(--color-base-content) 48%, transparent);
    padding: 4px 0 0;
  }
  /* Flat, Spotify-style: no inner boxes — rows separated by dividers */
  .group-card {
    display: flex;
    flex-direction: column;
    background: transparent;
    border: none;
    padding: 0;
  }

  /* ── Sliders ──────────────────────────────────────────────── */
  .setting-slider-row {
    display: flex; flex-direction: column; gap: 6px;
    padding: 10px 0; border-bottom: 1px solid var(--color-base-300);
  }
  .slider-head { display: flex; align-items: center; justify-content: space-between; }
  .slider-value {
    font-size: 12px; font-weight: 600; color: var(--color-accent);
    font-variant-numeric: tabular-nums; font-family: var(--font-ui);
  }
  .range {
    -webkit-appearance: none; appearance: none;
    width: 100%; height: 4px; border-radius: var(--ui-radius-full);
    background: color-mix(in oklch, var(--color-base-content) 18%, transparent);
    outline: none; cursor: pointer;
  }
  .range::-webkit-slider-thumb {
    -webkit-appearance: none; appearance: none;
    width: 18px; height: 18px; border-radius: 50%;
    background: var(--color-accent); border: 2px solid var(--color-base-100);
    box-shadow: 0 1px 4px rgba(0,0,0,.25); cursor: pointer;
    transition: transform 110ms;
  }
  .range::-webkit-slider-thumb:active { transform: scale(1.18); }
  .range::-moz-range-thumb {
    width: 18px; height: 18px; border-radius: 50%; border: 2px solid var(--color-base-100);
    background: var(--color-accent); box-shadow: 0 1px 4px rgba(0,0,0,.25); cursor: pointer;
  }

  /* ── Density picker ───────────────────────────────────────── */
  .density-picker { display: flex; gap: 4px; }

  /* ── Interface: nav style picker ──────────────────────────── */
  .navstyle-picker { display: flex; gap: 8px; }
  .navstyle-card {
    display: flex; flex-direction: column; align-items: center; gap: 6px;
    padding: 8px; border-radius: var(--ui-radius-sm);
    border: 1px solid var(--color-base-300); background: transparent;
    cursor: pointer; transition: all 130ms; position: relative; overflow: hidden;
  }
  .navstyle-card:hover { background: var(--color-base-200); }
  .navstyle-card.active {
    border-color: var(--color-accent);
    background: color-mix(in oklch, var(--color-accent) 10%, transparent);
  }
  .navstyle-label { font-size: 11px; font-weight: 600; color: var(--color-base-content); }
  .navstyle-preview {
    display: flex; align-items: center; gap: 5px;
    width: 64px; height: 26px; padding: 3px;
    background: color-mix(in oklch, var(--color-base-content) 10%, transparent);
    border-radius: var(--ui-radius-xs);
  }
  .navstyle-preview span {
    flex: 1; height: 8px; border-radius: var(--ui-radius-full);
    background: color-mix(in oklch, var(--color-base-content) 35%, transparent);
  }
  .navstyle-preview span:first-child { background: var(--color-accent); }
  .navstyle-preview--deck { padding: 3px 7px; border-radius: var(--ui-radius-full); border: 1px solid var(--color-base-300); }
  /* Modern: active icon sits in a tinted pill; Classic: whole item lights up */
  .navstyle-preview--modern span:first-child {
    background: color-mix(in oklch, var(--color-accent) 26%, transparent);
    height: 14px;
    margin-top: -3px;
    margin-bottom: -3px;
    border-radius: var(--ui-radius-full);
  }
  .navstyle-preview--classic span:first-child {
    background: color-mix(in oklch, var(--color-accent) 26%, transparent);
  }

  /* ── Interface: accent swatches ───────────────────────────── */
  .accent-row { flex-wrap: wrap; gap: 8px; }
  .accent-swatches { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
  .swatch {
    width: 26px; height: 26px; border-radius: 50%;
    border: 2px solid transparent; cursor: pointer; padding: 0;
    box-shadow: inset 0 0 0 2px var(--color-base-100);
    transition: transform 120ms, border-color 120ms;
    position: relative; overflow: hidden;
  }
  .swatch:hover { transform: scale(1.12); }
  .swatch.selected { border-color: var(--color-base-content); }
  .swatch-line { border-radius: var(--ui-radius-xs); }
  .swatch-custom {
    display: flex; align-items: center; justify-content: center;
    background:
      conic-gradient(#f66 0 0.5turn, #6cf 0.5turn 0.75turn, #f66 0.75turn);
    font-size: 0;
  }
  .swatch-custom input {
    position: absolute; inset: 0; opacity: 0; cursor: pointer; width: 100%; height: 100%;
  }

  .row-hint {
    font-size: 12px;
    line-height: 1.4;
    color: color-mix(in oklch, var(--color-base-content) 45%, transparent);
    margin: 4px 0 0;
  }

  /* ── Interface: tab order ─────────────────────────────────── */
  .taborder-list { display: flex; flex-direction: column; gap: 6px; }
  .taborder-row {
    display: flex; align-items: center; gap: 10px;
    padding: 8px 12px;
    border: 1px solid var(--color-base-300);
    border-radius: var(--ui-radius-sm);
    background: color-mix(in oklch, var(--color-base-100) 60%, transparent);
  }
  .taborder-icon {
    display: flex; align-items: center; color: var(--color-accent);
  }
  .taborder-label { flex: 1; font-size: 13px; font-weight: 500; color: var(--color-base-content); }
  .taborder-controls { display: flex; gap: 4px; }
  .taborder-btn {
    display: flex; align-items: center; justify-content: center;
    width: 28px; height: 28px;
    border: 1px solid var(--color-base-300); border-radius: var(--ui-radius-sm);
    background: transparent; color: var(--color-base-content);
    cursor: pointer; transition: all 120ms;
  }
  .taborder-btn:hover:not(:disabled) { background: var(--color-base-200); }
  .taborder-btn:disabled { opacity: 0.35; cursor: not-allowed; }
  .density-btn {
    padding: 6px 10px; border-radius: var(--ui-radius-sm); border: 1px solid var(--color-base-300);
    background: transparent; color: color-mix(in oklch, var(--color-base-content) 70%, transparent);
    font-size: 12px; font-weight: 600; cursor: pointer; transition: all 130ms;
    font-family: var(--font-ui);
  }
  .density-btn:hover { background: var(--color-base-200); color: var(--color-base-content); }
  .density-btn.active {
    background: color-mix(in oklch, var(--color-accent) 16%, transparent);
    border-color: var(--color-accent); color: var(--color-accent);
  }
</style>
