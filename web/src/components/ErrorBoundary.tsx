import { Component, type ErrorInfo, type ReactNode } from 'react'
import { Empty } from './ui/empty'
import { Button } from './ui/button'

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
        <Empty
          tone="error"
          className="py-16"
          title="Something broke on this page."
          detail={<span className="font-mono break-words">{this.state.error.message}</span>}
          action={
            <Button variant="outline" size="sm" onClick={() => window.location.reload()}>
              Reload
            </Button>
          }
        />
      )
    }
    return this.props.children
  }
}
