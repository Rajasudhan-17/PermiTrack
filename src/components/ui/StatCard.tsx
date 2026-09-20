import React from 'react';
import { Card } from './Card';

export interface StatCardProps {
  label: string;
  value: string | number;
  icon?: React.ReactNode;
  trend?: {
    text: string;
    positive?: boolean;
  };
  subtitle?: string;
  variant?: 'primary' | 'success' | 'warning' | 'danger' | 'info' | 'neutral';
  className?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  label,
  value,
  icon,
  trend,
  subtitle,
  variant = 'neutral',
  className = '',
}) => {
  const iconVariantClasses = {
    primary: 'bg-primary-subtle text-primary',
    success: 'bg-success-subtle text-success',
    warning: 'bg-warning-subtle text-warning',
    danger: 'bg-danger-subtle text-danger',
    info: 'bg-info-subtle text-info',
    neutral: 'bg-surface-elevated text-text-secondary',
  };

  return (
    <Card hoverable className={`flex flex-col gap-3 ${className}`}>
      <div className="flex items-center justify-between">
        <span className="text-xs md:text-sm font-medium text-text-muted">{label}</span>
        {icon && (
          <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${iconVariantClasses[variant]}`}>
            {icon}
          </div>
        )}
      </div>

      <div className="flex items-baseline justify-between gap-2">
        <span className="text-2xl sm:text-3xl md:text-4xl font-bold text-text-primary tracking-tight font-display">
          {value}
        </span>
        {trend && (
          <span
            className={`text-xs font-semibold px-2 py-0.5 rounded-pill ${
              trend.positive
                ? 'bg-success-subtle text-success'
                : 'bg-danger-subtle text-danger'
            }`}
          >
            {trend.text}
          </span>
        )}
      </div>

      {subtitle && (
        <span className="text-xs text-text-muted">{subtitle}</span>
      )}
    </Card>
  );
};
