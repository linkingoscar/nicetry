import { expect, test } from '@playwright/test'

import {
  expectNoHorizontalOverflow,
  expectNoSeriousAccessibilityViolations,
  installPageFailureMonitor,
} from './quality'
import {
  configureMethod,
  openAdvancedProcessEditor,
  openAnalysisLibrary,
  openAuthenticatedPage,
  openDataWorkspace,
} from './session'

async function chooseExistingData(page: Parameters<typeof openAuthenticatedPage>[0]) {
  await openDataWorkspace(page)
}

async function importQuestionnaireDemo(page: Parameters<typeof openAuthenticatedPage>[0]) {
  await chooseExistingData(page)
  await page.getByRole('radio', { name: /单次 \/ 横截面/ }).click()
  await page.getByRole('radio', { name: /观测相互独立/ }).click()
  await expect(page.getByRole('heading', { name: '导入单次 / 横截面数据' })).toBeVisible()
  await page.getByRole('button', { name: '一键导入经典问卷示例项目' }).click()
  await page.getByRole('tab', { name: '量表', exact: true }).click()
  await expect(page.getByText('测量层已完成 · v1')).toBeVisible()
  await expect(page.getByText('尚未创建数据版本')).toHaveCount(0)
}

async function profileAndSaveCurrentStructure(page: Parameters<typeof openAuthenticatedPage>[0]) {
  await page.getByRole('button', { name: '运行结构画像' }).click()
  await expect(page.getByText(/本次画像：/)).toBeVisible()
  const structureOverrideReason = page.getByLabel('继续使用的学术理由（至少 10 个字符）')
  if (await structureOverrideReason.isVisible()) {
    await structureOverrideReason.fill('已核对观测单位、时间索引与结构画像，保留该结构用于对应研究设计。')
  }
  await page.getByRole('button', { name: '保存结构版本' }).click()
  await expect(page.getByText('当前角色与服务端已保存的结构版本一致，可以继续进入下游工作流。')).toBeVisible()
  await page.getByRole('tab', { name: '量表', exact: true }).click()
}

test('@smoke keeps planning, context boundaries, and the entry workflow independently usable', async ({ page }) => {
  const failures = await installPageFailureMonitor(page)

  await openAuthenticatedPage(page)
  await expect(page.getByRole('heading', { name: '本地点按式实证分析工作台' })).toBeVisible()
  await page.getByRole('button', { name: /功效与研究规划/ }).click()
  await expect(page.getByRole('heading', { name: '把研究问题、估计对象和分析边界保存成可审计计划' })).toBeVisible()
  await expect(page.getByRole('heading', { name: '编辑研究设计计划' })).toBeVisible()
  await page.getByLabel('计划标题').fill('E2E 研究计划')
  await page.getByLabel('研究问题').fill('当前上下文下的结果变量是否存在预设方向的变化？')
  await page.getByLabel('Estimand / 估计对象').fill('回归 R2 增量')
  await page.getByRole('button', { name: '保存研究计划草稿' }).click()
  await expect(page.getByText(/草稿 revision/)).toBeVisible()

  await page.getByRole('button', { name: '项目首页' }).click()
  await page.getByRole('button', { name: /导入数据并开始分析/ }).click()
  await page.getByRole('radio', { name: /单次 \/ 横截面/ }).click()
  await page.getByRole('radio', { name: /存在聚类/ }).click()
  await expect(page.getByText(/普通独立样本回归不会被默认推荐/)).toBeVisible()
  await expect(page.getByRole('tab', { name: '数据', exact: true })).toBeVisible()
  await expect(page.getByRole('tab', { name: '分析', exact: true })).toBeVisible()
  await expect(page.getByRole('tab', { name: '输出', exact: true })).toBeVisible()
  await page.getByRole('radio', { name: /观测相互独立/ }).click()
  await page.getByRole('radio', { name: '随机实验' }).click()
  await expect(page.getByRole('tab', { name: '分析', exact: true })).toBeVisible()
  await page.getByRole('radio', { name: '观察性' }).click()
  await expectNoSeriousAccessibilityViolations(page)

  await failures.expectClean()
})

