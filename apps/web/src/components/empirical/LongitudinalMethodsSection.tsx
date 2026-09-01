import { useQuery } from '@tanstack/react-query'
import { getEmpiricalSegment } from '../../api'
import { DiaryMultilevelResult } from './DiaryMultilevelResult'
import { LongitudinalPanelResult } from './LongitudinalPanelResult'

interface LongitudinalMethodsSectionProps {
  method: 'longitudinal' | 'diary'
  datasetId: string
  measurementVersion: number | null
  reportId: string
  metric: (value: number | null | undefined, digits?: number) => string
  probability: (value: number | null | undefined) => string
}

export function LongitudinalMethodsSection({
  method,
  datasetId,
  measurementVersion,
  reportId,
  metric,
  probability,
}: LongitudinalMethodsSectionProps) {
  const query = useQuery({
    queryKey: ['empirical-segment', datasetId, measurementVersion, reportId, 'longitudinal'],
    queryFn: () => getEmpiricalSegment(
      datasetId,
      measurementVersion,
      reportId,
      'longitudinal',
    ),
    staleTime: Infinity,
  })

  if (query.isLoading) {
    return <div className="segment-loader">正在载入纵向与多层证据包…</div>
  }
  if (query.isError) {
    return <div className="error-banner">加载纵向模型失败: {String(query.error)}</div>
  }
  return (
    <>
      {method === 'longitudinal' ? (
        query.data?.longitudinalPanel ? (
          <LongitudinalPanelResult
            result={query.data.longitudinalPanel}
            metric={metric}
            probability={probability}
          />
        ) : (
          <div className="empty-analysis-state">
            <strong>本次未配置纵向面板模型</strong>
            <p>请在“纵向与日记高级流程”中配置 CLPM、RI-CLPM 或 LCM-SR 后重新运行。</p>
          </div>
        )
      ) : query.data?.diaryMultilevel ? (
        <DiaryMultilevelResult
          result={query.data.diaryMultilevel}
          metric={metric}
          probability={probability}
        />
      ) : (
        <div className="empty-analysis-state">
          <strong>本次未配置日记 / ESM 模型</strong>
          <p>请在“纵向与日记高级流程”中配置 LMM、GLMM、多层中介或 Bayesian DSEM 后重新运行。</p>
        </div>
      )}
    </>
  )
}
