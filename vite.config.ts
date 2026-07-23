import tailwindcss from '@tailwindcss/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';
import adapter from 'svelte-adapter-bun';

export default defineConfig({
  plugins: [
    tailwindcss(),
    sveltekit({
      compilerOptions: {
        // Force runes mode for the project, except for libraries. Can be removed in svelte 6.
        runes: ({ filename }) =>
          filename.split(/[/\\]/).includes('node_modules') ? undefined : true
      },
      preprocess: vitePreprocess(),
      adapter: adapter(),
      alias: {
        '@/*': './path/to/lib/*'
      },
      csrf: {
        trustedOrigins: ['*']
      },
      typescript: {
        config: (config) => {
          config.include.push('../drizzle.config.ts');
        }
      }
    })
  ],
  optimizeDeps: {
    exclude: ['lightningcss', 'lightningcss-linux-x64-gnu', '@tailwindcss/node']
  },
  server: {
    port: 5173,
    host: true
  }
});
