/**
 * Paints the native Android system-bar area (status + navigation) with the
 * app theme background and adjusts bar icon contrast to match.
 *
 * On Android 15+ the window is enforced edge-to-edge and Capacitor pads the
 * WebView natively, so the area behind the system bars shows the native
 * window background — the deprecated setNavigationBarColor/setStatusBarColor
 * are no-ops there. A tiny local plugin (ThemeBars, see
 * android/app/src/main/java/net/bergamonta/app/ThemeBarsPlugin.java) paints
 * the window background instead. On older Androids it falls back to the
 * classic window bar colors. Icon contrast is handled by the SystemBars
 * core plugin, which must run BEFORE the paint call: SystemBars resets the
 * window background to the Android theme color on every style change.
 * No-ops everywhere outside a native platform.
 */

import { Capacitor, registerPlugin, SystemBars, SystemBarsStyle } from '@capacitor/core';

const ThemeBars = registerPlugin<{
	setBackgroundColor(options: { color: string }): Promise<void>;
}>('ThemeBars');

function toHex(color: string): string {
	const c = color.trim().toLowerCase();
	const hex3 = c.match(/^#([0-9a-f]{3})$/);
	if (hex3) return '#' + hex3[1].split('').map(ch => ch + ch).join('');
	if (/^#[0-9a-f]{6}$/.test(c)) return c;
	if (/^#[0-9a-f]{8}$/.test(c)) return c.slice(0, 7);
	const rgb = c.match(/^rgba?\((\d+)[,\s]+(\d+)[,\s]+(\d+)/);
	if (rgb) {
		const chan = [rgb[1], rgb[2], rgb[3]].map(v => Math.max(0, Math.min(255, Number(v))));
		return '#' + chan.map(v => v.toString(16).padStart(2, '0')).join('');
	}
	return '#000000';
}

/* Dark backgrounds get light bar icons (Style DARK); light ones get dark icons. */
function isLightBackground(hex: string): boolean {
	const m = hex.match(/^#([0-9a-f]{6})$/);
	if (!m) return false;
	const n = parseInt(m[1], 16);
	const lum = 0.2126 * ((n >> 16) & 0xff) + 0.7152 * ((n >> 8) & 0xff) + 0.0722 * (n & 0xff);
	return lum > 128;
}

export async function applyNativeBars(color: string): Promise<void> {
	if (!Capacitor.isNativePlatform()) return;
	const hex = toHex(color);
	try {
		await SystemBars.setStyle({
			style: isLightBackground(hex) ? SystemBarsStyle.Light : SystemBarsStyle.Dark,
		});
	} catch {
		/* system bars unavailable */
	}
	try {
		await ThemeBars.setBackgroundColor({ color: hex });
	} catch {
		/* local plugin not registered */
	}
}