test('prepares nested cross-sectional measurement without conflating cluster and group roles', async ({ page }) => {
  test.setTimeout(120_000)
  const failures = await installPageFailureMonitor(page)

  await importQuestionnaireDemo(page)
  await expect(page.getByRole('button', { name: '进入横截面实证分析' })).toBeVisible()
  await page.getByRole('button', { name: '修改研究结构' }).click()
  await page.getByRole('radio', { name: /存在聚类/ }).click()
  await page.getByRole('button', { name: '数据结构', exact: true }).click()
  await expect(page.getByRole('heading', { name: '确认观测单位、索引与处理变量', exact: true })).toBeVisible()
  const clusterRole = page.getByRole('combobox', { name: /聚类 \/ Level 2 ID/ })
  await clusterRole.selectOption({ label: 'group (group)' })
  await profileAndSaveCurrentStructure(page)
  await expect(page.getByRole('heading', { name: '嵌套横截面测量与聚合准备' })).toBeVisible()
  await expect(page.getByText(/聚合证据只说明组层构念是否值得讨论/)).toBeVisible()
  await expect(page.getByText(/分组变量与 cluster 聚合变量是不同角色/)).toBeVisible()
  await expect(page.getByRole('button', { name: '进入横截面嵌套分析' })).toBeVisible()
  await expectNoSeriousAccessibilityViolations(page)

  await page.getByRole('button', { name: '进入横截面嵌套分析' }).click()
  await expect(page.getByRole('heading', { name: '分析方法', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: '配置组间差异检验', exact: true })).toHaveCount(0)
  await configureMethod(page, 'ICC 与聚合诊断')
  await page.getByLabel('Cluster ID').selectOption('group')
  await page.getByLabel(/构成团队层构念的题项/).selectOption(['autonomy_1', 'autonomy_2', 'autonomy_3'])
  const acceptedRun = page.waitForResponse((response) => (
    response.request().method() === 'POST'
    && response.url().endsWith('/advanced-analyses')
    && response.status() === 202
  ))
  await page.getByRole('button', { name: '检查设置', exact: true }).click()
  await expect(page.getByText('设置检查通过，可以运行分析')).toBeVisible()
  await page.getByRole('button', { name: '运行分析', exact: true }).click()
  const runId = (await (await acceptedRun).json() as { id: string }).id
  await expect.poll(async () => page.evaluate(async (id) => {
    const token = window.sessionStorage.getItem('researchpath.sessionToken')
    const response = await fetch(`/api/v1/advanced-analyses/${id}`, {
      headers: token ? { 'x-researchpath-token': token } : {},
    })
    const job = await response.json() as { status: string; error?: string | null }
    if (job.status === 'failed') throw new Error(job.error ?? 'nested 实证分析失败')
    return job.status
  }, runId), { timeout: 90_000 }).toBe('succeeded')
  await expect(page.getByRole('heading', { name: 'ICC 与聚合诊断 — 结果' })).toBeVisible({ timeout: 15_000 })
  await expect(page.getByRole('heading', { name: '描述统计与分布诊断' })).toHaveCount(0)
  await expect(page.getByRole('tab', { name: /相关与矩阵/ })).toHaveCount(0)

  await failures.expectClean()
})

test('keeps the panel-specific structure and measurement path independently reachable', async ({ page }) => {
  const failures = await installPageFailureMonitor(page)

  await chooseExistingData(page)
  await page.getByRole('radio', { name: /追踪面板/ }).click()
  await page.getByRole('radio', { name: /观测相互独立/ }).click()
  await expect(page.getByRole('heading', { name: '导入追踪面板数据' })).toBeVisible()
  await page.getByRole('button', { name: '一键导入追踪面板示例项目' }).click()
  await expect(page.getByText('longitudinal-panel-demo.csv').first()).toBeVisible()
  await page.getByRole('button', { name: '数据结构', exact: true }).click()
  await expect(page.getByRole('combobox', { name: /个体 \/ 研究对象 ID/ })).not.toHaveValue('')
  await expect(page.getByRole('combobox', { name: /面板数据布局/ })).toHaveValue('wide')
  await expect(page.getByRole('spinbutton', { name: /波次数/ })).toHaveValue('5')
  await profileAndSaveCurrentStructure(page)

  await expect(page.getByRole('heading', { name: '纵向题项与跨波次测量' })).toBeVisible()
  await expect(page.getByText(/宽格式面板/)).toBeVisible()
  await page.getByRole('button', { name: '进入纵向面板分析' }).click()
  await configureMethod(page, '传统 CLPM')
  await expect(page.locator('.analysis-shell-header h1')).toHaveText('纵向面板模型')
  await expect(page.getByText(/传统 CLPM 与 RI-CLPM 至少三时点/)).toBeVisible()
  await expectNoSeriousAccessibilityViolations(page)

  await failures.expectClean()
})

