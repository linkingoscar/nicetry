import { useEffect, useState } from 'react'
import { getAdvancedAnalysisCapabilities } from '../../api/advanced'
import type { AdvancedAnalysisCapability } from '../../types'

interface CapabilityListProps {
  onSelect: (capability: AdvancedAnalysisCapability) => void
}

const FAMILY_ICONS: Record<string, string> = {
  experimental_design: '🧪',
  multilevel_model: '🏗️',
  longitudinal_model: '📈',
  multiple_imputation: '🔄',
  power_analysis: '⚡',
}

const FAMILY_DESCRIPTIONS: Record<string, string> = {
  experimental_design: '组间 ANOVA/ANCOVA 与单一组内因子的受限重复测量切片',
  multilevel_model: '两层高斯线性混合模型（LMM）',
  longitudinal_model: '观测增长曲线与传统交叉滞后面板模型（CLPM）',
  multiple_imputation: 'MICE 插补数据集生成；尚未执行 Rubin 合并推断',
  power_analysis: '回归与组间 ANOVA 的解析功效（含双侧 t 检验）',
}

const FAMILY_ENGINES: Record<string, string> = {
  experimental_design: 'afex + emmeans',
  multilevel_model: 'lme4 + lmerTest',
  longitudinal_model: 'lavaan',
  multiple_imputation: 'mice',
  power_analysis: 'pwr',
}

export function CapabilityList({ onSelect }: CapabilityListProps) {
  const [capabilities, setCapabilities] = useState<AdvancedAnalysisCapability[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    getAdvancedAnalysisCapabilities()
      .then(res => {
        // A family runner is not enough: only show families with an executable slice.
        const validCaps = res.capabilities.filter(
          c => c.slices.some(slice => slice.executionAvailable) && (c.status === 'experimental' || c.status === 'supported')
        )
        setCapabilities(validCaps)
      })
      .catch(setError)
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="adv-loading-state" aria-live="polite">
        <div className="adv-spinner" />
        <p>正在加载可用的高级分析方法...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="adv-error-banner" role="alert">
        <strong>加载失败</strong>
        <p>{error.message}</p>
      </div>
    )
  }

  return (
    <section className="adv-capability-section" aria-label="高级统计分析方法">
      <div className="adv-section-header">
        <div>
          <p className="eyebrow">高级统计分析</p>
          <h1 id="adv-cap-heading">选择分析方法</h1>
          <p className="muted">
            以下方法处于受控实验阶段。分析结果不可替代正式方法审查。
          </p>
        </div>
      </div>

      {capabilities.length === 0 ? (
        <div className="adv-empty-state">
          <p>当前没有可执行的高级分析方法。</p>
          <p className="muted">请确认后端服务正常运行，并且至少有一个方法标记为可执行。</p>
        </div>
      ) : (
        <ul
          className="adv-capability-grid"
          aria-labelledby="adv-cap-heading"
        >
          {capabilities.map((cap, index) => (
            <li key={cap.family}>
              <button
                type="button"
                className="adv-capability-card"
                onClick={() => onSelect(cap)}
                style={{ animationDelay: `${index * 60}ms` }}
                aria-label={`${cap.label} — ${cap.status === 'experimental' ? '实验性' : '正式支持'}`}
              >
                <div className="adv-card-icon" aria-hidden="true">
                  {FAMILY_ICONS[cap.family] || '📊'}
                </div>
                <div className="adv-card-body">
                  <h3 className="adv-card-title">{cap.label}</h3>
                  <p className="adv-card-desc">
                    {cap.slices.filter(slice => slice.executionAvailable).map(slice => slice.label).join('；') || FAMILY_DESCRIPTIONS[cap.family] || `${cap.family} 分析`}
                  </p>
                </div>
                <div className="adv-card-footer">
                  <span
                    className={`adv-status-badge ${cap.status === 'supported' ? 'is-supported' : 'is-experimental'}`}
                  >
                    {cap.status === 'supported' ? '✓ 正式' : '⚗ 实验性'}
                  </span>
                  <span className="adv-engine-badge">
                    {FAMILY_ENGINES[cap.family] || cap.plannedEngine}
                  </span>
                </div>
                <svg className="adv-card-arrow" width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
                  <path d="M7 5l5 5-5 5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
