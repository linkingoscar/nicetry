import type { DatasetVersion } from '../types/datasets'
import type { WorkspaceView } from './workspaceStateTypes'

export interface WorkspaceStep {
  view: WorkspaceView
  label: string
  badge: string
}

interface BuildWorkspaceStepsInput {
  activeDataset: DatasetVersion | null
  analysisReady: boolean
}

export function buildWorkspaceSteps({ activeDataset, analysisReady }: BuildWorkspaceStepsInput): WorkspaceStep[] {
  return [
    { view: 'data', label: '数据', badge: activeDataset ? '当前数据' : '待导入' },
    { view: 'analyze', label: '分析', badge: activeDataset ? (analysisReady ? '可配置' : '按方法检查') : '待数据' },
    { view: 'output', label: '输出', badge: activeDataset ? '运行结果' : '待数据' },
  ]
}
