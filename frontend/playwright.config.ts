import path from 'node:path'

import { defineConfig } from '@playwright/test'

// Absolute, and platform-aware. A relative command is resolved by the shell rather than by
// Node, and `cmd.exe` does not accept `../` at the start of one.
const repoRoot = path.resolve(__dirname, '..')
const python = path.join(
  repoRoot,
  '.venv',
  process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python',
)
const backendEntry = path.join(repoRoot, 'ci', 'e2e_backend.py')

/**
 * The browser suite starts **both** processes (ADR-008) and drives the real thing: a real
 * Chromium against a real Next.js server proxying to a real FastAPI backend against a real
 * SQLite file. Nothing here is mocked, because the failures worth catching at this level are
 * the ones that only appear when the two processes have to agree.
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false, // one backend, one database, one storm at a time
  forbidOnly: !!process.env.CI,
  retries: 0, // a flaky end-to-end test is a finding, not something to paper over
  reporter: process.env.CI ? 'list' : [['list']],
  use: {
    baseURL: 'http://127.0.0.1:3100',
    trace: 'retain-on-failure',
  },
  webServer: [
    {
      command: `"${python}" "${backendEntry}"`,
      url: 'http://127.0.0.1:8100/api/v1/health',
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: 'npm run dev -- --port 3100',
      url: 'http://127.0.0.1:3100',
      reuseExistingServer: false,
      timeout: 180_000,
      env: { API_ORIGIN: 'http://127.0.0.1:8100' },
    },
  ],
})
