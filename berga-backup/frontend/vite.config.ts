import tailwindcss from "@tailwindcss/vite";
import { sveltekit } from "@sveltejs/kit/vite";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
    const env = loadEnv(mode, ".");
    const API_TARGET = env.API_URL || "http://backend:5746";

    return {
        plugins: [tailwindcss(), sveltekit()],
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
                    rewrite: (path: string) => path.replace(/^\/api/, ""),
                },
            },
        },
    };
});