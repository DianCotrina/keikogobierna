import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  // Production origin. Feeds absolute canonical/OG URLs and any future sitemap.
  // Update this if the production domain changes.
  site: 'https://keikogobierna.vercel.app',
  output: 'static',
  server: { port: 3000 },
  vite: { plugins: [tailwindcss()] },
});
