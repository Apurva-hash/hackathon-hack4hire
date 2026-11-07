import React, { useEffect } from 'react';
import { XIcon } from './Icons';
import { Button } from './Button';

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  description?: string;
  children?: React.ReactNode;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  // Confirmation mode
  isConfirmation?: boolean;
  confirmLabel?: string;
  confirmVariant?: 'primary' | 'danger';
  onConfirm?: () => void;
  confirmLoading?: boolean;
}

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  description,
  children,
  size = 'md',
  isConfirmation = false,
  confirmLabel = 'Confirm',
  confirmVariant = 'primary',
  onConfirm,
  confirmLoading = false,
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.body.style.overflow = 'unset';
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const sizeClasses = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-2xl',
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby={title ? 'modal-title' : undefined}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-fade-in"
      onClick={onClose}
    >
      <div
        className={`w-full ${sizeClasses[size]} bg-surface text-text rounded-modal border border-border shadow-warmXl p-6 overflow-hidden max-h-[90vh] flex flex-col`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between pb-3 border-b border-border/60">
          <div>
            {title && (
              <h2 id="modal-title" className="text-lg font-bold text-text">
                {title}
              </h2>
            )}
            {description && (
              <p className="text-xs text-text-muted mt-0.5">{description}</p>
            )}
          </div>
          <button
            onClick={onClose}
            aria-label="Close modal"
            className="p-1 rounded-full text-text-muted hover:text-text hover:bg-surface-alt transition-colors"
          >
            <XIcon size={20} />
          </button>
        </div>

        <div className="py-4 overflow-y-auto flex-1">{children}</div>

        {isConfirmation && (
          <div className="flex items-center justify-end gap-3 pt-3 border-t border-border/60">
            <Button variant="secondary" size="md" onClick={onClose} disabled={confirmLoading}>
              Cancel
            </Button>
            <Button
              variant={confirmVariant}
              size="md"
              loading={confirmLoading}
              onClick={onConfirm}
            >
              {confirmLabel}
            </Button>
          </div>
        )}
      </div>
    </div>
  );
};

