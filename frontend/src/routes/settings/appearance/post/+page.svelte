<script lang="ts">
  import '$lib/components/settings/settings.css';
  import { onMount } from 'svelte';
  import { t } from 'svelte-i18n';
  import SettingsToggle from '$lib/components/settings/SettingsToggle.svelte';
  import SettingsSlider from '$lib/components/settings/SettingsSlider.svelte';
  import SettingsPicker from '$lib/components/settings/SettingsPicker.svelte';
  import PostCard from '$lib/components/PostCard.svelte';
  import PreviewFrame from '$lib/components/settings/preview/PreviewFrame.svelte';
  import { MOCK_POST } from '$lib/components/settings/preview/previewMocks';
  import { ripple } from '$lib/actions/ripple';
  import {
    applyFont,
    getSavedFont,
    applyCoverAlign,
    FONT_LIST,
    FONT_LABELS,
  } from '$lib/utils/appearance';
  import { MODE_PRESETS, getSavedDesignMode, hasCustomFont } from '$lib/stores/designMode';
  import {
    applyDescLines,
    applyTitleBold,
    applyTitleSize,
    applyDescSize,
    applyDensity,
    getSavedDensity,
    applyCoverFit,
    applyCoverMaxWidth,
    applyCoverMaxHeight,
    applyCoverRadius,
    getSavedTitleSize,
    getSavedDescSize,
    POSTCARD_PREFS,
    type Density,
    type CoverAlign,
  } from '$lib/utils/appearance';
  import {
    showCoverImages,
    postcardDescLines,
    postcardTitleBold,
    showRecommendationScore,
    feedDensity,
    coverImagePosition,
    coverImageFit,
    coverImageMaxWidth,
    coverImageMaxHeight,
    coverImageRadius,
    coverImageAlign,
  } from '$lib/stores/preferences';

  const FONT_OPTIONS = FONT_LIST.map((f) => ({
    value: f.name,
    label: FONT_LABELS[f.name] ?? f.name,
    category: f.category === 'serif' ? 'serif' : 'sans',
  }));

  let postTitleFont = $state<string>(MODE_PRESETS[getSavedDesignMode()].fonts['post-title']);
  let bodyFont = $state<string>(MODE_PRESETS[getSavedDesignMode()].fonts['article-body']);
  let titleFontCustom = $state<boolean>(false);
  let bodyFontCustom = $state<boolean>(false);
  let showCover = $state<boolean>(showCoverImages.getEnabled());
  let scoreOn = $state<boolean>(showRecommendationScore.getValue());
  let descLines = $state<number>(POSTCARD_PREFS.descLines.default);
  let titleBold = $state<boolean>(POSTCARD_PREFS.titleBold.default);
  let titleSizeVal = $state<number>(getSavedTitleSize());
  let descSizeVal = $state<number>(getSavedDescSize());
  let density = $state<Density>('comfortable');
  let coverPos = $state<'right' | 'bottom'>('bottom');
  let coverFitVal = $state<'fill' | 'proportions'>('fill');
  let coverMaxWVal = $state<number>(POSTCARD_PREFS.coverMaxW.default);
  let coverMaxHVal = $state<number>(POSTCARD_PREFS.coverMaxH.default);
  let coverRadiusVal = $state<number>(POSTCARD_PREFS.coverRadius.default);
  let coverAlignVal = $state<CoverAlign>('center');

  onMount(() => {
    const mode = getSavedDesignMode();
    titleFontCustom = hasCustomFont('post-title');
    bodyFontCustom = hasCustomFont('article-body');
    postTitleFont = titleFontCustom ? getSavedFont('post-title') : MODE_PRESETS[mode].fonts['post-title'];
    bodyFont = bodyFontCustom ? getSavedFont('article-body') : MODE_PRESETS[mode].fonts['article-body'];
    showCover = showCoverImages.getEnabled();
    scoreOn = showRecommendationScore.getValue();
    descLines = postcardDescLines.getValue();
    titleBold = postcardTitleBold.getValue();
    density = getSavedDensity();
    coverPos = coverImagePosition.getPosition();
    coverFitVal = coverImageFit.getValue();
    coverMaxWVal = coverImageMaxWidth.getValue();
    coverMaxHVal = coverImageMaxHeight.getValue();
    coverRadiusVal = coverImageRadius.getValue();
    coverAlignVal = coverImageAlign.getValue();
  });

  function selectPostTitleFont(fontName: string) {
    applyFont('post-title', fontName, true);
    postTitleFont = fontName;
    titleFontCustom = true;
  }
  function selectBodyFont(fontName: string) {
    applyFont('article-body', fontName, true);
    bodyFont = fontName;
    bodyFontCustom = true;
  }

  /* Value shown in the dropdown trigger marks design-mode defaults as auto. */
  function fontTrigger(name: string, custom: boolean): string {
    const label = FONT_LABELS[name] ?? name;
    return custom ? label : `${label} ${$t('settings.fontAutoSuffix')}`;
  }
  function toggleShowCover() {
    showCover = !showCover;
    showCoverImages.setEnabled(showCover);
  }
  function toggleScore() {
    scoreOn = !scoreOn;
    showRecommendationScore.setValue(scoreOn);
  }
  function setDescLines(v: number) {
    descLines = v;
    applyDescLines(v, true);
    postcardDescLines.setValue(v);
  }
  function toggleTitleBold() {
    titleBold = !titleBold;
    applyTitleBold(titleBold, true);
    postcardTitleBold.setValue(titleBold);
  }
  function setTitleSize(v: number) {
    titleSizeVal = v;
    applyTitleSize(v, true);
  }
  function setDescSize(v: number) {
    descSizeVal = v;
    applyDescSize(v, true);
  }
  function setDensity(d: Density) {
    density = d;
    applyDensity(d, true);
    feedDensity.setValue(d);
  }
  function selectCoverPos(pos: 'right' | 'bottom') {
    coverPos = pos;
    coverImagePosition.setPosition(pos);
  }
  function setCoverFit(mode: 'fill' | 'proportions') {
    coverFitVal = mode;
    coverImageFit.setValue(mode);
    applyCoverFit(mode, true);
  }
  function setCoverMaxW(v: number) {
    coverMaxWVal = v;
    applyCoverMaxWidth(v, true);
    coverImageMaxWidth.setValue(v);
  }
  function setCoverMaxH(v: number) {
    coverMaxHVal = v;
    applyCoverMaxHeight(v, true);
    coverImageMaxHeight.setValue(v);
  }
  function setCoverRadius(v: number) {
    coverRadiusVal = v;
    applyCoverRadius(v, true);
    coverImageRadius.setValue(v);
  }
  function setCoverAlign(v: CoverAlign) {
    coverAlignVal = v;
    applyCoverAlign(v, true);
    coverImageAlign.setValue(v);
  }
