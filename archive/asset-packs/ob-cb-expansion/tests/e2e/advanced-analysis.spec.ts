import { test, expect } from '@playwright/test'

import { openAuthenticatedPage } from './session'

test.describe('Advanced Analysis Flow', () => {
  test.beforeEach(async ({ page }) => {
    await openAuthenticatedPage(page)
    await expect(page.getByRole('heading', { name: '导入问卷数据' })).toBeVisible()
    
    // Create a dummy project (e.g., using demo data)
    await page.getByRole('button', { name: '一键导入经典问卷示例项目' }).click()
    await expect(page.getByRole('heading', { name: '模型画布与预运行检查' })).toBeVisible()
  })

  test('can navigate to advanced analysis, validate spec, and submit', async ({ page }) => {
    const advancedLink = page.getByRole('button', { name: /高级统计方法/ })
    await expect(advancedLink).toBeEnabled()
    await advancedLink.click()

    await expect(
      page.getByRole('button', { name: /组间与受限重复测量实验切片/ }),
    ).toBeVisible()
    const powerCapability = page.getByRole('button', { name: /回归与组间 ANOVA 解析功效/ })
    await expect(powerCapability).toBeVisible()

    // Select Power Analysis
    await powerCapability.click()

    // Wizard Step 1: Config
    await expect(page.getByText('回归与组间 ANOVA 解析功效 — 规格配置')).toBeVisible()
    await expect(page.getByRole('spinbutton', { name: /显著性水平/ })).toBeVisible()

    // Validate
    await page.getByRole('button', { name: '验证规格' }).click()

    // Wizard Step 2: Validation Summary
    await expect(page.getByRole('heading', { name: '验证摘要' })).toBeVisible()
    await expect(page.getByText(/规格有效，可以提交运行/)).toBeVisible()

    // Submit
    await page.getByRole('button', { name: '提交后台运行' }).click()

    // Job Progress
    await expect(page.getByRole('region', { name: '分析进度' })).toBeVisible()
    
    await expect(
      page.getByRole('heading', { name: '回归与组间 ANOVA 解析功效 — 结果' }),
    ).toBeVisible({ timeout: 15_000 })
    await expect(page.getByText('详细结果')).toBeVisible()
    await expect(page.getByRole('table', { name: '参数估计' })).toBeVisible()
  })

  test('runs an experimental ANOVA against the active dataset and renders EMM confidence intervals', async ({ page }) => {
    const datasetId = await page.evaluate(() => localStorage.getItem('researchpath_active_dataset_id'))
    expect(datasetId).toBeTruthy()
    const datasetResponse = await page.request.get(
      `http://localhost:9999/api/v1/datasets/${datasetId}`,
    )
    expect(datasetResponse.ok()).toBeTruthy()
    const dataset = (await datasetResponse.json()) as {
      variables: Array<{ id: string; originalName: string }>
    }
    const outcomeId = dataset.variables.find((variable) => variable.originalName === 'age')?.id
    const factorId = dataset.variables.find((variable) => variable.originalName === 'group')?.id
    expect(outcomeId).toBeTruthy()
    expect(factorId).toBeTruthy()

    await page.getByRole('button', { name: /高级统计方法/ }).click()
    await page.getByRole('button', { name: /组间与受限重复测量实验切片/ }).click()
    await page.getByRole('button', { name: '高级 JSON 编辑' }).click()
    const spec = {
      schemaVersion: '0.1.0',
      analysisId: 'e2e-experimental-emm',
      name: 'E2E experimental EMM',
      confidenceLevel: 0.95,
      seed: 20260719,
      family: 'experimental_design',
      designType: 'factorial_anova',
      dataLayout: 'long',
      datasetVersionId: datasetId,
      outcomeIds: [outcomeId],
      betweenFactors: [{ variableId: factorId, coding: 'sum' }],
      sumOfSquares: 'III',
      postHocAdjustment: 'holm',
    }
    await page.getByRole('textbox', { name: '分析规格 JSON' }).fill(JSON.stringify(spec, null, 2))
    await page.getByRole('button', { name: '验证规格' }).click()
    await expect(page.getByText(/规格有效，可以提交运行/)).toBeVisible()
    await page.getByRole('button', { name: '提交后台运行' }).click()

    await expect(
      page.getByRole('heading', { name: '组间与受限重复测量实验切片 — 结果' }),
    ).toBeVisible({ timeout: 30_000 })
    await expect(page.getByRole('img', { name: /Estimated marginal means and confidence intervals/ })).toBeVisible()
    await expect(page.getByRole('table', { name: 'Estimated marginal means' })).toBeVisible()
    await expect(page.getByRole('table', { name: 'Contrasts' })).toBeVisible()
  })

  test('can cancel a running job', async ({ page }) => {
    const advancedLink = page.getByRole('button', { name: /高级统计方法/ })
    await expect(advancedLink).toBeEnabled()
    await advancedLink.click()

    await page.getByRole('button', { name: /回归与组间 ANOVA 解析功效/ }).click()
    await page.getByRole('button', { name: '验证规格' }).click()
    await expect(page.getByRole('heading', { name: '验证摘要' })).toBeVisible()
    await page.getByRole('button', { name: '提交后台运行' }).click()

    await expect(page.getByRole('region', { name: '分析进度' })).toBeVisible()
    
    const cancelBtn = page.getByRole('button', { name: '取消分析' })
    await expect(cancelBtn).toBeVisible()
    await cancelBtn.click()
    await expect(page.getByRole('heading', { name: '选择分析方法' })).toBeVisible({ timeout: 10_000 })
  })
})
