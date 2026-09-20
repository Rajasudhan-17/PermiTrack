import React from 'react';
import { Info, CheckCircle2, AlertTriangle, XCircle, X } from 'lucide-react';

export interface AlertProps {
  type?: 'info' | 'success' | 'warning' | 'danger';
  title?: string;
  children: React.ReactNode;
  onClose?: () => void;
  className?: string;
}

export const Alert: React.FC<AlertProps> = ({
  type = 'info',
  title,
  children,
  onClose,
  className = '',
}) => {
  const typeConfig = {
    info: {
      bg: 'bg-info-subtle',
      border: 'border-info/30',
      text: 'text-info',
      icon: <Info className="w-5 h-5 shrink-0" />,
    },
    success: {
      bg: 'bg-success-subtle',
      border: 'border-success/30',
      text: 'text-success',
      icon: <CheckCircle2 className="w-5 h-5 shrink-0" />,
    },
    warning: {
      bg: 'bg-warning-subtle',
      border: 'border-warning/30',
      text: 'text-warning',
      icon: <AlertTriangle className="w-5 h-5 shrink-0" />,
    },
    danger: {
      bg: 'bg-danger-subtle',
      border: 'border-danger/30',
      text: 'text-danger',
      icon: <XCircle className="w-5 h-5 shrink-0" />,
    },
  };

  const config = typeConfig[type];

  return (
    <div
      className={`flex items-start gap-3 p-4 rounded-lg border ${config.bg} ${config.border} ${className}`}
      role="alert"
    >
      <div className={config.text}>{config.icon}</div>
      <div className="flex-1 text-sm text-text-primary">
        {title && <div className={`font-semibold mb-0.5 ${config.text}`}>{title}</div>}
        <div className="text-text-secondary leading-relaxed">{children}</div>
      </div>
      {onClose && (
        <button
          type="button"
          onClick={onClose}
          className="text-text-muted hover:text-text-primary p-1 rounded transition-colors"
          aria-label="Close alert"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
};
