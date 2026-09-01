import { useViewport, useReactFlow } from '@xyflow/react'
import { SearchIcon } from './shared/Icons'

export function ZoomScaleBadge() {
  const { zoom } = useViewport()
  const { zoomTo } = useReactFlow()
  const percent = Math.round(zoom * 100)

  return (
    <button
      type="button"
      className="canvas-zoom-badge"
      style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}
      onClick={() => zoomTo(1, { duration: 250 })}
      title="点击直接复位至 100% 缩放；按住 Shift 键在画布拖拽可框选多节点"
    >
      <SearchIcon size={14} /> {percent}%
    </button>
  )
}
