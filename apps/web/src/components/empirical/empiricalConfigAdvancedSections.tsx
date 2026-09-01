import { LongitudinalPanelConfig } from './LongitudinalPanelConfig'
import { DiaryMultilevelConfig } from './DiaryMultilevelConfig'
import { useEmpiricalAnalysisContext } from './EmpiricalAnalysisContext'

export function EmpiricalAnalysisAdvancedSections() {
  const { researchParadigm } = useEmpiricalAnalysisContext()
  const showLongitudinal = researchParadigm === 'longitudinal'
  const showDiary = researchParadigm === 'diary'

  return (
    <>
      {showLongitudinal || showDiary ? (
      <div className="analysis-config-flow-heading is-advanced">
        <div>
          <strong>{showLongitudinal ? '纵向面板工作流' : '日记 / ESM 多层工作流'}</strong>
          <span>仅执行下方显式启用且与个体、时间结构匹配的模型</span>
        </div>
        <small>高级 Beta</small>
      </div>
      ) : null}
      {showLongitudinal ? (
        <LongitudinalSection />
      ) : null}
      {showDiary ? (
        <DiarySection />
      ) : null}
    </>
  )
}

function LongitudinalSection() {
  const {
    config: value,
    onConfigChange: onChange,
    longitudinalCandidates,
    longitudinalItemGroups,
    subjectCandidates,
    contextRoles,
  } = useEmpiricalAnalysisContext()

  return (
    <details className="analysis-config-section" open>
      <summary><span>3</span><strong>纵向追踪分析</strong><small>CLPM、RI-CLPM 与 LCM-SR</small></summary>
      <LongitudinalPanelConfig
        value={value.longitudinalPanel}
        variables={longitudinalCandidates}
        itemGroups={longitudinalItemGroups}
        subjectCandidates={subjectCandidates}
        defaultSubjectId={contextRoles?.subjectId}
        defaultWaveCount={contextRoles?.dataLayout === 'wide' ? contextRoles.waveCount : null}
        onChange={(longitudinalPanel) => onChange({ longitudinalPanel })}
      />
    </details>
  )
}

function DiarySection() {
  const {
    config: value,
    onConfigChange: onChange,
    longitudinalCandidates,
    longitudinalItemGroups,
    subjectCandidates,
    contextRoles,
  } = useEmpiricalAnalysisContext()

  return (
    <details className="analysis-config-section" open>
      <summary><span>2</span><strong>日记研究与多层模型</strong><small>LMM、GLMM、多层中介与 DSEM</small></summary>
      <DiaryMultilevelConfig
        value={value.diaryMultilevel}
        variables={longitudinalCandidates}
        itemGroups={longitudinalItemGroups}
        subjectCandidates={subjectCandidates}
        defaultSubjectId={contextRoles?.subjectId}
        defaultTimeId={contextRoles?.timeId}
        onChange={(diaryMultilevel) => onChange({ diaryMultilevel })}
      />
    </details>
  )
}
