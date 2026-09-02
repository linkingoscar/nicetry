import { useState } from 'react'
import type { UseMutationResult } from '@tanstack/react-query'

import type { DatasetVersion, MeasurementVersion, StudyContext, VariableType } from '../types'
import type { ResolvedAnalysisContext } from '../types/analysis-context'
import { VariableTable } from './VariableTable'
import { MeasurementWorkspace } from './MeasurementWorkspace'
import { DatasetMergeWizard } from './empirical/DatasetMergeWizard'
import { DataQualityWorkspace } from './DataQualityWorkspace'
import { DataStructureSetup } from './DataStructureSetup'
import { StructureMeasurementPreparation } from './context/StructureMeasurementPreparation'
import { DataGridView } from './data/DataGridView'
import { showToast } from './shared/Toast'
import styles from './DataWorkspace.module.css'

interface DataWorkspaceDatasetBodyProps {
  dataset: DatasetVersion
  selectedFile: File | null
  activeSheet: string
  activeError?: Error | null
  importMutation: UseMutationResult<DatasetVersion, Error, { file: File; sheet?: string }>
  dictionaryMutation: UseMutationResult<
    DatasetVersion,
    Error,
    { datasetId: string; variables: Array<{ id: string; confirmedType: VariableType }> }
  >
  activeMeasurement?: MeasurementVersion | null
  studyContext?: StudyContext
  resolvedContext?: ResolvedAnalysisContext | null
  structureKey: string
  structureReady: boolean
  analysisLabel: string
  onSheetChange: (sheet: string) => void
  showMergeWizard: boolean
  onShowMergeWizardChange: (show: boolean) => void
  onMergedDatasetReset: () => void
  onMergeSuccess: (dataset: DatasetVersion) => void
  onMeasurementReady?: (dataset: DatasetVersion, measurement: MeasurementVersion) => void
  onDictionarySave: (variables: Array<{ id: string; confirmedType: VariableType }>) => void
  onStructureSaved?: () => void
  onContinueToAnalysis?: () => void
  onStructureValidityChange: (valid: boolean) => void
}

type DataSubview = 'data' | 'variables' | 'scales'

const subviews: Array<{ id: DataSubview; label: string }> = [
  { id: 'data', label: '数据视图' },
  { id: 'variables', label: '变量视图' },
  { id: 'scales', label: '量表' },
]

