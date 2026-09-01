import { useState } from 'react'
import {
  BaseEdge,
  EdgeLabelRenderer,
  getBezierPath,
  getStraightPath,
  Position,
  type Edge,
  type EdgeProps,
} from '@xyflow/react'

import type { PathEvidence } from './pathEvidence'

export interface StatisticalEdgeData extends Record<string, unknown> {
  label: string
  evidence: PathEvidence
  measurement: boolean
}

export type StatisticalFlowEdge = Edge<StatisticalEdgeData, 'statistical'>

function evidenceText(evidence: PathEvidence): string {
  if (evidence.status === 'running') return '估计中'
  if (evidence.status === 'inference_signal') return '区间不含 0，或未提供区间时 p<.05；不等同于理论获得支持'
  if (evidence.status === 'inference_uncertain') return '区间含 0，或未提供区间时 p≥.05；不等同于没有效应'
  return '等待结果'
}

export function StatisticalEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition = Position.Right,
  targetPosition = Position.Left,
  markerEnd,
  data,
}: EdgeProps<StatisticalFlowEdge>) {
  const [isHovered, setIsHovered] = useState(false)
  const dx = Math.abs(targetX - sourceX)
  const dy = Math.abs(targetY - sourceY)
  const isDirectLongPath = dx > 380 && dy < 100

  const [path, labelX, labelY] = isDirectLongPath
    ? getBezierPath({
        sourceX,
        sourceY,
        sourcePosition,
        targetX,
        targetY,
        targetPosition,
        curvature: 0.4,
      })
    : getStraightPath({ sourceX, sourceY, targetX, targetY })
  const evidence = data?.evidence ?? { status: 'idle' }
  const status = evidence.status

  return (
    <>
      <BaseEdge id={id} path={path} markerEnd={markerEnd} className={`statistical-edge is-${status}${data?.measurement ? ' is-measurement' : ''}`} />
      {status === 'running' ? <circle r="4" className="path-runner"><animateMotion dur="1.35s" repeatCount="indefinite" path={path} /></circle> : null}
      {status === 'inference_signal' ? <circle r="3.5" className="path-runner-signal"><animateMotion dur="2.2s" repeatCount="indefinite" path={path} /></circle> : null}
      <EdgeLabelRenderer>
        <section
          aria-label={`路径${data?.label || ''}统计详情`}
          className={`path-evidence-label is-${status}`}
          style={{ transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`, cursor: 'pointer', position: 'absolute' }}
          onMouseEnter={() => setIsHovered(true)}
          onMouseLeave={() => setIsHovered(false)}
          onFocus={() => setIsHovered(true)}
          onBlur={() => setIsHovered(false)}
        >
          <button type="button" className="path-detail-trigger" aria-label={`查看${data?.label || '路径'}统计详情`} aria-expanded={isHovered} onClick={() => setIsHovered(current => !current)}><strong>{data?.label || '路径'}</strong></button>
          {typeof evidence.estimate === 'number' ? <span>B={evidence.estimate.toFixed(3)}</span> : null}
          <i title={evidenceText(evidence)}>{status === 'inference_signal' ? '◇' : status === 'inference_uncertain' ? '?' : status === 'running' ? '•' : ''}</i>

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
              <div style={{ borderBottom: '1px solid #334155', paddingBottom: '4px', fontWeight: 700, color: '#38bdf8' }}>
                路径: {data?.label}
              </div>
              <div>估计值 (B): <strong style={{ color: '#4a6dde' }}>{evidence.estimate.toFixed(3)}</strong></div>
              {typeof evidence.standardError === 'number' ? <div>标准误 (SE): {evidence.standardError.toFixed(3)}</div> : null}
              {typeof evidence.statistic === 'number' ? <div>z / t 临界比: {evidence.statistic.toFixed(3)}</div> : null}
              {typeof evidence.pValue === 'number' ? <div>P 值: {evidence.pValue < 0.001 ? '< .001' : evidence.pValue.toFixed(3)}</div> : null}
              {typeof evidence.lower === 'number' && typeof evidence.upper === 'number' ? (
                <div style={{ color: '#94a3b8' }}>95% CI: [{evidence.lower.toFixed(3)}, {evidence.upper.toFixed(3)}]</div>
              ) : null}
              <div style={{ color: '#cbd5e1', whiteSpace: 'normal', maxWidth: '260px' }}>{evidenceText(evidence)}</div>
            </div>
          ) : null}
        </section>
      </EdgeLabelRenderer>
    </>
  )
}
