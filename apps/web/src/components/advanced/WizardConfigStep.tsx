import type { AdvancedAnalysisCapability } from '../../types'
import type { QuestionnaireMeasurementSpec } from '../../types/advanced'
import { QuestionnaireMeasurementBuilder } from './QuestionnaireMeasurementBuilder'
import { PowerWizard, type PowerWizardSpec } from './PowerWizard'
import { ExperimentWizard, type ExperimentWizardSpec } from './ExperimentWizard'
import { ImputationWizard, type ImputationWizardSpec } from './ImputationWizard'
import { MultilevelWizard, type MultilevelWizardSpec } from './MultilevelWizard'
import type { DatasetVariableItem } from './DatasetVariablePicker'
import type { ResolvedAnalysisContext } from '../../types/analysis-context'
import type { AnalysisWizardPresentation } from './analysisWizardPresentation'

interface WizardConfigStepProps {
  capability: AdvancedAnalysisCapability
  datasetId?: string
  variables?: DatasetVariableItem[]
  constructs?: Array<{ id: string; label: string; itemIds: string[] }>
  context?: ResolvedAnalysisContext | null
  editMode: 'json' | 'visual'
  setEditMode: (mode: 'json' | 'visual') => void
  specJson: string
  setSpecJson: (json: string) => void
  supportsGuidedEditor: (family: string) => boolean
  buildAnalysisSpecTemplate: (
    family: string,
    sliceId: string | undefined,
    datasetId: string | undefined,
    variables: DatasetVariableItem[],
    constructs: Array<{ id: string; label: string; itemIds: string[] }>,
    context?: ResolvedAnalysisContext | null,
  ) => object
  validating: boolean
  validationError: string | null
  handleValidate: () => void
  presentation?: AnalysisWizardPresentation
}

export function WizardConfigStep({
  capability,
  datasetId,
  variables = [],
  constructs = [],
  context = null,
  editMode,
  setEditMode,
  specJson,
  setSpecJson,
  supportsGuidedEditor,
  buildAnalysisSpecTemplate,
  validating,
  validationError,
  handleValidate,
  presentation = 'advanced',
}: WizardConfigStepProps) {
  const guided = supportsGuidedEditor(capability.family)
  const modeButtons = guided ? (
    <div style={{ marginTop: '10px' }}>
      <button
        type="button"
        className={editMode === 'visual' ? 'adv-btn-primary' : 'adv-btn-secondary'}
        style={{ marginRight: '8px' }}
        onClick={() => setEditMode('visual')}
      >
        字段表单
      </button>
      <button
        type="button"
        className={editMode === 'json' ? 'adv-btn-primary' : 'adv-btn-secondary'}
        onClick={() => setEditMode('json')}
      >
        高级 JSON 编辑
      </button>
    </div>
  ) : null

  return (
    <div className="adv-wizard-panel">
      <div className="adv-panel-header">
        <h2>{capability.label} — {presentation === 'standard' ? '分析设置' : '规格配置'}</h2>
        <p className="muted">
          {presentation === 'standard'
            ? editMode === 'json'
              ? '正在直接编辑完整分析设置。完成后仍会走同一套后端校验与运行流程。'
              : '选择变量和分析参数。检查通过后再运行；高级 JSON 仅在需要直接编辑完整设置时使用。'
            : editMode === 'json'
              ? '编辑以下 JSON 规格。所有字段含义请参阅方法规范文档。'
              : capability.family === 'questionnaire_measurement'
                ? '通过字段化表单声明题项与构念；所有字段含义请参阅方法规范文档。'
                : '通过字段化向导配置分析规格；所有字段含义请参阅方法规范文档。'}
        </p>
        {guided ? (
          presentation === 'standard' ? (
            <details className="adv-spec-detail">
              <summary>高级设置</summary>
              {modeButtons}
            </details>
          ) : modeButtons
        ) : null}
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
              return buildAnalysisSpecTemplate(capability.family, capability.sliceId, datasetId, variables, constructs, context) as QuestionnaireMeasurementSpec
            }
          })()}
          variables={variables}
          onChange={newSpec => setSpecJson(JSON.stringify(newSpec, null, 2))}
        />
      ) : capability.family === 'power_analysis' ? (
        <PowerWizard
          spec={(() => {
            try {
              return JSON.parse(specJson)
            } catch {
              return buildAnalysisSpecTemplate(capability.family, capability.sliceId, datasetId, variables, constructs, context) as unknown as PowerWizardSpec
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
              return buildAnalysisSpecTemplate(capability.family, capability.sliceId, datasetId, variables, constructs, context) as unknown as ExperimentWizardSpec
            }
          })()}
          onChange={newSpec => setSpecJson(JSON.stringify(newSpec, null, 2))}
          variables={variables}
          sliceId={capability.sliceId}
        />
      ) : capability.family === 'multiple_imputation' ? (
        <ImputationWizard
          spec={(() => {
            try {
              return JSON.parse(specJson)
            } catch {
              return buildAnalysisSpecTemplate(capability.family, capability.sliceId, datasetId, variables, constructs, context) as unknown as ImputationWizardSpec
            }
          })()}
          onChange={newSpec => setSpecJson(JSON.stringify(newSpec, null, 2))}
          variables={variables}
        />
      ) : capability.family === 'multilevel_model' ? (
        <MultilevelWizard
          spec={(() => {
            try {
              return JSON.parse(specJson) as MultilevelWizardSpec
            } catch {
              return buildAnalysisSpecTemplate(capability.family, capability.sliceId, datasetId, variables, constructs, context) as MultilevelWizardSpec
            }
          })()}
          onChange={newSpec => setSpecJson(JSON.stringify(newSpec, null, 2))}
          variables={variables}
          sliceId={capability.sliceId}
        />
      ) : (
        <div />
      )}

      {validationError && (
        <div className="adv-error-banner" id="adv-validation-error" role="alert">
          <strong>{presentation === 'standard' ? '设置检查失败' : '验证失败'}</strong>
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
            <><span className="adv-btn-spinner" aria-hidden="true" /> {presentation === 'standard' ? '检查中...' : '验证中...'}</>
          ) : (
            presentation === 'standard' ? '检查设置' : '验证规格'
          )}
        </button>
      </div>
    </div>
  )
}
