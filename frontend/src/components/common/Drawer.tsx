import React, { useEffect } from 'react';
import { XIcon } from './Icons';

export interface DrawerProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  position?: 'right' | 'bottom';
  children: React.ReactNode;
  size?: 'sm' | 'md' | 'lg' | 'full';
}

export const Drawer: React.FC<DrawerProps> = ({
  isOpen,
  onClose,
  title,
  position = 'right',
  children,
  size = 'md',
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

  const rightSizeClasses = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-xl',
    full: 'max-w-3xl',
  };

  const bottomSizeClasses = {
    sm: 'max-h-[40vh]',
    md: 'max-h-[65vh]',
    lg: 'max-h-[85vh]',
    full: 'max-h-[95vh]',
  };

  if (position === 'bottom') {
    return (
      <div
        className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 backdrop-blur-sm animate-fade-in"
        onClick={onClose}
      >
        <div
          className={`w-full ${bottomSizeClasses[size]} bg-surface text-text rounded-t-sheet border-t border-x border-border shadow-warmXl flex flex-col overflow-hidden animate-slide-up`}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Grab handle */}
          <div className="w-12 h-1.5 bg-border rounded-full mx-auto mt-3 mb-1" />

          {title && (
            <div className="flex items-center justify-between px-5 py-3 border-b border-border/60">
              <h2 className="text-base font-bold text-text">{title}</h2>
              <button
                onClick={onClose}
                aria-label="Close sheet"
                className="p-1 rounded-full text-text-muted hover:text-text hover:bg-surface-alt"
              >
                <XIcon size={20} />
              </button>
            </div>
          )}

          <div className="p-5 overflow-y-auto flex-1">{children}</div>
        </div>
      </div>
    );
  }

  // Right-side drawer
  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-black/50 backdrop-blur-sm animate-fade-in"
      onClick={onClose}
    >
      <div
        className={`w-full ${rightSizeClasses[size]} h-full bg-surface text-text border-l border-border shadow-warmXl flex flex-col overflow-hidden animate-slide-left`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-border/60">
          <h2 className="text-lg font-bold text-text">{title || 'Details'}</h2>
          <button
            onClick={onClose}
            aria-label="Close drawer"
            className="p-1.5 rounded-full text-text-muted hover:text-text hover:bg-surface-alt transition-colors"
          >
            <XIcon size={20} />
          </button>
        </div>

        <div className="p-6 overflow-y-auto flex-1">{children}</div>
      </div>
    </div>
  );
};

