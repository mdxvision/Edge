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
        'bg-emerald-600 text-white',
        'hover:bg-emerald-500',
        'focus-visible:ring-emerald-500/30',
        'dark:bg-emerald-600 dark:hover:bg-emerald-500'
      ),
      secondary: clsx(
        'bg-gray-100 text-gray-700',
        'hover:bg-gray-200',
        'focus-visible:ring-gray-500/20',
        'dark:bg-slate-700 dark:text-slate-200 dark:hover:bg-slate-600'
      ),
      ghost: clsx(
        'bg-transparent text-gray-600',
        'hover:bg-gray-100',
        'focus-visible:ring-gray-500/20',
        'dark:text-slate-300 dark:hover:bg-slate-800'
      ),
      danger: clsx(
        'bg-red-500 text-white',
        'hover:bg-red-600',
        'focus-visible:ring-red-500/30',
        'dark:bg-red-500 dark:hover:bg-red-400'
      ),
      outline: clsx(
        'border-2 border-gray-200 bg-transparent text-gray-700',
        'hover:bg-gray-50 hover:border-gray-300',
        'focus-visible:ring-gray-500/20',
        'dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:border-slate-500'
      ),
      premium: clsx(
        'bg-amber-500 text-gray-900',
        'hover:bg-amber-400',
        'focus-visible:ring-amber-500/30',
        'dark:bg-amber-400 dark:hover:bg-amber-300'
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
