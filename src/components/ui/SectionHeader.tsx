import React from 'react';

export interface SectionHeaderProps {
  title: string;
  description?: string;
  actions?: React.ReactNode;
  className?: string;
}

export const SectionHeader: React.FC<SectionHeaderProps> = ({
  title,
  description,
  actions,
  className = '',
}) => {
  return (
    <div className={`flex items-center justify-between gap-4 mb-4 ${className}`}>
      <div>
        <h2 className="text-lg md:text-xl font-semibold text-text-primary tracking-tight">
          {title}
        </h2>
        {description && (
          <p className="text-xs md:text-sm text-text-muted mt-0.5">
            {description}
          </p>
        )}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
};
