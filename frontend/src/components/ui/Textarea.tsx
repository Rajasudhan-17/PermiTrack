import React from 'react';

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(({
  label,
  error,
  helperText,
  disabled,
  className = '',
  id,
  rows = 4,
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
      <textarea
        ref={ref}
        id={generatedId}
        disabled={disabled}
        rows={rows}
        className={`w-full bg-bg-secondary text-text-primary placeholder:text-text-muted text-sm rounded-md border px-3.5 py-2.5 transition-all outline-none resize-y disabled:opacity-50 disabled:cursor-not-allowed ${stateClasses} ${className}`}
        {...props}
      />
      {error ? (
        <span className="text-xs text-danger font-medium">{error}</span>
      ) : helperText ? (
        <span className="text-xs text-text-muted">{helperText}</span>
      ) : null}
    </div>
  );
});

Textarea.displayName = 'Textarea';
