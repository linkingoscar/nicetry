import { useMemo, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'

import { getAdvancedAnalysisResult } from '../../api/advanced'
import {
  createImputationPlan,
  getImputationPlanCompatibility,
  runImputationPlan,
} from '../../api/imputation-plans'
import type { AdvancedAnalysisCapability } from '../../types'
import type { ResolvedAnalysisContext } from '../../types/analysis-context'
import type { AdvancedJobResponse, AdvancedResultResponse } from '../../types/advanced'
import type { ImputationPlanCreateRequest } from '../../types/workflows'
import type { DatasetVariableItem } from '../advanced/DatasetVariablePicker'
import { AdvancedResultView } from '../advanced/AdvancedResultView'
import { ImputationWizard, type ImputationWizardSpec } from '../advanced/ImputationWizard'
import { JobProgress } from '../advanced/JobProgress'
import { registerOutputRun } from '../analyses/outputRunRegistry'

interface ImputationPlanWorkspaceProps {
  context: ResolvedAnalysisContext
  variables: DatasetVariableItem[]
  draftId?: string | null
}

const MI_METHOD_ID = 'missing.multiple-imputation'
const MI_METHOD_LABEL = '多重插补与 Rubin 合并'

function initialSpec(context: ResolvedAnalysisContext, variables: DatasetVariableItem[]): ImputationWizardSpec {
  const numeric = variables.filter((variable) => variable.type === 'numeric')
  const outcomeId = numeric[0]?.id ?? ''
  const predictorIds = numeric.slice(1, 3).map((variable) => variable.id)
  const modelIds = [outcomeId, ...predictorIds].filter(Boolean)
  const selectedIds = variables
    .filter((variable) => (variable.missingRate ?? 0) > 0)
    .map((variable) => variable.id)
    .slice(0, 5)
  const imputationIds = selectedIds.length > 0 ? selectedIds : modelIds
  return {
    family: 'multiple_imputation',
    datasetVersionId: context.dataset.id,
    method: 'mice_fcs',
    imputations: 20,
    iterations: 20,
    variables: imputationIds.map((variableId) => ({
      variableId,
      method: 'auto',
      predictorIds: modelIds.filter((id) => id !== variableId),
    })),
    passiveRules: [],
    clusterVariableId: context.structure?.roles.clusterId ?? null,
    pooling: 'rubin',
    pooledAnalysis: {
      modelType: 'linear_regression',
      outcomeId,
      predictorIds,
      includeIntercept: true,
    },
    diagnostics: ['trace', 'distribution', 'fraction_missing_information'],
    seed: 20260801,
  }
}

function capability(): AdvancedAnalysisCapability {
  return {
    family: 'multiple_imputation',
    label: MI_METHOD_LABEL,
    status: 'supported',
    specVersion: '0.1.0',
    resultVersion: '0.1.0',
    plannedEngine: 'R mice',
    minimumValidation: [],
    executionAvailable: true,
    slices: [],
  }
}

export function ImputationPlanWorkspace({ context, variables, draftId = null }: ImputationPlanWorkspaceProps) {
  const [spec, setSpec] = useState(() => initialSpec(context, variables))
  const [plan, setPlan] = useState<Awaited<ReturnType<typeof createImputationPlan>> | null>(null)
  const [job, setJob] = useState<AdvancedJobResponse | null>(null)
  const [result, setResult] = useState<AdvancedResultResponse | null>(null)
  const structureRequired = context.studyContext?.value
    ? !(
        context.studyContext.value.design === 'observational'
        && context.studyContext.value.timeStructure === 'cross_sectional'
        && context.studyContext.value.dependenceStructure === 'independent'
      )
    : true
  const planMutation = useMutation({
    mutationFn: () => {
      if (structureRequired && !context.structure?.id) throw new Error('当前上下文尚未确认 structureVersionId')
      const substantiveModel: ImputationPlanCreateRequest['substantiveModel'] = {
        modelType: 'linear_regression',
        outcomeId: spec.pooledAnalysis.outcomeId,
        predictorIds: spec.pooledAnalysis.predictorIds,
        includeIntercept: spec.pooledAnalysis.includeIntercept,
      }
      const request: ImputationPlanCreateRequest = {
        contextHash: context.contextHash,
        sampleVersionId: context.sample.id,
        measurementVersionId: context.measurement?.id ?? null,
        structureVersionId: context.structure?.id ?? null,
        substantiveModel,
        variables: spec.variables as unknown as Array<Record<string, unknown>>,
        passiveRules: spec.passiveRules ?? [],
        clusterVariableId: spec.clusterVariableId ?? null,
        imputations: spec.imputations,
        iterations: spec.iterations,
        seed: spec.seed ?? 20260801,
        diagnostics: spec.diagnostics,
      }
      if (spec.substantiveModelHash) request.substantiveModelHash = spec.substantiveModelHash
      return createImputationPlan(context.dataset.id, request)
    },
    onSuccess: (created) => {
      setPlan(created)
      setJob(null)
      setResult(null)
    },
  })
  const compatibilityQuery = useQuery({
    queryKey: ['imputation-plan-compatibility', plan?.id, draftId],
    queryFn: () => getImputationPlanCompatibility(plan?.id ?? '', draftId ?? ''),
    enabled: Boolean(plan?.id && draftId),
    staleTime: 0,
  })
  const runMutation = useMutation({
    mutationFn: () => runImputationPlan(plan?.id ?? ''),
    onSuccess: (started) => {
      registerOutputRun({
        runId: started.job.id,
        projectId: context.projectId,
        datasetVersionId: context.dataset.id,
        measurementVersionId: context.measurement?.id ?? null,
        source: 'advanced',
        label: MI_METHOD_LABEL,
        methodId: MI_METHOD_ID,
        family: 'multiple_imputation',
        createdAt: started.job.createdAt ?? new Date().toISOString(),
      })
      setJob(started.job)
      setResult(null)
    },
  })
  const resultQuery = useQuery({
    queryKey: ['advanced-analysis-result', job?.id],
    queryFn: () => getAdvancedAnalysisResult(job?.id ?? ''),
    enabled: job?.status === 'succeeded' && !result,
    retry: false,
  })
  const displayedResult = result ?? resultQuery.data ?? null
  const planLineage = useMemo(() => plan ? [
    ['计划版本', plan.id],
    ['数据版本', plan.datasetVersionId],
    ['数据 SHA-256', plan.datasetSha256],
    ['样本哈希', plan.sampleHash],
    ['结构哈希', plan.structureHash],
    ['测量哈希', plan.measurementHash ?? '无测量版本'],
    ['预测矩阵哈希', plan.predictorMatrixHash],
  ] : [], [plan])

  return (
    <section className="context-mi-workspace" aria-labelledby="context-mi-heading">
      <header>
        <p className="eyebrow">分析设置 → 检查插补计划 → 运行分析</p>
        <h2 id="context-mi-heading">{MI_METHOD_LABEL}</h2>
        <p className="muted">先冻结下游线性模型、缺失变量和插补矩阵，再显式运行。服务端任务是结果真相源，运行引用会进入统一输出工作区。</p>
      </header>
      {!plan ? (
        <>
          <ImputationWizard spec={spec} onChange={setSpec} variables={variables} />
          {planMutation.error ? <p className="error-message" role="alert">插补计划创建失败：{planMutation.error.message}</p> : null}
          <button type="button" className="run-button" onClick={() => planMutation.mutate()} disabled={planMutation.isPending || (structureRequired && !context.structure?.id) || !spec.pooledAnalysis.outcomeId || spec.pooledAnalysis.predictorIds.length === 0 || spec.variables.length === 0}>
            {planMutation.isPending ? '正在检查并保存设置…' : '检查并保存插补设置'}
          </button>
        </>
      ) : displayedResult ? (
        <>
          <div className="context-lineage-grid">
            {planLineage.map(([label, value]) => <div key={label}><span>{label}</span><code>{value}</code></div>)}
          </div>
          <AdvancedResultView
            result={displayedResult}
            capability={capability()}
            jobId={job?.id ?? ''}
            onNewAnalysis={() => {
              setJob(null)
              setResult(null)
            }}
          />
        </>
      ) : (
        <>
          <div className="context-lineage-grid">
            {planLineage.map(([label, value]) => <div key={label}><span>{label}</span><code>{value}</code></div>)}
          </div>
          {compatibilityQuery.data ? <p className={compatibilityQuery.data.compatible ? 'method-note' : 'method-warning'} role="status">分析草稿兼容性：{compatibilityQuery.data.compatible ? '可以运行' : compatibilityQuery.data.reasons.join('、')}</p> : null}
          {job ? (
            <JobProgress
              jobId={job.id}
              initialJob={job}
              capability={capability()}
              onComplete={(completed, completedResult) => {
                setJob(completed)
                setResult(completedResult ?? null)
              }}
              onCancel={() => setJob(null)}
            />
          ) : (
            <>
              {runMutation.error ? <p className="error-message" role="alert">插补运行失败：{runMutation.error.message}</p> : null}
              <button type="button" className="run-button" onClick={() => runMutation.mutate()} disabled={runMutation.isPending || compatibilityQuery.data?.compatible === false}>
                {runMutation.isPending ? '正在启动分析…' : '运行多重插补与 Rubin 合并'}
              </button>
              <button type="button" className="secondary-button" onClick={() => setPlan(null)}>返回修改设置</button>
            </>
          )}
        </>
      )}
    </section>
  )
}
