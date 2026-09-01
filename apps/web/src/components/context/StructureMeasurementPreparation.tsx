import type { DatasetRoleBindings, ResolvedAnalysisContext, StructureProfile } from '../../types/analysis-context'
import type { StudyContext } from '../../types/study-context'

interface StructureMeasurementPreparationProps {
  context: StudyContext
  roles?: DatasetRoleBindings | null
  profile?: StructureProfile | null
  measurement?: ResolvedAnalysisContext['measurement']
  variables?: Array<{ id: string; label: string }>
}

function roleLabel(
  roleId: string | null | undefined,
  variables: Array<{ id: string; label: string }>,
): string {
  if (!roleId) return '未绑定'
  return variables.find((variable) => variable.id === roleId)?.label ?? roleId
}

function Status({ ready, children }: { ready: boolean; children: string }) {
  return <span className={ready ? 'context-status is-ready' : 'context-status is-pending'}>{ready ? '已确认' : '待配置'} · {children}</span>
}

export function StructureMeasurementPreparation({
  context,
  roles,
  profile,
  measurement,
  variables = [],
}: StructureMeasurementPreparationProps) {
  const panel = context.timeStructure === 'panel'
  const nestedCrossSectional = context.timeStructure === 'cross_sectional'
    && context.dependenceStructure === 'nested'
  const subjectId = roles?.subjectId
  const clusterId = roles?.clusterId
  const timeId = roles?.timeId
  const widePanel = panel && roles?.dataLayout === 'wide'
  const hasMeasurement = Boolean(measurement)
  const hasClusterProfile = Boolean(
    clusterId
    && profile?.clusterCount
    && profile.clusterSize,
  )

  if (nestedCrossSectional) {
    return (
      <section className="structure-measurement-preparation" aria-labelledby="structure-measurement-heading">
        <p className="eyebrow">结构专属测量准备</p>
        <h2 id="structure-measurement-heading">嵌套横截面测量与聚合准备</h2>
        <p className="muted">
          先确认 cluster 角色和组规模，再把量表得分用于 ICC(1)、ICC(2)、设计效应与 rwg(j) 诊断。聚合证据只说明组层构念是否值得讨论，不等同于多层测量模型，也不会自动宣布“可以聚合”。
        </p>
        <div className="structure-measurement-bindings">
          <div><span>cluster</span><strong>{roleLabel(clusterId, variables)}</strong><Status ready={Boolean(clusterId)}>结构角色</Status></div>
          <div>
            <span>cluster 画像</span>
            <strong>{profile?.clusterCount ?? '—'} 组 · {profile?.clusterSize ? `${profile.clusterSize.minimum}–${profile.clusterSize.maximum} 人/组` : '规模待画像'}</strong>
            <Status ready={hasClusterProfile}>组数与组规模</Status>
          </div>
          <div><span>measurement</span><strong>{measurement?.id ?? '未绑定'}</strong><Status ready={hasMeasurement}>量表版本</Status></div>
        </div>
        <dl className="structure-measurement-checklist">
          <div><dt>观测依赖</dt><dd><Status ready={hasClusterProfile}>检查 cluster 数、单例组和组规模分布</Status></dd></div>
          <div><dt>聚合证据</dt><dd><Status ready={false}>在分析设置中使用已绑定 cluster 运行 ICC(1)、ICC(2)、设计效应与 rwg(j)</Status></dd></div>
          <div><dt>模型选择</dt><dd><Status ready={false}>聚合判断与两层 Gaussian LMM 分开解释；不把聚合诊断当作多层模型</Status></dd></div>
        </dl>
        <p className="method-warning">组间差异/多组等值性的分组变量与 cluster 聚合变量是不同角色；只有研究设计确实要求时才同时配置。</p>
      </section>
    )
  }

  return (
    <section className="structure-measurement-preparation" aria-labelledby="structure-measurement-heading">
      <p className="eyebrow">结构专属测量准备</p>
      <h2 id="structure-measurement-heading">{panel ? '纵向题项与跨波次测量' : '日记 / ESM 题项与时点测量'}</h2>
      <p className="muted">
        {panel
          ? widePanel
            ? '当前是宽格式面板：每个对象一行，波次数由结构版本显式声明；后续按 T1…Tn 映射题项，再进入纵向等值性与 RI-CLPM。'
            : '本入口先绑定 subject × time 和测量版本，再进入波次映射、纵向等值性与 RI-CLPM；横截面测量入口不能替代跨波次证据。'
          : '本入口先绑定 person × time 和测量版本，再检查 within/between 信度、低 within 变异、时点排序与依从性；横截面测量入口不能替代时点质量证据。'}
      </p>
      <div className="structure-measurement-bindings">
        <div><span>subject</span><strong>{roleLabel(subjectId, variables)}</strong><Status ready={Boolean(subjectId)}>结构角色</Status></div>
        <div><span>{widePanel ? '波次数' : 'time'}</span><strong>{widePanel ? `${roles?.waveCount ?? '未声明'} 波` : roleLabel(timeId, variables)}</strong><Status ready={widePanel ? Boolean(roles?.waveCount) : Boolean(timeId)}>{widePanel ? '结构声明' : '结构角色'}</Status></div>
        <div><span>measurement</span><strong>{measurement?.id ?? '未绑定'}</strong><Status ready={hasMeasurement}>上下文版本</Status></div>
      </div>
      <dl className="structure-measurement-checklist">
        {panel ? (
          <>
            <div><dt>跨波次题项映射</dt><dd><Status ready={hasMeasurement}>在纵向配置中声明 T1…Tn 对应题项/得分列</Status></dd></div>
            <div><dt>纵向等值性</dt><dd><Status ready={false}>配置 configural → metric → scalar/strict，并保留拟合变化证据</Status></dd></div>
            <div><dt>动态模型</dt><dd><Status ready={false}>通过测量门槛后才开放 CLPM / RI-CLPM / LCM-SR</Status></dd></div>
          </>
        ) : (
          <>
            <div><dt>within / between 信度</dt><dd><Status ready={false}>在日记质量配置中声明分解与可靠性估计</Status></dd></div>
            <div><dt>低 within 变异</dt><dd><Status ready={false}>运行时点内变异筛查并将低变异题项列入警告</Status></dd></div>
            <div><dt>时点依赖与依从性</dt><dd><Status ready={Boolean(subjectId && timeId)}>检查排序、时间间隔、依从性和残差相关结构</Status></dd></div>
          </>
        )}
      </dl>
    </section>
  )
}
