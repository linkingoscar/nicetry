import { useEffect, useMemo, useState } from 'react'
import { useMutation } from '@tanstack/react-query'

import {
  createDatasetStructureVersion,
  validateDatasetStructure,
} from '../api/studies'
import type { DatasetVariable, StudyContext } from '../types'
import type { StructureValidationResponse } from '../types/study-context'
import { RoleBindingSelector } from './context/RoleBindingSelector'
import type { ResolvedAnalysisContext } from '../types/analysis-context'
import { StructureSetupValidationPanel } from './StructureSetupValidationPanel'
import {
  fromBindings,
  roleName,
  sameRoles,
  toBindings,
  VARIABLE_ROLE_KEYS,
} from './dataStructureSetupUtils'
import type { PersistedStructure, RoleSelection } from './dataStructureSetupUtils'

interface DataStructureSetupProps {
  datasetId: string
  variables: DatasetVariable[]
  context: StudyContext
  studyContextVersionId: string | null
  initialStructure: ResolvedAnalysisContext['structure']
  onValidityChange: (valid: boolean) => void
  onStructureSaved?: () => void
}

export function DataStructureSetup({
  datasetId,
  variables,
  context,
  studyContextVersionId,
  initialStructure,
  onValidityChange,
  onStructureSaved,
}: DataStructureSetupProps) {
  const knownVariableIds = useMemo(() => new Set(variables.map(variable => variable.id)), [variables])
  const [roles, setRoles] = useState<RoleSelection>(() => fromBindings(initialStructure?.roles, knownVariableIds, context, variables))
  const [persisted, setPersisted] = useState<PersistedStructure | null>(initialStructure)
  const [validation, setValidation] = useState<StructureValidationResponse | null>(null)
  const [overrideReason, setOverrideReason] = useState(initialStructure?.overrideReason ?? '')
  const structureSyncInput = useMemo(() => ({
    datasetId,
    studyContextVersionId,
    initialStructure,
    variableIds: [...knownVariableIds].sort().join(','),
  }), [datasetId, initialStructure, knownVariableIds, studyContextVersionId])

  useEffect(() => {
    setRoles(fromBindings(structureSyncInput.initialStructure?.roles, knownVariableIds, context, variables))
    setPersisted(structureSyncInput.initialStructure)
    setValidation(null)
    setOverrideReason(structureSyncInput.initialStructure?.overrideReason ?? '')
  }, [context, knownVariableIds, structureSyncInput, variables])

  const isPanel = context.timeStructure === 'panel'
  const isWidePanel = isPanel && roles.dataLayout === 'wide'
  const subjectRequired = context.timeStructure !== 'cross_sectional'
  const requiresSubjectAndTime = context.timeStructure === 'intensive_longitudinal' || (isPanel && !isWidePanel)
  const requiresCluster = context.dependenceStructure === 'nested'
  const requiresTreatmentOrGroup = context.design !== 'observational'
  const requiresStructureVersion = context.timeStructure !== 'cross_sectional' || requiresCluster || requiresTreatmentOrGroup
  const distinctRoles = useMemo(() => {
    const values = VARIABLE_ROLE_KEYS.map(role => roles[role]).filter(Boolean)
    return values.length === new Set(values).size
  }, [roles])
  const parsedWaveCount = Number(roles.waveCount)
  const wideWaveCountValid = !isWidePanel || (Number.isInteger(parsedWaveCount) && parsedWaveCount >= 2 && parsedWaveCount <= 10)
  const selectionComplete = (
    (!subjectRequired || Boolean(roles.subjectId))
    && (!requiresSubjectAndTime || Boolean(roles.timeId))
    && wideWaveCountValid
    && (!requiresCluster || Boolean(roles.clusterId))
    && (!requiresTreatmentOrGroup || Boolean(roles.groupId || roles.treatmentId))
    && distinctRoles
  )

  const validationMutation = useMutation({
    mutationFn: () => {
      if (!studyContextVersionId) throw new Error('当前项目尚未返回可用的研究上下文版本。')
      return validateDatasetStructure(datasetId, studyContextVersionId, toBindings(roles))
    },
    onSuccess: (result) => setValidation(result),
  })

  const saveMutation = useMutation({
    mutationFn: () => {
      if (!studyContextVersionId) throw new Error('当前项目尚未返回可用的研究上下文版本。')
      if (!validation || validation.status === 'invalid') {
        throw new Error('请先运行结构画像，并修复 invalid 结果。')
      }
      return createDatasetStructureVersion(datasetId, {
        expectedRevision: persisted?.revision ?? null,
        studyContextVersionId,
        roles: toBindings(roles),
        overrideReason: validation.status === 'warning' ? overrideReason.trim() : null,
      })
    },
    onSuccess: (result) => {
      setPersisted(result)
      setValidation(null)
      onStructureSaved?.()
    },
  })

  const persistedMatches = Boolean(
    persisted
    && persisted.studyContextVersionId === studyContextVersionId
    && (persisted.status === 'valid' || persisted.status === 'warning')
    && sameRoles(persisted.roles, roles)
    && selectionComplete,
  )
  const valid = !requiresStructureVersion || persistedMatches

  useEffect(() => onValidityChange(valid), [onValidityChange, valid])

  const updateRole = (role: keyof RoleSelection, value: string) => {
    setRoles(current => ({ ...current, [role]: value }))
    setValidation(null)
    validationMutation.reset()
    saveMutation.reset()
  }
  const updateLayout = (dataLayout: 'long' | 'wide') => {
    setRoles(current => ({
      ...current,
      dataLayout,
      timeId: dataLayout === 'wide' ? '' : current.timeId,
      waveCount: dataLayout === 'wide' ? current.waveCount : '',
    }))
    setValidation(null)
    validationMutation.reset()
    saveMutation.reset()
  }
  const activeWarnings = validation?.warnings ?? persisted?.warnings ?? []
  const activeStatus = validation?.status ?? (persistedMatches ? persisted?.status : null)
  const saveAllowed = Boolean(
    studyContextVersionId
    && validation
    && validation.status !== 'invalid'
    && (validation.status !== 'warning' || overrideReason.trim().length >= 10)
    && !saveMutation.isPending,
  )
  const exampleRolesAutoFilled = !initialStructure && Boolean(roles.subjectId || roles.timeId || roles.waveCount)

  return (
    <section className="structure-setup" aria-labelledby="structure-setup-heading">
      <div>
        <p className="eyebrow">结构角色与版本</p>
        <h2 id="structure-setup-heading">确认观测单位、索引与处理变量</h2>
        <p className="muted">角色先由服务端运行结构画像，再以当前研究上下文版本保存为不可变结构版本。</p>
      </div>
      <RoleBindingSelector
        roles={roles}
        variables={variables}
        isPanel={isPanel}
        isWidePanel={isWidePanel}
        subjectRequired={subjectRequired}
        requiresSubjectAndTime={requiresSubjectAndTime}
        requiresCluster={requiresCluster}
        requiresTreatmentOrGroup={requiresTreatmentOrGroup}
        updateRole={updateRole}
        updateLayout={updateLayout}
      />
      {exampleRolesAutoFilled ? (
        <p className="method-note" role="status">
          已按当前示例数据的字段和时间结构预填角色；请核对后运行结构画像，再保存结构版本。宽格式示例会自动填入波次数，不会虚构时间列。
        </p>
      ) : null}
      {!distinctRoles ? <p className="error-message" role="alert">不同结构角色不能使用同一个变量。</p> : null}
      {requiresTreatmentOrGroup ? (
        <p className="method-note">随机实验或非随机比较都至少要声明分组变量或处理 / 暴露变量；二者可以同时声明，但不能指向同一列。非随机比较仅保存上下文，不会开放准实验因果识别。</p>
      ) : null}
      {isWidePanel ? (
        <p className="method-note">宽格式不会把年龄或列名猜作时间变量；请在后续纵向分析中按 T1–T{roles.waveCount || 'k'} 显式映射波次列。</p>
      ) : null}
      <StructureSetupValidationPanel
        studyContextVersionId={studyContextVersionId}
        requiresStructureVersion={requiresStructureVersion}
        selectionComplete={selectionComplete}
        validation={validation}
        validationMutation={validationMutation}
        saveMutation={saveMutation}
        persistedMatches={persistedMatches}
        activeWarnings={activeWarnings}
        activeStatus={activeStatus}
        overrideReason={overrideReason}
        onOverrideReasonChange={setOverrideReason}
        saveAllowed={saveAllowed}
      />
      {validationMutation.error || saveMutation.error ? (
        <p className="error-message" role="alert">结构版本操作失败：{(validationMutation.error ?? saveMutation.error)?.message}</p>
      ) : null}
      {requiresStructureVersion && !selectionComplete ? (
        <p className="method-note">还需要填写：{[
          ...(!roles.subjectId && subjectRequired ? ['个体 / 研究对象 ID'] : []),
          ...(!roles.timeId && requiresSubjectAndTime ? ['波次 / 时间变量'] : []),
          ...(isWidePanel && !wideWaveCountValid ? ['有效的波次数（2–10）'] : []),
          ...(!roles.clusterId && requiresCluster ? ['聚类 / Level 2 ID'] : []),
          ...(!roles.groupId && !roles.treatmentId && requiresTreatmentOrGroup ? ['分组变量或处理 / 暴露变量'] : []),
          ...(!distinctRoles ? ['不同的结构角色变量'] : []),
        ].join('、')}</p>
      ) : null}
      {persistedMatches ? <p className="method-note">当前角色与服务端已保存的结构版本一致，可以继续进入下游工作流。</p> : null}
      {VARIABLE_ROLE_KEYS.some(role => !roles[role]) && requiresStructureVersion ? (
        <p className="sr-only">未选择的角色：{VARIABLE_ROLE_KEYS.filter(role => !roles[role]).map(role => roleName(role)).join('、')}</p>
      ) : null}
    </section>
  )
}
