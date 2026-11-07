import React from 'react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  disabledReason?: string;
  icon?: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  loading = false,
  disabledReason,
  disabled,
  icon,
  children,
  className = '',
  ...props
}) => {
  const isDisabled = disabled || loading;

  const sizeClasses = {
    sm: 'px-3 py-1.5 text-xs font-medium rounded-input min-h-[36px]',
    md: 'px-4 py-2 text-sm font-semibold rounded-input min-h-[44px]',
    lg: 'px-6 py-3 text-base font-semibold rounded-input min-h-[48px]',
  };

  const variantClasses = {
    primary:
      'bg-primary text-white hover:bg-primary-hover active:scale-[0.98] shadow-warmSm focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2',
    secondary:
      'bg-surface-alt text-text hover:bg-border active:scale-[0.98] border border-border focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2',
    outline:
      'bg-transparent text-primary hover:bg-primary-tint border-2 border-primary active:scale-[0.98] focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2',
    danger:
      'bg-status-error text-white hover:opacity-90 active:scale-[0.98] shadow-warmSm focus-visible:ring-2 focus-visible:ring-status-error focus-visible:ring-offset-2',
    ghost:
      'bg-transparent text-text-muted hover:text-text hover:bg-surface-alt active:scale-[0.98] focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2',
  };

  const disabledClasses = isDisabled
    ? 'opacity-50 cursor-not-allowed hover:bg-none hover:text-inherit active:scale-100 shadow-none'
    : 'cursor-pointer transition-all duration-150';

  return (
    <button
      {...props}
      disabled={isDisabled}
      title={disabledReason || props.title}
      aria-disabled={isDisabled}
      className={`inline-flex items-center justify-center gap-2 font-medium select-none ${sizeClasses[size]} ${variantClasses[variant]} ${disabledClasses} ${className}`}
    >
      {loading ? (
        <span className="inline-block w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" aria-hidden="true" />
      ) : (
        icon && <span className="flex-shrink-0">{icon}</span>
      )}
      <span>{children}</span>
    </button>
  );
};

