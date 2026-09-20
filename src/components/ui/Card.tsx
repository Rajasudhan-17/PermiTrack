import React from 'react';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'elevated' | 'bordered';
  hoverable?: boolean;
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(({
  children,
  variant = 'default',
  hoverable = false,
  className = '',
  ...props
}, ref) => {
  const variantClasses = {
    default: "bg-surface border border-border",
    elevated: "bg-surface-elevated border border-border/80 shadow-md",
    bordered: "bg-transparent border border-border",
  };

  const hoverClass = hoverable ? "transition-all duration-200 hover:border-primary/40 hover:shadow-md" : "";

  return (
    <div
      ref={ref}
      className={`rounded-lg p-5 ${variantClasses[variant]} ${hoverClass} ${className}`}
      {...props}
    >
      {children}
    </div>
  );
});

Card.displayName = 'Card';

export const CardHeader = ({ children, className = '' }: { children: React.ReactNode; className?: string }) => (
  <div className={`flex items-center justify-between pb-3 mb-3 border-b border-border/50 ${className}`}>
    {children}
  </div>
);

export const CardTitle = ({ children, className = '' }: { children: React.ReactNode; className?: string }) => (
  <h3 className="text-lg font-semibold text-text-primary tracking-tight">{children}</h3>
);

export const CardContent = ({ children, className = '' }: { children: React.ReactNode; className?: string }) => (
  <div className={className}>{children}</div>
);

export const CardFooter = ({ children, className = '' }: { children: React.ReactNode; className?: string }) => (
  <div className={`pt-3 mt-4 border-t border-border/50 flex items-center justify-between ${className}`}>
    {children}
  </div>
);
