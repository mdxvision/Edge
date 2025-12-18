import { forwardRef } from 'react';
import type { HTMLAttributes, ReactNode } from 'react';
import { clsx } from 'clsx';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  padding?: 'none' | 'sm' | 'md' | 'lg';
  hover?: boolean;
}

interface CardHeaderProps extends HTMLAttributes<HTMLDivElement> {
  title?: string;
  subtitle?: string;
  action?: ReactNode;
}

interface CardFooterProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
}

const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ className, padding = 'md', hover = false, children, ...props }, ref) => {
    const paddingSizes = {
      none: '',
      sm: 'p-4',
      md: 'p-5 md:p-6',
      lg: 'p-6 md:p-8',
    };

    return (
      <div
        ref={ref}
        className={clsx(
          'card',
          paddingSizes[padding],
          hover && 'hover:translate-y-[-2px] cursor-pointer',
          className
        )}
        {...props}
      >
        {children}
      </div>
    );
  }
);

Card.displayName = 'Card';

// Card Header Component
const CardHeader = forwardRef<HTMLDivElement, CardHeaderProps>(
  ({ className, title, subtitle, action, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={clsx(
          'flex items-start justify-between gap-4 pb-4 mb-4',
          'border-b border-surface-200 dark:border-surface-800',
          className
        )}
        {...props}
      >
        {(title || subtitle) ? (
          <div className="min-w-0 flex-1">
            {title && (
              <h3 className="text-lg font-semibold text-surface-900 dark:text-white truncate">
                {title}
              </h3>
            )}
            {subtitle && (
              <p className="text-sm text-surface-500 dark:text-surface-400 mt-0.5">
                {subtitle}
              </p>
            )}
          </div>
        ) : children}
        {action && <div className="flex-shrink-0">{action}</div>}
      </div>
    );
  }
);

CardHeader.displayName = 'CardHeader';

// Card Footer Component
const CardFooter = forwardRef<HTMLDivElement, CardFooterProps>(
  ({ className, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={clsx(
          'pt-4 mt-4',
          'border-t border-surface-200 dark:border-surface-800',
          className
        )}
        {...props}
      >
        {children}
      </div>
    );
  }
);

CardFooter.displayName = 'CardFooter';

// Stat Card - specialized card for displaying stats
interface StatCardProps {
  label: string;
  value: string | number;
  change?: {
    value: number;
    type: 'increase' | 'decrease' | 'neutral';
  };
  icon?: ReactNode;
  className?: string;
}

function StatCard({ label, value, change, icon, className }: StatCardProps) {
  return (
    <Card padding="md" className={className}>
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <p className="text-sm font-medium text-surface-500 dark:text-surface-400">
            {label}
          </p>
          <p className="text-2xl font-bold text-surface-900 dark:text-white animate-stat">
            {value}
          </p>
          {change && (
            <div className={clsx(
              'flex items-center gap-1 text-sm font-medium',
              change.type === 'increase' && 'text-success-500 dark:text-success-400',
              change.type === 'decrease' && 'text-danger-500 dark:text-danger-400',
              change.type === 'neutral' && 'text-surface-500 dark:text-surface-400'
            )}>
              <span>
                {change.type === 'increase' && '+'}
                {change.type === 'decrease' && '-'}
                {Math.abs(change.value)}%
              </span>
              <span className="text-surface-400 dark:text-surface-500">vs last period</span>
            </div>
          )}
        </div>
        {icon && (
          <div className="p-3 rounded-xl bg-primary-50 text-primary-600 dark:bg-primary-500/10 dark:text-primary-400">
            {icon}
          </div>
        )}
      </div>
    </Card>
  );
}

export default Card;
export { Card, CardHeader, CardFooter, StatCard };
