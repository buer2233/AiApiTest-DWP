import { fileURLToPath, URL } from "node:url";

import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

// Vite 配置：路径别名 @ -> src；dev 代理 /api 到后端（地址走环境变量，不写死）。
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.VITE_API_BASE_URL || "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
