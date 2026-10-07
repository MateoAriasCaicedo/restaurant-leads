import { resolve } from "node:path"
import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

// The API (python app.py) listens on config.UI_PORT; the dev server on config.UI_DEV_PORT.
// Both are fixed because the API only accepts requests from these two origins.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": resolve(import.meta.dirname, "./src"),
    },
  },
  server: {
    port: 5183,
    strictPort: true,
    proxy: { "/api": "http://127.0.0.1:8642" },
  },
})
