import React, { createContext, useContext, useState, useCallback } from 'react';
import { CheckIcon, AlertTriangleIcon, XIcon, ClockIcon } from './Icons';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface ToastMessage {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
}

interface ToastContextType {
  toast: (title: string, message?: string, type?: ToastType) => void;
  success: (title: string, message?: string) => void;
  error: (title: string, message?: string) => void;
  warning: (title: string, message?: string) => void;
  info: (title: string, message?: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = useCallback(
    (title: string, message?: string, type: ToastType = 'info') => {
      const id = `${Date.now()}-${Math.random()}`;
      setToasts((prev) => [...prev, { id, title, message, type }]);
      setTimeout(() => {
        removeToast(id);
      }, 4000);
    },
    [removeToast]
  );

  const success = useCallback((title: string, message?: string) => toast(title, message, 'success'), [toast]);
  const error = useCallback((title: string, message?: string) => toast(title, message, 'error'), [toast]);
  const warning = useCallback((title: string, message?: string) => toast(title, message, 'warning'), [toast]);
  const info = useCallback((title: string, message?: string) => toast(title, message, 'info'), [toast]);

  const icons: Record<ToastType, React.ReactNode> = {
    success: <CheckIcon size={18} className="text-status-success" />,
    error: <AlertTriangleIcon size={18} className="text-status-error" />,
    warning: <ClockIcon size={18} className="text-status-pending" />,
    info: <ClockIcon size={18} className="text-status-progress" />,
  };

  const borders: Record<ToastType, string> = {
    success: 'border-l-4 border-l-status-success',
    error: 'border-l-4 border-l-status-error',
    warning: 'border-l-4 border-l-status-pending',
    info: 'border-l-4 border-l-status-progress',
  };

  return (
    <ToastContext.Provider value={{ toast, success, error, warning, info }}>
      {children}
      {/* Toast Container */}
      <div
        aria-live="polite"
        className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none px-4 sm:px-0"
      >
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`pointer-events-auto bg-surface text-text rounded-card border border-border shadow-warmLg p-3.5 flex items-start gap-3 transition-all duration-200 animate-slide-up ${borders[t.type]}`}
          >
            <div className="flex-shrink-0 mt-0.5">{icons[t.type]}</div>
            <div className="flex-1 min-w-0">
              <h4 className="text-xs font-bold text-text leading-tight">{t.title}</h4>
              {t.message && (
                <p className="text-xs text-text-muted mt-0.5 leading-snug line-clamp-2">
                  {t.message}
                </p>
              )}
            </div>
            <button
              onClick={() => removeToast(t.id)}
              aria-label="Dismiss toast"
              className="text-text-muted hover:text-text p-0.5 rounded"
            >
              <XIcon size={14} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
};

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
};

