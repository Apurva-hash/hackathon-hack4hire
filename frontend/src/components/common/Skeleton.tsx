import React from 'react';

export interface SkeletonProps {
  className?: string;
  variant?: 'text' | 'circular' | 'rectangular';
  width?: string | number;
  height?: string | number;
}

export const Skeleton: React.FC<SkeletonProps> = ({
  className = '',
  variant = 'rectangular',
  width,
  height,
}) => {
  const variantClasses = {
    text: 'h-4 w-full rounded',
    circular: 'rounded-full',
    rectangular: 'rounded-card',
  };

  const style: React.CSSProperties = {
    width: width !== undefined ? width : undefined,
    height: height !== undefined ? height : undefined,
  };

  return (
    <div
      style={style}
      aria-hidden="true"
      className={`animate-pulse bg-border/60 ${variantClasses[variant]} ${className}`}
    />
  );
};

export const CardSkeleton: React.FC = () => (
  <div className="p-5 bg-surface rounded-card border border-border shadow-warmSm space-y-4">
    <div className="flex items-center justify-between">
      <Skeleton variant="text" className="w-1/3 h-5" />
      <Skeleton variant="circular" className="w-8 h-8" />
    </div>
    <Skeleton variant="text" className="w-2/3 h-4" />
    <Skeleton variant="rectangular" className="w-full h-24" />
    <div className="flex gap-2 pt-2">
      <Skeleton variant="text" className="w-1/4 h-8 rounded-input" />
      <Skeleton variant="text" className="w-1/4 h-8 rounded-input" />
    </div>
  </div>
);

