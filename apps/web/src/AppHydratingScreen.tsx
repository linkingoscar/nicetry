export function AppHydratingScreen() {
  return (
    <div className="app-shell" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', background: 'var(--bg-app)', color: 'var(--brand-primary)', fontFamily: 'var(--font-main)' }}>
      <div style={{ textAlign: 'center' }}>
        <div className="spinner" style={{ border: '4px solid rgba(13, 31, 92,0.1)', borderTop: '4px solid var(--brand-primary)', borderRadius: '50%', width: '40px', height: '40px', animation: 'spin 1s linear infinite', margin: '0 auto 16px' }} />
        <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
        <strong>正在载入工作区中，请稍候...</strong>
      </div>
    </div>
  )
}
