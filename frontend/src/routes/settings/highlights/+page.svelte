<script lang="ts">
  import { t } from 'svelte-i18n';
  import Plus from '@lucide/svelte/icons/plus';
  import X from '@lucide/svelte/icons/x';
  import { ripple } from '$lib/actions/ripple';
  import {
    highlightColors,
    highlightOpacity,
    highlightRadius,
  } from '$lib/stores/preferences';
  import { hexToRgba } from '$lib/utils/color';

  const MAX_COLORS = 8;

  function updateColorAt(index: number, e: Event) {
    const input = e.target as HTMLInputElement;
    if (input.value) highlightColors.updateColor(index, input.value);
  }

  function removeColorAt(index: number) {
    if ($highlightColors.length <= 1) return;
    highlightColors.removeColor(index);
  }

  function addColor() {
    if ($highlightColors.length >= MAX_COLORS) return;
    highlightColors.addColor('#FF9800');
  }
</script>

<div class="tab-panel">
  <h2 class="section-title">{$t('settings.highlights')}</h2>
  <p class="section-desc">{$t('settings.highlightsDesc')}</p>

  <details class="section" open>
    <summary class="section-summary">
      <span class="section-summary-text">{$t('settings.highlightColors')}</span>
      <span class="section-summary-hint">{$highlightColors.length}/{MAX_COLORS}</span>
    </summary>
    <div class="section-body">
      {#each $highlightColors as color, i}
        <div class="color-row">
          <label class="color-swatch" style="background: {hexToRgba(color, 100)};" title={color}>
            <input
              type="color"
              value={color}
              oninput={(e) => updateColorAt(i, e)}
              aria-label={`${$t('settings.highlightColors')} ${i + 1}`}
            />
          </label>
          <span class="color-hex">{color.toUpperCase()}</span>
          <button
            class="remove-btn"
            onclick={() => removeColorAt(i)}
            disabled={$highlightColors.length <= 1}
            title={$t('settings.removeColor')}
            aria-label={$t('settings.removeColor')}
          >
            <X size={14} />
          </button>
        </div>
      {/each}

      <button class="action-btn accent add-btn" use:ripple onclick={addColor} disabled={$highlightColors.length >= MAX_COLORS}>
        <Plus size={14} />
        <span>{$t('settings.addColor')}</span>
      </button>
    </div>
  </details>

  <details class="section" open>
    <summary class="section-summary">
      <span class="section-summary-text">{$t('settings.highlightStyle')}</span>
    </summary>
    <div class="section-body">
      <div class="setting-slider-row">
        <div class="slider-head">
          <span class="setting-label">{$t('settings.highlightOpacity')}</span>
          <span class="slider-value">{$highlightOpacity}%</span>
        </div>
        <input
          type="range"
          class="range"
          min="10"
          max="100"
          step="1"
          value={$highlightOpacity}
          oninput={(e) => highlightOpacity.setValue(Number((e.target as HTMLInputElement).value))}
        />
      </div>

      <div class="setting-slider-row">
        <div class="slider-head">
          <span class="setting-label">{$t('settings.highlightRadius')}</span>
          <span class="slider-value">{$highlightRadius}%</span>
        </div>
        <input
          type="range"
          class="range"
          min="0"
          max="50"
          step="1"
          value={$highlightRadius}
          oninput={(e) => highlightRadius.setValue(Number((e.target as HTMLInputElement).value))}
        />
      </div>

      <div class="preview-block">
        <span class="preview-label">{$t('settings.highlightPreview')}</span>
        <p class="preview-text">
          This is how
          <mark
            class="preview-mark"
            style="background: {hexToRgba($highlightColors[0] ?? '#FFEB3B', $highlightOpacity)}; border-radius: {$highlightRadius}%;"
          >
            highlighted text
          </mark>
          will look.
        </p>
      </div>
    </div>
  </details>
</div>

<style>
  .tab-panel { display: flex; flex-direction: column; gap: 16px; padding-top: 12px; }
  .section-title { font-size: 16px; font-weight: 700; color: var(--color-base-content); margin: 0; }
  .section-desc { font-size: 13px; line-height: 1.45; color: color-mix(in oklch, var(--color-base-content) 50%, transparent); margin: -8px 0 0; }

  /* ── Collapsible sections ─────────────────────────────────── */
  .section {
    border: 1px solid var(--color-base-300);
    border-radius: 12px;
    overflow: hidden;
    background: color-mix(in oklch, var(--color-base-100) 60%, transparent);
  }
  .section > summary { list-style: none; }
  .section > summary::-webkit-details-marker { display: none; }
  .section-summary {
    display: flex; align-items: center; justify-content: space-between;
    padding: 12px 14px; cursor: pointer; user-select: none;
    font-size: 14px; font-weight: 600; color: var(--color-base-content);
    transition: background 130ms;
  }
  .section-summary:hover { background: var(--color-base-200); }
  .section-summary:active { background: color-mix(in oklch, var(--color-base-content) 6%, transparent); }
  .section-summary-text { display: flex; align-items: center; gap: 6px; }
  .section-summary-hint {
    font-size: 11px; font-weight: 700; color: var(--color-accent);
    font-variant-numeric: tabular-nums; font-family: var(--font-ui);
  }
  .section-body { padding: 4px 14px 12px; display: flex; flex-direction: column; gap: 6px; }

  /* ── Color rows ───────────────────────────────────────────── */
  .color-row {
    display: flex; align-items: center; gap: 12px;
    padding: 6px 0; border-bottom: 1px solid var(--color-base-300);
  }
  .color-swatch {
    width: 34px; height: 34px; border-radius: 10px;
    border: 2px solid var(--color-base-300);
    position: relative; overflow: hidden; cursor: pointer; flex-shrink: 0;
    transition: border-color 130ms, transform 130ms;
  }
  .color-swatch:hover { border-color: var(--color-base-content); transform: scale(1.06); }
  .color-swatch input[type="color"] {
    position: absolute; inset: -4px; width: calc(100% + 8px); height: calc(100% + 8px);
    opacity: 0; cursor: pointer;
  }
  .color-hex {
    flex: 1; font-size: 12px; font-weight: 600; letter-spacing: 0.04em;
    color: color-mix(in oklch, var(--color-base-content) 70%, transparent);
    font-variant-numeric: tabular-nums; font-family: var(--font-ui);
  }
  .remove-btn {
    display: inline-flex; align-items: center; justify-content: center;
    width: 28px; height: 28px; border-radius: 8px; border: none;
    background: transparent; color: color-mix(in oklch, var(--color-base-content) 40%, transparent);
    cursor: pointer; transition: all 130ms; flex-shrink: 0;
  }
  .remove-btn:hover { background: color-mix(in oklch, var(--color-error) 12%, transparent); color: var(--color-error); }
  .remove-btn:disabled { opacity: 0.35; cursor: not-allowed; }

  .add-btn { align-self: flex-start; margin-top: 8px; }

  .action-btn {
    display: inline-flex; align-items: center; justify-content: center; gap: 6px;
    padding: 8px 14px; border-radius: 10px; border: 1px solid var(--color-base-300);
    background: transparent; color: var(--color-base-content); cursor: pointer;
    font-size: 13px; font-weight: 600; transition: all 130ms ease;
    position: relative; overflow: hidden;
  }
  .action-btn:hover { background: var(--color-base-200); }
  .action-btn:active { transform: scale(0.97); }
  .action-btn.accent { border-color: var(--color-accent); color: var(--color-accent); }
  .action-btn.accent:hover { background: color-mix(in oklch, var(--color-accent) 10%, transparent); }
  .action-btn:disabled { opacity: 0.6; cursor: not-allowed; }

  /* ── Sliders ──────────────────────────────────────────────── */
  .setting-slider-row {
    display: flex; flex-direction: column; gap: 6px;
    padding: 10px 0; border-bottom: 1px solid var(--color-base-300);
  }
  .slider-head { display: flex; align-items: center; justify-content: space-between; }
  .setting-label { font-size: 14px; font-weight: 500; color: var(--color-base-content); }
  .slider-value {
    font-size: 12px; font-weight: 600; color: var(--color-accent);
    font-variant-numeric: tabular-nums; font-family: var(--font-ui);
  }
  .range {
    -webkit-appearance: none; appearance: none;
    width: 100%; height: 4px; border-radius: 999px;
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

  /* ── Preview ──────────────────────────────────────────────── */
  .preview-block { padding: 14px 0 4px; display: flex; flex-direction: column; gap: 8px; }
  .preview-label {
    font-size: 10px; text-transform: uppercase; letter-spacing: 0.06em;
    color: color-mix(in oklch, var(--color-base-content) 40%, transparent); font-weight: 700;
  }
  .preview-text {
    margin: 0; font-size: 15px; line-height: 1.8;
    color: color-mix(in oklch, var(--color-base-content) 80%, transparent);
  }
  .preview-mark {
    padding: 0 2px; cursor: default;
    font-family: inherit; font-size: inherit;
  }
</style>