export function DataWorkspaceDatasetBody({
  dataset,
  selectedFile,
  activeSheet,
  activeError,
  importMutation,
  dictionaryMutation,
  activeMeasurement,
  studyContext,
  resolvedContext,
  structureKey,
  structureReady,
  analysisLabel,
  onSheetChange,
  showMergeWizard,
  onShowMergeWizardChange,
  onMergedDatasetReset,
  onMergeSuccess,
  onMeasurementReady,
  onDictionarySave,
  onStructureSaved,
  onContinueToAnalysis,
  onStructureValidityChange,
}: DataWorkspaceDatasetBodyProps) {
  const [activeSubview, setActiveSubview] = useState<DataSubview>('data')
  const [showDataQuality, setShowDataQuality] = useState(false)
  const [showStructure, setShowStructure] = useState(false)
  const needsSpecialPreparation = Boolean(studyContext && (
    studyContext.timeStructure !== 'cross_sectional'
    || studyContext.dependenceStructure === 'nested'
  ))

  return (
    <>
      {dataset.originalFile.sheetNames && dataset.originalFile.sheetNames.length > 1 && (
        <div className={`sheet-selector-panel ${styles.sheetSelectorPanel}`}>
          <label htmlFor="sheet-select" className={styles.sheetSelectorLabel}>
            检测到当前工作簿包含多个工作表，重新导入指定工作表：
          </label>
          <select
            id="sheet-select"
            className={styles.sheetSelect}
            value={activeSheet || dataset.originalFile.sheet || ''}
            onChange={(event) => onSheetChange(event.target.value)}
          >
            {dataset.originalFile.sheetNames.map((name) => (
              <option key={name} value={name}>{name}</option>
            ))}
          </select>
          <button
            type="button"
            className={`run-button ${styles.sheetReimportButton}`}
            onClick={() => {
              if (selectedFile) {
                onMergedDatasetReset()
                dictionaryMutation.reset()
                importMutation.mutate({ file: selectedFile, sheet: activeSheet || dataset.originalFile.sheet })
              } else {
                showToast('请先在上方重新选择该 Excel 文件，然后点击切换。', 'info')
              }
            }}
          >
            切换并重新导入
          </button>
        </div>
      )}

      {activeError ? <p className="error-message error-banner" role="alert">{activeError.message}</p> : null}

      <section className={`dataset-summary ${styles.datasetSummary}`} aria-label="数据版本摘要">
        <div><span>数据行</span><strong>{dataset.rowCount}</strong></div>
        <div><span>变量列</span><strong>{dataset.columnCount}</strong></div>
        <div><span>文件格式</span><strong>{dataset.originalFile.format.toUpperCase()}</strong></div>
        <div><span>需确认变量</span><strong>{dataset.dictionary.totalCount - dataset.dictionary.confirmedCount}</strong></div>
      </section>

      <div className="dataset-provenance">
        <div>
          <span>原始文件</span>
          <strong>{dataset.originalFile.name}</strong>
        </div>
        <div>
          <span>SHA-256</span>
          <code>{dataset.originalFile.sha256}</code>
        </div>
      </div>

      <div className={styles.dataToolbar} role="toolbar" aria-label="数据工具">
        <button type="button" className="secondary-button" onClick={() => onShowMergeWizardChange(true)}>
          合并
        </button>
        <button
          type="button"
          className="secondary-button"
          aria-pressed={showDataQuality}
          onClick={() => setShowDataQuality(current => !current)}
        >
          数据检查
        </button>
        {studyContext ? (
          <button
            type="button"
            className="secondary-button"
            aria-pressed={showStructure}
            onClick={() => setShowStructure(current => !current)}
          >
            数据结构
          </button>
        ) : null}
        {onContinueToAnalysis ? (
          <button type="button" className={`run-button ${styles.analyzeButton}`} onClick={onContinueToAnalysis}>
            开始分析
          </button>
        ) : null}
      </div>

      {showMergeWizard ? (
        <DatasetMergeWizard
          primaryDataset={dataset}
          onMergeSuccess={onMergeSuccess}
          onCancel={() => onShowMergeWizardChange(false)}
        />
      ) : null}

      {showDataQuality ? (
        <DataQualityWorkspace key={`${dataset.id}:quality`} dataset={dataset} />
      ) : null}

      {showStructure && studyContext ? (
        <DataStructureSetup
          key={`${dataset.id}:${structureKey}`}
          datasetId={dataset.id}
          variables={dataset.variables}
          context={studyContext}
          studyContextVersionId={resolvedContext?.studyContext?.id ?? null}
          initialStructure={resolvedContext?.structure ?? null}
          onValidityChange={onStructureValidityChange}
          onStructureSaved={onStructureSaved}
        />
      ) : null}

      <nav className={styles.dataSubviewNav} aria-label="数据工作区子导航">
        {subviews.map((subview) => (
          <button
            key={subview.id}
            type="button"
            className={activeSubview === subview.id ? styles.activeSubview : undefined}
            aria-current={activeSubview === subview.id ? 'page' : undefined}
            onClick={() => setActiveSubview(subview.id)}
          >
            {subview.label}
          </button>
        ))}
      </nav>

      <div className={styles.dataSubviewBody}>
        {activeSubview === 'data' ? (
          <>
            <DataGridView dataset={dataset} />
            {dataset.warnings.map((warning) => (
              <p className="method-warning" key={`${warning.code}:${warning.message}`}>{warning.message}</p>
            ))}
          </>
        ) : null}

        {activeSubview === 'variables' ? (
          <VariableTable
            key={`${dataset.id}:${dataset.dictionary.version}`}
            variables={dataset.variables}
            isSaving={dictionaryMutation.isPending}
            onSave={onDictionarySave}
          />
        ) : null}

        {activeSubview === 'scales' ? (
          <>
            {needsSpecialPreparation && studyContext ? (
              <StructureMeasurementPreparation
                context={studyContext}
                roles={resolvedContext?.structure?.roles}
                profile={resolvedContext?.structure?.profile}
                measurement={resolvedContext?.measurement}
                variables={dataset.variables}
              />
            ) : null}
            <MeasurementWorkspace
              key={`${dataset.id}:measurement:${activeMeasurement?.version ?? 'new'}`}
              datasetId={dataset.id}
              variables={dataset.variables}
              initialMeasurement={
                activeMeasurement?.datasetVersionId === dataset.id
                  ? activeMeasurement
                  : undefined
              }
              onReady={(measurement) => onMeasurementReady?.(dataset, measurement)}
            />
          </>
        ) : null}
      </div>

      {!structureReady ? (
        <p className="measurement-gate">
          当前数据结构还有未完成设置；只会阻断依赖这些结构角色的方法，不影响兼容的基础分析。
        </p>
      ) : null}

      {onContinueToAnalysis ? (
        <section className="workflow-next-step" aria-label="下一步">
          <div>
            <span className="eyebrow">按需分析</span>
            <strong>数据已导入，可以进入统一方法库</strong>
            <p>系统只检查当前方法和所选变量真正需要的条件；无关变量、量表或结构设置不会阻塞基础方法。</p>
          </div>
          <button type="button" className="run-button" onClick={onContinueToAnalysis}>
            {analysisLabel}
          </button>
        </section>
      ) : null}
    </>
  )
}
