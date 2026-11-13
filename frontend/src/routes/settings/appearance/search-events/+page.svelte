<script lang="ts">
  import '$lib/components/settings/settings.css';
  import { onMount } from 'svelte';
  import { t } from 'svelte-i18n';
  import SettingsToggle from '$lib/components/settings/SettingsToggle.svelte';
  import SettingsSlider from '$lib/components/settings/SettingsSlider.svelte';
  import { ripple } from '$lib/actions/ripple';
  import EventCard from '$lib/components/EventCard.svelte';
  import PostCard from '$lib/components/PostCard.svelte';
  import PreviewFrame from '$lib/components/settings/preview/PreviewFrame.svelte';
  import { MOCK_POST, MOCK_EVENT } from '$lib/components/settings/preview/previewMocks';
  import { applySearchCoverAlign, applySearchCoverRadius, applyEventCoverPosition, applyEventTitleSize, applyEventCoverSpacing, POSTCARD_PREFS, type CoverAlign, type EventCoverPos } from '$lib/utils/appearance';
  import {
    searchCoverRadius,
    searchCoverAlign,
    showEventCovers,
    eventCoverPosition,
    eventTitleBelow,
    eventTitleSize,
    eventCoverSpacing,
    embeddedCovers,
    embeddedCoverPosition,
    type TriState,
  } from '$lib/stores/preferences';

  let searchRadiusVal = $state<number>(POSTCARD_PREFS.searchCoverRadius.default);
  let searchAlignVal = $state<CoverAlign>('center');
  let eventCoversOn = $state<boolean>(showEventCovers.getValue());
  let eventCoverPosVal = $state<EventCoverPos>('bottom');
  let eventTitleBelowVal = $state<boolean>(false);
  let eventTitleSizeVal = $state<number>(POSTCARD_PREFS.eventTitleSize.default);
  let eventCoverSpacingVal = $state<number>(POSTCARD_PREFS.eventCoverSpacing.default);
  let embeddedCoversVal = $state<TriState>('off');
  let embeddedPosVal = $state<'right' | 'bottom'>('right');

  onMount(() => {
    searchRadiusVal = searchCoverRadius.getValue();
    searchAlignVal = searchCoverAlign.getValue();
    eventCoversOn = showEventCovers.getValue();
    eventCoverPosVal = eventCoverPosition.getValue() as EventCoverPos;
    eventTitleBelowVal = eventTitleBelow.getValue();
    eventTitleSizeVal = eventTitleSize.getValue();
    eventCoverSpacingVal = eventCoverSpacing.getValue();
    embeddedCoversVal = embeddedCovers.getValue();
    embeddedPosVal = embeddedCoverPosition.getValue() as 'right' | 'bottom';
  });

  function setSearchRadius(v: number) {
    searchRadiusVal = v;
    applySearchCoverRadius(v, true);
    searchCoverRadius.setValue(v);
  }
  function setSearchAlign(v: CoverAlign) {
    searchAlignVal = v;
    applySearchCoverAlign(v, true);
    searchCoverAlign.setValue(v);
  }
  function toggleEventCovers() {
    eventCoversOn = !eventCoversOn;
    showEventCovers.setValue(eventCoversOn);
  }
  function setEventTitleBelow(v: boolean) {
    eventTitleBelowVal = v;
    eventTitleBelow.setValue(v);
  }
  function setEventTitleSize(v: number) {
    eventTitleSizeVal = v;
    applyEventTitleSize(v, true);
    eventTitleSize.setValue(v);
  }
  function setEventCoverSpacing(v: number) {
    eventCoverSpacingVal = v;
    applyEventCoverSpacing(v, true);
    eventCoverSpacing.setValue(v);
  }
  function setEventCoverPos(v: EventCoverPos) {
    eventCoverPosVal = v;
    applyEventCoverPosition(v, true);
    eventCoverPosition.setValue(v);
  }
  function setEmbeddedCovers(v: TriState) {
    embeddedCoversVal = v;
    embeddedCovers.setValue(v);
  }
  function setEmbeddedPos(v: 'right' | 'bottom') {
    embeddedPosVal = v;
    embeddedCoverPosition.setValue(v);
  }
</script>

