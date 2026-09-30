import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e/specs',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
    ['list']
  ],
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:5173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  projects: [
    // Functional Browser Projects
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
      testIgnore: /.*performance\.spec\.ts$/,
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
      testIgnore: /.*performance\.spec\.ts$/,
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
      testIgnore: /.*performance\.spec\.ts$/,
    },
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
      testIgnore: /.*performance\.spec\.ts$/,
    },

    // Dedicated Non-Functional Performance & Memory Project (isolated from functional gates)
    {
      name: 'perf',
      testMatch: /.*performance\.spec\.ts$/,
      use: {
        ...devices['Desktop Chrome'],
        launchOptions: {
          args: ['--enable-precise-memory-info', '--js-flags=--expose-gc'],
        },
      },
    },
  ],

  webServer: [
    {
      command: 'python -m uvicorn app.main:app --port 8001',
      cwd: '../backend',
      port: 8001,
      reuseExistingServer: !process.env.CI,
      env: {
        DATABASE_URL: 'sqlite:///./data/test_koshi_e2e.db',
        ENVIRONMENT: 'test',
        ALLOW_UNVERIFIED_GOOGLE_TOKENS: 'True',
        SEED_DEMO_DATA: 'True',
      },
    },
    {
      command: 'npm run dev -- --port 5173',
      port: 5173,
      reuseExistingServer: !process.env.CI,
      env: {
        VITE_API_URL: 'http://localhost:8001',
      },
    },
  ],
});
