<script lang="ts">
  import '$lib/components/settings/settings.css';
  import { onMount } from 'svelte';
  import { t } from 'svelte-i18n';
  import SettingsPicker from '$lib/components/settings/SettingsPicker.svelte';
  import SettingsSlider from '$lib/components/settings/SettingsSlider.svelte';
  import ArticlePreview from '$lib/components/settings/preview/ArticlePreview.svelte';
  import PreviewFrame from '$lib/components/settings/preview/PreviewFrame.svelte';
  import { ripple } from '$lib/actions/ripple';
  import {
    applyFont,
    getSavedFont,
    applyFontSize,
    applyFontWeight,
    applyLetterSpacing,
    applyLineHeight,
    applyArticleMaxWidth,
    applyArticleTitleMaxWidth,
    applyArticleImageWidth,
    snapFontWeight,
    ARTICLE_TYPOGRAPHY,
    FONT_LIST,
    FONT_LABELS,
  } from '$lib/utils/appearance';
  import type { TextAlign } from '$lib/stores/preferences';
  import { MODE_PRESETS, getSavedDesignMode, hasCustomFont } from '$lib/stores/designMode';
  import {
    articleFontSize,
    articleFontWeight,
    articleLetterSpacing,
    articleLineHeight,
    articleMaxWidth,
    articleTitleMaxWidth,
    articleImageWidth,
    titleTextAlign,
    bodyTextAlign,
  } from '$lib/stores/preferences';

  const FONT_OPTIONS = FONT_LIST.map((f) => ({
    value: f.name,
    label: FONT_LABELS[f.name] ?? f.name,
    category: f.category === 'serif' ? 'serif' : 'sans',
  }));

  const ALIGN_OPTIONS = ['left', 'justify', 'center', 'right'] as const;

  let bodyFont = $state<string>(MODE_PRESETS[getSavedDesignMode()].fonts['article-body']);
  let bodyFontCustom = $state<boolean>(false);
  let fontSize = $state<number>(ARTICLE_TYPOGRAPHY.fontSize.default);
  let fontWeight = $state<number>(ARTICLE_TYPOGRAPHY.fontWeight.default);
  let letterSpacing = $state<number>(ARTICLE_TYPOGRAPHY.letterSpacing.default);
  let lineHeight = $state<number>(ARTICLE_TYPOGRAPHY.lineHeight.default);
  let articleMaxW = $state<number>(ARTICLE_TYPOGRAPHY.maxWidth.default);
  let articleTitleMaxW = $state<number>(ARTICLE_TYPOGRAPHY.titleMaxWidth.default);
  let imageWidth = $state<number>(ARTICLE_TYPOGRAPHY.imageWidth.default);
  let titlePos = $state<TextAlign>('left');
  let bodyPos = $state<TextAlign>('justify');

  onMount(() => {
    const mode = getSavedDesignMode();
    bodyFontCustom = hasCustomFont('article-body');
    bodyFont = bodyFontCustom ? getSavedFont('article-body') : MODE_PRESETS[mode].fonts['article-body'];
    fontSize = articleFontSize.getValue();
    fontWeight = snapFontWeight(bodyFont, articleFontWeight.getValue());
    letterSpacing = articleLetterSpacing.getValue();
    lineHeight = articleLineHeight.getValue();
    articleMaxW = articleMaxWidth.getValue();
    articleTitleMaxW = articleTitleMaxWidth.getValue();
    imageWidth = articleImageWidth.getValue();
    titlePos = titleTextAlign.getPosition();
    bodyPos = bodyTextAlign.getPosition();
  });

  function fmtRem(v: number): string {
    return `${v.toFixed(2)}rem · ${(v * 16).toFixed(0)}px`;
  }

  function selectBodyFont(fontName: string) {
    applyFont('article-body', fontName, true);
    bodyFont = fontName;
    bodyFontCustom = true;
    const snapped = snapFontWeight(fontName, fontWeight);
    if (snapped !== fontWeight) {
      fontWeight = snapped;
      applyFontWeight(snapped, true);
      articleFontWeight.setValue(snapped);
    }
  }

  /* Value shown in the dropdown trigger marks design-mode defaults as auto. */
  function fontTrigger(name: string, custom: boolean): string {
    const label = FONT_LABELS[name] ?? name;
    return custom ? label : `${label} ${$t('settings.fontAutoSuffix')}`;
  }
  function setFontSize(v: number) {
    fontSize = v;
    applyFontSize(v, true);
    articleFontSize.setValue(v);
  }
  function setFontWeight(v: number) {
    const snapped = snapFontWeight(bodyFont, v);
    fontWeight = snapped;
    applyFontWeight(snapped, true);
    articleFontWeight.setValue(snapped);
  }
  function setLetterSpacing(v: number) {
    letterSpacing = v;
    applyLetterSpacing(v, true);
    articleLetterSpacing.setValue(v);
  }
  function setLineHeight(v: number) {
    lineHeight = v;
    applyLineHeight(v, true);
    articleLineHeight.setValue(v);
  }
  function setArticleMaxWidth(v: number) {
    articleMaxW = v;
    applyArticleMaxWidth(v, true);
    articleMaxWidth.setValue(v);
  }
  function setArticleTitleMaxWidth(v: number) {
    articleTitleMaxW = v;
    applyArticleTitleMaxWidth(v, true);
    articleTitleMaxWidth.setValue(v);
  }
  function setImageWidth(v: number) {
    imageWidth = v;
    applyArticleImageWidth(v, true);
    articleImageWidth.setValue(v);
  }
  function selectTitleAlign(pos: TextAlign) {
    titlePos = pos;
    titleTextAlign.setPosition(pos);
  }
  function selectBodyAlign(pos: TextAlign) {
    bodyPos = pos;
    bodyTextAlign.setPosition(pos);
  }

  function alignLabel(pos: TextAlign): string {
    switch (pos) {
      case 'left': return $t('settings.textAlignLeft');
      case 'justify': return $t('settings.textAlignJustified');
      case 'center': return $t('settings.textAlignCenter');
      default: return $t('settings.textAlignRight');
    }
  }
