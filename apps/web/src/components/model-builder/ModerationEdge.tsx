import { useState } from 'react'
import {
  BaseEdge,
  EdgeLabelRenderer,
  getBezierPath,
  Position,
  useInternalNode,
  type Edge,
  type EdgeProps,
} from '@xyflow/react'

import type { PathEvidence } from './pathEvidence'

interface ModerationEdgeData extends Record<string, unknown> {
  targetSourceId: string
  targetTargetId: string
  targetLabel: string
  moderatorLabel: string
  evidence: PathEvidence
}

export type ModerationFlowEdge = Edge<ModerationEdgeData, 'moderation'>

function center(node: ReturnType<typeof useInternalNode>) {
  if (!node) return null
  const position = node.internals.positionAbsolute
  return {
    x: position.x + (node.measured.width ?? 0) / 2,
    y: position.y + (node.measured.height ?? 0) / 2,
  }
}

export function ModerationEdge({ id, sourceX, sourceY, sourcePosition = Position.Top, data, markerEnd }: EdgeProps<ModerationFlowEdge>) {
  const [isHovered, setIsHovered] = useState(false)
  const sourceNode = useInternalNode(data?.targetSourceId ?? '')
  const targetNode = useInternalNode(data?.targetTargetId ?? '')
  const sourceCenter = center(sourceNode)
  const targetCenter = center(targetNode)
  if (!data || !sourceCenter || !targetCenter) return null
  const targetX = (sourceCenter.x + targetCenter.x) / 2
  const targetY = (sourceCenter.y + targetCenter.y) / 2
  const [path, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition: Position.Bottom,
    curvature: 0.35,
  })

  const evidence = data.evidence
  return (
    <>
      <BaseEdge id={id} path={path} markerEnd={markerEnd} className={`moderation-edge is-${data.evidence.status}`} />
      <circle cx={targetX} cy={targetY} r="3.5" fill="#bd7a0b" stroke="#ffffff" strokeWidth="1.5" />
      {data.evidence.status === 'running' ? <circle r="4" className="moderation-runner"><animateMotion dur="1.1s" repeatCount="indefinite" path={path} /></circle> : null}
      <EdgeLabelRenderer>
        <section
          aria-label={`调节效应${data.moderatorLabel}乘${data.targetLabel}统计详情`}
          className={`moderation-edge-label is-${data.evidence.status}`}
          style={{ transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`, cursor: 'pointer', position: 'absolute' }}
          onMouseEnter={() => setIsHovered(true)}
          onMouseLeave={() => setIsHovered(false)}
        >
          {data.moderatorLabel} × {data.targetLabel}
          {typeof data.evidence.estimate === 'number' ? (
            <span>B={data.evidence.estimate.toFixed(3)}</span>
          ) : typeof data.evidence.pValue === 'number' ? (
            <span>p{data.evidence.pValue < 0.001 ? '<.001' : `=${data.evidence.pValue.toFixed(3)}`}</span>
          ) : null}

          {isHovered && typeof evidence.estimate === 'number' ? (
            <div
              className="edge-hover-card"
              style={{
                position: 'absolute',
                bottom: '100%',
                left: '50%',
                transform: 'translateX(-50%) translateY(-8px)',
                background: '#0f172a',
                color: '#ffffff',
                padding: '10px 14px',
                borderRadius: '8px',
                fontSize: '11px',
                lineHeight: '1.5',
                boxShadow: '0 10px 25px rgba(0,0,0,0.25)',
                whiteSpace: 'nowrap',
                zIndex: 1000,
                pointerEvents: 'none',
                display: 'grid',
                gap: '4px',
              }}
            >
              <div style={{ borderBottom: '1px solid #334155', paddingBottom: '4px', fontWeight: 700, color: '#f59e0b' }}>
                调节效应: W × {data.targetLabel}
              </div>
              <div>交互项估计值 (B): <strong style={{ color: '#4a6dde' }}>{evidence.estimate.toFixed(3)}</strong></div>
              {typeof evidence.standardError === 'number' ? <div>标准误 (SE): {evidence.standardError.toFixed(3)}</div> : null}
              {typeof evidence.statistic === 'number' ? <div>t 值: {evidence.statistic.toFixed(3)}</div> : null}
              {typeof evidence.pValue === 'number' ? <div>P 值: {evidence.pValue < 0.001 ? '< .001' : evidence.pValue.toFixed(3)}</div> : null}
              {typeof evidence.lower === 'number' && typeof evidence.upper === 'number' ? (
                <div style={{ color: '#94a3b8' }}>95% CI: [{evidence.lower.toFixed(3)}, {evidence.upper.toFixed(3)}]</div>
              ) : null}
              <div style={{ color: '#cbd5e1', whiteSpace: 'normal', maxWidth: '260px' }}>
                {evidence.status === 'inference_signal'
                  ? '区间不含 0，或未提供区间时 p<.05；不等同于理论获得支持。'
                  : evidence.status === 'inference_uncertain'
                    ? '区间含 0，或未提供区间时 p≥.05；不等同于没有调节效应。'
                    : '当前没有可解释的推断结果。'}
              </div>
            </div>
          ) : null}
        </section>
      </EdgeLabelRenderer>
    </>
  )
}
