import React from 'react';
import { ChevronDown } from 'lucide-react';

export interface SelectOption {
  value: string | number;
  label: string;
  disabled?: boolean;
}

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  helperText?: string;
  options?: SelectOption[];
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(({
  label,
  error,
  helperText,
  options = [],
  children,
  disabled,
  className = '',
  id,
  ...props
}, ref) => {
  const generatedId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

  let stateClasses = "border-border hover:border-border-hover focus:border-primary focus:ring-1 focus:ring-primary/40";
  if (error) {
    stateClasses = "border-danger text-danger focus:border-danger focus:ring-1 focus:ring-danger/40";
  }

  return (
    <div className="w-full flex flex-col gap-1.5">
      {label && (
        <label htmlFor={generatedId} className="text-xs font-medium text-text-secondary select-none">
          {label}
        </label>
      )}
      <div className="relative flex items-center">
        <select
          ref={ref}
          id={generatedId}
          disabled={disabled}
          className={`w-full min-h-[44px] appearance-none bg-bg-secondary text-text-primary text-sm rounded-md border px-3.5 py-2.5 pr-10 transition-all outline-none disabled:opacity-50 disabled:cursor-not-allowed ${stateClasses} ${className}`}
          {...props}
        >
          {children || options.map((opt) => (
            <option key={opt.value} value={opt.value} disabled={opt.disabled} className="bg-surface text-text-primary">
              {opt.label}
            </option>
          ))}
        </select>
        <ChevronDown className="absolute right-3.5 w-4 h-4 text-text-muted pointer-events-none" />
      </div>
      {error ? (
        <span className="text-xs text-danger font-medium">{error}</span>
      ) : helperText ? (
        <span className="text-xs text-text-muted">{helperText}</span>
      ) : null}
    </div>
  );
});

Select.displayName = 'Select';
