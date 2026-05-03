import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props {
  children: ReactNode
  fallbackTitle?: string
  compact?: boolean
}

interface State {
  hasError: boolean
  message: string
  stack: string
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, message: '', stack: '' }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      message: error?.message ?? 'Unknown error',
      stack: error?.stack ?? '',
    }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[ATLAS ErrorBoundary]', error, info?.componentStack)
  }

  reset = () => this.setState({ hasError: false, message: '', stack: '' })

  render() {
    if (!this.state.hasError) return this.props.children

    if (this.props.compact) {
      return (
        <div className="atlas-card border border-border/60 bg-surface/40">
          <div className="flex items-start gap-2">
            <span className="text-bear text-base leading-none mt-0.5">⚠</span>
            <div className="flex-1 min-w-0">
              <div className="text-xs font-semibold text-text-primary">
                {this.props.fallbackTitle ?? 'Component failed to load'}
              </div>
              <div className="text-[11px] text-text-secondary mt-0.5 break-words">
                {this.state.message}
              </div>
              <button
                onClick={this.reset}
                className="mt-2 text-[10px] text-blue hover:underline"
              >
                Retry
              </button>
            </div>
          </div>
        </div>
      )
    }

    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-bg gap-4 px-6 text-center">
        <div className="text-2xl text-bear">⚠</div>
        <h2 className="text-text-primary font-semibold">Something went wrong</h2>
        <p className="text-text-secondary text-sm max-w-sm break-words">{this.state.message}</p>
        {this.state.stack && (
          <details className="text-left max-w-2xl w-full">
            <summary className="text-[10px] text-text-secondary cursor-pointer">Stack trace</summary>
            <pre className="text-[10px] text-text-secondary bg-surface p-3 rounded-lg mt-2 overflow-auto max-h-64 whitespace-pre-wrap">
              {this.state.stack}
            </pre>
          </details>
        )}
        <div className="flex gap-2">
          <button
            onClick={this.reset}
            className="px-4 py-2 rounded-lg bg-blue text-bg text-sm font-medium"
          >
            Try again
          </button>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 rounded-lg border border-border text-text-primary text-sm font-medium"
          >
            Reload page
          </button>
        </div>
      </div>
    )
  }
}
