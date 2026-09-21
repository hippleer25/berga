import tailwindcss from "@tailwindcss/vite";
import { sveltekit } from "@sveltejs/kit/vite";
import { VitePWA } from "vite-plugin-pwa";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, "..");
  const allowedOrigins = env.ALLOWED_ORIGINS || process.env.ALLOWED_ORIGINS || "";
  const API_TARGET = env.API_URL || "http://backend:5746";

  return {
    plugins: [
      tailwindcss(),
      sveltekit(),
      VitePWA({
        registerType: "autoUpdate",
        injectRegister: false,
        includeAssets: [
          "favicon.ico",
          "robots.txt",
          "icons/berga_32.png",
          "icons/berga_64.png",
          "icons/berga_128.png",
          "icons/berga_256.png",
          "icons/berga_512.png",
          "icons/berga_1024.png",
        ],
        manifest: false,
		workbox: {
			navigateFallback: "index.html",
			navigateFallbackDenylist: [/^\/api\//],
			cleanupOutdatedCaches: true,
			skipWaiting: true,
			clientsClaim: true,
			globPatterns: [
				"**/*.{js,css,html,ico,svg,woff2,ttf}",
				"icons/*.png",
			],
			maximumFileSizeToCacheInBytes: 3 * 1024 * 1024,
			runtimeCaching: [
				{
					urlPattern: ({ url }) => {
						const isFeed = [
							'/api/feed/recents',
							'/api/feed/saved',
							// NOTE: /api/feed/events intentionally NOT stale-while-revalidate — the
							// events list is refreshed cyclically and user-triggered; serving it
							// cache-first pins stale/empty payloads past a hard refresh (this once
							// showed "no events" for hours). It falls through to the api-cache
							// NetworkFirst rule below.
							// NOTE: /api/feed/recommendations also falls through — each
							// reload uses a different exclude_ids/refresh query string and
							// SWR would cache every variant separately, replaying stale or
							// empty ([]) responses over fresh data.
							'/api/list-subscriptions',
						].some(path => url.pathname.startsWith(path));
						return isFeed;
					},
					handler: "StaleWhileRevalidate",
					options: {
						cacheName: "feed-cache-v2",
						expiration: {
							maxEntries: 100,
							maxAgeSeconds: 60 * 60,
						},
						cacheableResponse: {
							statuses: [200],
						},
					},
				},
				{
					urlPattern: ({ url }) => {
						const isApi = url.pathname.startsWith('/api/');
						const isAuth = ['/api/login', '/api/logout', '/api/register', '/api/meu-perfil'].some(path => url.pathname.startsWith(path));
						return isApi && !isAuth;
					},
					handler: "NetworkFirst",
					options: {
						// cache-name bump: v2 → existing installs drop the old
						// (poisoned) caches on activation via cleanupOutdatedCaches
						cacheName: "api-cache-v2",
						expiration: {
							maxEntries: 200,
							maxAgeSeconds: 60 * 60,
						},
						networkTimeoutSeconds: 10,
						cacheableResponse: {
							statuses: [200],
						},
					},
				},
			],
		},
      }),
    ],
    css: {
      transformer: "lightningcss",
    },
    server: {
      host: true,
      allowedHosts: allowedOrigins
        ? allowedOrigins.split(",").map((h) => h.trim().replace(/^https?:\/\//, ""))
        : [],
      fs: {
        allow: [".."],
      },
		proxy: {
			"/api": {
				target: API_TARGET,
				changeOrigin: true,
				rewrite: (path) => path,
			},
		},
    },
  };
});
