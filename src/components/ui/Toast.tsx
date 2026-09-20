import React, { useEffect } from 'react';
import { CheckCircle2, AlertCircle, Info, XCircle, X } from 'lucide-react';

export interface ToastProps {
  id?: string;
  type?: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message?: string;
  duration?: number;
  onDismiss: () => void;
}

export const Toast: React.FC<ToastProps> = ({
  type = 'info',
  title,
  message,
  duration = 4000,
  onDismiss,
}) => {
  useEffect(() => {
    if (duration > 0) {
      const timer = setTimeout(onDismiss, duration);
      return () => clearTimeout(timer);
    }
  }, [duration, onDismiss]);

  const typeConfig = {
    success: {
      bg: 'bg-surface border-success/40 text-success',
      icon: <CheckCircle2 className="w-5 h-5 shrink-0 text-success" />,
    },
    error: {
      bg: 'bg-surface border-danger/40 text-danger',
      icon: <XCircle className="w-5 h-5 shrink-0 text-danger" />,
    },
    warning: {
      bg: 'bg-surface border-warning/40 text-warning',
      icon: <AlertCircle className="w-5 h-5 shrink-0 text-warning" />,
    },
    info: {
      bg: 'bg-surface border-info/40 text-info',
      icon: <Info className="w-5 h-5 shrink-0 text-info" />,
    },
  };

  const config = typeConfig[type];

  return (
    <div
      role="status"
      aria-live="polite"
      className={`flex items-start gap-3 p-3.5 sm:p-4 rounded-xl border shadow-lg w-full max-w-[calc(100vw-32px)] sm:max-w-sm bg-surface border-border z-50 animate-slideInRight ${config.bg}`}
    >
      <div className="mt-0.5">{config.icon}</div>
      <div className="flex-1 text-xs sm:text-sm min-w-0">
        <div className="font-semibold text-text-primary leading-tight">{title}</div>
        {message && <div className="text-text-muted mt-0.5 leading-relaxed text-xs">{message}</div>}
      </div>
      <button
        onClick={onDismiss}
        className="text-text-muted hover:text-text-primary p-1.5 rounded-lg transition-colors min-h-[36px] min-w-[36px] flex items-center justify-center shrink-0"
        aria-label="Dismiss toast"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
};
