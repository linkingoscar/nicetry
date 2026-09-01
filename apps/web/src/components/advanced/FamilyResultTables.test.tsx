import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { FamilyResultTables } from './FamilyResultTables'

describe('FamilyResultTables', () => {
  it.each([
    {
      family: 'experimental_design',
      result: { family: 'experimental_design', omnibusTests: [{ term: 'phase', f: 4.2 }], estimatedMarginalMeans: [], contrasts: [], plannedContrasts: [] },
      table: '总体效应检验',
    },
    {
      family: 'multilevel_model',
      result: { family: 'multilevel_model', fixedEffects: [{ term: 'Days', Estimate: 10.4 }], fitIndices: { AIC: 1755.6 } },
      table: 'Fixed effects',
    },
    {
      family: 'longitudinal_model',
      result: { family: 'longitudinal_model', waveSampleFlow: [{ wave: 'T3', observed: 360, attritionFromPrevious: 40 }], missingPatterns: '{"complete": 360}' },
      table: 'Wave sample flow',
    },
    {
      family: 'multiple_imputation',
      result: { family: 'multiple_imputation', missingInformation: [{ variableId: 'income', missingRate: 0.2 }] },
      table: '缺失信息',
    },
    {
      family: 'questionnaire_measurement',
      result: {
        family: 'questionnaire_measurement',
        modelType: 'cfa',
        cfa: {
          itemIds: ['q1', 'q2'],
          standardizedLoadings: [0.72, 0.81],
          cfi: 0.97,
          rmsea: 0.04,
        },
      },
      table: 'CFA 拟合指标',
    },
  ])('renders a dedicated $family table', ({ result, table }) => {
    render(<FamilyResultTables familyResult={result} />)
    expect(screen.getByRole('table', { name: table })).toBeInTheDocument()
  })
})
