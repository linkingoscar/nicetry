import { useState } from 'react'
import type {
  ResearchProgramSpec,
  StudyProtocolSpec,
  HypothesisInput,
  ProtocolDeviation,
  EstimandPlan
} from '../../types/protocol'
import {
  saveProgram,
  getProgram,
  saveProtocolDraft,
  freezeProtocol,
  listHypotheses,
  addOrUpdateHypothesis,
  verifyProtocolDeviation
} from '../../api/protocol'
import './advanced.css' // Import shared advanced styles

export function ResearchProgramManager() {
  const [step, setStep] = useState<number>(1)
  const [programId, setProgramId] = useState<string>('program_default_01')
  const [programTitle, setProgramTitle] = useState<string>('')
  const [theoreticalQuestion, setTheoreticalQuestion] = useState<string>('')
  const [targetJournal, setTargetJournal] = useState<string>('')
  const [owner, setOwner] = useState<string>('')
  const [constructKeys, setConstructKeys] = useState<string>('')

  // Study Protocol State
  const [studyId, setStudyId] = useState<string>('study_survey_01')
  const [studyTitle, setStudyTitle] = useState<string>('')
  const [designType, setDesignType] = useState<'survey' | 'experimental' | 'longitudinal' | 'diary'>('survey')
  const [population, setPopulation] = useState<string>('')
  const [recruitment, setRecruitment] = useState<string>('')
  const [inclusionCriteria, setInclusionCriteria] = useState<string>('')
  const [exclusionCriteria, setExclusionCriteria] = useState<string>('')

  // Planned Estimands
  const [estimands, setEstimands] = useState<EstimandPlan[]>([
    {
      estimandId: 'est_primary',
      outcomeVariableId: '',
      predictorVariableIds: [],
      covariateVariableIds: [],
      causal: false,
      estimandRole: 'primary',
    }
  ])

  // Experimental Plan State
  const [conditions, setConditions] = useState<string>('')
  const [randomizationUnit, setRandomizationUnit] = useState<string>('')
  const [allocationRatio, setAllocationRatio] = useState<string>('')

  // Hypotheses State
  const [hypotheses, setHypotheses] = useState<HypothesisInput[]>([])
  const [newHypText, setNewHypText] = useState<string>('')
  const [newHypDirection, setNewHypDirection] = useState<'positive' | 'negative' | 'non_directional'>('positive')
  const [newHypRole, setNewHypRole] = useState<'primary' | 'secondary' | 'exploratory'>('primary')

  // Freeze state
  const [versionId, setVersionId] = useState<string>('v1')
  const [preregUrl, setPreregUrl] = useState<string>('')
  const [frozenHash, setFrozenHash] = useState<string>('')
  const [isFrozen, setIsFrozen] = useState<boolean>(false)

  // Deviation verify state
  const [testOutcome, setTestOutcome] = useState<string>('')
  const [testPredictors, setTestPredictors] = useState<string>('')
  const [testCovariates, setTestCovariates] = useState<string>('')
  const [deviations, setDeviations] = useState<ProtocolDeviation[]>([])
  const [devChecked, setDevChecked] = useState<boolean>(false)

  // Load initial program
  const loadProgramData = async () => {
    try {
      const data = await getProgram(programId)
      setProgramTitle(data.title)
      setTheoreticalQuestion(data.theoreticalQuestion)
      setTargetJournal(data.targetJournal ?? '')
      setOwner(data.owner ?? '')
      setConstructKeys(data.constructKeys?.join(', ') ?? '')
    } catch {
      // Setup draft if not exists
    }
  }

  const handleSaveProgram = async () => {
    const keys = constructKeys.split(',').map(s => s.trim()).filter(Boolean)
    const program: ResearchProgramSpec = {
      id: programId,
      title: programTitle,
      theoreticalQuestion,
      targetJournal: targetJournal || null,
      owner: owner || null,
      constructKeys: keys,
    }
    await saveProgram(program)
    alert('研究计划已成功保存！')
    setStep(2)
  }

  const handleSaveProtocolDraft = async () => {
    const protocol: StudyProtocolSpec = {
      studyId,
      title: studyTitle || `${designType === 'survey' ? '问卷' : '实验'}实证研究`,
      designType,
      samplingPlan: {
        population: population || null,
        recruitment: recruitment || null,
        inclusionCriteria: inclusionCriteria.split('\n').map(s => s.trim()).filter(Boolean),
        exclusionCriteria: exclusionCriteria.split('\n').map(s => s.trim()).filter(Boolean),
      },
      experimentalPlan: designType === 'experimental' ? {
        conditions: conditions.split(',').map(s => s.trim()).filter(Boolean),
        randomizationUnit: randomizationUnit || null,
        allocationRatio: allocationRatio || null,
      } : null,
      plannedEstimands: estimands,
      preregistrationUrl: preregUrl || null,
    }
    await saveProtocolDraft(programId, studyId, protocol)
    alert('协议草稿已成功保存！')
    // Load hypotheses
    const list = await listHypotheses(programId, studyId)
    setHypotheses(list)
    setStep(3)
  }

  const handleAddHypothesis = async () => {
    if (!newHypText.trim()) return
    const id = `hyp_${Date.now()}`
    const hyp: HypothesisInput = {
      id,
      text: newHypText,
      directionality: newHypDirection,
      analysisRole: newHypRole,
      isPreregistered: false,
      status: 'untested',
    }
    await addOrUpdateHypothesis(programId, studyId, hyp)
    setNewHypText('')
    const list = await listHypotheses(programId, studyId)
    setHypotheses(list)
  }

  const handleFreeze = async () => {
    if (!versionId.trim()) {
      alert('请输入版本号！')
      return
    }
    try {
      const res = await freezeProtocol(programId, studyId, versionId, preregUrl)
      setFrozenHash(res.frozenHash)
      setIsFrozen(true)
      alert(`协议已成功冻结！版本号: ${res.versionId}`)
      setStep(5)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      alert(`冻结失败: ${msg}`)
    }
  }

  const handleCheckDeviation = async () => {
    const analysisSpec = {
      outcomeVariableId: testOutcome,
      predictorVariableIds: testPredictors.split(',').map(s => s.trim()).filter(Boolean),
      controlVariableIds: testCovariates.split(',').map(s => s.trim()).filter(Boolean),
    }
    try {
      const devs = await verifyProtocolDeviation(programId, studyId, versionId, analysisSpec)
      setDeviations(devs)
      setDevChecked(true)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      alert(`检测失败: ${msg}`)
    }
  }

  return (
    <div className="adv-main" style={{ maxWidth: '900px' }}>
      <div className="adv-breadcrumb">
        <span className="muted">研究协议管理中心 (WP-PROTOCOL)</span>
      </div>

      <div style={{ display: 'flex', gap: '12px', marginBottom: '32px' }}>
        {[1, 2, 3, 4, 5].map(s => (
          <button
            key={s}
            type="button"
            onClick={() => setStep(s)}
            className="adv-back-btn"
            style={{
              background: step === s ? '#1f5a49' : '#e8f0eb',
              color: step === s ? '#fff' : '#1f5a49',
              flex: 1,
              justifyContent: 'center',
            }}
          >
            步骤 {s}: {['基本计划', '协议设计', '设定假设', '签署冻结', '偏离检测'][s - 1]}
          </button>
        ))}
      </div>

      {step === 1 && (
        <section className="adv-capability-section">
          <h2>步骤 1: 声明 Research Program</h2>
          <div className="adv-section-header">
            <p className="muted">声明你的核心学术课题、目标期刊及构念注册表。</p>
          </div>
          <div className="form-group" style={{ display: 'grid', gap: '16px', marginTop: '20px' }}>
            <label htmlFor="program-id-input">
              计划 ID:
              <input
                id="program-id-input"
                type="text"
                className="form-control"
                value={programId}
                onChange={e => setProgramId(e.target.value)}
                style={{ width: '100%', padding: '8px', border: '1px solid #c0d1c7', borderRadius: '4px' }}
              />
            </label>
            <label htmlFor="program-title-input">
              课题名称:
              <input
                id="program-title-input"
                type="text"
                className="form-control"
                placeholder="例如：基于工作设计理论的变革型领导力与下属敬业度研究"
                value={programTitle}
                onChange={e => setProgramTitle(e.target.value)}
                style={{ width: '100%', padding: '8px', border: '1px solid #c0d1c7', borderRadius: '4px' }}
              />
            </label>
            <label htmlFor="theoretical-question-input">
              核心理论问题:
              <textarea
                id="theoretical-question-input"
                className="form-control"
                rows={3}
                placeholder="说明你的主要自变量、因变量与核心理论链条..."
                value={theoreticalQuestion}
                onChange={e => setTheoreticalQuestion(e.target.value)}
                style={{ width: '100%', padding: '8px', border: '1px solid #c0d1c7', borderRadius: '4px' }}
              />
            </label>
            <label htmlFor="target-journal-input">
              目标期刊:
              <input
                id="target-journal-input"
                type="text"
                className="form-control"
                value={targetJournal}
                onChange={e => setTargetJournal(e.target.value)}
                style={{ width: '100%', padding: '8px', border: '1px solid #c0d1c7', borderRadius: '4px' }}
              />
            </label>
            <label htmlFor="owner-input">
              课题负责人:
              <input
                id="owner-input"
                type="text"
                className="form-control"
                value={owner}
                onChange={e => setOwner(e.target.value)}
                style={{ width: '100%', padding: '8px', border: '1px solid #c0d1c7', borderRadius: '4px' }}
              />
            </label>
            <label htmlFor="construct-keys-input">
              构念注册表 (英文逗号分隔):
              <input
                id="construct-keys-input"
                type="text"
                className="form-control"
                placeholder="construct_autonomy, construct_engagement, construct_performance"
                value={constructKeys}
                onChange={e => setConstructKeys(e.target.value)}
                style={{ width: '100%', padding: '8px', border: '1px solid #c0d1c7', borderRadius: '4px' }}
              />
            </label>
            <div style={{ display: 'flex', gap: '12px', marginTop: '12px' }}>
              <button
                type="button"
                className="adv-back-btn"
                onClick={loadProgramData}
              >
                加载计划数据
              </button>
              <button
                type="button"
                className="adv-back-btn"
                style={{ background: '#1f5a49', color: '#fff' }}
                onClick={handleSaveProgram}
              >
                保存并下一步
              </button>
            </div>
          </div>
        </section>
      )}

      {step === 2 && (
        <section className="adv-capability-section">
          <h2>步骤 2: 设计 Study Protocol Draft</h2>
          <div className="adv-section-header">
            <p className="muted">定义具体研究协议（样本收集计划与统计设计规划）。</p>
          </div>
          <div className="form-group" style={{ display: 'grid', gap: '16px', marginTop: '20px' }}>
            <label htmlFor="study-id-input">
              研究 ID:
              <input
                id="study-id-input"
                type="text"
                className="form-control"
                value={studyId}
                onChange={e => setStudyId(e.target.value)}
                style={{ width: '100%', padding: '8px', border: '1px solid #c0d1c7', borderRadius: '4px' }}
              />
            </label>
            <label htmlFor="study-title-input">
              研究标题:
              <input
                id="study-title-input"
                type="text"
                className="form-control"
                value={studyTitle}
                onChange={e => setStudyTitle(e.target.value)}
                style={{ width: '100%', padding: '8px', border: '1px solid #c0d1c7', borderRadius: '4px' }}
              />
            </label>
            <label htmlFor="design-type-select">
              研究类型:
              <select
                id="design-type-select"
                className="form-control"
                value={designType}
                onChange={e => setDesignType(e.target.value as 'survey' | 'experimental' | 'longitudinal' | 'diary')}
                style={{ width: '100%', padding: '8px', border: '1px solid #c0d1c7', borderRadius: '4px' }}
              >
                <option value="survey">调查问卷 (Survey)</option>
                <option value="experimental">实验法 (Experimental)</option>
                <option value="longitudinal">纵向追踪 (Longitudinal)</option>
                <option value="diary">日记法 (Diary)</option>
              </select>
            </label>

            <fieldset style={{ border: '1px solid #c0d1c7', padding: '16px', borderRadius: '4px' }}>
              <legend style={{ padding: '0 8px', fontWeight: 'bold' }}>抽样与准入准出标准</legend>
              <label htmlFor="population-input" style={{ display: 'block', marginBottom: '12px' }}>
                目标人群:
                <input
                  id="population-input"
                  type="text"
                  className="form-control"
                  value={population}
                  onChange={e => setPopulation(e.target.value)}
                  style={{ width: '100%', padding: '8px', border: '1px solid #c0d1c7', borderRadius: '4px' }}
                />
              </label>
              <label htmlFor="recruitment-input" style={{ display: 'block', marginBottom: '12px' }}>
                招募渠道:
                <input
                  id="recruitment-input"
                  type="text"
                  className="form-control"
                  value={recruitment}
                  onChange={e => setRecruitment(e.target.value)}
                  style={{ width: '100%', padding: '8px', border: '1px solid #c0d1c7', borderRadius: '4px' }}
                />
              </label>
              <label htmlFor="inclusion-criteria-input" style={{ display: 'block', marginBottom: '12px' }}>
                纳入标准 (每行一条):
                <textarea
                  id="inclusion-criteria-input"
                  className="form-control"
                  rows={2}
                  value={inclusionCriteria}
                  onChange={e => setInclusionCriteria(e.target.value)}
                  style={{ width: '100%', padding: '8px', border: '1px solid #c0d1c7', borderRadius: '4px' }}
                />
              </label>
              <label htmlFor="exclusion-criteria-input" style={{ display: 'block' }}>
                排除与剔除标准 (每行一条):
                <textarea
                  id="exclusion-criteria-input"
                  className="form-control"
                  rows={2}
                  value={exclusionCriteria}
                  onChange={e => setExclusionCriteria(e.target.value)}
                  style={{ width: '100%', padding: '8px', border: '1px solid #c0d1c7', borderRadius: '4px' }}
                />
              </label>
            </fieldset>

            {designType === 'experimental' && (
              <fieldset style={{ border: '1px solid #c0d1c7', padding: '16px', borderRadius: '4px' }}>
                <legend style={{ padding: '0 8px', fontWeight: 'bold' }}>实验控制参数</legend>
                <label htmlFor="conditions-input" style={{ display: 'block', marginBottom: '12px' }}>
                  实验组别名称 (逗号分隔):
                  <input
                    id="conditions-input"
                    type="text"
                    className="form-control"
                    placeholder="control, treatment_a, treatment_b"
                    value={conditions}
                    onChange={e => setConditions(e.target.value)}
                    style={{ width: '100%', padding: '8px', border: '1px solid #c0d1c7', borderRadius: '4px' }}
                  />
                </label>
                <label htmlFor="randomization-unit-input" style={{ display: 'block', marginBottom: '12px' }}>
                  随机化单元:
                  <input
                    id="randomization-unit-input"
                    type="text"
                    className="form-control"
                    placeholder="例如：个人、班级、企业"
                    value={randomizationUnit}
                    onChange={e => setRandomizationUnit(e.target.value)}
                    style={{ width: '100%', padding: '8px', border: '1px solid #c0d1c7', borderRadius: '4px' }}
                  />
                </label>
                <label htmlFor="allocation-ratio-input" style={{ display: 'block' }}>
                  分配比例:
                  <input
                    id="allocation-ratio-input"
                    type="text"
                    className="form-control"
                    placeholder="例如：1:1"
                    value={allocationRatio}
                    onChange={e => setAllocationRatio(e.target.value)}
                    style={{ width: '100%', padding: '8px', border: '1px solid #c0d1c7', borderRadius: '4px' }}
                  />
                </label>
              </fieldset>
            )}

            <fieldset style={{ border: '1px solid #c0d1c7', padding: '16px', borderRadius: '4px' }}>
              <legend style={{ padding: '0 8px', fontWeight: 'bold' }}>统计计划设计 (Planned Estimands)</legend>
              {estimands.map((est, idx) => (
                <div key={est.estimandId || idx} style={{ display: 'grid', gap: '8px', marginBottom: '12px' }}>
                  <div style={{ fontWeight: 'bold' }}>估算目标 {idx + 1}:</div>
                  <label htmlFor={`estimand-outcome-${idx}`}>
                    规划因变量 (Outcome ID):
                    <input
                      id={`estimand-outcome-${idx}`}
                      type="text"
                      className="form-control"
                      value={est.outcomeVariableId ?? ''}
                      onChange={e => {
                        const newEsts = [...estimands]
                        newEsts[idx].outcomeVariableId = e.target.value
                        setEstimands(newEsts)
                      }}
                      style={{ width: '100%', padding: '8px', border: '1px solid #c0d1c7', borderRadius: '4px' }}
                    />
                  </label>
                  <label htmlFor={`estimand-predictors-${idx}`}>
                    规划自变量 (Predictors, 逗号分隔):
                    <input
                      id={`estimand-predictors-${idx}`}
                      type="text"
                      className="form-control"
                      value={est.predictorVariableIds?.join(', ') ?? ''}
                      onChange={e => {
                        const newEsts = [...estimands]
                        newEsts[idx].predictorVariableIds = e.target.value.split(',').map(s => s.trim()).filter(Boolean)
                        setEstimands(newEsts)
                      }}
                      style={{ width: '100%', padding: '8px', border: '1px solid #c0d1c7', borderRadius: '4px' }}
                    />
                  </label>
                  <label htmlFor={`estimand-covariates-${idx}`}>
                    规划控制变量 (Controls/Covariates, 逗号分隔):
                    <input
                      id={`estimand-covariates-${idx}`}
                      type="text"
                      className="form-control"
                      value={est.covariateVariableIds?.join(', ') ?? ''}
                      onChange={e => {
                        const newEsts = [...estimands]
                        newEsts[idx].covariateVariableIds = e.target.value.split(',').map(s => s.trim()).filter(Boolean)
                        setEstimands(newEsts)
                      }}
                      style={{ width: '100%', padding: '8px', border: '1px solid #c0d1c7', borderRadius: '4px' }}
                    />
                  </label>
                </div>
              ))}
            </fieldset>

            <button
              type="button"
              className="adv-back-btn"
              style={{ background: '#1f5a49', color: '#fff', justifySelf: 'start' }}
              onClick={handleSaveProtocolDraft}
            >
              保存协议草稿并下一步
            </button>
          </div>
        </section>
      )}

      {step === 3 && (
        <section className="adv-capability-section">
          <h2>步骤 3: 声明假说 (Hypotheses Specs)</h2>
          <div className="adv-section-header">
            <p className="muted">录入并绑定该项研究设计要测试的假说内容与方向性要求。</p>
          </div>

          <div style={{ border: '1px solid #e8f0eb', borderRadius: '4px', padding: '16px', background: '#f5f9f6', marginBottom: '20px' }}>
            <h4>新增假说</h4>
            <div style={{ display: 'grid', gap: '12px', marginTop: '12px' }}>
              <label htmlFor="new-hyp-text">
                假说内容文本:
                <textarea
                  id="new-hyp-text"
                  className="form-control"
                  rows={2}
                  placeholder="例如：工作自主性正向预测员工敬业度。"
                  value={newHypText}
                  onChange={e => setNewHypText(e.target.value)}
                  style={{ width: '100%', padding: '8px', border: '1px solid #c0d1c7', borderRadius: '4px' }}
                />
              </label>
              <div style={{ display: 'flex', gap: '12px' }}>
                <label htmlFor="new-hyp-direction" style={{ flex: 1 }}>
                  假说方向:
                  <select
                    id="new-hyp-direction"
                    className="form-control"
                    value={newHypDirection}
                    onChange={e => setNewHypDirection(e.target.value as 'positive' | 'negative' | 'non_directional')}
                    style={{ width: '100%', padding: '8px', border: '1px solid #c0d1c7', borderRadius: '4px' }}
                  >
                    <option value="positive">正向 (Positive)</option>
                    <option value="negative">负向 (Negative)</option>
                    <option value="non_directional">无方向性 (Non-directional)</option>
                  </select>
                </label>
                <label htmlFor="new-hyp-role" style={{ flex: 1 }}>
                  假说角色:
                  <select
                    id="new-hyp-role"
                    className="form-control"
                    value={newHypRole}
                    onChange={e => setNewHypRole(e.target.value as 'primary' | 'secondary' | 'exploratory')}
                    style={{ width: '100%', padding: '8px', border: '1px solid #c0d1c7', borderRadius: '4px' }}
                  >
                    <option value="primary">主效应/核心 (Primary)</option>
                    <option value="secondary">副效应 (Secondary)</option>
                    <option value="exploratory">探索性 (Exploratory)</option>
                  </select>
                </label>
              </div>
              <button
                type="button"
                className="adv-back-btn"
                style={{ justifySelf: 'start' }}
                onClick={handleAddHypothesis}
              >
                添加假说并保存
              </button>
            </div>
          </div>

          <h3>已录入的假说列表</h3>
          {hypotheses.length === 0 ? (
            <p className="muted">当前没有任何假说。</p>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '12px' }}>
              <thead>
                <tr style={{ background: '#e8f0eb', borderBottom: '2px solid #c0d1c7' }}>
                  <th style={{ padding: '8px', textAlign: 'left' }}>ID</th>
                  <th style={{ padding: '8px', textAlign: 'left' }}>文本</th>
                  <th style={{ padding: '8px', textAlign: 'left' }}>方向</th>
                  <th style={{ padding: '8px', textAlign: 'left' }}>角色</th>
                  <th style={{ padding: '8px', textAlign: 'left' }}>状态</th>
                </tr>
              </thead>
              <tbody>
                {hypotheses.map(h => (
                  <tr key={h.id} style={{ borderBottom: '1px solid #e8f0eb' }}>
                    <td style={{ padding: '8px' }}>{h.id}</td>
                    <td style={{ padding: '8px' }}>{h.text}</td>
                    <td style={{ padding: '8px' }}>{h.directionality}</td>
                    <td style={{ padding: '8px' }}>{h.analysisRole}</td>
                    <td style={{ padding: '8px' }}>{h.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <button
            type="button"
            className="adv-back-btn"
            style={{ background: '#1f5a49', color: '#fff', marginTop: '20px' }}
            onClick={() => setStep(4)}
          >
            下一步
          </button>
        </section>
      )}

      {step === 4 && (
        <section className="adv-capability-section">
          <h2>步骤 4: 签署与冻结协议 (Preregistration Freeze)</h2>
          <div className="adv-section-header">
            <p className="muted">在进行正式数据导入与分析前，将协议草稿锁定为只读预注册版本。</p>
          </div>

          <div className="form-group" style={{ display: 'grid', gap: '16px', marginTop: '20px' }}>
            <label htmlFor="version-id-input">
              预注册版本号:
              <input
                id="version-id-input"
                type="text"
                className="form-control"
                value={versionId}
                disabled={isFrozen}
                onChange={e => setVersionId(e.target.value)}
                style={{ width: '100%', padding: '8px', border: '1px solid #c0d1c7', borderRadius: '4px' }}
              />
            </label>
            <label htmlFor="prereg-url-input">
              公开预注册链接 (如 OSF/AsPredicted 链接):
              <input
                id="prereg-url-input"
                type="text"
                className="form-control"
                value={preregUrl}
                disabled={isFrozen}
                placeholder="https://osf.io/..."
                onChange={e => setPreregUrl(e.target.value)}
                style={{ width: '100%', padding: '8px', border: '1px solid #c0d1c7', borderRadius: '4px' }}
              />
            </label>

            {isFrozen ? (
              <div style={{ background: '#e8f0eb', padding: '16px', borderRadius: '4px', border: '1px solid #c0d1c7' }}>
                <h4 style={{ color: '#1f5a49', margin: 0 }}>协议已冻结</h4>
                <p style={{ wordBreak: 'break-all', marginTop: '8px' }}>
                  <strong>SHA-256 完整性哈希:</strong> <code style={{ background: '#fff', padding: '2px 4px', borderRadius: '2px' }}>{frozenHash}</code>
                </p>
                <p className="muted" style={{ margin: 0 }}>
                  根据科学规范，此协议已完全锁定。任何之后的实际分析 design 偏差都将被偏离检测机制所记录。
                </p>
              </div>
            ) : (
              <div style={{ background: '#fff9e6', padding: '16px', borderRadius: '4px', border: '1px solid #ffe89e', color: '#856404' }}>
                ⚠️ <strong>警告：</strong> 冻结后此版本将被写保护，并且成为只读。不可逆转！
              </div>
            )}

            {!isFrozen && (
              <button
                type="button"
                className="adv-back-btn"
                style={{ background: '#721c24', color: '#fff', border: 'none' }}
                onClick={handleFreeze}
              >
                🔐 确认签署并冻结协议
              </button>
            )}
            {isFrozen && (
              <button
                type="button"
                className="adv-back-btn"
                style={{ background: '#1f5a49', color: '#fff' }}
                onClick={() => setStep(5)}
              >
                前往偏离检测
              </button>
            )}
          </div>
        </section>
      )}

      {step === 5 && (
        <section className="adv-capability-section">
          <h2>步骤 5: 协议设计偏离审计 (Deviation Audit)</h2>
          <div className="adv-section-header">
            <p className="muted">对比实际运行的分析设计模型与预注册冷冻协议的偏离度，输出合规警告。</p>
          </div>

          <div style={{ border: '1px solid #c0d1c7', borderRadius: '4px', padding: '16px', background: '#f5f9f6', marginBottom: '20px' }}>
            <h4>模拟或实际运行的 `AnalysisSpec`</h4>
            <div style={{ display: 'grid', gap: '12px', marginTop: '12px' }}>
              <label htmlFor="test-outcome-input">
                因变量 (Outcome ID):
                <input
                  id="test-outcome-input"
                  type="text"
                  className="form-control"
                  value={testOutcome}
                  onChange={e => setTestOutcome(e.target.value)}
                  style={{ width: '100%', padding: '8px', border: '1px solid #c0d1c7', borderRadius: '4px' }}
                />
              </label>
              <label htmlFor="test-predictors-input">
                自变量列表 (Predictors, 逗号分隔):
                <input
                  id="test-predictors-input"
                  type="text"
                  className="form-control"
                  value={testPredictors}
                  onChange={e => setTestPredictors(e.target.value)}
                  style={{ width: '100%', padding: '8px', border: '1px solid #c0d1c7', borderRadius: '4px' }}
                />
              </label>
              <label htmlFor="test-covariates-input">
                控制变量列表 (Covariates, 逗号分隔):
                <input
                  id="test-covariates-input"
                  type="text"
                  className="form-control"
                  value={testCovariates}
                  onChange={e => setTestCovariates(e.target.value)}
                  style={{ width: '100%', padding: '8px', border: '1px solid #c0d1c7', borderRadius: '4px' }}
                />
              </label>
              <button
                type="button"
                className="adv-back-btn"
                style={{ justifySelf: 'start', background: '#1f5a49', color: '#fff' }}
                onClick={handleCheckDeviation}
              >
                🔎 执行偏离度差异检测 (Compare with {versionId})
              </button>
            </div>
          </div>

          {devChecked && (
            <div>
              <h3>偏离检测报告</h3>
              {deviations.length === 0 ? (
                <div style={{ background: '#d4edda', color: '#155724', padding: '16px', borderRadius: '4px', border: '1px solid #c3e6cb' }}>
                  🎉 <strong>完美契合！</strong> 分析模型完全符合预注册冻结协议的设计要求，无任何偏离警告。
                </div>
              ) : (
                <div style={{ display: 'grid', gap: '12px' }}>
                  {deviations.map((d, i) => (
                    <div
                      key={d.deviationType || i}
                      style={{ background: '#f8d7da', color: '#721c24', padding: '16px', borderRadius: '4px', border: '1px solid #f5c6cb' }}
                    >
                      <h4 style={{ margin: 0 }}>⚠️ 偏离警告: {d.deviationType}</h4>
                      <p style={{ margin: '4px 0 0 0' }}>{d.message}</p>
                      <div style={{ marginTop: '8px', fontSize: '12px', display: 'flex', gap: '20px' }}>
                        <span><strong>预期规划 (Expected):</strong> {JSON.stringify(d.expectedValue)}</span>
                        <span><strong>实际执行 (Actual):</strong> {JSON.stringify(d.actualValue)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </section>
      )}
    </div>
  )
}
