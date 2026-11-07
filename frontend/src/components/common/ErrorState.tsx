import React from 'react';
import { AlertTriangleIcon, RefreshCwIcon } from './Icons';
import { Button } from './Button';

export interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  className?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Something went wrong',
  message,
  onRetry,
  className = '',
}) => {
  return (
    <div
      role="alert"
      className={`flex flex-col items-center justify-center p-8 sm:p-10 text-center bg-status-error/5 rounded-card border border-status-error/20 ${className}`}
    >
      <div className="w-12 h-12 rounded-full bg-status-error/15 flex items-center justify-center text-status-error mb-3 shadow-warmSm">
        <AlertTriangleIcon size={24} />
      </div>
      <h3 className="text-base font-bold text-status-error mb-1">{title}</h3>
      <p className="text-xs sm:text-sm text-text-muted max-w-sm mb-4">{message}</p>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry} icon={<RefreshCwIcon size={16} />}>
          Try Again
        </Button>
      )}
    </div>
  );
};

