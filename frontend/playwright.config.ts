import { defineConfig, devices } from '@playwright/test'

/**
 * End-to-end configuration.
 *
 * The suite runs against an already-running dev stack (API on :8000, Vite on
 * :5173) and drives a real Chromium in a phone-sized viewport, because
 * mobile is the primary way this directory will be used.
 */
export default defineConfig({
  testDir: './e2e',
  timeout: 90_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://127.0.0.1:5173',
    // Use whichever Chromium the environment already provides, rather than
    // downloading one that matches this @playwright/test build exactly.
    ...(process.env.CHROMIUM_PATH ? { launchOptions: { executablePath: process.env.CHROMIUM_PATH } } : {}),
    locale: 'ar-LB',
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
  projects: [
    {
      name: 'mobile-chromium',
      use: {
        ...devices['Pixel 7'],
        launchOptions: {
          args: ['--no-sandbox'],
          ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}),
        },
      },
    },
  ],
})
