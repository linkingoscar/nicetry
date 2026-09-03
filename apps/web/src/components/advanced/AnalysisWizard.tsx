import { useCallback, useEffect, useMemo, useState } from 'react'
import type { AdvancedAnalysisCapability, AdvancedAnalysisSpec } from '../../types'
import type { AdvancedJobResponse } from '../../types/advanced'
import { validateAdvancedAnalysisSpec, runAdvancedAnalysis } from '../../api/advanced'
import { updateAnalysisDraft } from '../../api/analysis-context'
import type { DatasetVariableItem } from './DatasetVariablePicker'
import type { ResolvedAnalysisContext } from '../../types/analysis-context'
import { collectDraftRoleOverrides } from './draftAdapters'
import { WizardConfigStep } from './WizardConfigStep'
import { WizardStatusCard } from './WizardStatusCard'
import { buildAnalysisSpecTemplate } from './AnalysisWizard.template'
import { analysisWizardPresentation } from './analysisWizardPresentation'

export { buildAnalysisSpecTemplate } from './AnalysisWizard.template'

interface AnalysisWizardProps {
  capability: AdvancedAnalysisCapability
  datasetId?: string
  variables?: DatasetVariableItem[]
  constructs?: Array<{ id: string; label: string; itemIds: string[] }>
  context?: ResolvedAnalysisContext | null
  draftId?: string | null
  draftRevision?: number | null
  onJobStarted: (job: AdvancedJobResponse) => void
}

type WizardStep = 'config' | 'validation' | 'submitting'

interface ValidationResult {
  valid: boolean
  spec: AdvancedAnalysisSpec | null
  warnings: Array<{ code: string; severity: 'info' | 'warning' | 'error'; message: string }>
  specHash?: string
}

const STAGE_LABELS: Record<string, string> = {
  config: '编辑规格',
  validation: '验证摘要',
  submitting: '提交中',
}

const STEP_ORDER: WizardStep[] = ['config', 'validation', 'submitting']

function supportsGuidedEditor(family: string): boolean {
  return [
    'questionnaire_measurement',
    'power_analysis',
    'experimental_design',
    'multiple_imputation',
    'multilevel_model',
  ].includes(family)
}

