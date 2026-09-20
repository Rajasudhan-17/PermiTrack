import React from 'react';

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'text' | 'circular' | 'rectangular';
  width?: string | number;
  height?: string | number;
}

export const Skeleton: React.FC<SkeletonProps> = ({
  variant = 'text',
  width,
  height,
  className = '',
  style,
  ...props
}) => {
  const variantClasses = {
    text: 'rounded h-4 w-full',
    circular: 'rounded-full',
    rectangular: 'rounded-lg w-full h-24',
  };

  return (
    <div
      className={`bg-surface-elevated/70 animate-pulse ${variantClasses[variant]} ${className}`}
      style={{
        width,
        height,
        ...style,
      }}
      {...props}
    />
  );
};

export const CardSkeleton: React.FC<{ className?: string }> = ({ className = '' }) => (
  <div className={`p-6 bg-surface border border-border rounded-xl space-y-4 ${className}`}>
    <div className="flex items-center justify-between">
      <Skeleton variant="text" width="40%" />
      <Skeleton variant="circular" width={32} height={32} />
    </div>
    <Skeleton variant="rectangular" height={60} />
    <Skeleton variant="text" width="70%" />
  </div>
);

export const TableSkeleton: React.FC<{ rows?: number; className?: string }> = ({ rows = 3, className = '' }) => (
  <div className={`p-4 bg-surface border border-border rounded-xl space-y-3 ${className}`}>
    <Skeleton variant="text" width="30%" height={24} />
    <div className="space-y-2">
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} variant="rectangular" height={44} />
      ))}
    </div>
  </div>
);
