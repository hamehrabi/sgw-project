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
  // **And `fullyParallel: false` is not what delivers that sentence.** It keeps the tests inside
  // one file serial and in declaration order; separate files still run in **parallel workers**,
  // and on this machine that was seven files at once against one SQLite file. Three of the seven
  // load the same storm, and TASK-008's first case files a damage report — so ATEST-007's *the
  // empty board reads "no damage reported"*, whose own docstring rests on *"nothing else in the
  // suite files a damage report"*, was racing a file that does. It won the race for two tasks and
  // lost it the moment anything shifted the timing, which is a green that was never evidence.
  // A flaky end-to-end test is a finding, and the finding here is the shared database rather than
  // any one case: serial is the only reading of it that is true.
  workers: 1,
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
