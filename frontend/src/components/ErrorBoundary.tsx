import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Office World Error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          width: '100vw',
          height: '100vh',
          background: '#0a0f14',
          color: '#e8eef3',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          fontFamily: 'monospace',
          fontSize: 14,
          padding: 20,
        }}>
          <h1 style={{ color: '#ff6b6b', marginBottom: 16 }}>⚠️ Office World Crashed</h1>
          <pre style={{
            background: '#1a2228',
            padding: 16,
            borderRadius: 8,
            color: '#ff6b6b',
            fontSize: 12,
            maxWidth: '100%',
            overflow: 'auto',
          }}>
            {this.state.error?.message || 'Unknown error'}
            {'\n\n'}
            {this.state.error?.stack?.split('\n').slice(0, 5).join('\n')}
          </pre>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;