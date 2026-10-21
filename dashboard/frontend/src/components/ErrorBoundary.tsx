import { Component, type ReactNode } from 'react'

type Props = { children: ReactNode }
type State = { error: Error | null }

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error) {
    return { error }
  }

  render() {
    if (this.state.error) {
      return (
        <div className="card" style={{ color: 'var(--danger)' }}>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>Something went wrong</div>
          <pre className="mono" style={{ whiteSpace: 'pre-wrap', fontSize: 12 }}>
            {this.state.error.message}
          </pre>
          <button className="btn" style={{ marginTop: 8 }} onClick={() => this.setState({ error: null })}>
            Try again
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
