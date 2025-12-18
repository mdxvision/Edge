import type { HTMLAttributes } from 'react';
import { forwardRef } from 'react';
import { clsx } from 'clsx';

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: 'primary' | 'success' | 'warning' | 'danger' | 'premium' | 'neutral' | 'outline';
  size?: 'sm' | 'md';
}

const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, variant = 'neutral', size = 'md', children, ...props }, ref) => {
    const variants = {
      primary: clsx(
        'bg-primary-100 text-primary-700',
        'dark:bg-primary-500/15 dark:text-primary-400'
      ),
      success: clsx(
        'bg-success-50 text-success-600',
        'dark:bg-success-500/15 dark:text-success-400'
      ),
      warning: clsx(
        'bg-warning-50 text-warning-700',
        'dark:bg-warning-500/15 dark:text-warning-400'
      ),
      danger: clsx(
        'bg-danger-50 text-danger-600',
        'dark:bg-danger-500/15 dark:text-danger-400'
      ),
      premium: clsx(
        'bg-premium-500/10 text-premium-600',
        'dark:bg-premium-500/15 dark:text-premium-400'
      ),
      neutral: clsx(
        'bg-surface-100 text-surface-600',
        'dark:bg-surface-800 dark:text-surface-300'
      ),
      outline: clsx(
        'bg-transparent border border-surface-300 text-surface-600',
        'dark:border-surface-600 dark:text-surface-400'
      ),
    };

    const sizes = {
      sm: 'px-2 py-0.5 text-xs',
      md: 'px-2.5 py-1 text-xs',
    };

    return (
      <span
        ref={ref}
        className={clsx(
          'inline-flex items-center font-medium rounded-full',
          'transition-colors duration-200',
          variants[variant],
          sizes[size],
          className
        )}
        {...props}
      >
        {children}
      </span>
    );
  }
);

Badge.displayName = 'Badge';

export default Badge;
