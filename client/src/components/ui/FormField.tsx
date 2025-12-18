import { clsx } from 'clsx';
import { AlertCircle, CheckCircle } from 'lucide-react';
import type { ReactNode } from 'react';

interface FormFieldProps {
  label: string;
  htmlFor: string;
  error?: string;
  success?: string;
  hint?: string;
  required?: boolean;
  children: ReactNode;
  className?: string;
}

export default function FormField({
  label,
  htmlFor,
  error,
  success,
  hint,
  required,
  children,
  className,
}: FormFieldProps) {
  return (
    <div className={clsx('space-y-2', className)}>
      <label
        htmlFor={htmlFor}
        className="block text-sm font-medium text-surface-700 dark:text-surface-300"
      >
        {label}
        {required && <span className="text-danger-500 ml-1">*</span>}
      </label>

      {children}

      {error && (
        <div className="flex items-center gap-2 text-sm text-danger-500 dark:text-danger-400">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {success && !error && (
        <div className="flex items-center gap-2 text-sm text-success-600 dark:text-success-400">
          <CheckCircle className="w-4 h-4 flex-shrink-0" />
          <span>{success}</span>
        </div>
      )}

      {hint && !error && !success && (
        <p className="text-sm text-surface-500 dark:text-surface-400">
          {hint}
        </p>
      )}
    </div>
  );
}

// Apple-style input with proper focus ring
interface StyledInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  hasError?: boolean;
  hasSuccess?: boolean;
}

export function StyledInput({ hasError, hasSuccess, className, ...props }: StyledInputProps) {
  return (
    <input
      {...props}
      className={clsx(
        // Base styles
        'w-full px-4 py-3 rounded-xl border text-base',
        'transition-all duration-200 ease-out',
        'placeholder:text-surface-400 dark:placeholder:text-surface-500',
        // Focus styles
        'focus:outline-none focus:ring-4 focus:ring-offset-0',
        // Light mode
        'bg-white text-surface-900',
        // Dark mode
        'dark:bg-surface-800 dark:text-white',
        // States
        hasError
          ? 'border-danger-300 focus:border-danger-500 focus:ring-danger-500/20 dark:border-danger-500/50'
          : hasSuccess
          ? 'border-success-300 focus:border-success-500 focus:ring-success-500/20 dark:border-success-500/50'
          : 'border-surface-200 hover:border-surface-300 focus:border-primary-500 focus:ring-primary-500/20 dark:border-surface-700 dark:hover:border-surface-600',
        className
      )}
    />
  );
}

// Apple-style select
interface StyledSelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  hasError?: boolean;
  hasSuccess?: boolean;
}

export function StyledSelect({ hasError, hasSuccess, className, children, ...props }: StyledSelectProps) {
  return (
    <select
      {...props}
      className={clsx(
        // Base styles
        'w-full px-4 py-3 rounded-xl border text-base appearance-none',
        'transition-all duration-200 ease-out',
        'bg-no-repeat bg-right',
        // Focus styles
        'focus:outline-none focus:ring-4 focus:ring-offset-0',
        // Light mode
        'bg-white text-surface-900',
        // Dark mode
        'dark:bg-surface-800 dark:text-white',
        // States
        hasError
          ? 'border-danger-300 focus:border-danger-500 focus:ring-danger-500/20 dark:border-danger-500/50'
          : hasSuccess
          ? 'border-success-300 focus:border-success-500 focus:ring-success-500/20 dark:border-success-500/50'
          : 'border-surface-200 hover:border-surface-300 focus:border-primary-500 focus:ring-primary-500/20 dark:border-surface-700 dark:hover:border-surface-600',
        className
      )}
      style={{
        backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%2364748b' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E")`,
        backgroundPosition: 'right 12px center',
        paddingRight: '40px'
      }}
    >
      {children}
    </select>
  );
}

// Apple-style textarea
interface StyledTextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  hasError?: boolean;
  hasSuccess?: boolean;
}

export function StyledTextarea({ hasError, hasSuccess, className, ...props }: StyledTextareaProps) {
  return (
    <textarea
      {...props}
      className={clsx(
        // Base styles
        'w-full px-4 py-3 rounded-xl border text-base resize-none',
        'transition-all duration-200 ease-out',
        'placeholder:text-surface-400 dark:placeholder:text-surface-500',
        // Focus styles
        'focus:outline-none focus:ring-4 focus:ring-offset-0',
        // Light mode
        'bg-white text-surface-900',
        // Dark mode
        'dark:bg-surface-800 dark:text-white',
        // States
        hasError
          ? 'border-danger-300 focus:border-danger-500 focus:ring-danger-500/20 dark:border-danger-500/50'
          : hasSuccess
          ? 'border-success-300 focus:border-success-500 focus:ring-success-500/20 dark:border-success-500/50'
          : 'border-surface-200 hover:border-surface-300 focus:border-primary-500 focus:ring-primary-500/20 dark:border-surface-700 dark:hover:border-surface-600',
        className
      )}
    />
  );
}