test('keeps the diary-specific person-time preparation path independently reachable', async ({ page }) => {
  const failures = await installPageFailureMonitor(page)

  await chooseExistingData(page)
  await page.getByRole('radio', { name: /密集追踪/ }).click()
  await page.getByRole('radio', { name: /观测相互独立/ }).click()
  await expect(page.getByRole('heading', { name: '导入密集追踪数据' })).toBeVisible()
  await page.getByRole('button', { name: '一键导入密集追踪示例项目' }).click()
  await expect(page.getByText('daily-diary-demo.csv').first()).toBeVisible()
  await page.getByRole('button', { name: '数据结构', exact: true }).click()
  await expect(page.getByRole('combobox', { name: /个体 \/ 研究对象 ID/ })).not.toHaveValue('')
  await expect(page.getByRole('combobox', { name: /波次 \/ 时间变量/ })).not.toHaveValue('')
  await profileAndSaveCurrentStructure(page)

  await expect(page.getByRole('heading', { name: '日记 / ESM 题项与时点测量' })).toBeVisible()
  await expect(page.getByText(/person × time/)).toBeVisible()
  await page.getByRole('button', { name: '进入日记 / ESM 分析' }).click()
  await configureMethod(page, '日记 / ESM 数据质量')
  await expect(page.locator('.analysis-shell-header h1')).toHaveText('日记 / ESM 模型')
  await expect(page.getByText(/重复日\/时点嵌套于被试/)).toBeVisible()
  await expectNoSeriousAccessibilityViolations(page)

  await failures.expectClean()
})

