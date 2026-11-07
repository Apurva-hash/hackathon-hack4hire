import React from 'react';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'flat' | 'interactive';
  padding?: 'none' | 'sm' | 'md' | 'lg';
}

export const Card: React.FC<CardProps> = ({
  variant = 'default',
  padding = 'md',
  children,
  className = '',
  ...props
}) => {
  const paddingStyles = {
    none: '',
    sm: 'p-3',
    md: 'p-4 sm:p-5',
    lg: 'p-6',
  };

  const variantStyles = {
    default: 'bg-surface border border-border shadow-warmSm rounded-card',
    flat: 'bg-surface-alt border border-border/70 rounded-card',
    interactive:
      'bg-surface border border-border shadow-warmSm hover:shadow-warmMd hover:border-primary/40 transition-all duration-150 cursor-pointer rounded-card active:scale-[0.99]',
  };

  return (
    <div
      className={`${variantStyles[variant]} ${paddingStyles[padding]} ${className}`}
      {...props}
    >
      {children}
    </div>
  );
};

