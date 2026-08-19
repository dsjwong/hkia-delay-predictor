import { Component, type ErrorInfo, type ReactNode } from 'react'

interface State {
  error: Error | null
}

/** Catches render/chunk errors so a page never goes blank. A failed dynamic import right after a deploy (stale index.html
 *  pointing at hashed chunks that no longer exist) reloads the page once. */
export class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { error: null }
  static getDerivedStateFromError(error: Error): State {
    return { error }
  }
  componentDidCatch(error: Error, info: ErrorInfo) {
    if (/dynamically imported module|Loading chunk|Importing a module script failed/i.test(error.message)) {
      const key = 'hk-chunk-reload'
      if (!sessionStorage.getItem(key)) {
        sessionStorage.setItem(key, String(Date.now()))
        window.location.reload()
        return
      }
    }
    console.error('render error', error, info.componentStack)
  }
  render() {
    if (this.state.error) {
      return (
        <div className="p-6 text-sm" role="alert">
          <div className="text-critical font-semibold">Something broke on this page.</div>
          <div className="text-ink-2 mt-1 font-mono text-xs break-words">{this.state.error.message}</div>
          <button className="mt-3 text-accent underline cursor-pointer" onClick={() => window.location.reload()}>
            Reload
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
