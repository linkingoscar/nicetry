import { Component, type ErrorInfo, type ReactNode } from 'react'

interface SectionErrorBoundaryProps {
  children: ReactNode
  resetKey: string
  title?: string
}

interface SectionErrorBoundaryState {
  error: Error | null
}

export class SectionErrorBoundary extends Component<
  SectionErrorBoundaryProps,
  SectionErrorBoundaryState
> {
  state: SectionErrorBoundaryState = { error: null }

  static getDerivedStateFromError(error: Error): SectionErrorBoundaryState {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Result section failed to render', error, info)
  }

  componentDidUpdate(previous: SectionErrorBoundaryProps) {
    if (previous.resetKey !== this.props.resetKey && this.state.error) {
      this.setState({ error: null })
    }
  }

  render() {
    if (!this.state.error) return this.props.children
    return (
      <section className="section-error-boundary" role="alert">
        <strong>{this.props.title ?? '本结果区暂时无法显示'}</strong>
        <p>其他分析结果仍可继续查看。请重试；若问题持续，重新运行本次分析。</p>
        <details>
          <summary>查看技术信息</summary>
          <code>{this.state.error.message}</code>
        </details>
        <button type="button" onClick={() => this.setState({ error: null })}>重试本区</button>
      </section>
    )
  }
}
