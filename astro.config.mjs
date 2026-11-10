import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';
import sitemap from '@astrojs/sitemap';
import { pageLastModified } from './src/lib/freshness.mjs';

// Production origin. Feeds absolute canonical/OG URLs and the sitemap.
// Update this if the production domain changes.
const site = 'https://www.keikogobierna.com';

// <lastmod> only where a dated record backs it; see src/lib/freshness.mjs.
const lastModified = pageLastModified();

export default defineConfig({
  site,
  output: 'static',
  integrations: [
    sitemap({
      serialize(item) {
        const date = lastModified.get(new URL(item.url).pathname);
        return date ? { ...item, lastmod: date } : item;
      },
    }),
  ],
  server: { port: 3000 },
  vite: { plugins: [tailwindcss()] },
});
