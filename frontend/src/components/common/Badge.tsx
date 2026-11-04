import React from 'react';
import {
  CheckIcon,
  ClockIcon,
  HourglassIcon,
  AlertTriangleIcon,
  XIcon,
} from './Icons';

export type BadgeVariant =
  | 'success' // Completed / success / on track
  | 'progress' // In progress / en route
  | 'pending' // At risk / pending
  | 'error' // Breached / high-risk / error
  | 'neutral' // Cancelled / offline / inactive
  | 'warning' // Alias for pending
  | 'info'; // Alias for progress

export interface BadgeProps {
  variant?: BadgeVariant;
  children: React.ReactNode;
  icon?: React.ReactNode;
  size?: 'sm' | 'md';
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  variant = 'neutral',
  children,
  icon,
  size = 'md',
  className = '',
}) => {
  const normalizedVariant =
    variant === 'warning' ? 'pending' : variant === 'info' ? 'progress' : variant;

  const variantStyles: Record<
    'success' | 'progress' | 'pending' | 'error' | 'neutral',
    { bg: string; text: string; border: string; defaultIcon: React.ReactNode }
  > = {
    success: {
      bg: 'bg-status-success/15',
      text: 'text-status-success',
      border: 'border-status-success/30',
      defaultIcon: <CheckIcon size={size === 'sm' ? 12 : 14} />,
    },
    progress: {
      bg: 'bg-status-progress/15',
      text: 'text-status-progress',
      border: 'border-status-progress/30',
      defaultIcon: <ClockIcon size={size === 'sm' ? 12 : 14} />,
    },
    pending: {
      bg: 'bg-status-pending/15',
      text: 'text-status-pending',
      border: 'border-status-pending/30',
      defaultIcon: <HourglassIcon size={size === 'sm' ? 12 : 14} />,
    },
    error: {
      bg: 'bg-status-breached/15',
      text: 'text-status-breached',
      border: 'border-status-breached/30',
      defaultIcon: <AlertTriangleIcon size={size === 'sm' ? 12 : 14} />,
    },
    neutral: {
      bg: 'bg-status-neutral/15',
      text: 'text-status-neutral',
      border: 'border-status-neutral/30',
      defaultIcon: <XIcon size={size === 'sm' ? 12 : 14} />,
    },
  };

  const style = variantStyles[normalizedVariant] || variantStyles.neutral;
  const padding = size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-1 text-xs';

  return (
    <span
      className={`inline-flex items-center gap-1 font-semibold rounded-pill border ${style.bg} ${style.text} ${style.border} ${padding} ${className}`}
    >
      {icon !== undefined ? icon : style.defaultIcon}
      <span>{children}</span>
    </span>
  );
};

// Helper component that maps arbitrary status strings to badges
export const StatusBadge: React.FC<{ status: string; size?: 'sm' | 'md' }> = ({
  status,
  size = 'md',
}) => {
  const s = status.toLowerCase();

  if (['completed', 'approved', 'active', 'online', 'resolved'].includes(s)) {
    return <Badge variant="success" size={size}>{status.replace('_', ' ')}</Badge>;
  }
  if (['in_progress', 'en_route', 'accepted', 'assigned', 'matching'].includes(s)) {
    return <Badge variant="progress" size={size}>{status.replace('_', ' ')}</Badge>;
  }
  if (['pending', 'requested', 'at_risk', 'urgent'].includes(s)) {
    return <Badge variant="pending" size={size}>{status.replace('_', ' ')}</Badge>;
  }
  if (['breached', 'critical', 'emergency', 'cancelled', 'suspended', 'rejected', 'failed'].includes(s)) {
    return <Badge variant="error" size={size}>{status.replace('_', ' ')}</Badge>;
  }

  return <Badge variant="neutral" size={size}>{status.replace('_', ' ')}</Badge>;
};
