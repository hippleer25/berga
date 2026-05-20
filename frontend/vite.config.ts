import tailwindcss from "@tailwindcss/vite";
import { sveltekit } from "@sveltejs/kit/vite";
import { VitePWA } from "vite-plugin-pwa";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".");
  const API_TARGET = env.API_URL || "http://backend:5746";

  return {
    plugins: [
      tailwindcss(),
      sveltekit(),
      VitePWA({
        registerType: "autoUpdate",
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
          globPatterns: [
            "**/*.{js,css,html,ico,svg,woff2,ttf}",
            "icons/*.png",
          ],
          maximumFileSizeToCacheInBytes: 3 * 1024 * 1024,
          runtimeCaching: [
            {
              urlPattern: /^\/api\/.*/i,
              handler: "NetworkFirst",
              options: {
                cacheName: "api-cache",
                expiration: {
                  maxEntries: 200,
                  maxAgeSeconds: 60 * 60,
                },
                networkTimeoutSeconds: 10,
                cacheableResponse: {
                  statuses: [0, 200],
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
      allowedHosts: ["berga.hippler.net.br"],
      fs: {
        allow: [".."],
      },
      proxy: {
        "/api": {
          target: API_TARGET,
          changeOrigin: true,
        },
      },
    },
  };
});
