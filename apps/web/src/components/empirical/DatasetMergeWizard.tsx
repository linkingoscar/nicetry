import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { importDataset, mergeDatasets } from '../../api'
import type { DatasetVersion, DatasetMergeReport } from '../../types'
import styles from './DatasetMergeWizard.module.css'
import { suggestSubjectKey, suggestWaveKey } from './datasetMergeKeySuggestions'
import { DatasetMergeStep1 } from './DatasetMergeWizardStep1'
import { DatasetMergeStep2 } from './DatasetMergeWizardStep2'
import { DatasetMergeStep3 } from './DatasetMergeWizardStep3'

interface DatasetMergeWizardProps {
  primaryDataset: DatasetVersion
  onMergeSuccess: (mergedDataset: DatasetVersion) => void
  onCancel: () => void
}

export function DatasetMergeWizard({
  primaryDataset,
  onMergeSuccess,
  onCancel,
}: DatasetMergeWizardProps) {
  const [step, setStep] = useState<1 | 2 | 3>(1)
  const [targetFile, setTargetFile] = useState<File | null>(null)
  const [targetDataset, setTargetDataset] = useState<DatasetVersion | null>(null)

  const [subjectKey, setSubjectKey] = useState<string>('')
  const [waveKey, setWaveKey] = useState<string>('')

  const [mergeReport, setMergeReport] = useState<DatasetMergeReport | null>(null)

  const importTargetMutation = useMutation({
    mutationFn: (file: File) => importDataset(file),
    onSuccess: (data) => {
      setTargetDataset(data)
      const primaryCols = primaryDataset.variables.map(v => v.originalName)
      const targetCols = data.variables.map(v => v.originalName)
      const commonCols = primaryCols.filter(col => targetCols.includes(col))
      setSubjectKey(suggestSubjectKey(commonCols))
      setWaveKey(suggestWaveKey(commonCols))
      setStep(2)
    },
  })

  const mergeMutation = useMutation({
    mutationFn: () => {
      if (!targetDataset) {
        throw new Error('No target dataset loaded')
      }
      return mergeDatasets(primaryDataset.id, targetDataset.id, subjectKey, waveKey || null)
    },
    onSuccess: (data) => {
      setMergeReport(data.report)
      setStep(3)
    },
  })

  const primaryCols = primaryDataset.variables.map(v => v.originalName)
  const targetCols = targetDataset ? targetDataset.variables.map(v => v.originalName) : []
  const commonCols = primaryCols.filter(col => targetCols.includes(col))
  const importError = importTargetMutation.isError ? importTargetMutation.error.message : null
  const mergeError = mergeMutation.isError ? mergeMutation.error.message : null

  const handleUploadTarget = (e: React.FormEvent) => {
    e.preventDefault()
    if (targetFile) {
      importTargetMutation.mutate(targetFile)
    }
  }

  const handleApply = () => {
    if (mergeMutation.data?.dataset) {
      onMergeSuccess(mergeMutation.data.dataset)
    }
  }

  return (
    <div className={styles.overlay}>
      <div className={styles.card}>
        <div className={styles.headerRow}>
          <div>
            <span className={styles.eyebrow}>
              多波次与数据源合并向导
            </span>
            <h2 className={styles.title}>
              {step === 1 && '第一步：选择目标数据源'}
              {step === 2 && '第二步：配置合并关联键'}
              {step === 3 && '第三步：合并诊断与结果确认'}
            </h2>
          </div>
          <button
            type="button"
            onClick={onCancel}
            className={styles.closeButton}
            aria-label="关闭"
          >
            &times;
          </button>
        </div>

        <div className={styles.progressRow}>
          <div className={styles.progressSegmentFirst} />
          <div className={`${styles.progressSegment} ${step >= 2 ? styles.progressSegmentActive : ''}`} />
          <div className={`${styles.progressSegment} ${step >= 3 ? styles.progressSegmentActive : ''}`} />
        </div>

        {step === 1 && (
          <DatasetMergeStep1
            primaryDataset={primaryDataset}
            targetFile={targetFile}
            importPending={importTargetMutation.isPending}
            importError={importError}
            onTargetFileChange={setTargetFile}
            onCancel={onCancel}
            onSubmit={handleUploadTarget}
          />
        )}

        {step === 2 && targetDataset && (
          <DatasetMergeStep2
            targetDataset={targetDataset}
            primaryCols={primaryCols}
            commonCols={commonCols}
            subjectKey={subjectKey}
            waveKey={waveKey}
            mergePending={mergeMutation.isPending}
            mergeError={mergeError}
            onSubjectKeyChange={setSubjectKey}
            onWaveKeyChange={setWaveKey}
            onBack={() => setStep(1)}
            onMerge={() => mergeMutation.mutate()}
          />
        )}

        {step === 3 && mergeReport && (
          <DatasetMergeStep3
            mergeReport={mergeReport}
            onCancel={onCancel}
            onApply={handleApply}
          />
        )}
      </div>
    </div>
  )
}
