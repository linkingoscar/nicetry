import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { DatasetVersion } from '../types'
import { registerOutputRun } from './analyses/outputRunRegistry'
import { OutputWorkspace } from './OutputWorkspace'

vi.mock('./analyses/useOutputRunJobs', () => ({ useOutputRunJobs: () => new Map() }))

const dataset = {
  id: 'dataset_current',
  projectId: 'project_demo',
  originalFile: { name: 'demo.csv' },
  dictionary: { version: 1 },
} as DatasetVersion

beforeEach(() => localStorage.clear())

describe('OutputWorkspace registered model and advanced runs', () => {
  it('shows project-level model and advanced run references even without empirical documents', () => {
    registerOutputRun({
      runId: 'run_process_1',
      projectId: dataset.projectId,
      datasetVersionId: dataset.id,
      measurementVersionId: null,
      source: 'model',
      label: '简单中介（PROCESS Model 4）',
      methodId: 'model.process',
      modelId: 'model_demo',
      createdAt: '2026-09-03T10:00:00Z',
    })
    registerOutputRun({
      runId: 'run_anova_1',
      projectId: dataset.projectId,
      datasetVersionId: 'dataset_old',
      measurementVersionId: null,
      source: 'advanced',
      label: '组间析因方差分析',
      methodId: 'experimental_design.factorial_anova.long.single_outcome',
      family: 'experimental_design',
      createdAt: '2026-09-03T11:00:00Z',
    })

    render(<OutputWorkspace dataset={dataset} measurement={null} onOpenProcedure={vi.fn()} />)

    expect(screen.getByRole('heading', { name: '输出索引' })).toBeInTheDocument()
    expect(screen.getByText('简单中介（PROCESS Model 4）')).toBeInTheDocument()
    expect(screen.getByText('组间析因方差分析')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: '还没有运行任何分析' })).not.toBeInTheDocument()
    expect(screen.getAllByText('基于旧设置')).toHaveLength(1)
  })

  it('searches registered runs together with the project output index', () => {
    registerOutputRun({
      runId: 'run_sem_1',
      projectId: dataset.projectId,
      datasetVersionId: dataset.id,
      measurementVersionId: null,
      source: 'model',
      label: '结构方程模型（SEM）',
      methodId: 'model.sem',
      modelId: 'model_sem',
      createdAt: '2026-09-03T10:00:00Z',
    })
    registerOutputRun({
      runId: 'run_lmm_1',
      projectId: dataset.projectId,
      datasetVersionId: dataset.id,
      measurementVersionId: null,
      source: 'advanced',
      label: '两层 Gaussian LMM',
      methodId: 'multilevel_model.gaussian.two_level',
      family: 'multilevel_model',
      createdAt: '2026-09-03T11:00:00Z',
    })

    render(<OutputWorkspace dataset={dataset} measurement={null} onOpenProcedure={vi.fn()} />)
    fireEvent.change(screen.getByLabelText('搜索输出'), { target: { value: 'LMM' } })

    expect(screen.getByText('两层 Gaussian LMM')).toBeInTheDocument()
    expect(screen.queryByText('结构方程模型（SEM）')).not.toBeInTheDocument()
    expect(screen.getByText('显示 1 / 2 项输出')).toBeInTheDocument()
  })
})
