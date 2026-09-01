import { useCallback, useMemo, useState } from 'react'
import type { AdvancedAnalysisCapability, AdvancedAnalysisSpec } from '../../types'
import type { AdvancedJobResponse, QuestionnaireMeasurementSpec } from '../../types/advanced'
import { validateAdvancedAnalysisSpec, runAdvancedAnalysis } from '../../api/advanced'
import { VisualFormulaBuilder } from './VisualFormulaBuilder'
import { QuestionnaireMeasurementBuilder } from './QuestionnaireMeasurementBuilder'
import { PowerWizard, type PowerWizardSpec } from './PowerWizard'
import { ExperimentWizard, type ExperimentWizardSpec } from './ExperimentWizard'
import { ImputationWizard, type ImputationWizardSpec } from './ImputationWizard'
import { LongitudinalWizard, type LongitudinalWizardSpec } from './LongitudinalWizard'

interface AnalysisWizardProps {
  capability: AdvancedAnalysisCapability
  datasetId?: string
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
    'longitudinal_model',
    'multilevel_model',
  ].includes(family)
}

function specTemplate(family: string, datasetId?: string): object {
  const base = {
    schemaVersion: '0.1.0',
    analysisId: `analysis-${Date.now().toString(36)}`,
    name: '新分析',
    confidenceLevel: 0.95,
    seed: 20260714,
  }
  switch (family) {
    case 'power_analysis':
      return {
        ...base,
        family: 'power_analysis',
        designFamily: 'regression',
        method: 'analytic',
        solveFor: 'sample_size',
        alpha: 0.05,
        targetPower: 0.8,
        effectSize: { metric: 'cohens_f2', value: 0.15 },
        effectSizeMetric: 'cohens_f2',
        predictors: 3,
        groups: 1,
        simulations: 5000,
        alternative: 'two_sided',
        roundingRule: 'ceil',
      }
    case 'experimental_design':
      return {
        ...base,
        family: 'experimental_design',
        designType: 'factorial_anova',
        dataLayout: 'long',
        datasetVersionId: datasetId ?? '',
        outcomeIds: [''],
        betweenFactors: [{ variableId: '', coding: 'sum' }],
        sumOfSquares: 'III',
        postHocAdjustment: 'holm',
      }
    case 'multilevel_model':
      return {
        ...base,
        family: 'multilevel_model',
        datasetVersionId: datasetId ?? '',
        outcomeId: '',
        distribution: 'gaussian',
        clusterVariableId: '',
        fixedEffectIds: [''],
        randomEffects: [{ groupingVariableId: '', intercept: true, slopeVariableIds: [], covariance: 'correlated' }],
        estimator: 'REML',
        degreesOfFreedom: 'satterthwaite',
        minimumClusterCount: 30,
      }
    case 'multiple_imputation':
      return {
        ...base,
        family: 'multiple_imputation',
        datasetVersionId: datasetId ?? '',
        method: 'mice_fcs',
        imputations: 20,
        iterations: 20,
        variables: [{ variableId: '', method: 'auto' }],
        pooling: 'none',
        diagnostics: ['trace', 'distribution'],
      }
    case 'longitudinal_model':
      return {
        ...base,
        family: 'longitudinal_model',
        datasetVersionId: datasetId ?? '',
        modelType: 'growth_curve',
        subjectId: '',
        waves: [
          { wave: 'T1', timeValue: 0, variables: {} },
          { wave: 'T2', timeValue: 1, variables: {} },
          { wave: 'T3', timeValue: 2, variables: {} },
        ],
        estimator: 'MLR',
        missing: 'available_rows_ml',
      }
    case 'questionnaire_measurement':
      return {
        ...base,
        family: 'questionnaire_measurement',
        datasetVersionId: datasetId ?? '',
        modelType: 'reliability',
        itemIds: ['item_1', 'item_2', 'item_3', 'item_4'],
        constructs: [
          { id: 'construct_a', label: '构念 A', itemIds: ['item_1', 'item_2'] },
          { id: 'construct_b', label: '构念 B', itemIds: ['item_3', 'item_4'] },
        ],
        estimator: 'ML',
        itemScale: 'continuous',
        factorCount: 2,
        rotation: 'promax',
        parallelIterations: 1000,
        invarianceLevels: ['configural', 'metric', 'scalar'],
      }
    default:
      return { ...base, family }
  }
}

