<script lang="ts">
  import '$lib/components/settings/settings.css';
  import { t } from 'svelte-i18n';
  import SettingsToggle from '$lib/components/settings/SettingsToggle.svelte';
  import { ripple } from '$lib/actions/ripple';
  import History from '@lucide/svelte/icons/history';
  import Plus from '@lucide/svelte/icons/plus';
  import Blend from '@lucide/svelte/icons/blend';
  import ChevronUp from '@lucide/svelte/icons/chevron-up';
  import {
    uiChatBtnBorders,
    uiChatBtnLabels,
    getSavedChatBtnBorders,
    getSavedChatBtnLabels,
    applyChatBtnBorders,
    applyChatBtnLabels,
    type ChatBtnLabels,
  } from '$lib/stores/uiPrefs';

  const LABEL_MODES: { value: ChatBtnLabels; labelKey: string }[] = [
    { value: 'text', labelKey: 'settings.motaLabelsText' },
    { value: 'both', labelKey: 'settings.motaLabelsBoth' },
    { value: 'icons', labelKey: 'settings.motaLabelsIcons' },
  ];

  let btnBorders = $state<boolean>(getSavedChatBtnBorders());
  let labelsMode = $state<ChatBtnLabels>(getSavedChatBtnLabels());

  function setBtnBorders(v: boolean) {
    btnBorders = v;
    applyChatBtnBorders(v, true);
    uiChatBtnBorders.set(v);
  }
  function setLabelsMode(v: ChatBtnLabels) {
    labelsMode = v;
    applyChatBtnLabels(v, true);
    uiChatBtnLabels.set(v);
  }
</script>

<div class="tab-panel">
  <h2 class="section-title">{$t('settings.subsecMotaAi')}</h2>

  <div class="settings-group">
    <div class="group-label">{$t('settings.motaComposerGroup')}</div>
    <div class="group-card">
      <SettingsToggle
        label={$t('settings.motaBtnOutline')}
        desc={$t('settings.motaBtnOutlineHint')}
        checked={btnBorders}
        onClick={() => setBtnBorders(!btnBorders)}
      />

      <p class="section-desc">{$t('settings.motaBtnLabelsHint')}</p>
      <div class="setting-row">
        <span class="setting-label">{$t('settings.motaBtnLabels')}</span>
        <div class="navstyle-picker">
          {#each LABEL_MODES as mode (mode.value)}
            <button
              class="navstyle-card"
              class:active={labelsMode === mode.value}
              use:ripple
              onclick={() => setLabelsMode(mode.value)}
              aria-pressed={labelsMode === mode.value}
            >
              <span class="mota-btn-preview" data-mode={mode.value}>
                <History size={13} />
                <Plus size={13} />
                <span class="mota-btn-preview-label">Aa</span>
                <Blend size={13} />
                <ChevronUp size={11} />
              </span>
              <span class="navstyle-label">{$t(mode.labelKey)}</span>
            </button>
          {/each}
        </div>
      </div>
    </div>
  </div>
</div>

<style>
  .mota-btn-preview {
    display: flex;
    align-items: center;
    gap: 4px;
    height: 24px;
    padding: 0 7px;
    border: 1px solid var(--ui-hairline);
    border-radius: var(--ui-radius-sm);
    background: color-mix(in oklch, var(--color-base-200) 70%, transparent);
    color: var(--ui-text-subtle);
  }
  .mota-btn-preview-label {
    display: none;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: -0.01em;
  }
  .mota-btn-preview[data-mode='both'] .mota-btn-preview-label,
  .mota-btn-preview[data-mode='text'] .mota-btn-preview-label {
    display: inline;
  }
  .mota-btn-preview[data-mode='text'] :global(svg) {
    display: none;
  }
  .mota-btn-preview[data-mode='icons'] :global(svg:last-child),
  .mota-btn-preview[data-mode='both'] :global(svg:last-child) {
    color: var(--ui-text-faint);
  }
</style>
