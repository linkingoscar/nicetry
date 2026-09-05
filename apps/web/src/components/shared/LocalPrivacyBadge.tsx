import { useState } from 'react'

interface LocalPrivacyBadgeProps {
  datasetName?: string
  datasetSha256?: string
}

export function LocalPrivacyBadge({
  datasetName = '问卷数据集',
  datasetSha256,
}: LocalPrivacyBadgeProps) {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <>
      <button
        type="button"
        className="local-privacy-badge"
        onClick={() => setIsOpen(true)}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '7px',
          padding: '5px 12px',
          borderRadius: '9999px',
          fontSize: '12px',
          fontWeight: 600,
          color: 'var(--text-body)',
          background: 'rgba(255, 255, 255, 0.08)',
          border: '1px solid rgba(255, 255, 255, 0.22)',
          cursor: 'pointer',
          transition: 'transform 0.2s ease, box-shadow 0.2s ease',
          boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
        }}
      >
        <span
          style={{
            display: 'inline-block',
            width: '7px',
            height: '7px',
            borderRadius: '50%',
            background: '#1037b9',
            boxShadow: '0 0 0 3px rgba(16, 55, 185, 0.3)',
            animation: 'pulse-glow 1.8s ease-in-out infinite',
          }}
        />
        <span>本机处理 · 不上传远端云服务</span>
      </button>

      {isOpen ? (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="privacy-modal-title"
          tabIndex={-1}
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 10000,
            background: 'rgba(15, 23, 42, 0.65)',
            backdropFilter: 'blur(6px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '24px',
          }}
          onClick={(e) => {
            if (e.target === e.currentTarget) setIsOpen(false)
          }}
          onKeyDown={(e) => {
            if (e.key === 'Escape') setIsOpen(false)
          }}
        >
          <div
            style={{
              background: '#ffffff',
              color: '#0f172a',
              borderRadius: '16px',
              padding: '24px',
              maxWidth: '520px',
              width: '100%',
              boxShadow: '0 20px 50px rgba(0,0,0,0.3)',
              display: 'grid',
              gap: '16px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className="local-privacy-mark" aria-hidden="true">LOCAL</span>
                <h3 id="privacy-modal-title" style={{ margin: 0, fontSize: '18px', color: '#0d1f5c' }}>
                  本机处理架构与数据边界
                </h3>
              </div>
              <button
                type="button"
                style={{
                  background: 'transparent',
                  border: 0,
                  fontSize: '20px',
                  cursor: 'pointer',
                  color: '#566579',
                }}
                onClick={() => setIsOpen(false)}
              >
                ✕
              </button>
            </div>

            <div
              style={{
                background: '#ecf0fd',
                border: '1px solid #a7b9f3',
                borderRadius: '10px',
                padding: '12px 16px',
                fontSize: '12px',
                color: '#061b5f',
                lineHeight: '1.6',
              }}
            >
              <strong>✓ 本机处理边界：</strong>
              浏览器通过 localhost HTTP API 将分析数据交给本机 FastAPI 服务和本机 R worker / 子进程计算；该传输经过本机网络栈，但本产品不会把研究数据上传到远端云服务。数据版本、任务与报告可在本机工作区持久化，请按设备和工作区权限管理敏感数据。
            </div>

            <div style={{ display: 'grid', gap: '8px', fontSize: '12px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '6px', borderBottom: '1px solid #e2e8f0' }}>
                <span style={{ color: '#566579' }}>当前文件:</span>
                <strong>{datasetName}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '6px', borderBottom: '1px solid #e2e8f0' }}>
                <span style={{ color: '#566579' }}>SHA-256 哈希防篡改摘要:</span>
                <code style={{ fontSize: '11px', color: '#0d1f5c' }}>{datasetSha256 ? `${datasetSha256.slice(0, 20)}…` : '未提供'}</code>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '6px', borderBottom: '1px solid #e2e8f0' }}>
                <span style={{ color: '#566579' }}>处理架构:</span>
                <span style={{ color: '#052796', fontWeight: 700 }}>浏览器 + localhost API + 本机 R 进程</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '6px', borderBottom: '1px solid #e2e8f0' }}>
                <span style={{ color: '#566579' }}>本地状态:</span>
                <span style={{ color: '#0f172a', fontWeight: 600 }}>原始版本只读；工作区结果可持久化</span>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '8px' }}>
              <button
                type="button"
                style={{
                  background: '#0d1f5c',
                  color: '#ffffff',
                  border: 0,
                  padding: '8px 18px',
                  borderRadius: '8px',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
                onClick={() => setIsOpen(false)}
              >
                了解并返回工作台
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  )
}
