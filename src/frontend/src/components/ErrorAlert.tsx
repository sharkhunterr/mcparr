import { AlertTriangle, X, RefreshCw } from 'lucide-react';

interface ErrorAlertProps {
  error: string;
  onDismiss?: () => void;
  onRetry?: () => void;
  className?: string;
}

export default function ErrorAlert({
  error,
  onDismiss,
  onRetry,
  className = ''
}: ErrorAlertProps) {
  return (
    <div className={`card border-l-4 border-l-danger-500 ${className}`}>
      <div className="card-body">
        <div className="flex items-start">
          <div className="flex-shrink-0">
            <AlertTriangle className="h-5 w-5 text-danger-500" />
          </div>

          <div className="ml-3 flex-1">
            <h3 className="text-sm font-medium text-danger-800">
              Error
            </h3>
            <p className="text-sm text-danger-700 mt-1">{error}</p>
          </div>

          <div className="ml-auto flex-shrink-0 flex space-x-2">
            {onRetry && (
              <button
                type="button"
                className="inline-flex items-center text-xs text-danger-700 hover:text-danger-600"
                onClick={onRetry}
              >
                <RefreshCw className="h-3 w-3 mr-1" />
                Retry
              </button>
            )}

            {onDismiss && (
              <button
                type="button"
                className="inline-flex text-danger-400 hover:text-danger-500"
                onClick={onDismiss}
              >
                <span className="sr-only">Dismiss</span>
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}