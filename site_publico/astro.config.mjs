import react from '@astrojs/react';
import sitemap from '@astrojs/sitemap';
import { defineConfig } from 'astro/config';

export default defineConfig({
  site: process.env.PUBLIC_SITE_URL || 'http://localhost:4321',
  integrations: [react(), sitemap()],
  server: { host: '127.0.0.1', port: 4321 },
});
