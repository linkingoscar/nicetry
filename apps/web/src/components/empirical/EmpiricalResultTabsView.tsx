import type React from 'react'
import { LongitudinalMethodsSection } from './LongitudinalMethodsSection'
import { metric, probability } from './resultFormatters'
import { EmpiricalOverviewTab } from './EmpiricalOverviewTab'
import { EmpiricalCorrelationTab } from './EmpiricalCorrelationTab'
import { EmpiricalMeasurementTab } from './EmpiricalMeasurementTab'
import { EmpiricalValidityTab } from './EmpiricalValidityTab'
import { EmpiricalRegressionTab } from './EmpiricalRegressionTab'
import { SectionErrorBoundary } from '../shared/SectionErrorBoundary'
import type { EmpiricalResultTab } from './EmpiricalResultsNav'
import type { EmpiricalAnalysisOptions } from '../../types'
import type { EmpiricalResultQueries } from './segmentQuery'

interface EmpiricalResultTabsViewProps {
  activeTab: EmpiricalResultTab
  reportId: string
  datasetId: string
  measurementVersion: number | null
  reportOptions: Pick<EmpiricalAnalysisOptions, 'correlationMethod'>
  queries: EmpiricalResultQueries
  showToast: (msg: string) => void
}

export const EmpiricalResultTabsView: React.FC<EmpiricalResultTabsViewProps> = ({
  activeTab,
  reportId,
  datasetId,
  measurementVersion,
  reportOptions,
  queries,
  showToast,
}) => {
  return (
    <SectionErrorBoundary
      resetKey={`${reportId}-${activeTab}`}
      title="本结果分区暂时无法显示"
    >
      <div
        role="tabpanel"
        id={`empirical-panel-${activeTab}`}
        aria-labelledby={`empirical-tab-${activeTab}`}
        style={{ outline: 'none' }}
      >
        {activeTab === 'overview' && (
          <EmpiricalOverviewTab query={queries.summary} showToast={showToast} />
        )}

        {activeTab === 'correlation' && (
          <EmpiricalCorrelationTab query={queries.correlation} reportOptions={reportOptions} />
        )}

        {activeTab === 'measurement' && (
          <>
            <EmpiricalMeasurementTab query={queries.efaCfa} summaryQuery={queries.summary} />
            <EmpiricalValidityTab query={queries.validity} />
          </>
        )}

        {['groups', 'regression', 'advanced'].includes(activeTab) && (
          <EmpiricalRegressionTab query={queries.regression} activeTab={activeTab} />
        )}

        {activeTab === 'longitudinal' || activeTab === 'diary' ? (
          <LongitudinalMethodsSection
            method={activeTab}
            datasetId={datasetId}
            measurementVersion={measurementVersion}
            reportId={reportId}
            metric={metric}
            probability={probability}
          />
        ) : null}
      </div>
    </SectionErrorBoundary>
  )
}
