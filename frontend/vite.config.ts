import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  // ...plugins and other config
  server: {
    proxy: {
      // Whenever the frontend makes a request to /api, it gets forwarded to the backend container
      '/api': {
        target: 'http://backend:8000',
        changeOrigin: true,
        secure: false,
      },
    },
    host: '0.0.0.0'
  }
})