import { resolve } from 'node:path';
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import tailwindcss from '@tailwindcss/vite';

const polyfillPath = resolve(__dirname, 'scripts/node20-polyfill.cjs');

// https://vite.dev/config/
export default defineConfig({
  // Frontend sources live under source/frontend (see documentation/D3-architecture.md)
  root: 'source/frontend',
  build: {
    outDir: '../../dist',
    emptyOutDir: true,
  },
  plugins: [
    vue(),
    tailwindcss()
  ],
  test: {
    // Default to node; component tests opt into jsdom with a
    // `// @vitest-environment jsdom` docblock.
    environment: 'node',
    include: ['**/*.test.ts'],
    setupFiles: ['./test-setup.ts'],
    poolOptions: {
      forks: {
        execArgv: ['--require', polyfillPath],
      },
      threads: {
        execArgv: ['--require', polyfillPath],
      },
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  }
});
