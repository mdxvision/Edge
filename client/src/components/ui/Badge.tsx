import { HTMLAttributes, forwardRef } from 'react';
import { clsx } from 'clsx';

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: 'primary' | 'success' | 'warning' | 'danger' | 'neutral';
}

const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, variant = 'neutral', children, ...props }, ref) => {
    const variants = {
      primary: 'bg-primary-50 text-primary-600 dark:bg-primary-500/20 dark:text-primary-400',
      success: 'bg-success-50 text-success-600 dark:bg-success-500/20 dark:text-success-500',
      warning: 'bg-warning-50 text-warning-600 dark:bg-warning-500/20 dark:text-warning-500',
      danger: 'bg-danger-50 text-danger-600 dark:bg-danger-500/20 dark:text-danger-500',
      neutral: 'bg-surface-100 text-surface-600 dark:bg-surface-800 dark:text-surface-400',
    };

    return (
      <span
        ref={ref}
        className={clsx(
          'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
          variants[variant],
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
