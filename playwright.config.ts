import { defineConfig, devices } from '@playwright/test'

import { bootstrapToken, previewOrigin, previewSessionToken } from './tests/e2e/constants'

function environmentPort(name: string, fallback: number): number {
  const value = Number.parseInt(process.env[name] ?? String(fallback), 10)
  if (!Number.isInteger(value) || value < 1 || value > 65_535) {
    throw new Error(`${name} 必须是 1—65535 的有效端口`)
  }
  return value
}

const apiPort = environmentPort('RESEARCHPATH_E2E_API_PORT', 19_999)
const webPort = environmentPort('RESEARCHPATH_E2E_WEB_PORT', 15_173)
const apiOrigin = `http://127.0.0.1:${apiPort}`
const webOrigin = `http://127.0.0.1:${webPort}`
const pythonExecutable = process.platform === 'win32'
  ? '..\\..\\.venv\\Scripts\\python.exe'
  : '../../.venv/bin/python'

export default defineConfig({
  testDir: './tests/e2e',
  globalSetup: './tests/e2e/global-setup.ts',
  outputDir: './output/playwright/artifacts',
  timeout: 60_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [['list'], ['html', { outputFolder: './output/playwright/report', open: 'never' }]],
  use: {
    baseURL: webOrigin,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: [
    {
      command: `${pythonExecutable} -m uvicorn app.main:app --host 127.0.0.1 --port ${apiPort}`,
      cwd: './apps/api',
      url: `${apiOrigin}/api/v1/health`,
      env: { RESEARCHPATH_BOOTSTRAP_TOKEN: bootstrapToken },
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command: `npm run dev --workspace @researchpath/web -- --host 127.0.0.1 --port ${webPort} --strictPort`,
      url: webOrigin,
      env: { RESEARCHPATH_API_ORIGIN: apiOrigin },
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command: `${pythonExecutable} -m uvicorn app.main:app --host 127.0.0.1 --port ${environmentPort('RESEARCHPATH_E2E_PREVIEW_API_PORT', 19_998)}`,
      cwd: './apps/api',
      url: `${previewOrigin()}/api/v1/health`,
      env: {
        RESEARCHPATH_BOOTSTRAP_TOKEN: bootstrapToken,
        RESEARCHPATH_SESSION_TOKEN: previewSessionToken,
        RESEARCHPATH_SERVE_WEB: '1',
      },
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
})
