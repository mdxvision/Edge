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
        'bg-emerald-100 text-emerald-700',
        'dark:bg-emerald-500/15 dark:text-emerald-400'
      ),
      success: clsx(
        'bg-emerald-50 text-emerald-600',
        'dark:bg-emerald-500/15 dark:text-emerald-400'
      ),
      warning: clsx(
        'bg-amber-50 text-amber-700',
        'dark:bg-amber-500/15 dark:text-amber-400'
      ),
      danger: clsx(
        'bg-red-50 text-red-600',
        'dark:bg-red-500/15 dark:text-red-400'
      ),
      premium: clsx(
        'bg-amber-500/10 text-amber-600',
        'dark:bg-amber-500/15 dark:text-amber-400'
      ),
      neutral: clsx(
        'bg-gray-100 text-gray-600',
        'dark:bg-slate-700 dark:text-slate-300'
      ),
      outline: clsx(
        'bg-transparent border border-gray-300 text-gray-600',
        'dark:border-slate-600 dark:text-slate-400'
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
