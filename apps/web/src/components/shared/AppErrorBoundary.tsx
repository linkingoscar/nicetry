import { Component, type ErrorInfo, type ReactNode } from 'react'

interface AppErrorBoundaryProps {
  children: ReactNode
}

interface AppErrorBoundaryState {
  error: Error | null
}

export class AppErrorBoundary extends Component<
  AppErrorBoundaryProps,
  AppErrorBoundaryState
> {
  state: AppErrorBoundaryState = { error: null }

  static getDerivedStateFromError(error: Error): AppErrorBoundaryState {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('App crashed:', error, info.componentStack)
  }

  handleReset = () => {
    this.setState({ error: null })
  }

  render() {
    if (!this.state.error) return this.props.children
    return (
      <main className="app-error-boundary" role="alert">
        <h1>研径遇到了问题</h1>
        <p>应用整体未能继续渲染。可以尝试重试；若问题持续，请查看控制台日志后重新启动。</p>
        <details>
          <summary>查看技术信息</summary>
          <code>{this.state.error.message}</code>
        </details>
        <button type="button" onClick={this.handleReset}>
          重试
        </button>
      </main>
    )
  }
}
