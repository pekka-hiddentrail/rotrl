import { defineConfig, devices } from '@playwright/test'

// Live integration tests — hit the real FastAPI backend + Claude Haiku.
// Requires:
//   1. ANTHROPIC_API_KEY in .env (or environment)
//   2. FastAPI backend running:  python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
//
// Run:  npx playwright test --config playwright.live.config.ts
// UI:   npx playwright test --config playwright.live.config.ts --ui

export default defineConfig({
  testDir: './e2e',
  testMatch: '**/live-flows.spec.ts',

  // LLM calls can take up to ~60 s; give each test plenty of room.
  timeout: 120_000,
  expect: { timeout: 60_000 },

  // Run tests in sequence — each one may leave backend state that affects the next.
  fullyParallel: false,

  reporter: [['list']],

  use: {
    baseURL: 'http://127.0.0.1:5173',
    // Always capture a trace so failures in LLM calls are fully reproducible.
    trace: 'on',
  },

  // Auto-start the Vite dev server; backend must be started manually (see above).
  webServer: {
    command: 'npm run dev -- --host 127.0.0.1',
    url: 'http://127.0.0.1:5173',
    reuseExistingServer: true,
    timeout: 30_000,
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
})
