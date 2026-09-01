import type { UseMutationResult } from '@tanstack/react-query'

import type { DatasetVersion, MeasurementVersion, StudyContext, VariableType } from '../types'
import type { ResolvedAnalysisContext } from '../types/analysis-context'
import { VariableTable } from './VariableTable'
import { MeasurementWorkspace } from './MeasurementWorkspace'
import { DatasetMergeWizard } from './empirical/DatasetMergeWizard'
import { DataQualityWorkspace } from './DataQualityWorkspace'
import { DataStructureSetup } from './DataStructureSetup'
import { StructureMeasurementPreparation } from './context/StructureMeasurementPreparation'
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
        <div><span>字典状态</span><strong>{dataset.dictionary.status === 'confirmed' ? '已确认' : '草稿'}</strong></div>
        <button
          type="button"
          className={`run-button ${styles.mergeButton}`}
          onClick={() => onShowMergeWizardChange(true)}
        >
          🔗 合并多波次/其他数据源
        </button>
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

      <DataQualityWorkspace key={`${dataset.id}:quality`} dataset={dataset} />

      {dataset.warnings.map((warning) => (
        <p className="method-warning" key={warning.message}>{warning.message}</p>
      ))}

      {studyContext ? (
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

      <VariableTable
        key={`${dataset.id}:${dataset.dictionary.version}`}
        variables={dataset.variables}
        isSaving={dictionaryMutation.isPending}
        onSave={onDictionarySave}
      />

      {dataset.dictionary.status === 'confirmed' && structureReady ? (
        <>
          {studyContext && (
            studyContext.timeStructure !== 'cross_sectional'
            || studyContext.dependenceStructure === 'nested'
          ) ? (
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
      ) : (
        <p className="measurement-gate">
          {dataset.dictionary.status !== 'confirmed'
            ? '确认全部变量类型后，才会开放构念分组和量表计分。'
            : '确认当前数据结构所需的 ID、聚类或时间角色后，才会开放测量准备。'}
        </p>
      )}

      {showMergeWizard && (
        <DatasetMergeWizard
          primaryDataset={dataset}
          onMergeSuccess={onMergeSuccess}
          onCancel={() => onShowMergeWizardChange(false)}
        />
      )}

      {structureReady && dataset.dictionary.status === 'confirmed' && onContinueToAnalysis ? (
        <section className="workflow-next-step" aria-label="下一步">
          <div>
            <span className="eyebrow">下一步</span>
            <strong>{activeMeasurement ? '数据字典与测量版本均已就绪' : '数据字典已就绪，可直接分析原始变量'}</strong>
            <p>{activeMeasurement ? '先检查上方样本质量与量表结果；确认无误后进入实证分析。' : '描述、频数、缺失、相关和原始变量回归不要求构念计分；量表分析可稍后配置。'}</p>
          </div>
          <button type="button" className="run-button" onClick={onContinueToAnalysis}>
            {analysisLabel}
          </button>
        </section>
      ) : null}
    </>
  )
}
