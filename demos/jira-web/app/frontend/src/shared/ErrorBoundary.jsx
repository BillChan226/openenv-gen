import { Component } from 'react';

export class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    console.error('ErrorBoundary caught:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback || (
          <div className="min-h-screen flex items-center justify-center p-6">
            <div className="surface max-w-lg w-full p-6">
              <h2 className="text-lg font-semibold">Something went wrong</h2>
              <p className="text-sm text-fg-muted mt-2">{this.state.error?.message}</p>
              <div className="mt-4 flex gap-2">
                <button className="btn" onClick={() => window.location.reload()} data-testid="reload-app">
                  Reload
                </button>
              </div>
            </div>
          </div>
        )
      );
    }

    return this.props.children;
  }
}
