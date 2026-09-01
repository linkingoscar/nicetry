import { useCallback, useState, type FormEvent } from 'react'
import { useMutation } from '@tanstack/react-query'

import { confirmDictionary, importDataset } from '../api'
import type { DatasetVersion, MeasurementVersion, StudyContext, VariableType } from '../types'
import type { ResolvedAnalysisContext } from '../types/analysis-context'
import { DataWorkspaceDatasetBody } from './DataWorkspaceDatasetBody'
import { DataWorkspaceEmptyState } from './DataWorkspaceEmptyState'
import { DataImportDropzone } from './data/DataImportDropzone'

interface DataWorkspaceProps {
  activeDataset?: DatasetVersion | null
  activeMeasurement?: MeasurementVersion | null
  onDatasetReady?: (dataset: DatasetVersion) => void
  onClearWorkspace?: () => boolean
  onMeasurementReady?: (dataset: DatasetVersion, measurement: MeasurementVersion) => void
  onStructureSaved?: () => void
  onContinueToAnalysis?: () => void
  onLoadDemo?: () => void
  loadingDemo?: boolean
  studyContext?: StudyContext
  resolvedContext?: ResolvedAnalysisContext | null
}

export function DataWorkspace({
  activeDataset,
  activeMeasurement,
  onDatasetReady,
  onClearWorkspace,
  onMeasurementReady,
  onStructureSaved,
  onContinueToAnalysis,
  onLoadDemo,
  loadingDemo = false,
  studyContext,
  resolvedContext,
}: DataWorkspaceProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [fileInputKey, setFileInputKey] = useState(0)
  const [mergedDataset, setMergedDataset] = useState<DatasetVersion | null>(null)
  const [showMergeWizard, setShowMergeWizard] = useState(false)
  const [activeSheet, setActiveSheet] = useState<string>('')
  const [structureValidity, setStructureValidity] = useState({ key: '', valid: false })

  const importMutation = useMutation({
    mutationFn: ({ file, sheet }: { file: File; sheet?: string }) => importDataset(file, sheet),
    onSuccess: (nextDataset) => {
      setMergedDataset(null)
      setStructureValidity({ key: '', valid: false })
      onDatasetReady?.(nextDataset)
    },
  })
  const dictionaryMutation = useMutation({
    mutationFn: ({
      datasetId,
      variables,
    }: {
      datasetId: string
      variables: Array<{ id: string; confirmedType: VariableType }>
    }) => confirmDictionary(datasetId, variables),
    onSuccess: (nextDataset) => {
      setStructureValidity({ key: '', valid: false })
      onDatasetReady?.(nextDataset)
    },
  })
  const dataset: DatasetVersion | undefined =
    mergedDataset ?? dictionaryMutation.data ?? importMutation.data ?? activeDataset ?? undefined
  const structureKey = studyContext
    ? `${studyContext.timeStructure}:${studyContext.dependenceStructure}:${studyContext.design}`
    : ''
  const handleStructureValidity = useCallback((valid: boolean) => {
    setStructureValidity(current => (
      current.key === structureKey && current.valid === valid
        ? current
        : { key: structureKey, valid }
    ))
  }, [structureKey])
  const structureRequired = studyContext
    ? resolvedContext
      ? resolvedContext.missingRequirements.includes('structure')
      : studyContext.timeStructure !== 'cross_sectional'
        || studyContext.dependenceStructure === 'nested'
        || studyContext.design !== 'observational'
    : false
  const structureReady = !structureRequired
    || (structureValidity.key === structureKey && structureValidity.valid)

  const handleImport = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (selectedFile) {
      setMergedDataset(null)
      dictionaryMutation.reset()
      importMutation.mutate({ file: selectedFile })
    }
  }

  const handleDictionarySave = (
    variables: Array<{ id: string; confirmedType: VariableType }>,
  ) => {
    if (dataset) {
      dictionaryMutation.mutate({ datasetId: dataset.id, variables })
    }
  }

  const activeError = importMutation.error ?? dictionaryMutation.error
  const dataStructureLabel = studyContext?.timeStructure === 'panel'
    ? '追踪面板数据'
    : studyContext?.timeStructure === 'intensive_longitudinal'
      ? '密集追踪数据'
      : '单次 / 横截面数据'
  const analysisLabel = studyContext?.timeStructure === 'panel'
    ? '进入纵向面板分析'
    : studyContext?.timeStructure === 'intensive_longitudinal'
      ? '进入日记 / ESM 分析'
      : studyContext?.dependenceStructure === 'nested'
        ? '进入横截面嵌套分析'
        : '进入横截面实证分析'
  const demoLabel = studyContext?.timeStructure === 'panel'
    ? '一键导入追踪面板示例项目'
    : studyContext?.timeStructure === 'intensive_longitudinal'
      ? '一键导入密集追踪示例项目'
      : '一键导入经典问卷示例项目'
  const demoDescription = studyContext?.timeStructure === 'panel'
    ? '或者，您也可以一键加载系统内置的五波追踪面板示例数据与测量版本：'
    : studyContext?.timeStructure === 'intensive_longitudinal'
      ? '或者，您也可以一键加载系统内置的日记 / ESM 密集追踪示例数据与测量版本：'
      : '或者，您也可以一键加载系统内置的标准问卷示例数据与模型：'

  return (
    <section className="data-workspace" aria-labelledby="data-heading">
      {dataset && onClearWorkspace ? <div className="current-dataset-actions">
        <div><strong>当前数据 · {dataset.originalFile.name}</strong><p>清空仅退出当前数据；已保存的版本、草稿和结果仍保留在本机。</p></div>
        <button type="button" className="secondary-button" disabled={importMutation.isPending || dictionaryMutation.isPending || loadingDemo || showMergeWizard} onClick={() => {
          if (!onClearWorkspace()) return
          importMutation.reset(); dictionaryMutation.reset()
          setSelectedFile(null); setMergedDataset(null); setActiveSheet(''); setShowMergeWizard(false)
          setStructureValidity({ key: '', valid: false }); setFileInputKey(key => key + 1)
        }}>清空当前数据</button>
      </div> : null}
      <DataImportDropzone
        key={fileInputKey}
        selectedFile={selectedFile}
        onFileSelect={(file) => {
          setSelectedFile(file)
          setActiveSheet('')
        }}
        onImport={handleImport}
        isPending={importMutation.isPending}
        dataStructureLabel={dataStructureLabel}
        dependenceStructure={studyContext?.dependenceStructure}
      />

      {dataset ? (
        <DataWorkspaceDatasetBody
          dataset={dataset}
          selectedFile={selectedFile}
          activeSheet={activeSheet}
          activeError={activeError}
          importMutation={importMutation}
          dictionaryMutation={dictionaryMutation}
          activeMeasurement={activeMeasurement}
          studyContext={studyContext}
          resolvedContext={resolvedContext}
          structureKey={structureKey}
          structureReady={structureReady}
          analysisLabel={analysisLabel}
          onSheetChange={setActiveSheet}
          showMergeWizard={showMergeWizard}
          onShowMergeWizardChange={setShowMergeWizard}
          onMergedDatasetReset={() => setMergedDataset(null)}
          onMergeSuccess={(merged) => {
            setMergedDataset(merged)
            setStructureValidity({ key: '', valid: false })
            onDatasetReady?.(merged)
            setShowMergeWizard(false)
          }}
          onMeasurementReady={onMeasurementReady}
          onDictionarySave={handleDictionarySave}
          onStructureSaved={onStructureSaved}
          onContinueToAnalysis={onContinueToAnalysis}
          onStructureValidityChange={handleStructureValidity}
        />
      ) : (
        <DataWorkspaceEmptyState
          demoLabel={demoLabel}
          demoDescription={demoDescription}
          loadingDemo={loadingDemo}
          onLoadDemo={onLoadDemo}
        />
      )}
    </section>
  )
}
