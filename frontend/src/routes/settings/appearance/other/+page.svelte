<script lang="ts">
  import '$lib/components/settings/settings.css';
  import { t } from 'svelte-i18n';
  import SettingsToggle from '$lib/components/settings/SettingsToggle.svelte';
  import SettingsSlider from '$lib/components/settings/SettingsSlider.svelte';
  import { ripple } from '$lib/actions/ripple';
  import Settings2 from '@lucide/svelte/icons/settings-2';
  import {
    uiRadiusSurface,
    uiRadiusControl,
    uiHoverRadius,
    uiButtonBorders,
    uiBorderOn,
    uiBorderWidth,
    uiBorderColor,
    uiSettingsIconPlacement,
    getSavedRadiusSurface,
    getSavedRadiusControl,
    hasSavedRadiusSurface,
    hasSavedRadiusControl,
    getSavedHoverRadius,
    getSavedButtonBorders,
    getSavedBorderOn,
    getSavedBorderWidth,
    getSavedBorderColor,
    getSavedSettingsIconPlacement,
    applyRadiusSurfaces,
    applyRadiusControls,
    applyHoverRadius,
    applyButtonBorders,
    applyBorder,
    applySettingsIconPlacement,
    RADIUS_SURFACE_MIN,
    RADIUS_SURFACE_MAX,
    RADIUS_CONTROL_MIN,
    RADIUS_CONTROL_MAX,
    HOVER_RADIUS_MIN,
    HOVER_RADIUS_MAX,
    BORDER_WIDTH_MIN,
    BORDER_WIDTH_MAX,
    type SettingsIconPlacement,
  } from '$lib/stores/uiPrefs';
  import { MODE_PRESETS, getSavedDesignMode } from '$lib/stores/designMode';

  const BORDER_COLOR_PRESETS: (string | null)[] = [
    null,
    '#F5B942',
    '#4F9CF9',
    '#4CAF7D',
    '#E5533D',
    '#9B6BF2',
    '#2DD4BF',
  ];

  let radiusSurfaceVal = $state<number>(
    hasSavedRadiusSurface() ? getSavedRadiusSurface() : MODE_PRESETS[getSavedDesignMode()].radiusSurface
  );
  let radiusControlVal = $state<number>(
    hasSavedRadiusControl() ? getSavedRadiusControl() : MODE_PRESETS[getSavedDesignMode()].radiusControl
  );
  let hoverRadiusVal = $state<number>(getSavedHoverRadius());
  let btnBorders = $state<boolean>(getSavedButtonBorders());
  let borderOn = $state<boolean>(getSavedBorderOn());
  let borderWidth = $state<number>(getSavedBorderWidth());
  let borderColor = $state<string | null>(getSavedBorderColor());
  let customBorderColor = $state<string>(getSavedBorderColor() ?? '#8f8f96');
  let settingsIconVal = $state<SettingsIconPlacement>(getSavedSettingsIconPlacement());

  function setRadiusSurface(v: number) {
    radiusSurfaceVal = v;
    applyRadiusSurfaces(v, true);
    uiRadiusSurface.set(v);
  }
  function setRadiusControl(v: number) {
    radiusControlVal = v;
    applyRadiusControls(v, true);
    uiRadiusControl.set(v);
  }
  function setHoverRadius(v: number) {
    hoverRadiusVal = v;
    applyHoverRadius(v, true);
    uiHoverRadius.set(v);
  }
  function setBtnBorders(v: boolean) {
    btnBorders = v;
    applyButtonBorders(v, true);
    uiButtonBorders.set(v);
  }
  function setBorderOn(v: boolean) {
    borderOn = v;
    applyBorder(v, borderWidth, borderColor, true);
    uiBorderOn.set(v);
  }
  function setBorderWidth(v: number) {
    borderWidth = v;
    applyBorder(borderOn, v, borderColor, true);
    uiBorderWidth.set(v);
  }
  function setBorderColor(hex: string | null) {
    borderColor = hex;
    applyBorder(borderOn, borderWidth, hex, true);
    uiBorderColor.set(hex);
    if (hex) customBorderColor = hex;
  }
  function setSettingsIcon(v: SettingsIconPlacement) {
    settingsIconVal = v;
    applySettingsIconPlacement(v, true);
    uiSettingsIconPlacement.set(v);
  }
