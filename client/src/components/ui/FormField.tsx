import { clsx } from 'clsx';
import { AlertCircle, CheckCircle } from 'lucide-react';
import { ReactNode } from 'react';

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
    <div className={clsx('space-y-1.5', className)}>
      <label
        htmlFor={htmlFor}
        className="block text-sm font-medium text-surface-700 dark:text-surface-300"
      >
        {label}
        {required && <span className="text-danger-500 ml-1">*</span>}
      </label>

      {children}

      {error && (
        <div className="flex items-center gap-1.5 text-sm text-danger-600 dark:text-danger-400">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {success && !error && (
        <div className="flex items-center gap-1.5 text-sm text-success-600 dark:text-success-400">
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

// Styled input that shows error/success states
interface StyledInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  hasError?: boolean;
  hasSuccess?: boolean;
}

export function StyledInput({ hasError, hasSuccess, className, ...props }: StyledInputProps) {
  return (
    <input
      {...props}
      className={clsx(
        'w-full px-3 py-2 rounded-lg border text-sm transition-colors',
        'bg-white dark:bg-surface-800',
        'text-surface-900 dark:text-white',
        'placeholder:text-surface-400 dark:placeholder:text-surface-500',
        'focus:outline-none focus:ring-2 focus:ring-offset-0',
        hasError
          ? 'border-danger-300 dark:border-danger-500 focus:border-danger-500 focus:ring-danger-500/20'
          : hasSuccess
          ? 'border-success-300 dark:border-success-500 focus:border-success-500 focus:ring-success-500/20'
          : 'border-surface-300 dark:border-surface-600 focus:border-primary-500 focus:ring-primary-500/20',
        className
      )}
    />
  );
}

// Styled select that shows error/success states
interface StyledSelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  hasError?: boolean;
  hasSuccess?: boolean;
}

export function StyledSelect({ hasError, hasSuccess, className, children, ...props }: StyledSelectProps) {
  return (
    <select
      {...props}
      className={clsx(
        'w-full px-3 py-2 rounded-lg border text-sm transition-colors',
        'bg-white dark:bg-surface-800',
        'text-surface-900 dark:text-white',
        'focus:outline-none focus:ring-2 focus:ring-offset-0',
        hasError
          ? 'border-danger-300 dark:border-danger-500 focus:border-danger-500 focus:ring-danger-500/20'
          : hasSuccess
          ? 'border-success-300 dark:border-success-500 focus:border-success-500 focus:ring-success-500/20'
          : 'border-surface-300 dark:border-surface-600 focus:border-primary-500 focus:ring-primary-500/20',
        className
      )}
    >
      {children}
    </select>
  );
}

// Styled textarea that shows error/success states
interface StyledTextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  hasError?: boolean;
  hasSuccess?: boolean;
}

export function StyledTextarea({ hasError, hasSuccess, className, ...props }: StyledTextareaProps) {
  return (
    <textarea
      {...props}
      className={clsx(
        'w-full px-3 py-2 rounded-lg border text-sm transition-colors',
        'bg-white dark:bg-surface-800',
        'text-surface-900 dark:text-white',
        'placeholder:text-surface-400 dark:placeholder:text-surface-500',
        'focus:outline-none focus:ring-2 focus:ring-offset-0',
        hasError
          ? 'border-danger-300 dark:border-danger-500 focus:border-danger-500 focus:ring-danger-500/20'
          : hasSuccess
          ? 'border-success-300 dark:border-success-500 focus:border-success-500 focus:ring-success-500/20'
          : 'border-surface-300 dark:border-surface-600 focus:border-primary-500 focus:ring-primary-500/20',
        className
      )}
    />
  );
}