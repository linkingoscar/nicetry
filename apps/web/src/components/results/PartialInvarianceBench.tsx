import { useState } from 'react'
import type { ModelSpec } from '../../types'

interface PartialInvarianceBenchProps {
  model: ModelSpec
  onUpdateReleases: (releases: Array<{
    stage: 'metric' | 'scalar' | 'strict'
    constraint: 'loading' | 'intercept_or_threshold' | 'residual'
    latentId: string | null
    indicatorId: string
    rationale: string
  }>) => void
}

export function PartialInvarianceBench({ model, onUpdateReleases }: PartialInvarianceBenchProps) {
  const currentReleases = model.estimation.multiGroup?.partialInvarianceReleases || []
  
  const [stage, setStage] = useState<'metric' | 'scalar' | 'strict'>('metric')
  const [constraint, setConstraint] = useState<'loading' | 'intercept_or_threshold' | 'residual'>('loading')
  const [indicatorId, setIndicatorId] = useState('')
  const [rationale, setRationale] = useState('')
  const [error, setError] = useState<string | null>(null)

  const handleAdd = () => {
    if (!indicatorId.trim()) {
      setError('请选择或指定需要释放等值的指标/题项 ID')
      return
    }
    if (rationale.trim().length < 8) {
      setError('学术规范要求：释放理由不得少于 8 个字符（需包含理论或诊断依据）')
      return
    }

    const newRelease = {
      stage,
      constraint,
      latentId: null,
      indicatorId: indicatorId.trim(),
      rationale: rationale.trim(),
    }

    onUpdateReleases([...currentReleases, newRelease])
    setIndicatorId('')
    setRationale('')
    setError(null)
  }

  const handleRemove = (index: number) => {
    const updated = currentReleases.filter((_, i) => i !== index)
    onUpdateReleases(updated)
  }

  return (
    <div className="partial-invariance-bench card p-4">
      <h4>⚙️ 部分等值释放工作台 (Partial Invariance Release Bench)</h4>
      <p className="field-hint">
        当完全等值（Full Invariance）未满足时，根据修正指数 (MI) 或理论依据选择性释放特定参数等值约束，建立部分等值模型 (Partial Invariance Model)。
      </p>

      {/* 释放清单 */}
      {currentReleases.length > 0 ? (
        <div className="releases-list mb-3">
          <h5>已释放等值项清单 ({currentReleases.length})</h5>
          <ul className="list-group">
            {currentReleases.map((rel) => (
              <li key={`${rel.stage}-${rel.constraint}-${rel.indicatorId}`} className="list-group-item d-flex justify-content-between align-items-center">
                <div>
                  <span className="badge bg-secondary me-2">{rel.stage.toUpperCase()}</span>
                  <strong>{rel.indicatorId}</strong> ({rel.constraint})
                  <div className="text-muted small mt-1">理由: "{rel.rationale}"</div>
                </div>
                <button
                  type="button"
                  className="btn btn-sm btn-outline-danger"
                  onClick={() => handleRemove(currentReleases.indexOf(rel))}
                >
                  撤销释放
                </button>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <div className="alert alert-info py-2">目前未手动释放任何参数等值约束（运行完全等值模型）。</div>
      )}

      {/* 新增释放表单 */}
      <div className="add-release-form card bg-light p-3 mt-3">
        <h6>新增参数释放规则</h6>
        <div className="row g-2">
          <div className="col-md-3">
            <label htmlFor="release-stage" className="form-label small">释放阶段</label>
            <select
              id="release-stage"
              className="form-select form-select-sm"
              value={stage}
              onChange={(e) => setStage(e.target.value as 'metric' | 'scalar' | 'strict')}
            >
              <option value="metric">Metric (载荷阶段)</option>
              <option value="scalar">Scalar (截距/阈值阶段)</option>
              <option value="strict">Strict (残差阶段)</option>
            </select>
          </div>
          <div className="col-md-3">
            <label htmlFor="release-constraint" className="form-label small">约束类型</label>
            <select
              id="release-constraint"
              className="form-select form-select-sm"
              value={constraint}
              onChange={(e) => setConstraint(e.target.value as 'loading' | 'intercept_or_threshold' | 'residual')}
            >
              <option value="loading">测量载荷 (Loading)</option>
              <option value="intercept_or_threshold">截距/阈值 (Intercept/Threshold)</option>
              <option value="residual">残差方差 (Residual)</option>
            </select>
          </div>
          <div className="col-md-6">
            <label htmlFor="release-indicator" className="form-label small">观测指标 / 题项 ID</label>
            <input
              id="release-indicator"
              type="text"
              className="form-control form-control-sm"
              placeholder="如：item_x1"
              value={indicatorId}
              onChange={(e) => setIndicatorId(e.target.value)}
            />
          </div>
          <div className="col-12 mt-2">
            <label htmlFor="release-rationale" className="form-label small">理论/学术释放理由（强制 &ge; 8 字符）</label>
            <input
              id="release-rationale"
              type="text"
              className="form-control form-control-sm"
              placeholder="例如：修正指数 MI 显著且跨群体文化对该题项理解语义存在偏差"
              value={rationale}
              onChange={(e) => setRationale(e.target.value)}
            />
          </div>
        </div>

        {error && <div className="text-danger small mt-2">{error}</div>}

        <div className="mt-3 text-end">
          <button type="button" className="btn btn-sm btn-primary" onClick={handleAdd}>
            + 添加释放规则
          </button>
        </div>
      </div>
    </div>
  )
}
