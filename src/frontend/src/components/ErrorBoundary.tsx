import { Component, type ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { logger } from '../lib/logger';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error,
      errorInfo: null,
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);

    // Log error to backend
    logger.critical(`React Error: ${error.message}`, 'error-boundary', {
      errorName: error.name,
      errorStack: error.stack,
      componentStack: errorInfo.componentStack,
      url: window.location.href,
    });

    this.setState({
      error,
      errorInfo,
    });
  }

  handleReload = () => {
    window.location.reload();
  };

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
          <div className="max-w-md w-full">
            <div className="card">
              <div className="card-body text-center">
                <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-danger-100 mb-4">
                  <AlertTriangle className="h-6 w-6 text-danger-600" />
                </div>

                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  Something went wrong
                </h3>

                <p className="text-sm text-gray-600 mb-6">
                  An unexpected error occurred. Please try refreshing the page or contact support if the problem persists.
                </p>

                {import.meta.env.DEV && this.state.error && (
                  <details className="mb-6 text-left">
                    <summary className="text-sm font-medium text-gray-700 cursor-pointer mb-2">
                      Error Details
                    </summary>
                    <div className="bg-gray-100 rounded-md p-3 text-xs text-gray-800 font-mono overflow-auto max-h-32">
                      <div className="font-semibold mb-1">Error:</div>
                      <div className="mb-3">{this.state.error.toString()}</div>
                      {this.state.errorInfo && (
                        <>
                          <div className="font-semibold mb-1">Component Stack:</div>
                          <div>{this.state.errorInfo.componentStack}</div>
                        </>
                      )}
                    </div>
                  </details>
                )}

                <div className="flex space-x-3 justify-center">
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={this.handleReset}
                  >
                    Try Again
                  </button>

                  <button
                    type="button"
                    className="btn btn-primary btn-sm"
                    onClick={this.handleReload}
                  >
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Reload Page
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;