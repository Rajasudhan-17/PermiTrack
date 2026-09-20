import React from 'react';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  success?: boolean;
  helperText?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(({
  label,
  error,
  success,
  helperText,
  leftIcon,
  rightIcon,
  disabled,
  className = '',
  id,
  ...props
}, ref) => {
  const generatedId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

  let stateClasses = "border-border hover:border-border-hover focus:border-primary focus:ring-1 focus:ring-primary/40";
  if (error) {
    stateClasses = "border-danger text-danger focus:border-danger focus:ring-1 focus:ring-danger/40";
  } else if (success) {
    stateClasses = "border-success focus:border-success focus:ring-1 focus:ring-success/40";
  }

  return (
    <div className="w-full flex flex-col gap-1.5">
      {label && (
        <label htmlFor={generatedId} className="text-xs font-medium text-text-secondary select-none">
          {label}
        </label>
      )}
      <div className="relative flex items-center">
        {leftIcon && (
          <div className="absolute left-3.5 text-text-muted pointer-events-none">
            {leftIcon}
          </div>
        )}
        <input
          ref={ref}
          id={generatedId}
          disabled={disabled}
          className={`w-full min-h-[44px] bg-bg-secondary text-text-primary placeholder:text-text-muted text-sm rounded-md border px-3.5 py-2.5 transition-all outline-none disabled:opacity-50 disabled:cursor-not-allowed ${leftIcon ? 'pl-10' : ''} ${rightIcon ? 'pr-10' : ''} ${stateClasses} ${className}`}
          {...props}
        />
        {rightIcon && (
          <div className="absolute right-3.5 text-text-muted">
            {rightIcon}
          </div>
        )}
      </div>
      {error ? (
        <span className="text-xs text-danger font-medium">{error}</span>
      ) : helperText ? (
        <span className="text-xs text-text-muted">{helperText}</span>
      ) : null}
    </div>
  );
});

Input.displayName = 'Input';
