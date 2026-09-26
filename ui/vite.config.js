import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base "./" so the build works both under /occam/demo/ on GitHub Pages and behind the API
export default defineConfig({
  plugins: [react()],
  base: "./",
  build: { outDir: process.env.OCCAM_UI_OUT || "dist", emptyOutDir: true },
  server: { proxy: { "/ach": "http://127.0.0.1:8000", "/scenarios": "http://127.0.0.1:8000", "/stix": "http://127.0.0.1:8000", "/extract": "http://127.0.0.1:8000" } },
});