test('@real-r runs one browser-to-API-to-real-R empirical analysis and renders its result', async ({ page }) => {
  test.setTimeout(120_000)
  const failures = await installPageFailureMonitor(page)

  await importQuestionnaireDemo(page)
  await page.getByRole('button', { name: '进入横截面实证分析' }).click()
  await configureMethod(page, '描述统计')
  const acceptedRun = page.waitForResponse((response) => (
    response.request().method() === 'POST'
    && response.url().includes('/empirical-analysis')
    && response.status() === 202
  ))
  await page.getByRole('checkbox', { name: '工作自主性', exact: true }).check()
  await page.getByRole('button', { name: '运行描述统计' }).click()
  const runId = (await (await acceptedRun).json() as { id: string }).id
  // A selected descriptive run may finish before a cancellation control is painted.
  await expect(page.getByRole('combobox', { name: /运行记录/ })).toHaveValue(runId)

  let terminalJob: { status: string; error?: string | null } | null = null
  await expect.poll(async () => {
    terminalJob = await page.evaluate(async (id) => {
      const token = window.sessionStorage.getItem('researchpath.sessionToken')
      const response = await fetch(`/api/v1/analyses/${id}`, {
        headers: token ? { 'x-researchpath-token': token } : {},
      })
      return response.json() as Promise<{ status: string; error?: string | null }>
    }, runId)
    if (terminalJob?.status === 'failed') {
      throw new Error(`真实 R 实证分析失败：${terminalJob.error ?? '未返回错误详情'}`)
    }
    return terminalJob?.status
  }, {
    message: '真实 R 实证分析应成功完成',
    timeout: 90_000,
  }).toBe('succeeded')
  expect(terminalJob?.error ?? null).toBeNull()
  await expect(page.getByRole('heading', { name: '描述统计与分布诊断' })).toBeVisible({
    timeout: 15_000,
  })
  const autonomyRow = page.getByRole('row', { name: /工作自主性/ }).first()
  await expect(autonomyRow).toBeVisible()
  await expect(autonomyRow).toContainText(/\d/)
  await expect(page.getByRole('heading', { name: '验证性因子分析' })).toHaveCount(0)
  await configureMethod(page, '相关与偏相关')
  await expect(page.getByRole('heading', { name: '描述统计与分布诊断' })).toHaveCount(0)
  // Each method now owns its draft; correlation must explicitly select both variables.
  await page.getByRole('checkbox', { name: '工作自主性', exact: true }).check()
  await page.getByRole('checkbox', { name: '工作投入', exact: true }).check()
  await page.getByRole('button', { name: '运行相关分析', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Pearson 相关矩阵' })).toBeVisible({ timeout: 45_000 })
  await expect(page.getByRole('rowheader', { name: '2. 工作投入', exact: true })).toBeVisible()
  await page.reload()
  await configureMethod(page, '描述统计')
  await expect(page.getByRole('combobox', { name: /运行记录/ }).getByRole('option')).toHaveCount(2)
  await page.getByRole('combobox', { name: /运行记录/ }).selectOption(runId)
  await expect(page.getByRole('heading', { name: '描述统计与分布诊断' })).toBeVisible()
  await page.setViewportSize({ width: 390, height: 844 })
  await expectNoHorizontalOverflow(page)
  await expectNoSeriousAccessibilityViolations(page)

  await failures.expectClean()
})

test('@smoke @a11y keeps model-canvas inference language, accessibility, and mobile layout honest', async ({ page }) => {
  const failures = await installPageFailureMonitor(page, {
    classifyModelCanvasResizeLoop: true,
  })

  await importQuestionnaireDemo(page)
  await expect(page.getByRole('button', { name: '修改研究结构' })).toBeVisible()
  await expect(page.getByRole('button', { name: '进入横截面实证分析' })).toBeVisible()
  await page.getByRole('button', { name: '进入横截面实证分析' }).click()
  await configureMethod(page, '相关与偏相关')
  await expect(page.getByText('纵向与日记高级流程')).toHaveCount(0)

  await openAdvancedProcessEditor(page)
  await expect(page.getByRole('heading', { name: '模型画布与预运行检查' })).toBeVisible()
  await expect(page.getByText('55 个编号可识别，执行以检查为准')).toBeVisible()
  await expect(page.getByText('区间不含 0 / p<.05（非理论支持）')).toBeVisible()
  await expect(page.getByText('区间含 0 / p≥.05（非无效证据）')).toBeVisible()
  await expect(page.getByText('证据未支持')).toHaveCount(0)
  await expectNoSeriousAccessibilityViolations(page)

  await page.getByRole('button', { name: '添加 W' }).click()
  await page.getByRole('button', { name: '2 · 路径与调节' }).click()
  const manualMap = page.getByRole('group', { name: /自由构建/ })
  const directPath = manualMap.locator('.manual-moderation-row').filter({ hasText: 'X→Y' })
  await directPath.getByRole('button', { name: 'W', exact: true }).click()
  await expect(page.getByText('PROCESS Model 5', { exact: true }).first()).toBeVisible()

  await directPath.getByRole('button', { name: 'W', exact: true }).click()
  await page.getByRole('button', { name: '1 · 变量与控制' }).click()
  await page.getByRole('button', { name: '添加 Z' }).click()
  await page.getByRole('button', { name: '2 · 路径与调节' }).click()
  const firstStagePath = manualMap.locator('.manual-moderation-row').filter({ hasText: 'X→M' })
  await firstStagePath.getByRole('button', { name: 'W', exact: true }).click()
  await firstStagePath.getByRole('button', { name: 'Z', exact: true }).click()
  await expect(page.getByRole('region', { name: '调节效应Z乘X→M统计详情', exact: true })).toBeVisible()
  await expect(page.getByText('PROCESS Model 9', { exact: true }).first()).toBeVisible()
  await expect(page.getByText('估计模式：PROCESS (OLS)')).toBeVisible()
  const runModelButton = page.getByRole('button', { name: '运行模型分析与估计' })
  await expect(runModelButton).toBeDisabled()
  const overrideReason = page.getByPlaceholder('记录方法警告的处理与解释边界')
  if (await overrideReason.isVisible()) {
    await overrideReason.fill('横截面模型仅解释条件间接关联，不作因果推断。')
  }
  await expect(page.getByRole('button', { name: '冻结并确定模型版本' })).toBeEnabled()
  await expectNoSeriousAccessibilityViolations(page)

  await page.getByRole('button', { name: '3 · 估计设置' }).click()
  const semToggle = page.getByRole('button', { name: 'lavaan (SEM 结构方程)' }).first()
  if (await semToggle.count()) {
    page.once('dialog', dialog => dialog.accept())
    await semToggle.click()
    await page.getByRole('button', { name: '1 · 变量与控制' }).click()
    await expect(page.getByText('潜变量与测量指标', { exact: true })).toBeVisible()
    await expect(page.getByRole('region', { name: '模型节点 Y', exact: true })).toContainText('个题项指标')
    await expectNoSeriousAccessibilityViolations(page)
  }

  await page.setViewportSize({ width: 390, height: 844 })
  await expect(page.getByRole('heading', { name: '模型画布与预运行检查' })).toBeVisible()
  await expectNoHorizontalOverflow(page)

  await failures.expectClean()
})


test('@smoke keeps method discovery compact, searchable, keyboard accessible and recoverable', async ({ page }) => {
  const failures = await installPageFailureMonitor(page)
  await page.setViewportSize({ width: 1280, height: 900 })
  await importQuestionnaireDemo(page)
  await openAnalysisLibrary(page)
  await expect(page.getByRole('searchbox', { name: '搜索方法' })).toBeVisible()
  const firstMethod = page.getByRole('button', { name: '配置描述统计' })
  await expect(firstMethod).toBeInViewport()
  const bounds = await firstMethod.boundingBox()
  expect(bounds!.y + bounds!.height).toBeLessThan(760)
  await expect(page.getByRole('radio', { name: /单次/ })).not.toBeVisible()
  await expect(page.locator('.context-hash')).not.toBeVisible()
  await expect(page.getByRole('tab', { name: '分析', exact: true })).toContainText('可配置')
  await page.screenshot({ path: 'output/playwright/usability-desktop.png' })

  await page.getByRole('tab', { name: '分析', exact: true }).focus()
  await page.keyboard.press('Home')
  await expect(page.getByRole('tab', { name: '数据', exact: true })).toBeFocused()
  await page.keyboard.press('End')
  await expect(page.getByRole('tab', { name: '输出', exact: true })).toHaveAttribute('aria-selected', 'true')
  await openAnalysisLibrary(page)

  await page.getByRole('searchbox', { name: '搜索方法' }).fill('没有这种方法')
  await expect(page.getByText(/没有匹配的方法/)).toBeVisible()
  await page.getByRole('button', { name: '清除筛选' }).click()
  await page.getByRole('combobox', { name: '研究任务' }).selectOption('regression')
  await page.getByRole('searchbox', { name: '搜索方法' }).fill('线性 / 分层回归')
  await expect(page.getByRole('article')).toHaveCount(1)
  await page.getByRole('button', { name: '配置线性 / 分层回归' }).click()
  await expect(page.getByRole('tab', { name: '分析', exact: true })).toHaveAttribute('aria-selected', 'true')
  await expect(page.getByRole('button', { name: '运行分层线性回归', exact: true })).toBeVisible()

  await openAnalysisLibrary(page)
  await page.getByRole('combobox', { name: '研究任务' }).selectOption('power')
  await page.getByRole('button', { name: '配置回归解析功效' }).click()
  await expect(page.getByRole('heading', { name: '回归解析功效', exact: true })).toBeVisible()
  await expect(page.getByRole('searchbox', { name: '搜索方法' })).toHaveCount(0)
  await page.getByRole('button', { name: '返回方法库', exact: true }).click()
  await expect(page.getByRole('button', { name: '配置回归解析功效' })).toBeFocused()
  await expect(page.getByRole('combobox', { name: '研究任务' })).toHaveValue('power')
  await page.getByRole('button', { name: '清除筛选' }).click()
  await page.getByText('版本与诊断详情', { exact: true }).click()
  await expect(page.locator('.context-hash')).toBeVisible()
  await page.getByText('版本与诊断详情', { exact: true }).click()
  await expectNoSeriousAccessibilityViolations(page)

  await page.getByRole('button', { name: '明亮模式', exact: true }).click()
  await expect(page.getByRole('button', { name: '暗色模式', exact: true })).toBeVisible()
  await expectNoSeriousAccessibilityViolations(page)
  await page.screenshot({ path: 'output/playwright/usability-dark.png' })
  await page.setViewportSize({ width: 390, height: 844 })
  await expect(page.getByRole('tab', { name: '分析', exact: true })).toBeInViewport()
  await expectNoHorizontalOverflow(page)
  await expectNoSeriousAccessibilityViolations(page)
  await page.screenshot({ path: 'output/playwright/usability-mobile.png' })
  await failures.expectClean()
})