</script>

<div class="tab-panel">
  <h2 class="section-title">{$t('settings.subsecArticles')}</h2>

  <div class="settings-group">
    <div class="group-label">{$t('settings.articlesTypographyGroup')}</div>
    <div class="group-card">
      <div class="setting-row">
        <span class="setting-label">{$t('settings.postTitleFont')}</span>
        <SettingsPicker
          value={bodyFont}
          options={FONT_OPTIONS}
          onSelect={selectBodyFont}
          trigger={fontTrigger(bodyFont, bodyFontCustom)}
          fontList
        />
      </div>

      <SettingsSlider
        label={$t('settings.fontSize')}
        value={fontSize}
        min={ARTICLE_TYPOGRAPHY.fontSize.min}
        max={ARTICLE_TYPOGRAPHY.fontSize.max}
        step={ARTICLE_TYPOGRAPHY.fontSize.step}
        onInput={setFontSize}
        format={fmtRem}
      />

      <SettingsSlider
        label={$t('settings.fontWeight')}
        value={fontWeight}
        min={ARTICLE_TYPOGRAPHY.fontWeight.min}
        max={ARTICLE_TYPOGRAPHY.fontWeight.max}
        step={ARTICLE_TYPOGRAPHY.fontWeight.step}
        onInput={setFontWeight}
        format={(v) => `${v}`}
      />

      <SettingsSlider
        label={$t('settings.letterSpacing')}
        value={letterSpacing}
        min={ARTICLE_TYPOGRAPHY.letterSpacing.min}
        max={ARTICLE_TYPOGRAPHY.letterSpacing.max}
        step={ARTICLE_TYPOGRAPHY.letterSpacing.step}
        onInput={setLetterSpacing}
        format={(v) => (v === 0 ? $t('settings.normal') : `${v}em`)}
      />

      <SettingsSlider
        label={$t('settings.lineHeight')}
        value={lineHeight}
        min={ARTICLE_TYPOGRAPHY.lineHeight.min}
        max={ARTICLE_TYPOGRAPHY.lineHeight.max}
        step={ARTICLE_TYPOGRAPHY.lineHeight.step}
        onInput={setLineHeight}
        format={(v) => v.toFixed(2)}
      />
    </div>
  </div>

  <div class="settings-group">
    <div class="group-label">{$t('settings.sectionReading')}</div>
    <div class="group-card">
      <SettingsSlider
        label={$t('settings.bodyWidth')}
        value={articleMaxW}
        min={ARTICLE_TYPOGRAPHY.maxWidth.min}
        max={ARTICLE_TYPOGRAPHY.maxWidth.max}
        step={ARTICLE_TYPOGRAPHY.maxWidth.step}
        onInput={setArticleMaxWidth}
        format={(v) => `${v.toFixed(2)}rem (${(v * 16).toFixed(0)}px)`}
      />

      <SettingsSlider
        label={$t('settings.titleWidth')}
        value={articleTitleMaxW}
        min={ARTICLE_TYPOGRAPHY.titleMaxWidth.min}
        max={ARTICLE_TYPOGRAPHY.titleMaxWidth.max}
        step={ARTICLE_TYPOGRAPHY.titleMaxWidth.step}
        onInput={setArticleTitleMaxWidth}
        format={(v) => `${v.toFixed(2)}rem (${(v * 16).toFixed(0)}px)`}
      />

      <SettingsSlider
        label={$t('settings.imageWidth')}
        value={imageWidth}
        min={ARTICLE_TYPOGRAPHY.imageWidth.min}
        max={ARTICLE_TYPOGRAPHY.imageWidth.max}
        step={ARTICLE_TYPOGRAPHY.imageWidth.step}
        onInput={setImageWidth}
        format={(v) => (v === 0 ? $t('settings.imageWidthAuto') : `${v}%`)}
      />

      <div class="setting-row">
        <span class="setting-label">{$t('settings.titleTextPosition')}</span>
        <SettingsPicker
          value={titlePos as string}
          options={ALIGN_OPTIONS.map((a) => ({ value: a, labelKey: `settings.textAlign${a === 'justify' ? 'Justified' : a.charAt(0).toUpperCase() + a.slice(1)}` }))}
          onSelect={(v) => selectTitleAlign(v as TextAlign)}
          trigger={alignLabel(titlePos)}
        />
      </div>

      <div class="setting-row">
        <span class="setting-label">{$t('settings.bodyTextPosition')}</span>
        <SettingsPicker
          value={bodyPos as string}
          options={ALIGN_OPTIONS.map((a) => ({ value: a, labelKey: `settings.textAlign${a === 'justify' ? 'Justified' : a.charAt(0).toUpperCase() + a.slice(1)}` }))}
          onSelect={(v) => selectBodyAlign(v as TextAlign)}
          trigger={alignLabel(bodyPos)}
        />
      </div>
    </div>
  </div>

  <PreviewFrame label={$t('settings.preview')}>
    <ArticlePreview />
  </PreviewFrame>
</div>
