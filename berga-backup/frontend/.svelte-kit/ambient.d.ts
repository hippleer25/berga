
// this file is generated — do not edit it


/// <reference types="@sveltejs/kit" />

/**
 * Environment variables [loaded by Vite](https://vitejs.dev/guide/env-and-mode.html#env-files) from `.env` files and `process.env`. Like [`$env/dynamic/private`](https://svelte.dev/docs/kit/$env-dynamic-private), this module cannot be imported into client-side code. This module only includes variables that _do not_ begin with [`config.kit.env.publicPrefix`](https://svelte.dev/docs/kit/configuration#env) _and do_ start with [`config.kit.env.privatePrefix`](https://svelte.dev/docs/kit/configuration#env) (if configured).
 * 
 * _Unlike_ [`$env/dynamic/private`](https://svelte.dev/docs/kit/$env-dynamic-private), the values exported from this module are statically injected into your bundle at build time, enabling optimisations like dead code elimination.
 * 
 * ```ts
 * import { API_KEY } from '$env/static/private';
 * ```
 * 
 * Note that all environment variables referenced in your code should be declared (for example in an `.env` file), even if they don't have a value until the app is deployed:
 * 
 * ```
 * MY_FEATURE_FLAG=""
 * ```
 * 
 * You can override `.env` values from the command line like so:
 * 
 * ```sh
 * MY_FEATURE_FLAG="enabled" npm run dev
 * ```
 */
declare module '$env/static/private' {
	export const XDG_GREETER_DATA_DIR: string;
	export const XDG_SESSION_PATH: string;
	export const XDG_DATA_DIRS: string;
	export const SHELL: string;
	export const XDG_SEAT_PATH: string;
	export const DEBUG_COLORS: string;
	export const SESSION_MANAGER: string;
	export const XDG_SESSION_CLASS: string;
	export const COLORTERM: string;
	export const DISPLAY: string;
	export const HOME: string;
	export const FORCE_COLOR: string;
	export const MEMORY_PRESSURE_WATCH: string;
	export const GTK_OVERLAY_SCROLLING: string;
	export const DBUS_STARTER_ADDRESS: string;
	export const DBUS_STARTER_BUS_TYPE: string;
	export const XDG_CURRENT_DESKTOP: string;
	export const PATH: string;
	export const SSH_AGENT_PID: string;
	export const MATE_DESKTOP_SESSION_ID: string;
	export const LOGNAME: string;
	export const QT_FONT_DPI: string;
	export const MOCHA_COLORS: string;
	export const LANG: string;
	export const GDMSESSION: string;
	export const XDG_ACTIVATION_TOKEN: string;
	export const XAUTHORITY: string;
	export const LANGUAGE: string;
	export const QT_SCALE_FACTOR: string;
	export const MEMORY_PRESSURE_WRITE: string;
	export const SYSTEMD_EXEC_PID: string;
	export const npm_config_color: string;
	export const GIO_LAUNCHED_DESKTOP_FILE_PID: string;
	export const SSH_AUTH_SOCK: string;
	export const XDG_RUNTIME_DIR: string;
	export const QT_ACCESSIBILITY: string;
	export const GPG_AGENT_INFO: string;
	export const MANAGERPID: string;
	export const DESKTOP_SESSION: string;
	export const USER: string;
	export const XDG_SESSION_TYPE: string;
	export const XDG_SESSION_DESKTOP: string;
	export const PWD: string;
	export const DBUS_SESSION_BUS_ADDRESS: string;
	export const NODE_ENV: string;
}

/**
 * Similar to [`$env/static/private`](https://svelte.dev/docs/kit/$env-static-private), except that it only includes environment variables that begin with [`config.kit.env.publicPrefix`](https://svelte.dev/docs/kit/configuration#env) (which defaults to `PUBLIC_`), and can therefore safely be exposed to client-side code.
 * 
 * Values are replaced statically at build time.
 * 
 * ```ts
 * import { PUBLIC_BASE_URL } from '$env/static/public';
 * ```
 */
