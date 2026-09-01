import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { StudyContext } from '../../types/study-context'
import { StructureMeasurementPreparation } from './StructureMeasurementPreparation'

const nestedContext: StudyContext = {
  schemaVersion: '1.0.0',
  timeStructure: 'cross_sectional',
  dependenceStructure: 'nested',
  design: 'observational',
}

describe('StructureMeasurementPreparation', () => {
  it('shows cluster profile and keeps aggregation evidence distinct from multilevel modeling', () => {
    render(
      <StructureMeasurementPreparation
        context={nestedContext}
        roles={{
          subjectId: null,
          clusterId: 'team_id',
          timeId: null,
          groupId: null,
          treatmentId: null,
          dataLayout: 'long',
          waveCount: null,
        }}
        profile={{
          rowCount: 120,
          missingRoleCounts: {},
          subjectCount: null,
          clusterCount: 24,
          singletonClusterCount: 0,
          clusterSize: { minimum: 3, median: 5, maximum: 8 },
          duplicateSubjectTimeCount: null,
          observationsPerSubject: null,
          timePointCount: 1,
          nestingClassification: 'two_level',
        }}
        measurement={{ id: 'measurement_demo', hash: 'a'.repeat(64) }}
        variables={[{ id: 'team_id', label: '团队编号' }]}
      />,
    )

    expect(screen.getByRole('heading', { name: '嵌套横截面测量与聚合准备' })).toBeInTheDocument()
    expect(screen.getByText('团队编号')).toBeInTheDocument()
    expect(screen.getByText('24 组 · 3–8 人/组')).toBeInTheDocument()
    expect(screen.getByText(/聚合证据只说明组层构念/)).toBeInTheDocument()
    expect(screen.getByText(/组间差异\/多组等值性的分组变量与 cluster 聚合变量是不同角色/)).toBeInTheDocument()
  })
})
