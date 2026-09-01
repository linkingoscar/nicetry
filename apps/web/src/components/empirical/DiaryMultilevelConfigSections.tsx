import type { DiaryMultilevelOptions } from '../../types'

export interface DiaryCandidate {
  id: string
  label: string
}

export function createDiaryMultilevelDefault(
  subjectCandidates: DiaryCandidate[],
  defaultSubjectId?: string | null,
  defaultTimeId?: string | null,
): DiaryMultilevelOptions {
  const subjectId = defaultSubjectId && subjectCandidates.some((candidate) => candidate.id === defaultSubjectId)
    ? defaultSubjectId
    : subjectCandidates[0]?.id ?? ''
  return {
    analysisType: 'lmm',
    subjectVariableId: subjectId,
    timeVariableId: defaultTimeId ?? '',
    outcomeVariableId: '',
    predictorVariableId: '',
    mediatorVariableId: null,
    level2CovariateIds: [],
    controlVariableIds: [],
    randomSlope: true,
    residualStructure: 'independent',
    outcomeFamily: 'gaussian',
    countModel: 'standard',
    zeroProcessPredictors: 'intercept_only',
    distributionDiagnosticSimulations: 250,
    distributionDiagnosticSeed: 20260729,
    clusterStructure: 'nested',
    crossClassVariableId: null,
    exposureVariableId: null,
    centering: 'person_mean',
    mediationType: '1-1-1',
    temporalEffect: 'contemporaneous',
    lagOrder: 1,
    expectedTimeInterval: null,
    timeIntervalTolerance: 0,
    includeLinearTime: true,
    includeQuadraticTime: false,
    timeOriginStrategy: 'sample_mean',
    customTimeOrigin: null,
    level2ModeratorVariableId: null,
    expectedObservationsPerPerson: null,
    minimumComplianceRate: 0,
    excludeLowCompliance: false,
    responseLatencyVariableId: null,
    minimumResponseLatency: null,
    maximumResponseLatency: null,
    excludeOutOfWindow: false,
    reliabilityConstructs: [],
    missingStrategy: 'complete_cases',
    imputationCount: 20,
    imputationIterations: 10,
    runRobustnessChecks: false,
    powerAnalysis: null,
    dsem: null,
  }
}

export function diaryAnalysisTypePatch(value: DiaryMultilevelOptions, analysisType: DiaryMultilevelOptions['analysisType']): Partial<DiaryMultilevelOptions> {
  return {
    analysisType,
    outcomeFamily: analysisType === 'glmm' ? 'binomial' : 'gaussian',
    countModel: 'standard',
    zeroProcessPredictors: 'intercept_only',
    clusterStructure: ['mediation', 'bayesian_dsem'].includes(analysisType)
      ? 'nested'
      : value.clusterStructure,
    crossClassVariableId: ['mediation', 'bayesian_dsem'].includes(analysisType)
      ? null
      : value.crossClassVariableId,
    exposureVariableId: analysisType === 'glmm'
      ? value.exposureVariableId
      : null,
    centering: analysisType === 'bayesian_dsem'
      ? 'person_mean'
      : value.centering,
    temporalEffect: analysisType === 'bayesian_dsem'
      ? 'lagged'
      : analysisType === 'mediation' && value.temporalEffect === 'both'
        ? 'contemporaneous'
        : value.temporalEffect,
    missingStrategy: ['mediation', 'glmm', 'bayesian_dsem'].includes(analysisType)
      ? 'complete_cases'
      : value.missingStrategy,
    powerAnalysis: analysisType === 'lmm'
      ? value.powerAnalysis
      : null,
    dsem: analysisType === 'bayesian_dsem'
      ? (value.dsem ?? {
        chains: 4,
        iterations: 2000,
        warmup: 1000,
        thin: 1,
        priorMeanSd: 1,
        priorScale: 1,
        randomDynamicSlopes: true,
        plotDrawsPerChain: 300,
        predictiveReplications: 200,
        runPriorSensitivity: true,
        seed: 20260728,
      })
      : null,
  }
}

interface DiaryAnalysisTypeSelectProps {
  value: DiaryMultilevelOptions
  onChange: (patch: Partial<DiaryMultilevelOptions>) => void
}

export function DiaryAnalysisTypeSelect({ value, onChange }: DiaryAnalysisTypeSelectProps) {
  return (
    <label>分析类型
      <select
        value={value.analysisType}
        onChange={(event) => onChange(diaryAnalysisTypePatch(value, event.target.value as DiaryMultilevelOptions['analysisType']))}
      >
        <option value="lmm">二层线性混合模型</option>
        <option value="glmm">二元/计数广义多层模型</option>
        <option value="mediation">多层中介</option>
        <option value="bayesian_dsem">Bayesian DSEM（T≥20）</option>
      </select>
    </label>
  )
}

interface DiaryVariableSelectProps {
  label: string
  value: string
  options: DiaryCandidate[]
  disabled?: boolean
  placeholder: string
  onChange: (value: string) => void
}

export function DiaryVariableSelect({
  label,
  value,
  options,
  disabled = false,
  placeholder,
  onChange,
}: DiaryVariableSelectProps) {
  return (
    <label>{label}
      <select
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="">{placeholder}</option>
        {options.map((candidate) => (
          <option key={candidate.id} value={candidate.id}>{candidate.label}</option>
        ))}
      </select>
    </label>
  )
}
