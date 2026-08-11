import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('ErrorBoundary caught:', error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-svh items-center justify-center bg-bg-primary px-4">
          <div className="max-w-md text-center">
            <p className="mb-3 text-[10px] font-bold uppercase tracking-[0.16em] text-accent-red">Unexpected error</p>
            <h1 className="mb-3 text-3xl font-medium tracking-[-0.04em] text-text-primary">Something went wrong</h1>
            <p className="mb-7 text-sm leading-6 text-text-muted">
              {this.state.error?.message || 'An unexpected error occurred.'}
            </p>
            <button
              onClick={() => {
                this.setState({ hasError: false, error: null });
                window.location.href = '/';
              }}
              className="primary-button"
            >
              Back to login
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
