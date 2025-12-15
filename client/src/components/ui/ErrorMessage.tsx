import { clsx } from 'clsx';
import { AlertCircle, RefreshCw, X } from 'lucide-react';

interface ErrorMessageProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  onDismiss?: () => void;
  variant?: 'inline' | 'banner' | 'fullpage';
  className?: string;
}

export default function ErrorMessage({
  title = 'Something went wrong',
  message,
  onRetry,
  onDismiss,
  variant = 'inline',
  className,
}: ErrorMessageProps) {
  if (variant === 'fullpage') {
    return (
      <div
        className={clsx(
          'flex flex-col items-center justify-center py-16 px-4 text-center',
          className
        )}
      >
        <div className="w-16 h-16 rounded-full bg-danger-50 dark:bg-danger-500/10 flex items-center justify-center mb-4">
          <AlertCircle className="w-8 h-8 text-danger-500" />
        </div>

        <h3 className="text-lg font-semibold text-surface-900 dark:text-white mb-1">
          {title}
        </h3>

        <p className="text-sm text-surface-500 dark:text-surface-400 max-w-sm mb-4">
          {message}
        </p>

        {onRetry && (
          <button
            onClick={onRetry}
            className="flex items-center gap-2 px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white text-sm font-medium rounded-lg transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Try Again
          </button>
        )}
      </div>
    );
  }

  if (variant === 'banner') {
    return (
      <div
        className={clsx(
          'w-full p-4 bg-danger-50 dark:bg-danger-500/10 border border-danger-200 dark:border-danger-500/20 rounded-lg',
          className
        )}
      >
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-danger-500 flex-shrink-0 mt-0.5" />

          <div className="flex-1 min-w-0">
            <h4 className="text-sm font-medium text-danger-800 dark:text-danger-200">
              {title}
            </h4>
            <p className="text-sm text-danger-700 dark:text-danger-300 mt-1">
              {message}
            </p>

            {onRetry && (
              <button
                onClick={onRetry}
                className="flex items-center gap-1 text-sm font-medium text-danger-600 dark:text-danger-400 hover:underline mt-2"
              >
                <RefreshCw className="w-3 h-3" />
                Retry
              </button>
            )}
          </div>

          {onDismiss && (
            <button
              onClick={onDismiss}
              className="p-1 rounded hover:bg-danger-100 dark:hover:bg-danger-500/20 transition-colors"
              aria-label="Dismiss"
            >
              <X className="w-4 h-4 text-danger-500" />
            </button>
          )}
        </div>
      </div>
    );
  }

  // Default: inline variant
  return (
    <div
      className={clsx(
        'flex items-center gap-2 p-3 bg-danger-50 dark:bg-danger-500/10 border border-danger-200 dark:border-danger-500/20 rounded-lg text-sm text-danger-700 dark:text-danger-300',
        className
      )}
    >
      <AlertCircle className="w-4 h-4 text-danger-500 flex-shrink-0" />
      <span className="flex-1">{message}</span>

      {onRetry && (
        <button
          onClick={onRetry}
          className="p-1 rounded hover:bg-danger-100 dark:hover:bg-danger-500/20 transition-colors"
          aria-label="Retry"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      )}

      {onDismiss && (
        <button
          onClick={onDismiss}
          className="p-1 rounded hover:bg-danger-100 dark:hover:bg-danger-500/20 transition-colors"
          aria-label="Dismiss"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}