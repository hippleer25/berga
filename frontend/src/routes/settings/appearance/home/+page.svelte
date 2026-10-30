<script lang="ts">
  import '$lib/components/settings/settings.css';
  import { onMount } from 'svelte';
  import { t } from 'svelte-i18n';
  import SettingsToggle from '$lib/components/settings/SettingsToggle.svelte';
  import SettingsSlider from '$lib/components/settings/SettingsSlider.svelte';
  import SettingsPicker from '$lib/components/settings/SettingsPicker.svelte';
  import HomePreview from '$lib/components/settings/preview/HomePreview.svelte';
  import PreviewFrame from '$lib/components/settings/preview/PreviewFrame.svelte';
  import { ripple } from '$lib/actions/ripple';
  import {
    applyFont,
    getSavedFont,
    FONT_LIST,
    FONT_LABELS,
  } from '$lib/utils/appearance';
  import {
    uiWelcomeStyle,
    getSavedWelcomeStyle,
    applyWelcomeStyle,
    uiWelcomeSpace,
    getSavedWelcomeSpace,
    applyWelcomeSpace,
    uiChipIcons,
    getSavedChipIcons,
    applyChipIcons,
    WELCOME_SPACE_MIN,
    WELCOME_SPACE_MAX,
    type WelcomeStyle,
  } from '$lib/stores/uiPrefs';
  import { MODE_PRESETS, getSavedDesignMode, hasCustomFont } from '$lib/stores/designMode';

  const WELCOME_STYLE_OPTIONS: { value: WelcomeStyle; labelKey: string }[] = [
    { value: 'regular', labelKey: 'settings.welcomeStyleRegular' },
    { value: 'normal', labelKey: 'settings.welcomeStyleNormal' },
    { value: 'bold', labelKey: 'settings.welcomeStyleBold' },
    { value: 'italic', labelKey: 'settings.welcomeStyleItalic' },
  ];

  const FONT_OPTIONS = FONT_LIST.map((f) => ({
    value: f.name,
    label: FONT_LABELS[f.name] ?? f.name,
    category: f.category === 'serif' ? 'serif' : 'sans',
  }));

  let titleFont = $state<string>(MODE_PRESETS[getSavedDesignMode()].fonts['page-title']);
  let titleFontCustom = $state<boolean>(false);
  let welcomeStyleVal = $state<WelcomeStyle>(getSavedWelcomeStyle());
  let welcomeSpace = $state<number>(getSavedWelcomeSpace());
  let chipIcons = $state<boolean>(getSavedChipIcons());

  onMount(() => {
    titleFontCustom = hasCustomFont('page-title');
    titleFont = titleFontCustom ? getSavedFont('page-title') : MODE_PRESETS[getSavedDesignMode()].fonts['page-title'];
  });

  function setWelcomeStyle(s: WelcomeStyle) {
    welcomeStyleVal = s;
    applyWelcomeStyle(s, true);
    uiWelcomeStyle.set(s);
  }
  function setWelcomeSpace(v: number) {
    welcomeSpace = v;
    applyWelcomeSpace(v, true);
    uiWelcomeSpace.set(v);
  }
  function toggleChipIcons() {
    chipIcons = !chipIcons;
    applyChipIcons(chipIcons, true);
    uiChipIcons.set(chipIcons);
  }
  function selectTitleFont(fontName: string) {
    applyFont('page-title', fontName, true);
    titleFont = fontName;
    titleFontCustom = true;
  }

  /* Value shown in the dropdown trigger marks design-mode defaults as auto. */
  function fontTrigger(name: string, custom: boolean): string {
    const label = FONT_LABELS[name] ?? name;
    return custom ? label : `${label} ${$t('settings.fontAutoSuffix')}`;
  }
</script>

<div class="tab-panel">
  <h2 class="section-title">{$t('settings.subsecHome')}</h2>

  <div class="settings-group">
    <div class="group-label">{$t('settings.homeTypographyGroup')}</div>
    <div class="group-card">
      <div class="setting-row">
        <span class="setting-label">{$t('settings.pageTitleFont')}</span>
        <SettingsPicker
          value={titleFont}
          options={FONT_OPTIONS}
          onSelect={selectTitleFont}
          trigger={fontTrigger(titleFont, titleFontCustom)}
          fontList
        />
      </div>

      <div class="setting-row">
        <span class="setting-label">{$t('settings.welcomeStyle')}</span>
        <div class="navstyle-picker">
          {#each WELCOME_STYLE_OPTIONS as opt (opt.value)}
            <button
              class="navstyle-card"
              class:active={welcomeStyleVal === opt.value}
              use:ripple
              onclick={() => setWelcomeStyle(opt.value)}
              aria-pressed={welcomeStyleVal === opt.value}
            >
              <span class="welcome-style-swatch" data-style={opt.value}>Aa</span>
              <span class="navstyle-label">{$t(opt.labelKey)}</span>
            </button>
          {/each}
        </div>
      </div>

      <SettingsSlider
        label={$t('settings.welcomeSpace')}
        value={welcomeSpace}
        min={WELCOME_SPACE_MIN}
        max={WELCOME_SPACE_MAX}
        step={0.25}
        onInput={setWelcomeSpace}
        format={(v) => `${v.toFixed(2)}rem`}
        hint={$t('settings.welcomeSpaceHint')}
      />

      <SettingsToggle label={$t('settings.chipIcons')} checked={chipIcons} onClick={toggleChipIcons} />
    </div>
  </div>

  <PreviewFrame label={$t('settings.preview')}>
    <HomePreview />
  </PreviewFrame>
</div>
