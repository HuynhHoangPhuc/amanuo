import { defineConfig } from 'vite'
import { devtools } from '@tanstack/devtools-vite'
import tsconfigPaths from 'vite-tsconfig-paths'

import { tanstackRouter } from '@tanstack/router-plugin/vite'

import viteReact from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Use Docker service name when running inside container, localhost otherwise
const apiTarget = process.env.VITE_API_URL || 'http://localhost:8000'

const proxyRoutes = [
  '/api', '/schemas', '/jobs', '/pipelines', '/batches',
  '/webhooks', '/extract', '/auth', '/workspaces', '/api-keys', '/health',
]

const proxy = Object.fromEntries(
  proxyRoutes.map((route) => [route, { target: apiTarget, changeOrigin: true }]),
)

const config = defineConfig({
  plugins: [
    devtools(),
    tsconfigPaths({ projects: ['./tsconfig.json'] }),
    tailwindcss(),
    tanstackRouter({ target: 'react', autoCodeSplitting: true }),
    viteReact(),
  ],
  server: {
    port: 3000,
    host: true,
    proxy,
  },
})

export default config
