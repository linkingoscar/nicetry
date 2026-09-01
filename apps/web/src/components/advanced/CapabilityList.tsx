import { useEffect, useState } from 'react'
import { getAdvancedAnalysisCapabilities } from '../../api/advanced'
import type { AdvancedAnalysisCapability, CapabilityMaturity, PublicationEligibility } from '../../types/advanced'

interface CapabilityListProps {
  onSelect: (capability: AdvancedAnalysisCapability) => void
  hasDataset?: boolean
  allowedFamilies?: string[]
  title?: string
  description?: string
}

const FAMILY_ICONS: Record<string, string> = {
  experimental_design: 'EX',
  multilevel_model: 'ML',
  longitudinal_model: 'LG',
  multiple_imputation: 'MI',
  power_analysis: 'PA',
  questionnaire_measurement: 'QM',
}

const FAMILY_DESCRIPTIONS: Record<string, string> = {
  experimental_design: '随机实验的组间 ANOVA/ANCOVA 与单一组内因子的受限重复测量切片；不提供准实验因果识别',
  multilevel_model: '两层高斯线性混合模型（LMM）',
  longitudinal_model: '观测增长曲线与传统交叉滞后面板模型（CLPM）',
  multiple_imputation: '类型感知 MICE、逐份拟合、Rubin 合并与 FMI 诊断',
  power_analysis: '回归、t 检验和组间 ANOVA 的解析、精度与 Monte Carlo 功效',
  questionnaire_measurement: '声明 Target 的 ESEM、连续/有序 Bifactor、二元 2PL 与多分类 GRM IRT/DIF',
}

const FAMILY_ENGINES: Record<string, string> = {
  experimental_design: 'afex + emmeans',
  multilevel_model: 'lme4 + lmerTest',
  longitudinal_model: 'lavaan',
  multiple_imputation: 'mice',
  power_analysis: 'pwr',
  questionnaire_measurement: 'lavaan + mirt',
}

const FAMILY_ORDER = ['power_analysis', 'multiple_imputation', 'questionnaire_measurement', 'experimental_design', 'multilevel_model', 'longitudinal_model']

function maturityLabel(maturity: CapabilityMaturity | undefined): string {
  if (maturity === 'publication_ready') return '论文级就绪'
  if (maturity === 'reviewer_ready') return '审稿就绪候选'
  return maturity === 'validated' ? '已验证切片' : '实验性切片'
}

function publicationLabel(eligibility: PublicationEligibility | undefined): string {
  if (eligibility === 'eligible') return '论文级就绪'
  return eligibility === 'conditional' ? '有条件：仍需论文证据图' : '暂不具备论文主分析资格'
}

export function CapabilityList({
  onSelect,
  hasDataset = true,
  allowedFamilies,
  title = '选择分析方法',
  description = '以下方法处于受控实验阶段。分析结果不可替代正式方法审查。',
}: CapabilityListProps) {
  const [capabilities, setCapabilities] = useState<AdvancedAnalysisCapability[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    getAdvancedAnalysisCapabilities()
      .then(res => {
        // A family runner is not enough: only show families with an executable slice.
        const allowed = allowedFamilies ? new Set(allowedFamilies) : null
        const validCaps = res.capabilities.filter(
          c => (!allowed || allowed.has(c.family))
            && c.executionAvailable
            && c.slices.some(slice => slice.executionAvailable)
            && (c.status === 'experimental' || c.status === 'supported')
        ).sort((left, right) => FAMILY_ORDER.indexOf(left.family) - FAMILY_ORDER.indexOf(right.family))
        setCapabilities(validCaps)
      })
      .catch(setError)
      .finally(() => setLoading(false))
  }, [allowedFamilies])

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
          <h1 id="adv-cap-heading">{title}</h1>
          <p className="muted">{description}</p>
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
              {(() => {
                const requiresDataset = cap.family !== 'power_analysis'
                const disabled = requiresDataset && !hasDataset
                return (
              <button
                type="button"
                className="adv-capability-card"
                onClick={() => onSelect(cap)}
                disabled={disabled}
                style={{ animationDelay: `${index * 60}ms` }}
                aria-label={`${cap.label} — ${disabled ? '需先准备数据' : maturityLabel(cap.maturityLevel)}；${publicationLabel(cap.publicationEligibility)}`}
              >
                <div className="adv-card-icon" aria-hidden="true">
                  {FAMILY_ICONS[cap.family] || 'MT'}
                </div>
                <div className="adv-card-body">
                  <h3 className="adv-card-title">{cap.label}</h3>
                  <p className="adv-card-desc">
                    {cap.slices.filter(slice => slice.executionAvailable).map(slice => slice.label).join('；') || FAMILY_DESCRIPTIONS[cap.family] || `${cap.family} 分析`}
                  </p>
                </div>
                <div className="adv-card-footer">
                  <span
                    className={`adv-status-badge is-${cap.maturityLevel ?? 'experimental'}`}
                  >
                    {maturityLabel(cap.maturityLevel)}
                  </span>
                  <span className="adv-engine-badge" title={cap.publicationEligibilityReason}>
                    {publicationLabel(cap.publicationEligibility)}
                  </span>
                  {disabled && <span className="adv-engine-badge">需先完成数据与测量</span>}
                  <span className="adv-engine-badge">
                    {FAMILY_ENGINES[cap.family] || cap.plannedEngine}
                  </span>
                </div>
                <svg className="adv-card-arrow" width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
                  <path d="M7 5l5 5-5 5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
                )
              })()}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
