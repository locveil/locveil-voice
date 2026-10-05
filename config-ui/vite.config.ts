import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { writeFile } from 'node:fs/promises'
import pkg from './package.json' with { type: 'json' }
import fragmentSource from './manifest.fragment.json' with { type: 'json' }

/* UI-17: config-ui builds as the VOICE WORKBENCH PLUGIN (HK-11 runtime assembly) —
   an ESM library with the frozen singleton set external (the shell serves those via
   its import map) plus a build-emitted manifest fragment. The standalone app is
   retired; the shell owns chrome, router, tokens and preflight. */

const SINGLETONS = [
  'react',
  'react-dom',
  'react-dom/client',
  'react/jsx-runtime',
  'react-router-dom',
  'locveil-ui-kit',
]

/* The manifest fragment's SOURCE is ./manifest.fragment.json — id, entry, styles and the
   peer majors the shell refuses-and-surfaces on (contract: ManifestFragment.peers). Only
   `version` is added here, from package.json. Keeping the source as data is what lets the
   workbench pin's conformance test (backend/tests/test_workbench_pin_conformance.py)
   validate exactly what this build emits against the pinned manifest-fragment schema,
   with no build and no Node — change the fragment there, never inline here. */
function emitManifestFragment(): Plugin {
  return {
    name: 'voice-manifest-fragment',
    async writeBundle() {
      const fragment = {
        id: fragmentSource.id,
        version: pkg.version,
        entry: fragmentSource.entry,
        styles: fragmentSource.styles,
        peers: fragmentSource.peers,
      }
      await writeFile(
        path.resolve(__dirname, 'dist/manifest.json'),
        JSON.stringify(fragment, null, 2) + '\n'
      )
    },
  }
}

export default defineConfig({
  plugins: [react(), emitManifestFragment()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    lib: {
      entry: path.resolve(__dirname, 'src/plugin.tsx'),
      formats: ['es'],
      fileName: () => 'index.js',
      cssFileName: 'style',
    },
    rollupOptions: {
      external: SINGLETONS,
    },
    sourcemap: true,
  },
})