export function AnalysisWizard({
  capability,
  datasetId,
  variables = [],
  constructs = [],
  context = null,
  draftId = null,
  draftRevision = null,
  onJobStarted,
}: AnalysisWizardProps) {
  const presentation = analysisWizardPresentation(capability)
  const [step, setStep] = useState<WizardStep>('config')
  const [currentDraftRevision, setCurrentDraftRevision] = useState<number | null>(draftRevision)

  useEffect(() => {
    setCurrentDraftRevision(draftRevision ?? null)
  }, [draftRevision])

  const defaultJson = useMemo(
    () => JSON.stringify(buildAnalysisSpecTemplate(capability.family, capability.sliceId, datasetId, variables, constructs, context), null, 2),
    [capability.family, capability.sliceId, datasetId, variables, constructs, context],
  )
  const [specJson, setSpecJson] = useState(defaultJson)
  const [editMode, setEditMode] = useState<'json' | 'visual'>(
    supportsGuidedEditor(capability.family) ? 'visual' : 'json',
  )

  const [validating, setValidating] = useState(false)
  const [validationError, setValidationError] = useState<string | null>(null)
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null)

  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [overrideReason, setOverrideReason] = useState('')

  const handleValidate = useCallback(async () => {
    setValidating(true)
    setValidationError(null)
    setValidationResult(null)
    try {
      const parsed = JSON.parse(specJson)
      const res = await validateAdvancedAnalysisSpec(parsed, datasetId)
      setValidationResult({
        valid: true,
        spec: res.spec as AdvancedAnalysisSpec,
        warnings: res.warnings || [],
      })
      setStep('validation')
    } catch (e: unknown) {
      const err = e as { response?: { status: number; data: unknown }; message?: string }
      if (err.response && err.response.status === 422) {
        setValidationError(JSON.stringify(err.response.data, null, 2))
      } else if (e instanceof SyntaxError) {
        setValidationError(`JSON 格式错误：${e.message}`)
      } else {
        setValidationError(err.message || '未知验证错误')
      }
    } finally {
      setValidating(false)
    }
  }, [datasetId, specJson])

  const handleSubmit = useCallback(async () => {
    if (!validationResult?.spec) return
    setSubmitting(true)
    setSubmitError(null)
    setStep('submitting')
    try {
      const validatedSpec = validationResult.spec as unknown as Record<string, unknown>
      const overrideCandidates = context && capability.sliceId
        ? collectDraftRoleOverrides(capability.sliceId, validatedSpec, context)
        : []
      if (overrideCandidates.length > 0 && overrideReason.trim().length < 10) {
        throw new Error('检测到角色覆盖，请填写至少 10 个字符的覆盖理由后再提交。')
      }
      if (draftId && currentDraftRevision !== null && currentDraftRevision !== undefined) {
        const roleOverrides = Object.fromEntries(overrideCandidates.map((candidate) => [
          candidate.role,
          { variableId: candidate.variableId, reason: overrideReason.trim() },
        ]))
        const updatedDraft = await updateAnalysisDraft(draftId, {
          expectedRevision: currentDraftRevision,
          spec: validatedSpec,
          roleOverrides,
        })
        setCurrentDraftRevision(updatedDraft.revision)
      }
      const jobRes = draftId
        ? await runAdvancedAnalysis(validationResult.spec, datasetId, draftId)
        : await runAdvancedAnalysis(validationResult.spec, datasetId)
      onJobStarted(jobRes)
    } catch (e: unknown) {
      const err = e as { message?: string }
      setSubmitError(err.message || '提交失败')
      setStep('validation')
    } finally {
      setSubmitting(false)
    }
  }, [capability.sliceId, context, currentDraftRevision, datasetId, draftId, onJobStarted, overrideReason, validationResult])

  const stepIndex = STEP_ORDER.indexOf(step)

  return (
    <div className={`adv-wizard${presentation === 'standard' ? ' is-standard-analysis' : ''}`}>
      {presentation === 'advanced' ? (
        <nav className="adv-step-indicator" aria-label="向导步骤">
          {STEP_ORDER.map((s, i) => (
            <div
              key={s}
              className={`adv-step ${i < stepIndex ? 'is-complete' : ''} ${i === stepIndex ? 'is-active' : ''}`}
              aria-current={i === stepIndex ? 'step' : undefined}
            >
              <div className="adv-step-number" aria-hidden="true">
                {i < stepIndex ? (
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                    <title>Completed</title>
                    <path d="M3 7l3 3 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                ) : (
                  i + 1
                )}
              </div>
              <span className="adv-step-label">{STAGE_LABELS[s]}</span>
            </div>
          ))}
        </nav>
      ) : null}

      {step === 'config' && (
        <WizardConfigStep
          capability={capability}
          datasetId={datasetId}
          variables={variables}
          constructs={constructs}
          context={context}
          editMode={editMode}
          setEditMode={setEditMode}
          specJson={specJson}
          setSpecJson={setSpecJson}
          supportsGuidedEditor={supportsGuidedEditor}
          buildAnalysisSpecTemplate={buildAnalysisSpecTemplate}
          validating={validating}
          validationError={validationError}
          handleValidate={handleValidate}
          presentation={presentation}
        />
      )}

      {step === 'validation' && validationResult && (
        <WizardStatusCard
          capability={capability}
          validationResult={validationResult}
          draftId={draftId}
          context={context}
          overrideReason={overrideReason}
          setOverrideReason={setOverrideReason}
          submitError={submitError}
          submitting={submitting}
          onBackToConfig={() => setStep('config')}
          onSubmit={handleSubmit}
          presentation={presentation}
        />
      )}

      {step === 'submitting' && (
        <div className="adv-wizard-panel">
          <div className="adv-loading-state" role="status" aria-live="polite">
            <div className="adv-spinner" />
            <p>{presentation === 'standard' ? '正在启动分析…' : '正在提交分析任务...'}</p>
          </div>
        </div>
      )}
    </div>
  )
}
