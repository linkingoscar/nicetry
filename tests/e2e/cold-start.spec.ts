import { spawn } from 'node:child_process'
import { randomUUID } from 'node:crypto'
import { mkdir, mkdtemp } from 'node:fs/promises'
import { resolve } from 'node:path'
import { expect, test } from '@playwright/test'
import { installPageFailureMonitor } from './quality'

for (const source of ['demo', 'upload'] as const) {
  test(`@smoke fresh default research context can be confirmed before ${source}`, async ({ page }) => {
    const parent = resolve('output/playwright')
    await mkdir(parent, { recursive: true })
    const state = await mkdtemp(resolve(parent, 'cold-start-'))
    const token = randomUUID()
    const port = 19996
    const origin = `http://127.0.0.1:${port}`
    const server = spawn(resolve('.venv/Scripts/python.exe'), ['tests/e2e/isolated_api.py', state, String(port), token], { windowsHide: true, stdio: 'ignore' })
    try {
      await expect.poll(async () => {
        if (server.exitCode !== null) throw new Error(`Isolated API exited: ${server.exitCode}`)
        return fetch(`${origin}/api/v1/health`).then(response => response.status).catch(() => 0)
      }).toBe(200)
      const failures = await installPageFailureMonitor(page)
      await page.addInitScript(value => sessionStorage.setItem('researchpath.sessionToken', value), token)
      // Route to the real isolated server; no response fixtures or prewritten study context.
      await page.route('**/api/v1/**', async route => {
        const url = new URL(route.request().url())
        await route.fulfill({ response: await route.fetch({ url: `${origin}${url.pathname}${url.search}` }) })
      })
      await page.goto('/')
      await page.getByRole('button', { name: /分析已有数据/ }).click()
      await expect(page.getByText('研究结构已保存', { exact: true })).toHaveCount(0)
      await page.getByRole('button', { name: '确认并保存研究结构' }).click()
      await expect(page.getByText('研究结构已保存', { exact: true })).toBeVisible()
      if (source === 'demo') {
        await page.getByRole('button', { name: '一键导入经典问卷示例项目' }).click()
        await expect(page.getByText('测量层已完成 · v1')).toBeVisible()
      } else {
        await page.getByLabel('选择数据文件').setInputFiles({ name: 'categories.csv', mimeType: 'text/csv', buffer: Buffer.from('group\nA\nB\nA\nC\n') })
        await page.getByRole('button', { name: '导入并创建数据版本' }).click()
        await page.getByLabel('group的最终类型').selectOption('nominal')
        await page.getByRole('button', { name: '确认全部变量' }).click()
      }
      await page.getByRole('tab', { name: '统计分析', exact: true }).click()
      await expect(page.getByRole('button', { name: '频数分析', exact: true })).toBeVisible()
      await page.reload()
      await expect(page.getByText('研究结构已保存', { exact: true })).toBeVisible()
      await expect(page.getByRole('button', { name: '频数分析', exact: true })).toBeVisible()
      await failures.expectClean()
    } finally {
      server.kill()
      await new Promise<void>(done => { if (server.exitCode !== null) done(); else server.once('exit', () => done()) })
    }
  })
}
