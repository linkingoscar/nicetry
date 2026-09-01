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
    { view: 'data', label: '数据准备', badge: analysisReady ? '已准备' : activeDataset ? '待确认' : '待导入' },
    { view: 'empirical', label: '统计分析', badge: analysisReady ? '按需运行' : '待准备' },
    { view: 'model', label: '路径与 SEM', badge: analysisReady ? '配置模型' : '待准备' },
    { view: 'methods', label: '方法目录', badge: activeDataset ? '按结构筛选' : '待数据' },
  ]
}