export function AnalysisWizard({ capability, datasetId, onJobStarted }: AnalysisWizardProps) {
  const [step, setStep] = useState<WizardStep>('config')

  const defaultJson = useMemo(
    () => JSON.stringify(specTemplate(capability.family, datasetId), null, 2),
    [capability.family, datasetId]
  )
  const [specJson, setSpecJson] = useState(defaultJson)
  const [editMode, setEditMode] = useState<'json' | 'visual'>(
    supportsGuidedEditor(capability.family) ? 'visual' : 'json'
  )

  const [validating, setValidating] = useState(false)
  const [validationError, setValidationError] = useState<string | null>(null)
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null)

  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

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
      const jobRes = await runAdvancedAnalysis(validationResult.spec, datasetId)
      onJobStarted(jobRes)
    } catch (e: unknown) {
      const err = e as { message?: string }
      setSubmitError(err.message || '提交失败')
      setStep('validation')
    } finally {
      setSubmitting(false)
    }
  }, [datasetId, validationResult, onJobStarted])

  const stepIndex = STEP_ORDER.indexOf(step)

  return (
    <div className="adv-wizard">
      {/* Step indicator */}
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
                  <path d="M3 7l3 3 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              ) : (
                i + 1
              )}
            </div>
            <span className="adv-step-label">{STAGE_LABELS[s]}</span>
          </div>
        ))}
      </nav>

      {/* Step 1: Config */}
      {step === 'config' && (
        <div className="adv-wizard-panel">
          <div className="adv-panel-header">
            <h2>{capability.label} — 规格配置</h2>
            <p className="muted">
              {editMode === 'json'
                ? '编辑以下 JSON 规格。所有字段含义请参阅方法规范文档。'
                : capability.family === 'questionnaire_measurement'
                  ? '通过字段化表单声明题项与构念；所有字段含义请参阅方法规范文档。'
                  : capability.family === 'multilevel_model'
                    ? '通过拖拽下方变量构建模型架构。'
                    : '通过字段化向导配置分析规格；所有字段含义请参阅方法规范文档。'}
            </p>
            {supportsGuidedEditor(capability.family) && (
              <div style={{ marginTop: '10px' }}>
                <button
                  type="button"
                  className={editMode === 'visual' ? 'adv-btn-primary' : 'adv-btn-secondary'}
                  style={{ marginRight: '8px' }}
                  onClick={() => setEditMode('visual')}
                >
                  {capability.family === 'multilevel_model' ? '可视化构建' : '向导配置'}
                </button>
                <button
                  type="button"
                  className={editMode === 'json' ? 'adv-btn-primary' : 'adv-btn-secondary'}
                  onClick={() => setEditMode('json')}
                >
                  高级 JSON 编辑
                </button>
              </div>
            )}
          </div>

          {editMode === 'json' ? (
            <div className="adv-spec-editor">
              <label htmlFor="adv-spec-textarea" className="sr-only">分析规格 JSON</label>
              <textarea
                id="adv-spec-textarea"
                value={specJson}
                onChange={e => setSpecJson(e.target.value)}
                className="adv-textarea"
                spellCheck={false}
                aria-describedby={validationError ? 'adv-validation-error' : undefined}
                aria-invalid={validationError ? 'true' : undefined}
              />
              <div className="adv-spec-meta">
                <span>{specJson.split('\n').length} 行</span>
                <span>{new Blob([specJson]).size} 字节</span>
              </div>
            </div>
          ) : capability.family === 'questionnaire_measurement' ? (
            <QuestionnaireMeasurementBuilder
              spec={(() => {
                try {
                  return JSON.parse(specJson) as QuestionnaireMeasurementSpec
                } catch {
                  return specTemplate(capability.family, datasetId) as QuestionnaireMeasurementSpec
                }
              })()}
              onChange={newSpec => setSpecJson(JSON.stringify(newSpec, null, 2))}
            />
          ) : capability.family === 'power_analysis' ? (
            <PowerWizard
              spec={(() => {
                try {
                  return JSON.parse(specJson)
                } catch {
                  return specTemplate(capability.family, datasetId) as unknown as PowerWizardSpec
                }
              })()}
              onChange={newSpec => setSpecJson(JSON.stringify(newSpec, null, 2))}
            />
          ) : capability.family === 'experimental_design' ? (
            <ExperimentWizard
              spec={(() => {
                try {
                  return JSON.parse(specJson)
                } catch {
                  return specTemplate(capability.family, datasetId) as unknown as ExperimentWizardSpec
                }
              })()}
              onChange={newSpec => setSpecJson(JSON.stringify(newSpec, null, 2))}
              variables={[]}
            />
          ) : capability.family === 'multiple_imputation' ? (
            <ImputationWizard
              spec={(() => {
                try {
                  return JSON.parse(specJson)
                } catch {
                  return specTemplate(capability.family, datasetId) as unknown as ImputationWizardSpec
                }
              })()}
              onChange={newSpec => setSpecJson(JSON.stringify(newSpec, null, 2))}
              variables={[]}
            />
          ) : capability.family === 'longitudinal_model' ? (
            <LongitudinalWizard
              spec={(() => {
                try {
                  return JSON.parse(specJson)
                } catch {
                  return specTemplate(capability.family, datasetId) as unknown as LongitudinalWizardSpec
                }
              })()}
              onChange={newSpec => setSpecJson(JSON.stringify(newSpec, null, 2))}
              variables={[]}
            />
          ) : capability.family === 'multilevel_model' ? (
            <div style={{ marginBottom: '20px' }}>
              <VisualFormulaBuilder
                spec={(() => {
                  try {
                    return JSON.parse(specJson)
                  } catch {
                    return specTemplate(capability.family, datasetId)
                  }
                })()}
                onChange={(newSpec) => setSpecJson(JSON.stringify(newSpec, null, 2))}
              />
            </div>
          ) : (
            <div />
          )}

          {validationError && (
            <div className="adv-error-banner" id="adv-validation-error" role="alert">
              <strong>验证失败</strong>
              <pre className="adv-error-detail">{validationError}</pre>
            </div>
          )}

          <div className="adv-wizard-actions">
            <button
              type="button"
              className="adv-btn-primary"
              onClick={handleValidate}
              disabled={validating || !specJson.trim()}
            >
              {validating ? (
                <><span className="adv-btn-spinner" aria-hidden="true" /> 验证中...</>
              ) : (
                '验证规格'
              )}
            </button>
          </div>
        </div>
      )}

      {/* Step 2: Validation Summary */}
      {step === 'validation' && validationResult && (
        <div className="adv-wizard-panel">
          <div className="adv-panel-header">
            <h2>验证摘要</h2>
          </div>

          <div className="adv-validation-summary">
            <div className="adv-valid-banner" role="status">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
                <circle cx="10" cy="10" r="9" stroke="currentColor" strokeWidth="2"/>
                <path d="M6 10l3 3 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              <span>规格有效，可以提交运行</span>
            </div>

            {/* Warnings */}
            {validationResult.warnings.length > 0 && (
              <ul className="adv-warnings-list" aria-label="验证警告">
                {validationResult.warnings.map(w => (
                  <li
                    key={`${w.code}:${w.message}`}
                    className={`adv-warning-item severity-${w.severity}`}
                  >
                    <span className="adv-warning-code">{w.code}</span>
                    <span className="adv-warning-msg">{w.message}</span>
                  </li>
                ))}
              </ul>
            )}

            {/* Spec summary table */}
            <div className="adv-spec-summary">
              <h3>规格概要</h3>
              <dl className="adv-spec-dl">
                <div>
                  <dt>方法族</dt>
                  <dd><code>{capability.family}</code></dd>
                </div>
                <div>
                  <dt>分析 ID</dt>
                  <dd><code>{(validationResult.spec as Record<string, unknown>)?.analysisId as string || '—'}</code></dd>
                </div>
                <div>
                  <dt>置信水平</dt>
                  <dd><code>{(validationResult.spec as Record<string, unknown>)?.confidenceLevel as number || 0.95}</code></dd>
                </div>
                <div>
                  <dt>随机种子</dt>
                  <dd><code>{(validationResult.spec as Record<string, unknown>)?.seed as number || '—'}</code></dd>
                </div>
              </dl>
            </div>

            {/* Raw validated spec */}
            <details className="adv-spec-detail">
              <summary>查看完整验证后规格</summary>
              <pre className="adv-spec-pre">
                {JSON.stringify(validationResult.spec, null, 2)}
              </pre>
            </details>
          </div>

          {submitError && (
            <div className="adv-error-banner" role="alert">
              <strong>提交失败</strong>
              <p>{submitError}</p>
            </div>
          )}

          <div className="adv-wizard-actions">
            <button
              type="button"
              className="adv-btn-secondary"
              onClick={() => setStep('config')}
            >
              返回编辑
            </button>
            <button
              type="button"
              className="adv-btn-primary"
              onClick={handleSubmit}
              disabled={submitting}
            >
              {submitting ? (
                <><span className="adv-btn-spinner" aria-hidden="true" /> 提交中...</>
              ) : (
                '提交后台运行'
              )}
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Submitting (brief transition state) */}
      {step === 'submitting' && (
        <div className="adv-wizard-panel">
          <div className="adv-loading-state">
            <div className="adv-spinner" />
            <p>正在提交分析任务...</p>
          </div>
        </div>
      )}
    </div>
  )
}