<div class="tab-panel">
  <h2 class="section-title">{$t('settings.subsecSearchEvents')}</h2>

  <div class="settings-group">
    <div class="group-label">{$t('settings.searchCoversGroup')}</div>
    <div class="group-card">
      <SettingsSlider
        label={$t('settings.searchCoverImageRadius')}
        value={searchRadiusVal}
        min={POSTCARD_PREFS.searchCoverRadius.min}
        max={POSTCARD_PREFS.searchCoverRadius.max}
        step={POSTCARD_PREFS.searchCoverRadius.step}
        onInput={setSearchRadius}
        format={(v) => (v === 0 ? $t('settings.imageRadiusAuto') : `${v.toFixed(2)}rem`)}
      />
      <p class="row-hint">{$t('settings.searchCoverImageRadiusHint')}</p>

      <div class="setting-row">
        <span class="setting-label">{$t('settings.searchCoverImageAlign')}</span>
        <div class="picker-wrap density-picker">
          <button class="density-btn" class:active={searchAlignVal === 'left'} use:ripple onclick={() => setSearchAlign('left')} aria-pressed={searchAlignVal === 'left'}>
            {$t('settings.textAlignLeft')}
          </button>
          <button class="density-btn" class:active={searchAlignVal === 'center'} use:ripple onclick={() => setSearchAlign('center')} aria-pressed={searchAlignVal === 'center'}>
            {$t('settings.textAlignCenter')}
          </button>
          <button class="density-btn" class:active={searchAlignVal === 'right'} use:ripple onclick={() => setSearchAlign('right')} aria-pressed={searchAlignVal === 'right'}>
            {$t('settings.textAlignRight')}
          </button>
        </div>
      </div>
      <p class="row-hint">{$t('settings.searchCoverImageAlignHint')}</p>
    </div>
  </div>

  <div class="settings-group">
    <div class="group-label">{$t('settings.eventsSection')}</div>
    <div class="group-card">
      <div class="setting-row">
        <span class="setting-label">{$t('settings.eventTitleOrder')}</span>
        <div class="picker-wrap density-picker">
          <button class="density-btn" class:active={!eventTitleBelowVal} use:ripple onclick={() => setEventTitleBelow(false)} aria-pressed={!eventTitleBelowVal}>
            {$t('settings.eventTitleAbove')}
          </button>
          <button class="density-btn" class:active={eventTitleBelowVal} use:ripple onclick={() => setEventTitleBelow(true)} aria-pressed={eventTitleBelowVal}>
            {$t('settings.eventTitleBelow')}
          </button>
        </div>
      </div>

      <SettingsSlider
        label={$t('settings.eventTitleSize')}
        value={eventTitleSizeVal}
        min={POSTCARD_PREFS.eventTitleSize.min}
        max={POSTCARD_PREFS.eventTitleSize.max}
        step={POSTCARD_PREFS.eventTitleSize.step}
        onInput={setEventTitleSize}
        format={(v) => `${v}%`}
      />

      <SettingsToggle label={$t('settings.showEventCovers')} checked={eventCoversOn} onClick={toggleEventCovers} />

      {#if eventCoversOn}
        <div class="setting-row">
          <span class="setting-label">{$t('settings.eventCoverPosition')}</span>
          <div class="picker-wrap density-picker">
            <button class="density-btn" class:active={eventCoverPosVal === 'side'} use:ripple onclick={() => setEventCoverPos('side')} aria-pressed={eventCoverPosVal === 'side'}>
              {$t('settings.coverImagePositionRight')}
            </button>
            <button class="density-btn" class:active={eventCoverPosVal === 'top'} use:ripple onclick={() => setEventCoverPos('top')} aria-pressed={eventCoverPosVal === 'top'}>
              {$t('settings.coverImagePositionTop')}
            </button>
            <button class="density-btn" class:active={eventCoverPosVal === 'bottom'} use:ripple onclick={() => setEventCoverPos('bottom')} aria-pressed={eventCoverPosVal === 'bottom'}>
              {$t('settings.coverImagePositionBottom')}
            </button>
          </div>
        </div>

        {#if eventCoverPosVal === 'bottom'}
          <SettingsSlider
            label={$t('settings.eventCoverSpacing')}
            value={eventCoverSpacingVal}
            min={POSTCARD_PREFS.eventCoverSpacing.min}
            max={POSTCARD_PREFS.eventCoverSpacing.max}
            step={POSTCARD_PREFS.eventCoverSpacing.step}
            onInput={setEventCoverSpacing}
            format={(v) => `${v}px`}
          />
          <p class="row-hint">{$t('settings.eventCoverSpacingHint')}</p>
        {/if}
      {/if}

      <div class="setting-row">
        <div class="setting-text">
          <span class="setting-label">{$t('settings.showEmbeddedCovers')}</span>
        </div>
        <div class="picker-wrap density-picker">
          <button class="density-btn" class:active={embeddedCoversVal === 'auto'} use:ripple onclick={() => setEmbeddedCovers('auto')} aria-pressed={embeddedCoversVal === 'auto'}>
            {$t('settings.coversAuto')}
          </button>
          <button class="density-btn" class:active={embeddedCoversVal === 'on'} use:ripple onclick={() => setEmbeddedCovers('on')} aria-pressed={embeddedCoversVal === 'on'}>
            {$t('settings.coversOn')}
          </button>
          <button class="density-btn" class:active={embeddedCoversVal === 'off'} use:ripple onclick={() => setEmbeddedCovers('off')} aria-pressed={embeddedCoversVal === 'off'}>
            {$t('settings.coversOff')}
          </button>
        </div>
      </div>
      <p class="row-hint">{$t('settings.embeddedCoversHint')}</p>

      {#if embeddedCoversVal !== 'off'}
        <div class="setting-row">
          <span class="setting-label">{$t('settings.embeddedCoverPosition')}</span>
          <div class="picker-wrap density-picker">
            <button class="density-btn" class:active={embeddedPosVal === 'right'} use:ripple onclick={() => setEmbeddedPos('right')} aria-pressed={embeddedPosVal === 'right'}>
              {$t('settings.coverImagePositionRight')}
            </button>
            <button class="density-btn" class:active={embeddedPosVal === 'bottom'} use:ripple onclick={() => setEmbeddedPos('bottom')} aria-pressed={embeddedPosVal === 'bottom'}>
              {$t('settings.coverImagePositionBottom')}
            </button>
          </div>
        </div>
      {/if}
    </div>
  </div>

  <PreviewFrame label={$t('settings.preview')}>
    <div class="event-stage">
      <EventCard event={MOCK_EVENT} open={true} />
    </div>
    <div class="search-stage">
      <PostCard item={MOCK_POST} />
      <p class="row-hint">{$t('settings.searchCoverImageRadiusHint')}</p>
    </div>
  </PreviewFrame>
</div>

<style>
  .event-stage { max-width: 34rem; }
  /* Same var remap the real search page applies to its root. */
  .search-stage {
    max-width: 30rem;
    --cover-image-radius: var(--search-cover-image-radius, var(--ui-radius-sm));
    --cover-image-align: var(--search-cover-image-align, center);
    --cover-image-align-margin: var(--search-cover-image-align-margin, auto);
  }
</style>
