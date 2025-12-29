import { Component } from 'react';
import { Alert } from './ui/Alert.jsx';

export class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    // eslint-disable-next-line no-console
    console.error('ErrorBoundary caught:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="container-page py-10">
          <div className="max-w-2xl">
            <h1 className="text-2xl font-semibold text-gray-900">Something went wrong</h1>
            <div className="mt-4">
              <Alert variant="error">
                {this.state.error?.message || 'An unexpected error occurred.'}
              </Alert>
            </div>
            <button
              type="button"
              className="mt-4 inline-flex items-center rounded bg-brand-blue px-4 py-2 text-sm font-semibold text-white hover:opacity-95 focus-ring"
              onClick={() => window.location.reload()}
              data-testid="reload-app"
            >
              Reload page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
