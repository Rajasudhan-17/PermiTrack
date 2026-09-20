import React from 'react';

export interface BadgeProps {
  children: React.ReactNode;
  variant?: 'primary' | 'secondary' | 'success' | 'warning' | 'danger' | 'info' | 'neutral';
  size?: 'sm' | 'md';
  icon?: React.ReactNode;
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'secondary',
  size = 'md',
  icon,
  className = '',
}) => {
  const variantClasses = {
    primary: 'bg-primary-subtle text-primary border-primary/30',
    secondary: 'bg-surface-elevated text-text-secondary border-border',
    success: 'bg-success-subtle text-success border-success/30',
    warning: 'bg-warning-subtle text-warning border-warning/30',
    danger: 'bg-danger-subtle text-danger border-danger/30',
    info: 'bg-info-subtle text-info border-info/30',
    neutral: 'bg-surface text-text-muted border-border/50',
  };

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-[11px] gap-1',
    md: 'px-2.5 py-1 text-xs gap-1.5',
  };

  return (
    <span
      className={`inline-flex items-center font-medium rounded-pill border ${variantClasses[variant]} ${sizeClasses[size]} ${className}`}
    >
      {icon && <span className="shrink-0">{icon}</span>}
      <span>{children}</span>
    </span>
  );
};
