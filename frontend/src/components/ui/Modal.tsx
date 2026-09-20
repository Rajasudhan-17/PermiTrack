import React, { useEffect } from 'react';
import { X } from 'lucide-react';

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  description?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  size?: 'sm' | 'md' | 'lg' | 'xl';
}

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  description,
  children,
  footer,
  size = 'md',
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.body.style.overflow = '';
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const sizeClasses = {
    sm: 'sm:max-w-md',
    md: 'sm:max-w-lg',
    lg: 'sm:max-w-2xl',
    xl: 'sm:max-w-4xl',
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-bg/80 backdrop-blur-sm animate-fadeIn">
      {/* Backdrop click handler */}
      <div className="fixed inset-0" onClick={onClose} aria-hidden="true" />

      {/* Modal Container */}
      <div
        className={`relative w-[calc(100%-32px)] ${sizeClasses[size]} bg-surface border border-border rounded-xl shadow-lg flex flex-col max-h-[90vh] z-10 overflow-hidden animate-scaleUp focus:outline-none`}
        role="dialog"
        aria-modal="true"
        tabIndex={-1}
      >
        {/* Header */}
        {(title || description) && (
          <div className="flex items-start justify-between p-4 sm:p-5 border-b border-border shrink-0">
            <div>
              {title && <h2 className="text-base sm:text-lg font-semibold text-text-primary">{title}</h2>}
              {description && <p className="text-xs text-text-muted mt-0.5">{description}</p>}
            </div>
            <button
              onClick={onClose}
              className="text-text-muted hover:text-text-primary p-1.5 rounded-md transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
              aria-label="Close modal"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        )}

        {/* Content Body */}
        <div className="p-4 sm:p-5 overflow-y-auto flex-1 leading-relaxed text-xs sm:text-sm text-text-secondary">
          {children}
        </div>

        {/* Footer */}
        {footer && (
          <div className="flex flex-wrap items-center justify-end gap-3 p-3.5 sm:p-4 border-t border-border bg-surface-elevated/50 shrink-0">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
};
