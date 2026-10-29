/// <reference types="vitest/config" />
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const repoRoot = fileURLToPath(new URL('..', import.meta.url))

export default defineConfig({
  plugins: [react()],
  server: {
    // Real sample designs, engine outputs and brand assets are read straight from the repo,
    // never copied into the frontend.
    fs: { allow: ['.', `${repoRoot}input`, `${repoRoot}output`, `${repoRoot}brand_kit`] },
    // Reem's dev API (PLAN §3). Port is a placeholder until docs/api-contract.md lands.
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/__tests__/setup.ts'],
  },
})
