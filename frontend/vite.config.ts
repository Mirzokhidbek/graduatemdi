import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// /api so'rovlari FastAPI backendga yuboriladi. Standart: http://127.0.0.1:8000;
// boshqa port uchun: UZTERM_API_URL=http://127.0.0.1:8765 npm run dev
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": process.env.UZTERM_API_URL ?? "http://127.0.0.1:8000",
    },
  },
});