</script>

<div class="tab-panel">
  <h2 class="section-title">{$t('settings.subsecOther')}</h2>

  <div class="settings-group">
    <div class="group-label">{$t('settings.otherShapesGroup')}</div>
    <div class="group-card">
      <SettingsSlider
        label={$t('settings.radiusSurfaces')}
        value={radiusSurfaceVal}
        min={RADIUS_SURFACE_MIN}
        max={RADIUS_SURFACE_MAX}
        step={1}
        onInput={setRadiusSurface}
        format={(v) => `${v}px`}
      />

      <SettingsSlider
        label={$t('settings.hoverRadius')}
        value={hoverRadiusVal}
        min={HOVER_RADIUS_MIN}
        max={HOVER_RADIUS_MAX}
        step={1}
        onInput={setHoverRadius}
        format={(v) => (v === 0 ? $t('settings.radiusAuto') : `${v}px`)}
        hint={$t('settings.hoverRadiusHint')}
      />

      <SettingsSlider
        label={$t('settings.radiusControls')}
        value={radiusControlVal}
        min={RADIUS_CONTROL_MIN}
        max={RADIUS_CONTROL_MAX}
        step={1}
        onInput={setRadiusControl}
        format={(v) => `${v}px`}
        hint={$t('settings.radiusHint')}
      />
    </div>
  </div>

  <div class="settings-group">
    <div class="group-label">{$t('settings.otherChromeGroup')}</div>
    <div class="group-card">
      <div class="setting-row">
        <span class="setting-label">{$t('settings.settingsIcon')}</span>
        <div class="navstyle-picker">
          <button
            class="navstyle-card"
            class:active={settingsIconVal === 'top'}
            use:ripple
            onclick={() => setSettingsIcon('top')}
            aria-pressed={settingsIconVal === 'top'}
          >
            <span class="settings-icon-swatch settings-icon-swatch--top"><Settings2 size={12} /></span>
            <span class="navstyle-label">{$t('settings.settingsIconTop')}</span>
          </button>
          <button
            class="navstyle-card"
            class:active={settingsIconVal === 'navbar'}
            use:ripple
            onclick={() => setSettingsIcon('navbar')}
            aria-pressed={settingsIconVal === 'navbar'}
          >
            <span class="settings-icon-swatch settings-icon-swatch--navbar"><Settings2 size={12} /></span>
            <span class="navstyle-label">{$t('settings.settingsIconNavbar')}</span>
          </button>
          <button
            class="navstyle-card"
            class:active={settingsIconVal === 'both'}
            use:ripple
            onclick={() => setSettingsIcon('both')}
            aria-pressed={settingsIconVal === 'both'}
          >
            <span class="settings-icon-swatch settings-icon-swatch--both"><Settings2 size={12} /><Settings2 size={12} /></span>
            <span class="navstyle-label">{$t('settings.settingsIconBoth')}</span>
          </button>
        </div>
      </div>

      <SettingsToggle
        label={$t('settings.buttonBorders')}
        desc={$t('settings.buttonBordersHint')}
        checked={btnBorders}
        onClick={() => setBtnBorders(!btnBorders)}
      />

      <SettingsToggle label={$t('settings.borders')} checked={borderOn} onClick={() => setBorderOn(!borderOn)} />

      {#if borderOn}
        <SettingsSlider
          label={$t('settings.borderWidth')}
          value={borderWidth}
          min={BORDER_WIDTH_MIN}
          max={BORDER_WIDTH_MAX}
          step={0.5}
          onInput={setBorderWidth}
          format={(v) => `${v}px`}
        />

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
    </div>
  </div>
</div>
