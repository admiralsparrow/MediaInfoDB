import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { readFileSync, existsSync } from "fs";
import { resolve } from "path";

const versionPath = existsSync(resolve(__dirname, "../VERSION"))
  ? resolve(__dirname, "../VERSION")
  : "/VERSION";
const version = readFileSync(versionPath, "utf-8").trim();

export default defineConfig({
  plugins: [react()],
  define: {
    __APP_VERSION__: JSON.stringify(version),
  },
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
