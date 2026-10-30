<script lang="ts">
  import '$lib/components/settings/settings.css';
  import { onMount } from 'svelte';
  import { t } from 'svelte-i18n';
  import SettingsToggle from '$lib/components/settings/SettingsToggle.svelte';
  import SettingsSlider from '$lib/components/settings/SettingsSlider.svelte';
  import DockPreview from '$lib/components/settings/preview/DockPreview.svelte';
  import PreviewFrame from '$lib/components/settings/preview/PreviewFrame.svelte';
  import { ripple } from '$lib/actions/ripple';
  import { ChevronUp, ChevronDown } from '@lucide/svelte';
  import { tabOrder, setTabOrder, TAB_DEFS, type TabId } from '$lib/config/tabs';
  import {
    uiNavStyle,
    uiDesktopNav,
    uiDockWidthVmin,
    uiDockRadiusPct,
    uiDockPadPct,
    uiDockInsetVmin,
    uiDockHeightPct,
    uiDockShadowPct,
    uiDockSpacingPct,
    uiNavBg,
    uiGlass,
    uiNavIndicator,
    uiSidebarCollapsed,
    uiSidebarMargin,
    uiSidebarSize,
    uiDeckWidthPct,
    uiDeckHeightVw,
    uiDeckRadiusPct,
    uiMnavIconSize,
    uiMnavIconBox,
    uiMnavLabelSize,
    uiMnavLabelGap,
    uiMnavHeight,
    uiMnavLabels,
    uiMnavItemRadius,
    applyNavStyle,
    applyDesktopNav,
    applyDockWidthVmin,
    applyDockRadiusPct,
    applyDockPadPct,
    applyDockInsetVmin,
    applyDockHeightPct,
    applyDockShadowPct,
    applyDockSpacingPct,
    applyGlass,
    applyNavIndicator,
    applySidebarCollapsed,
    applySidebarMargin,
    applySidebarSize,
    applyDeckWidthPct,
    applyDeckHeightVw,
    applyDeckRadiusPct,
    applyNavBg,
    applyMnavIconSize,
    applyMnavIconBox,
    applyMnavLabelSize,
    applyMnavLabelGap,
    applyMnavHeight,
    applyMnavLabels,
    applyMnavItemRadius,
    getSavedNavStyle,
    getSavedDesktopNav,
    getSavedDockWidthVmin,
    getSavedDockRadiusPct,
    getSavedDockPadPct,
    getSavedDockInsetVmin,
    getSavedDockHeightPct,
    getSavedDockShadowPct,
    getSavedDockSpacingPct,
    getSavedGlass,
    getSavedNavIndicator,
    getSavedSidebarCollapsed,
    getSavedSidebarMargin,
    getSavedSidebarSize,
    getSavedDeckWidthPct,
    getSavedDeckHeightVw,
    getSavedDeckRadiusPct,
    getSavedNavBg,
    getSavedMnavIconSize,
    getSavedMnavIconBox,
    getSavedMnavLabelSize,
    getSavedMnavLabelGap,
    getSavedMnavHeight,
    getSavedMnavLabels,
    getSavedMnavItemRadius,
    DOCK_WIDTH_MIN,
    DOCK_WIDTH_MAX,
    DOCK_WIDTH_DEFAULT,
    DOCK_RADIUS_MIN,
    DOCK_RADIUS_MAX,
    DOCK_HEIGHT_MIN,
    DOCK_HEIGHT_MAX,
    DOCK_HEIGHT_DEFAULT,
    DOCK_PAD_MIN,
    DOCK_PAD_MAX,
    DOCK_PAD_DEFAULT,
    DOCK_INSET_MIN,
    DOCK_INSET_MAX,
    DOCK_INSET_DEFAULT,
    DOCK_SHADOW_MIN,
    DOCK_SHADOW_MAX,
    DOCK_SHADOW_DEFAULT,
    DOCK_SPACING_MIN,
    DOCK_SPACING_MAX,
    DOCK_SPACING_DEFAULT,
    SIDEBAR_MARGIN_MIN,
    SIDEBAR_MARGIN_MAX,
    SIDEBAR_MARGIN_DEFAULT,
    SIDEBAR_SIZE_MIN,
    SIDEBAR_SIZE_MAX,
    SIDEBAR_SIZE_DEFAULT,
    DECK_WIDTH_PCT_MIN,
    DECK_WIDTH_PCT_MAX,
    DECK_WIDTH_PCT_DEFAULT,
    DECK_HEIGHT_VW_MIN,
    DECK_HEIGHT_VW_MAX,
    DECK_HEIGHT_VW_DEFAULT,
    DECK_RADIUS_PCT_MIN,
    DECK_RADIUS_PCT_MAX,
    DECK_RADIUS_PCT_DEFAULT,
    MNAV_ICON_SIZE_MIN,
    MNAV_ICON_SIZE_MAX,
    MNAV_ICON_SIZE_DEFAULT,
    MNAV_ICON_BOX_MIN,
    MNAV_ICON_BOX_MAX,
    MNAV_ICON_BOX_DEFAULT,
    MNAV_LABEL_SIZE_MIN,
    MNAV_LABEL_SIZE_MAX,
    MNAV_LABEL_SIZE_DEFAULT,
    MNAV_LABEL_GAP_MIN,
    MNAV_LABEL_GAP_MAX,
    MNAV_LABEL_GAP_DEFAULT,
    MNAV_HEIGHT_MIN,
    MNAV_HEIGHT_MAX,
    MNAV_HEIGHT_DEFAULT,
    type NavStyle,
    type NavBg,
    type NavIndicator,
    type DesktopNavModel,
    type MnavItemRadius,
  } from '$lib/stores/uiPrefs';

  let isDesktop = $state(false);
  let desktopNavVal = $state<DesktopNavModel>(getSavedDesktopNav());
  let navStyleVal = $state<NavStyle>(getSavedNavStyle());
  let dockWidth = $state<number>(getSavedDockWidthVmin());
  let dockHeight = $state<number>(getSavedDockHeightPct());
  let dockRadius = $state<number>(getSavedDockRadiusPct());
  let dockPad = $state<number>(getSavedDockPadPct());
  let dockInset = $state<number>(getSavedDockInsetVmin());
  let dockShadow = $state<number>(getSavedDockShadowPct());
  let dockSpacing = $state<number>(getSavedDockSpacingPct());
  let glassVal = $state<boolean>(getSavedGlass());
  let navIndicatorVal = $state<NavIndicator>(getSavedNavIndicator());
  let navBgVal = $state<NavBg>(getSavedNavBg());
  let sidebarCollapsed = $state<boolean>(getSavedSidebarCollapsed());
  let sidebarMargin = $state<number>(getSavedSidebarMargin());
  let sidebarSize = $state<number>(getSavedSidebarSize());
  let deckWidth = $state<number>(getSavedDeckWidthPct());
  let deckHeight = $state<number>(getSavedDeckHeightVw());
  let deckRadius = $state<number>(getSavedDeckRadiusPct());
  let mnavIconSize = $state<number>(getSavedMnavIconSize());
  let mnavIconBox = $state<number>(getSavedMnavIconBox());
  let mnavLabelSize = $state<number>(getSavedMnavLabelSize());
  let mnavLabelGap = $state<number>(getSavedMnavLabelGap());
  let mnavHeight = $state<number>(getSavedMnavHeight());
  let mnavLabels = $state<boolean>(getSavedMnavLabels());
  let mnavItemRadius = $state<MnavItemRadius>(getSavedMnavItemRadius());

  const NAV_BG_OPTIONS: { value: NavBg; labelKey: string; color: string | null }[] = [
    { value: 'default', labelKey: 'settings.navColorDefault', color: null },
    { value: 'white', labelKey: 'settings.navColorWhite', color: '#ffffff' },
    { value: 'berga-white', labelKey: 'settings.navColorBergaWhite', color: '#fbfaf7' },
    { value: 'berga-gray', labelKey: 'settings.navColorBergaGray', color: '#f8f7f3' },
    { value: 'dark', labelKey: 'settings.navColorDark', color: '#17181d' },
    { value: 'amoled', labelKey: 'settings.navColorAmoled', color: '#000000' },
  ];

  onMount(() => {
    isDesktop = window.matchMedia('(min-width: 768px)').matches;
  });

  function setDesktopNav(s: DesktopNavModel) {
    desktopNavVal = s;
    applyDesktopNav(s, true);
    uiDesktopNav.set(s);
  }
  function setNavStyle(s: NavStyle) {
    navStyleVal = s;
    applyNavStyle(s, true);
    uiNavStyle.set(s);
  }
  function setDockWidth(v: number) {
    dockWidth = v; applyDockWidthVmin(v, true); uiDockWidthVmin.set(v);
  }
  function setDockHeight(v: number) {
    dockHeight = v; applyDockHeightPct(v, true); uiDockHeightPct.set(v);
  }
  function setDockRadius(v: number) {
    dockRadius = v; applyDockRadiusPct(v, true); uiDockRadiusPct.set(v);
  }
  function setDockPad(v: number) {
    dockPad = v; applyDockPadPct(v, true); uiDockPadPct.set(v);
  }
  function setDockInset(v: number) {
    dockInset = v; applyDockInsetVmin(v, true); uiDockInsetVmin.set(v);
  }
  function setDockShadow(v: number) {
    dockShadow = v; applyDockShadowPct(v, true); uiDockShadowPct.set(v);
  }
  function setDockSpacing(v: number) {
    dockSpacing = v; applyDockSpacingPct(v, true); uiDockSpacingPct.set(v);
  }
  function toggleGlass() {
    glassVal = !glassVal; applyGlass(glassVal, true); uiGlass.set(glassVal);
  }
  function setNavIndicator(s: NavIndicator) {
    navIndicatorVal = s; applyNavIndicator(s, true); uiNavIndicator.set(s);
  }
  function setNavBg(v: NavBg) {
    navBgVal = v; applyNavBg(v, true); uiNavBg.set(v);
  }
  function toggleSidebarCollapsed() {
    sidebarCollapsed = !sidebarCollapsed;
    applySidebarCollapsed(sidebarCollapsed, true);
    uiSidebarCollapsed.set(sidebarCollapsed);
  }
  function setSidebarMargin(v: number) {
    sidebarMargin = v; applySidebarMargin(v, true); uiSidebarMargin.set(v);
  }
  function setSidebarSize(v: number) {
    sidebarSize = v; applySidebarSize(v, true); uiSidebarSize.set(v);
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
  function setMnavIconSize(v: number) {
    mnavIconSize = v; applyMnavIconSize(v, true); uiMnavIconSize.set(v);
  }
  function setMnavIconBox(v: number) {
    mnavIconBox = v; applyMnavIconBox(v, true); uiMnavIconBox.set(v);
  }
  function setMnavLabelSize(v: number) {
    mnavLabelSize = v; applyMnavLabelSize(v, true); uiMnavLabelSize.set(v);
  }
  function setMnavLabelGap(v: number) {
    mnavLabelGap = v; applyMnavLabelGap(v, true); uiMnavLabelGap.set(v);
  }
  function setMnavHeight(v: number) {
    mnavHeight = v; applyMnavHeight(v, true); uiMnavHeight.set(v);
  }
  function toggleMnavLabels() {
    mnavLabels = !mnavLabels; applyMnavLabels(mnavLabels, true); uiMnavLabels.set(mnavLabels);
  }
  function setMnavItemRadius(mode: MnavItemRadius) {
    mnavItemRadius = mode; applyMnavItemRadius(mode, true); uiMnavItemRadius.set(mode);
  }

  function moveTab(i: number, dir: -1 | 1) {
    const arr = [...$tabOrder];
    const j = i + dir;
    if (j < 0 || j >= arr.length) return;
    [arr[i], arr[j]] = [arr[j], arr[i]];
    setTabOrder(arr);
  }

  function formatVmin(v: number): string {
    return `${v.toFixed(1)}vmin`;
  }
</script>

<div class="tab-panel">
  <h2 class="section-title">{$t('settings.subsecDock')}</h2>

  <div class="settings-group">
    <div class="group-label">{$t('settings.dockCore')}</div>
    <div class="group-card">
      <div class="setting-row">
        <span class="setting-label">{$t('settings.dockModeLabel')}</span>
        {#if isDesktop}
          <div class="navstyle-picker">
            <button
              class="navstyle-card"
              class:active={desktopNavVal === 'sidebar'}
              use:ripple
              onclick={() => setDesktopNav('sidebar')}
              aria-pressed={desktopNavVal === 'sidebar'}
            >
              <span class="navstyle-preview navstyle-preview--leftbar"><span></span><span></span><span></span></span>
              <span class="navstyle-label">{$t('settings.desktopNavSidebar')}</span>
            </button>
            <button
              class="navstyle-card"
              class:active={desktopNavVal === 'dock'}
              use:ripple
              onclick={() => setDesktopNav('dock')}
              aria-pressed={desktopNavVal === 'dock'}
            >
              <span class="navstyle-preview navstyle-preview--dock"><span></span><span></span><span></span><span></span></span>
              <span class="navstyle-label">{$t('settings.desktopNavDock')}</span>
            </button>
          </div>
        {:else}
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
        {/if}
      </div>

      <div class="setting-row">
        <span class="setting-label">{$t('settings.dockColor')}</span>
        <div class="navstyle-picker">
          {#each NAV_BG_OPTIONS as opt (opt.value)}
            <button
              class="navstyle-card"
              class:active={navBgVal === opt.value}
              use:ripple
              onclick={() => setNavBg(opt.value)}
              aria-pressed={navBgVal === opt.value}
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

      <div class="setting-row">
        <span class="setting-label">{$t('settings.dockIndicator')}</span>
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
          <button
            class="navstyle-card"
            class:active={navIndicatorVal === 'none'}
            use:ripple
            onclick={() => setNavIndicator('none')}
            aria-pressed={navIndicatorVal === 'none'}
          >
            <span class="navstyle-preview navstyle-preview--none"><span></span><span></span><span></span></span>
            <span class="navstyle-label">{$t('settings.navIndicatorNone')}</span>
          </button>
        </div>
      </div>

      {#if !isDesktop}
        <SettingsToggle label={$t('settings.frostedGlass')} checked={glassVal} onClick={toggleGlass} />
      {/if}
    </div>
  </div>

  {#if isDesktop}
    {#if desktopNavVal === 'sidebar'}
      <div class="settings-group">
        <div class="group-label">{$t('settings.dockSidebarGroup')}</div>
        <div class="group-card">
          <SettingsToggle label={$t('settings.collapseSidebar')} checked={sidebarCollapsed} onClick={toggleSidebarCollapsed} />
          <SettingsSlider
            label={$t('settings.sidebarMargin')}
            value={sidebarMargin}
            min={SIDEBAR_MARGIN_MIN}
            max={SIDEBAR_MARGIN_MAX}
            step={0.0625}
            onInput={setSidebarMargin}
            format={(v) => `${v.toFixed(2)}rem`}
            hint={$t('settings.sidebarMarginHint')}
          />
          <SettingsSlider
            label={$t('settings.sidebarSize')}
            value={sidebarSize}
            min={SIDEBAR_SIZE_MIN}
            max={SIDEBAR_SIZE_MAX}
            step={0.0625}
            onInput={setSidebarSize}
            format={(v) => `${v.toFixed(2)}rem`}
            hint={$t('settings.sidebarSizeHint')}
          />
        </div>
      </div>
    {:else}
      <div class="settings-group">
        <div class="group-label">{$t('settings.dockFloatingGroup')}</div>
        <div class="group-card">
          <SettingsToggle label={$t('settings.frostedGlass')} checked={glassVal} onClick={toggleGlass} />
          <SettingsSlider
            label={$t('settings.dockWidth')}
            value={dockWidth}
            min={DOCK_WIDTH_MIN}
            max={DOCK_WIDTH_MAX}
            step={0.5}
            onInput={setDockWidth}
            format={formatVmin}
          />
          <SettingsSlider
            label={$t('settings.dockHeight')}
            value={dockHeight}
            min={DOCK_HEIGHT_MIN}
            max={DOCK_HEIGHT_MAX}
            step={5}
            onInput={setDockHeight}
            format={(v) => (v === 0 ? $t('settings.dockHeightAuto') : `${v}%`)}
            hint={$t('settings.dockHeightHint')}
          />
          <SettingsSlider
            label={$t('settings.dockRadius')}
            value={dockRadius}
            min={DOCK_RADIUS_MIN}
            max={DOCK_RADIUS_MAX}
            step={1}
            onInput={setDockRadius}
            format={(v) => `${v}%`}
          />
        </div>
      </div>
      <div class="settings-group">
        <div class="group-label">{$t('settings.dockExtrasGroup')}</div>
        <div class="group-card">
          <SettingsSlider
            label={$t('settings.dockPad')}
            value={dockPad}
            min={DOCK_PAD_MIN}
            max={DOCK_PAD_MAX}
            step={1}
            onInput={setDockPad}
            format={(v) => `${v}%`}
          />
          <SettingsSlider
            label={$t('settings.dockInset')}
            value={dockInset}
            min={DOCK_INSET_MIN}
            max={DOCK_INSET_MAX}
            step={0.5}
            onInput={setDockInset}
            format={formatVmin}
          />
          <SettingsSlider
            label={$t('settings.dockSpacing')}
            value={dockSpacing}
            min={DOCK_SPACING_MIN}
            max={DOCK_SPACING_MAX}
            step={5}
            onInput={setDockSpacing}
            format={(v) => `${v}%`}
          />
          <SettingsSlider
            label={$t('settings.dockShadow')}
            value={dockShadow}
            min={DOCK_SHADOW_MIN}
            max={DOCK_SHADOW_MAX}
            step={5}
            onInput={setDockShadow}
            format={(v) => `${v}%`}
          />
          <p class="row-hint">{$t('settings.dockHint')}</p>
        </div>
      </div>
    {/if}
  {:else}
    {#if navStyleVal === 'deck'}
      <div class="settings-group">
        <div class="group-label">{$t('settings.dockDeckGroup')}</div>
        <div class="group-card">
          <SettingsSlider
            label={$t('settings.deckWidth')}
            value={deckWidth}
            min={DECK_WIDTH_PCT_MIN}
            max={DECK_WIDTH_PCT_MAX}
            step={1}
            onInput={setDeckWidth}
            format={(v) => `${v}%`}
          />
          <SettingsSlider
            label={$t('settings.deckHeight')}
            value={deckHeight}
            min={DECK_HEIGHT_VW_MIN}
            max={DECK_HEIGHT_VW_MAX}
            step={0.5}
            onInput={setDeckHeight}
            format={(v) => `${v}%`}
          />
          <SettingsSlider
            label={$t('settings.deckRadius')}
            value={deckRadius}
            min={DECK_RADIUS_PCT_MIN}
            max={DECK_RADIUS_PCT_MAX}
            step={1}
            onInput={setDeckRadius}
            format={(v) => `${v}%`}
          />
          <p class="row-hint">{$t('settings.mnavDeckHint')}</p>
        </div>
      </div>
    {:else}
      <div class="settings-group">
        <div class="group-label">{$t('settings.dockBarGroup')}</div>
        <div class="group-card">
          <SettingsToggle
            label={$t('settings.mnavShowLabels')}
            desc={$t('settings.mnavShowLabelsHint')}
            checked={mnavLabels}
            onClick={toggleMnavLabels}
          />
          <SettingsSlider
            label={$t('settings.mnavHeight')}
            value={mnavHeight}
            min={MNAV_HEIGHT_MIN}
            max={MNAV_HEIGHT_MAX}
            step={1}
            onInput={setMnavHeight}
            format={(v) => `${v}px`}
            hint={$t('settings.mnavHeightHint')}
          />
          <SettingsSlider
            label={$t('settings.mnavIconSize')}
            value={mnavIconSize}
            min={MNAV_ICON_SIZE_MIN}
            max={MNAV_ICON_SIZE_MAX}
            step={1}
            onInput={setMnavIconSize}
            format={(v) => `${v}px`}
            hint={$t('settings.mnavIconSizeHint')}
          />
          <SettingsSlider
            label={$t('settings.mnavIconBox')}
            value={mnavIconBox}
            min={MNAV_ICON_BOX_MIN}
            max={MNAV_ICON_BOX_MAX}
            step={1}
            onInput={setMnavIconBox}
            format={(v) => `${v}px`}
            hint={$t('settings.mnavIconBoxHint')}
          />
          <SettingsSlider
            label={$t('settings.mnavLabelSize')}
            value={mnavLabelSize}
            min={MNAV_LABEL_SIZE_MIN}
            max={MNAV_LABEL_SIZE_MAX}
            step={0.5}
            onInput={setMnavLabelSize}
            format={(v) => `${v}px`}
            hint={$t('settings.mnavLabelSizeHint')}
          />
          <SettingsSlider
            label={$t('settings.mnavLabelGap')}
            value={mnavLabelGap}
            min={MNAV_LABEL_GAP_MIN}
            max={MNAV_LABEL_GAP_MAX}
            step={1}
            onInput={setMnavLabelGap}
            format={(v) => `${v}px`}
          />
          <div class="setting-row">
            <span class="setting-label">{$t('settings.mnavItemRadius')}</span>
            <div class="picker-wrap density-picker">
              <button
                class="density-btn"
                class:active={mnavItemRadius === 'theme'}
                use:ripple
                onclick={() => setMnavItemRadius('theme')}
                aria-pressed={mnavItemRadius === 'theme'}
              >
                {$t('settings.mnavItemRadiusTheme')}
              </button>
              <button
                class="density-btn"
                class:active={mnavItemRadius === 'round'}
                use:ripple
                onclick={() => setMnavItemRadius('round')}
                aria-pressed={mnavItemRadius === 'round'}
              >
                {$t('settings.mnavItemRadiusRound')}
              </button>
              <button
                class="density-btn"
                class:active={mnavItemRadius === 'square'}
                use:ripple
                onclick={() => setMnavItemRadius('square')}
                aria-pressed={mnavItemRadius === 'square'}
              >
                {$t('settings.mnavItemRadiusSquare')}
              </button>
            </div>
          </div>
        </div>
      </div>
    {/if}
  {/if}

  <PreviewFrame label={$t('settings.preview')}>
    <DockPreview device={isDesktop ? 'desktop' : 'mobile'} mode={isDesktop ? desktopNavVal : navStyleVal} />
  </PreviewFrame>

  <div class="settings-group">
    <div class="group-label">{$t('settings.tabOrder')}</div>
    <div class="taborder-list">
      {#each $tabOrder as id, i (id)}
        {@const TabIcon = TAB_DEFS[id].icon}
        <div class="taborder-row" class:first={i === 0} class:last={i === $tabOrder.length - 1}>
          <span class="taborder-icon"><TabIcon size={18} strokeWidth={1.8} /></span>
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
</div>
