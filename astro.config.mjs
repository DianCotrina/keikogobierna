import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';
import sitemap from '@astrojs/sitemap';

export default defineConfig({
  // Production origin. Feeds absolute canonical/OG URLs and any future sitemap.
  // Update this if the production domain changes.
  site: 'https://www.keikogobierna.com',
  output: 'static',
  integrations: [sitemap()],
  server: { port: 3000 },
  vite: { plugins: [tailwindcss()] },
});
