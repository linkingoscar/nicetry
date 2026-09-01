import type { UseMutationResult } from '@tanstack/react-query'
import type {
  DatasetStructureVersion,
  StructureValidationResponse,
} from '../types/study-context'

interface StructureSetupValidationPanelProps {
  studyContextVersionId: string | null
  requiresStructureVersion: boolean
  selectionComplete: boolean
  validation: StructureValidationResponse | null
  validationMutation: UseMutationResult<StructureValidationResponse, Error, void>
  saveMutation: UseMutationResult<DatasetStructureVersion, Error, void>
  persistedMatches: boolean
  activeWarnings: DatasetStructureVersion['warnings']
  activeStatus: DatasetStructureVersion['status'] | null | undefined
  overrideReason: string
  onOverrideReasonChange: (value: string) => void
  saveAllowed: boolean
}

export function StructureSetupValidationPanel({
  studyContextVersionId,
  requiresStructureVersion,
  selectionComplete,
  validation,
  validationMutation,
  saveMutation,
  persistedMatches,
  activeWarnings,
  activeStatus,
  overrideReason,
  onOverrideReasonChange,
  saveAllowed,
}: StructureSetupValidationPanelProps) {
  if (!requiresStructureVersion) {
    return (
      <p className="method-note">当前是独立观测的横截面研究，未强制要求结构角色；方法目录仍会依据服务端上下文和真实数据版本判断适用性。</p>
    )
  }

  return (
    <>
      {!studyContextVersionId ? (
        <p className="method-warning" role="status">正在等待服务端研究上下文版本；上下文版本返回前不能保存结构角色。</p>
      ) : null}
      <div className="structure-validation-actions">
        <button
          type="button"
          className="secondary-button"
          disabled={!studyContextVersionId || !selectionComplete || validationMutation.isPending}
          onClick={() => validationMutation.mutate()}
        >
          {validationMutation.isPending ? '正在运行结构画像…' : '运行结构画像'}
        </button>
        <button
          type="button"
          className="run-button"
          disabled={!saveAllowed}
          onClick={() => saveMutation.mutate()}
        >
          {saveMutation.isPending ? '正在保存结构版本…' : persistedMatches ? '结构版本已保存' : '保存结构版本'}
        </button>
      </div>
      {validation ? (
        <div className={`structure-validation-result is-${validation.status}`} role="status">
          <strong>本次画像：{validation.status === 'valid' ? '通过' : validation.status === 'warning' ? '有警告' : '未通过'}</strong>
          <span>建议结构哈希：<code>{validation.proposedStructureHash}</code></span>
          <div className="structure-profile-summary">
            <span>行数 {validation.profile.rowCount}</span>
            <span>个体 {validation.profile.subjectCount ?? '—'}</span>
            <span>聚类 {validation.profile.clusterCount ?? '—'}</span>
            <span>时间点 {validation.profile.timePointCount ?? '—'}</span>
            <span>嵌套判定 {validation.profile.nestingClassification}</span>
          </div>
        </div>
      ) : null}
      {activeWarnings.length > 0 ? (
        <div className="method-warning" role="alert">
          <strong>结构画像警告</strong>
          <ul>
            {activeWarnings.map(warning => <li key={`${warning.code}:${warning.message}`}>{warning.message}</li>)}
          </ul>
        </div>
      ) : null}
      {activeStatus === 'warning' && validation?.status === 'warning' ? (
        <label>
          继续使用的学术理由（至少 10 个字符）
          <textarea
            value={overrideReason}
            onChange={event => onOverrideReasonChange(event.target.value)}
            minLength={10}
            maxLength={1000}
            placeholder="说明为什么该结构警告不会改变本研究的识别假设，或计划如何在报告中披露。"
          />
        </label>
      ) : null}
    </>
  )
}
