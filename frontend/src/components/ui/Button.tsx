import React from 'react';
import { Loader2 } from 'lucide-react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  icon?: React.ReactNode;
  fullWidth?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  icon,
  fullWidth = false,
  disabled,
  className = '',
  ...props
}, ref) => {
  // Base classes with min 44px touch target (py-2 px-4 minimum h-[44px])
  const baseClasses = "inline-flex items-center justify-center font-medium rounded-sm transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary/50 disabled:opacity-50 disabled:cursor-not-allowed select-none min-h-[44px]";
  
  const variantClasses = {
    primary: "bg-primary text-[#07151F] hover:bg-primary-hover active:bg-[#1DA1B7] font-semibold shadow-sm",
    secondary: "bg-surface-elevated text-text-primary hover:bg-[#1A384C] active:bg-[#112635] border border-border",
    outline: "border border-border text-text-primary hover:border-primary/50 hover:bg-primary-subtle active:bg-primary/20",
    ghost: "text-text-secondary hover:text-text-primary hover:bg-surface-elevated active:bg-surface",
    danger: "bg-danger text-white hover:bg-[#D9382C] active:bg-[#B82B20] font-semibold shadow-sm",
  };

  const sizeClasses = {
    sm: "px-3 py-1.5 text-xs gap-1.5 min-h-[38px]",
    md: "px-4 py-2.5 text-sm gap-2 min-h-[44px]",
    lg: "px-6 py-3 text-base gap-2.5 min-h-[48px]",
  };

  const widthClass = fullWidth ? "w-full" : "";

  return (
    <button
      ref={ref}
      disabled={disabled || isLoading}
      className={`${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]} ${widthClass} ${className}`}
      {...props}
    >
      {isLoading ? (
        <Loader2 className="w-4 h-4 animate-spin shrink-0" />
      ) : icon ? (
        <span className="shrink-0">{icon}</span>
      ) : null}
      <span>{children}</span>
    </button>
  );
});

Button.displayName = 'Button';
