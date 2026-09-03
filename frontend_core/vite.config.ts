import { fileURLToPath, URL } from 'node:url';
import { loadEnv } from "vite";
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

const hostsAllowed = ['dev-front.unindosorte.com.br', 'localhost'];

// https://vitejs.dev/config/

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const apiBaseUrl = env.VITE_API_BASE_URL || '/api';
  const apiProxyPrefix = apiBaseUrl.startsWith('/') ? apiBaseUrl.replace(/\/$/, '') : '/api';
  const apiProxyTarget = env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8000';

  return {
    plugins: [
      react(),
      {
        name: 'leaflet-heat-bind-l',
        transform(code, id) {
          if (!id.includes('leaflet-heat')) return null;
          if (code.includes("from 'leaflet'")) return null;
          return {
            code: `import L from 'leaflet';\n${code}`,
            map: null,
          };
        },
      },
    ],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    server: {
      host: '127.0.0.1',
      port: 5173,
      allowedHosts: hostsAllowed,
      proxy: {
        [apiProxyPrefix]: {
          target: apiProxyTarget,
          changeOrigin: true,
          xfwd: true,
          rewrite: (path) => path.replace(new RegExp(`^${apiProxyPrefix}`), ''),
        },
      },
    },
    preview: {
      host: '127.0.0.1',
      port: 4173,
    },
    test: {
      environment: 'jsdom',
      setupFiles: './src/test/setup.ts',
      css: true,
      globals: true,
      include: ['src/**/*.{test,spec}.{ts,tsx}'],
      exclude: ['e2e/**', 'node_modules/**', 'dist/**'],
    },
  };
});
