import { browser } from '$app/environment';
import { writable, get, type Writable } from 'svelte/store';
import { applyFont, type FontCategory } from '$lib/utils/appearance';
import {
	applyRadiusControls,
	applyRadiusSurfaces,
	hasSavedRadiusControl,
	hasSavedRadiusSurface,
	uiRadiusControl,
	uiRadiusSurface,
} from '$lib/stores/uiPrefs';

/**
 * Master design languages.
 *
 * `elegant` — editorial/timeless: serif titles and body, squarer controls,
 *   quiet relief. Reads like a well-set newspaper.
 * `modern` — rounded, glossy, sans, more vivid relief (Cloudflare-like).
 *
 * The mode only provides defaults. Any font/radius the user set explicitly
 * in Appearance keeps winning, by design.
 */
export type DesignMode = 'elegant' | 'modern';

export const DESIGN_MODE_KEY = 'ui-design-mode';
export const DESIGN_MODE_DEFAULT: DesignMode = 'elegant';

export type ModePreset = {
	radiusSurface: number;
	radiusControl: number;
	fonts: Record<FontCategory, string>;
};

export const MODE_PRESETS: Record<DesignMode, ModePreset> = {
	elegant: {
		radiusSurface: 6,
		radiusControl: 3,
		fonts: {
			'page-title': 'Newsreader',
			'post-title': 'PT Serif',
			'article-body': 'Source Serif 4',
			'ui': 'Inter',
		},
	},
	modern: {
		radiusSurface: 17,
		radiusControl: 7,
		fonts: {
			'page-title': 'Figtree',
			'post-title': 'Figtree',
			'article-body': 'Inter',
			'ui': 'Inter',
		},
	},
};

const FONT_CATEGORIES: FontCategory[] = ['page-title', 'post-title', 'article-body', 'ui'];

export function getSavedDesignMode(): DesignMode {
	if (!browser) return DESIGN_MODE_DEFAULT;
	const raw = localStorage.getItem(DESIGN_MODE_KEY);
	return raw === 'modern' ? 'modern' : raw === 'elegant' ? 'elegant' : DESIGN_MODE_DEFAULT;
}

/** True when the user has not overridden the given typography role. */
export function hasCustomFont(category: FontCategory): boolean {
	return browser && localStorage.getItem(`font-${category}`) !== null;
}

/**
 * Applies the mode's shape/typography defaults to every role the user has
 * not overridden, and mirrors them into the reactive stores so the settings
 * UI reflects the real values.
 */
export function applyDesignMode(mode: DesignMode, persist = false) {
	if (!browser) return;
	const root = document.documentElement;
	root.setAttribute('data-ui-mode', mode);
	uiDesignMode.set(mode);

	const preset = MODE_PRESETS[mode];

	if (!hasSavedRadiusSurface()) {
		uiRadiusSurface.set(preset.radiusSurface);
		applyRadiusSurfaces(preset.radiusSurface);
	}
	if (!hasSavedRadiusControl()) {
		uiRadiusControl.set(preset.radiusControl);
		applyRadiusControls(preset.radiusControl);
	}

	for (const category of FONT_CATEGORIES) {
		if (!hasCustomFont(category)) applyFont(category, preset.fonts[category]);
	}

	if (persist) localStorage.setItem(DESIGN_MODE_KEY, mode);
}

export function initDesignMode() {
	applyDesignMode(getSavedDesignMode());
}

export const uiDesignMode: Writable<DesignMode> = writable(getSavedDesignMode());

/** Current mode, clamped when storage contains junk. */
export function currentDesignMode(): DesignMode {
	return get(uiDesignMode);
}
