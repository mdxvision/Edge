import type { ButtonHTMLAttributes } from 'react';
import { forwardRef } from 'react';
import { clsx } from 'clsx';
import { Loader2 } from 'lucide-react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'outline' | 'premium';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', isLoading, children, disabled, ...props }, ref) => {
    const baseStyles = clsx(
      'inline-flex items-center justify-center gap-2 font-semibold',
      'rounded-xl transition-all duration-200 ease-out',
      'focus:outline-none focus-visible:ring-4 focus-visible:ring-offset-0',
      'disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none',
      'active:scale-[0.98]'
    );

    const variants = {
      primary: clsx(
        'bg-primary-600 text-white',
        'hover:bg-primary-700',
        'focus-visible:ring-primary-500/30',
        'dark:bg-primary-500 dark:hover:bg-primary-400'
      ),
      secondary: clsx(
        'bg-surface-100 text-surface-700',
        'hover:bg-surface-200',
        'focus-visible:ring-surface-500/20',
        'dark:bg-surface-800 dark:text-surface-200 dark:hover:bg-surface-700'
      ),
      ghost: clsx(
        'bg-transparent text-surface-600',
        'hover:bg-surface-100',
        'focus-visible:ring-surface-500/20',
        'dark:text-surface-300 dark:hover:bg-surface-800'
      ),
      danger: clsx(
        'bg-danger-500 text-white',
        'hover:bg-danger-600',
        'focus-visible:ring-danger-500/30',
        'dark:bg-danger-400 dark:hover:bg-danger-500'
      ),
      outline: clsx(
        'border-2 border-surface-200 bg-transparent text-surface-700',
        'hover:bg-surface-50 hover:border-surface-300',
        'focus-visible:ring-surface-500/20',
        'dark:border-surface-700 dark:text-surface-300 dark:hover:bg-surface-800 dark:hover:border-surface-600'
      ),
      premium: clsx(
        'bg-premium-500 text-surface-900',
        'hover:bg-premium-400',
        'focus-visible:ring-premium-500/30',
        'dark:bg-premium-400 dark:hover:bg-premium-300'
      ),
    };

    const sizes = {
      sm: 'px-4 py-2 text-sm',
      md: 'px-5 py-2.5 text-sm',
      lg: 'px-6 py-3 text-base',
    };

    return (
      <button
        ref={ref}
        className={clsx(baseStyles, variants[variant], sizes[size], className)}
        disabled={disabled || isLoading}
        {...props}
      >
        {isLoading && <Loader2 className="w-4 h-4 animate-spin" />}
        {children}
      </button>
    );
  }
);

Button.displayName = 'Button';

export default Button;
