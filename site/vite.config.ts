import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import {defineConfig} from 'vite';

// Served from https://defuseddata.github.io/events-validator/ (GitHub Pages project site).
// If a custom domain is attached later, change base to '/'.
export default defineConfig({
  base: '/events-validator/',
  plugins: [react(), tailwindcss()],
  build: {outDir: 'dist', sourcemap: false},
});