declare module '$env/static/public' {
	
}

/**
 * This module provides access to runtime environment variables, as defined by the platform you're running on. For example if you're using [`adapter-node`](https://github.com/sveltejs/kit/tree/main/packages/adapter-node) (or running [`vite preview`](https://svelte.dev/docs/kit/cli)), this is equivalent to `process.env`. This module only includes variables that _do not_ begin with [`config.kit.env.publicPrefix`](https://svelte.dev/docs/kit/configuration#env) _and do_ start with [`config.kit.env.privatePrefix`](https://svelte.dev/docs/kit/configuration#env) (if configured).
 * 
 * This module cannot be imported into client-side code.
 * 
 * ```ts
 * import { env } from '$env/dynamic/private';
 * console.log(env.DEPLOYMENT_SPECIFIC_VARIABLE);
 * ```
 * 
 * > [!NOTE] In `dev`, `$env/dynamic` always includes environment variables from `.env`. In `prod`, this behavior will depend on your adapter.
 */
declare module '$env/dynamic/private' {
	export const env: {
		XDG_GREETER_DATA_DIR: string;
		XDG_SESSION_PATH: string;
		XDG_DATA_DIRS: string;
		SHELL: string;
		XDG_SEAT_PATH: string;
		DEBUG_COLORS: string;
		SESSION_MANAGER: string;
		XDG_SESSION_CLASS: string;
		COLORTERM: string;
		DISPLAY: string;
		HOME: string;
		FORCE_COLOR: string;
		MEMORY_PRESSURE_WATCH: string;
		GTK_OVERLAY_SCROLLING: string;
		DBUS_STARTER_ADDRESS: string;
		DBUS_STARTER_BUS_TYPE: string;
		XDG_CURRENT_DESKTOP: string;
		PATH: string;
		SSH_AGENT_PID: string;
		MATE_DESKTOP_SESSION_ID: string;
		LOGNAME: string;
		QT_FONT_DPI: string;
		MOCHA_COLORS: string;
		LANG: string;
		GDMSESSION: string;
		XDG_ACTIVATION_TOKEN: string;
		XAUTHORITY: string;
		LANGUAGE: string;
		QT_SCALE_FACTOR: string;
		MEMORY_PRESSURE_WRITE: string;
		SYSTEMD_EXEC_PID: string;
		npm_config_color: string;
		GIO_LAUNCHED_DESKTOP_FILE_PID: string;
		SSH_AUTH_SOCK: string;
		XDG_RUNTIME_DIR: string;
		QT_ACCESSIBILITY: string;
		GPG_AGENT_INFO: string;
		MANAGERPID: string;
		DESKTOP_SESSION: string;
		USER: string;
		XDG_SESSION_TYPE: string;
		XDG_SESSION_DESKTOP: string;
		PWD: string;
		DBUS_SESSION_BUS_ADDRESS: string;
		NODE_ENV: string;
		[key: `PUBLIC_${string}`]: undefined;
		[key: `${string}`]: string | undefined;
	}
}

/**
 * Similar to [`$env/dynamic/private`](https://svelte.dev/docs/kit/$env-dynamic-private), but only includes variables that begin with [`config.kit.env.publicPrefix`](https://svelte.dev/docs/kit/configuration#env) (which defaults to `PUBLIC_`), and can therefore safely be exposed to client-side code.
 * 
 * Note that public dynamic environment variables must all be sent from the server to the client, causing larger network requests — when possible, use `$env/static/public` instead.
 * 
 * ```ts
 * import { env } from '$env/dynamic/public';
 * console.log(env.PUBLIC_DEPLOYMENT_SPECIFIC_VARIABLE);
 * ```
 */
declare module '$env/dynamic/public' {
	export const env: {
		[key: `PUBLIC_${string}`]: string | undefined;
	}
}
