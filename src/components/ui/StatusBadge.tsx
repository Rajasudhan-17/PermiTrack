import React from 'react';
import { CheckCircle2, Clock, XCircle, AlertCircle, RefreshCw, MinusCircle, FileText } from 'lucide-react';

export type StatusType = 
  | 'APPROVED' 
  | 'PENDING' 
  | 'REJECTED' 
  | 'SUBMITTED' 
  | 'UNDER_REVIEW' 
  | 'CANCELLED' 
  | 'COMPLETED'
  | string;

export interface StatusBadgeProps {
  status: StatusType;
  showIcon?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  showIcon = true,
  size = 'md',
  className = '',
}) => {
  const normalizedStatus = (status || '').toUpperCase().trim();

  let config = {
    label: normalizedStatus,
    bg: 'bg-surface-elevated',
    text: 'text-text-secondary',
    border: 'border-border',
    icon: <Clock className="w-3.5 h-3.5" />,
  };

  switch (normalizedStatus) {
    case 'APPROVED':
      config = {
        label: 'Approved',
        bg: 'bg-success-subtle',
        text: 'text-success',
        border: 'border-success/30',
        icon: <CheckCircle2 className="w-3.5 h-3.5" />,
      };
      break;
    case 'PENDING':
      config = {
        label: 'Pending',
        bg: 'bg-warning-subtle',
        text: 'text-warning',
        border: 'border-warning/30',
        icon: <Clock className="w-3.5 h-3.5" />,
      };
      break;
    case 'REJECTED':
      config = {
        label: 'Rejected',
        bg: 'bg-danger-subtle',
        text: 'text-danger',
        border: 'border-danger/30',
        icon: <XCircle className="w-3.5 h-3.5" />,
      };
      break;
    case 'SUBMITTED':
      config = {
        label: 'Submitted',
        bg: 'bg-info-subtle',
        text: 'text-info',
        border: 'border-info/30',
        icon: <FileText className="w-3.5 h-3.5" />,
      };
      break;
    case 'UNDER_REVIEW':
      config = {
        label: 'Under Review',
        bg: 'bg-primary-subtle',
        text: 'text-primary',
        border: 'border-primary/30',
        icon: <RefreshCw className="w-3.5 h-3.5 animate-spin-slow" />,
      };
      break;
    case 'CANCELLED':
      config = {
        label: 'Cancelled',
        bg: 'bg-surface-elevated',
        text: 'text-text-muted',
        border: 'border-border',
        icon: <MinusCircle className="w-3.5 h-3.5" />,
      };
      break;
    case 'COMPLETED':
      config = {
        label: 'Completed',
        bg: 'bg-success-subtle',
        text: 'text-success',
        border: 'border-success/30',
        icon: <CheckCircle2 className="w-3.5 h-3.5" />,
      };
      break;
  }

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-[11px] gap-1',
    md: 'px-2.5 py-1 text-xs gap-1.5',
    lg: 'px-3 py-1.5 text-sm gap-2',
  };

  return (
    <span
      className={`inline-flex items-center font-medium rounded-pill border ${config.bg} ${config.text} ${config.border} ${sizeClasses[size]} ${className}`}
    >
      {showIcon && <span className="shrink-0">{config.icon}</span>}
      <span>{config.label}</span>
    </span>
  );
};
