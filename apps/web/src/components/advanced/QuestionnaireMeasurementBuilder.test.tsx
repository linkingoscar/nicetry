import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { QuestionnaireMeasurementSpec } from '../../types/advanced'
import { QuestionnaireMeasurementBuilder } from './QuestionnaireMeasurementBuilder'

const spec: QuestionnaireMeasurementSpec = {
  schemaVersion: '0.1.0',
  analysisId: 'measurement-ui-test',
  name: 'Measurement UI test',
  family: 'questionnaire_measurement',
  datasetVersionId: 'dataset-1',
  confidenceLevel: 0.95,
  seed: 20260714,
  modelType: 'reliability',
  itemIds: ['q1', 'q2', 'q3', 'q4'],
  constructs: [
    { id: 'factor_a', label: 'Factor A', itemIds: ['q1', 'q2'] },
    { id: 'factor_b', label: 'Factor B', itemIds: ['q3', 'q4'] },
  ],
  estimator: 'ML',
  irtModel: 'auto',
  extractionMethod: 'ml',
  itemScale: 'continuous',
  factorCount: 2,
  rotation: 'promax',
  parallelIterations: 1000,
  invarianceLevels: ['configural', 'metric', 'scalar'],
}

describe('QuestionnaireMeasurementBuilder', () => {
  it('renders method-specific fields without exposing a JSON editor', () => {
    render(<QuestionnaireMeasurementBuilder spec={spec} onChange={vi.fn()} />)

    expect(screen.getByRole('heading', { name: '问卷测量配置' })).toBeInTheDocument()
    expect(screen.getByLabelText(/测量题项/)).toBeInTheDocument()
    expect(screen.getAllByText('q1').length).toBeGreaterThan(0)
    expect(screen.queryByLabelText('分析规格 JSON')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: '增加构念' })).toBeInTheDocument()
  })
})
