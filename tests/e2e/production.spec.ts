import { expect, test } from '@playwright/test'

import { previewOrigin, previewSessionToken } from './constants'

test('@production serves the built app and runs one real R mediation', async ({ page, request }) => {
  const origin = previewOrigin()

  await page.addInitScript(
    (sessionToken: string) =>
      window.sessionStorage.setItem('researchpath.sessionToken', sessionToken),
    previewSessionToken,
  )
  await page.goto(`${origin}/`)
  await expect(
    page.getByRole('heading', { name: '你现在处于哪个阶段？' }),
  ).toBeVisible()

  const demoResponse = await request.get(`${origin}/api/v1/demo`)
  expect(demoResponse.ok()).toBeTruthy()
  const demo = (await demoResponse.json()) as { modelSpec?: Record<string, unknown> }
  expect(demo.modelSpec).toBeTruthy()

  const analysisResponse = await request.post(`${origin}/api/v1/analyses/mediation`, {
    headers: { 'X-ResearchPath-Token': previewSessionToken },
    data: { dataset_id: 'mediation-demo', model_spec: demo.modelSpec },
  })
  expect(analysisResponse.ok()).toBeTruthy()
  const result = (await analysisResponse.json()) as {
    run?: { status?: string }
    effects?: unknown[]
  }
  expect(result.run?.status).toBe('succeeded')
  expect(result.effects?.length).toBeGreaterThan(0)
})