</script>

<div class="tab-panel">
  <h2 class="section-title">{$t('settings.subsecPost')}</h2>

  <div class="settings-group">
    <div class="group-label">{$t('settings.sectionPostcards')}</div>
    <div class="group-card">
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

      <div class="setting-row">
        <span class="setting-label">{$t('settings.postTitleFont')}</span>
        <SettingsPicker
          value={postTitleFont}
          options={FONT_OPTIONS}
          onSelect={selectPostTitleFont}
          trigger={fontTrigger(postTitleFont, titleFontCustom)}
          fontList
        />
      </div>

      <div class="setting-row">
        <span class="setting-label">{$t('settings.articleBodyFont')}</span>
        <SettingsPicker
          value={bodyFont}
          options={FONT_OPTIONS}
          onSelect={selectBodyFont}
          trigger={fontTrigger(bodyFont, bodyFontCustom)}
          fontList
        />
      </div>

      <SettingsToggle label={$t('settings.showCoverImages')} checked={showCover} onClick={toggleShowCover} />

      <SettingsToggle label={$t('settings.showRecommendationScore')} checked={scoreOn} onClick={toggleScore} />

      {#if showCover}
        <div class="setting-row">
          <span class="setting-label">{$t('settings.coverImagePosition')}</span>
          <SettingsPicker
            value={coverPos}
            options={[
              { value: 'right', labelKey: 'settings.coverImagePositionRight' },
              { value: 'bottom', labelKey: 'settings.coverImagePositionBottom' },
            ]}
            onSelect={(v) => selectCoverPos(v as 'right' | 'bottom')}
            trigger={coverPos === 'right' ? $t('settings.coverImagePositionRight') : $t('settings.coverImagePositionBottom')}
          />
        </div>

        <div class="setting-row">
          <span class="setting-label">{$t('settings.coverImageFit')}</span>
          <div class="picker-wrap density-picker">
            <button
              class="density-btn"
              class:active={coverFitVal === 'fill'}
              use:ripple
              onclick={() => setCoverFit('fill')}
              aria-pressed={coverFitVal === 'fill'}
            >
              {$t('settings.coverFitFill')}
            </button>
            <button
              class="density-btn"
              class:active={coverFitVal === 'proportions'}
              use:ripple
              onclick={() => setCoverFit('proportions')}
              aria-pressed={coverFitVal === 'proportions'}
            >
              {$t('settings.coverFitProportions')}
            </button>
          </div>
        </div>

        {#if coverFitVal === 'fill'}
          <SettingsSlider
            label={$t('settings.coverMaxWidth')}
            value={coverMaxWVal}
            min={POSTCARD_PREFS.coverMaxW.min}
            max={POSTCARD_PREFS.coverMaxW.max}
            step={POSTCARD_PREFS.coverMaxW.step}
            onInput={setCoverMaxW}
            format={(v) => `${v.toFixed(2)}rem`}
          />
          <SettingsSlider
            label={$t('settings.coverMaxHeight')}
            value={coverMaxHVal}
            min={POSTCARD_PREFS.coverMaxH.min}
            max={POSTCARD_PREFS.coverMaxH.max}
            step={POSTCARD_PREFS.coverMaxH.step}
            onInput={setCoverMaxH}
            format={(v) => `${v.toFixed(2)}rem`}
          />
        {/if}

        <SettingsSlider
          label={$t('settings.coverImageRadius')}
          value={coverRadiusVal}
          min={POSTCARD_PREFS.coverRadius.min}
          max={POSTCARD_PREFS.coverRadius.max}
          step={POSTCARD_PREFS.coverRadius.step}
          onInput={setCoverRadius}
          format={(v) => (v === 0 ? $t('settings.imageRadiusAuto') : `${v.toFixed(2)}rem`)}
        />

        <div class="setting-row">
          <span class="setting-label">{$t('settings.coverImageAlign')}</span>
          <div class="picker-wrap density-picker">
            <button class="density-btn" class:active={coverAlignVal === 'left'} use:ripple onclick={() => setCoverAlign('left')} aria-pressed={coverAlignVal === 'left'}>
              {$t('settings.textAlignLeft')}
            </button>
            <button class="density-btn" class:active={coverAlignVal === 'center'} use:ripple onclick={() => setCoverAlign('center')} aria-pressed={coverAlignVal === 'center'}>
              {$t('settings.textAlignCenter')}
            </button>
            <button class="density-btn" class:active={coverAlignVal === 'right'} use:ripple onclick={() => setCoverAlign('right')} aria-pressed={coverAlignVal === 'right'}>
              {$t('settings.textAlignRight')}
            </button>
          </div>
        </div>
      {/if}

      <SettingsSlider
        label={$t('settings.descLines')}
        value={descLines}
        min={POSTCARD_PREFS.descLines.min}
        max={POSTCARD_PREFS.descLines.max}
        step={POSTCARD_PREFS.descLines.step}
        onInput={setDescLines}
        format={(v) => (v === 0 ? $t('settings.descLinesHidden') : String(v))}
      />

      <SettingsToggle label={$t('settings.boldTitle')} checked={titleBold} onClick={toggleTitleBold} />

      <SettingsSlider
        label={$t('settings.cardTitleSize')}
        value={titleSizeVal}
        min={POSTCARD_PREFS.titleSize.min}
        max={POSTCARD_PREFS.titleSize.max}
        step={POSTCARD_PREFS.titleSize.step}
        onInput={setTitleSize}
        format={(v) => `${v}%`}
      />

      <SettingsSlider
        label={$t('settings.cardDescSize')}
        value={descSizeVal}
        min={POSTCARD_PREFS.descSize.min}
        max={POSTCARD_PREFS.descSize.max}
        step={POSTCARD_PREFS.descSize.step}
        onInput={setDescSize}
        format={(v) => `${v}%`}
      />
    </div>
  </div>

  <PreviewFrame label={$t('settings.preview')}>
    <div class="postcard-stage">
      <PostCard item={MOCK_POST} />
    </div>
  </PreviewFrame>
</div>

<style>
  .postcard-stage {
    max-width: 30rem;
  }
</style>
