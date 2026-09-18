# Plan: Remove visible scrollbars on tab panes (app-wide consistency)

## Diagnosis (verified)

- User sees an always-visible classic scrollbar at the right edge of tab pages on a desktop Chromium browser **with the split view active**.
- Root cause: the new split-view layout in `frontend/src/routes/+layout.svelte` gives each pane `overflow-y: auto` (line 133) with **no scrollbar hiding** — unlike the tab panels (`PageTrack.svelte`) and the root scroller (`app.css`), which already hide theirs.
- Verified via headless Chromium (puppeteer, docker) against the running instance on :4657:
  - Root scrollbar: `scrollbar-width: none` computed, gutter = 0 even with forced overflow → single-tab desktop is already clean.
  - The served CSS contains the existing `html` and `.panel` hiding rules.
- Secondary inconsistency found: `.screen-shell` (stacked screens opened from tabs — feed page, article, search results, settings) has `overflow-y: auto` on mobile with no hiding, while the tab `.panel`s hide it. Fixing both makes the app consistent.

## Changes (2 files, CSS-only)

### 1. `frontend/src/routes/+layout.svelte` — split panes (the reported bug)

In the `@media (min-width: 768px)` block, extend `.tabs-layer.split .pane`:

```css
.tabs-layer.split .pane {
    ...existing rules...
    scrollbar-width: none;
}
.tabs-layer.split .pane::-webkit-scrollbar {
    width: 0;
    height: 0;
    display: none;
}
```

Same pattern already used by `.panel` in `PageTrack.svelte:283-293` (Svelte scopes the selector fine, same as PageTrack).

### 2. `frontend/src/lib/components/ScreenShell.svelte` — stacked screens (mobile)

In the `@media (max-width: 767.98px)` block, extend `.screen-shell` (currently `overflow-y: auto` at line 147):

```css
.screen-shell {
    ...existing rules...
    scrollbar-width: none;
}
.screen-shell::-webkit-scrollbar {
    width: 0;
    height: 0;
    display: none;
}
```

## Explicitly left unchanged (intentional styling, not part of the complaint)

- `.drawer-body` (LeftPanel) — `thin` scrollbar
- `.chat-scroll` (MotaTab) — custom 4px accent-colored scrollbar
- Small dropdown pickers (HomeTab/PostCard/syncFeedTags) — `thin`

## Verification

1. Rebuild + restart frontend: `docker compose build frontend && docker compose up -d frontend`
2. Confirm served CSS contains the new rules:
   `curl -s http://localhost:4657/_app/immutable/assets/<main>.css | grep -c scrollbar-width:none` (find hash via the entry JS, as done during research)
3. Headless-Chromium probe (docker puppeteer image, already local):
   - open `/login` (no auth needed), inject `split` class + a `.pane` element via JS, assert `getComputedStyle(pane).scrollbarWidth === 'none'`
   - 390px viewport: assert `.screen-shell` computed `scrollbar-width: none`
4. User visual check: Followers/Home/search tabs in split view — no bar; wheel/trackpad scrolling still works in both panes.

## Risks / notes

- Hiding scrollbars removes the visual affordance, but scrolling still works (wheel, touch, keyboard); this matches the existing design decision already applied to the tabs and root scroller (commit fcdb91e).
- Alternative if the user later wants a hint: replicate MotaTab's styled 4px accent thumb instead of full hide — not doing it now to stay consistent with the rest of the app.
