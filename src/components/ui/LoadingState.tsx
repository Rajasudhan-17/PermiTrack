import React from 'react';
import { Loader2 } from 'lucide-react';

export interface LoadingStateProps {
  message?: string;
  size?: 'sm' | 'md' | 'lg';
  fullPage?: boolean;
  className?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  message = 'Loading...',
  size = 'md',
  fullPage = false,
  className = '',
}) => {
  const spinnerSizes = {
    sm: 'w-5 h-5',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
  };

  const containerClasses = fullPage
    ? 'fixed inset-0 z-50 bg-bg/80 backdrop-blur-sm flex flex-col items-center justify-center gap-3'
    : 'flex flex-col items-center justify-center p-8 gap-3';

  return (
    <div className={`${containerClasses} ${className}`}>
      <Loader2 className={`${spinnerSizes[size]} text-primary animate-spin`} />
      {message && <span className="text-xs sm:text-sm text-text-muted font-medium">{message}</span>}
    </div>
  );
};
