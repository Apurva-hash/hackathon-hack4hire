import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/apiClient';
import { UserRole } from '../../types';
import { BellIcon, SunIcon, MoonIcon, WrenchIcon, SearchIcon } from '../common/Icons';

export interface NavbarProps {
  onOpenNotifications?: () => void;
  unreadNotificationsCount?: number;
}

export const Navbar: React.FC<NavbarProps> = ({
  onOpenNotifications,
  unreadNotificationsCount = 0,
}) => {
  const { user, role, logout, quickLogin, isDarkMode, toggleDarkMode } = useAuth();
  const navigate = useNavigate();

  const [backendHealthy, setBackendHealthy] = useState<boolean | null>(null);
  const [showRoleMenu, setShowRoleMenu] = useState(false);

  useEffect(() => {
    // Quick health probe
    fetch('/api/health')
      .then((res) => (res.ok ? setBackendHealthy(true) : setBackendHealthy(false)))
      .catch(() => setBackendHealthy(false));
  }, []);

  const handleRoleSwitch = async (targetRole: UserRole) => {
    setShowRoleMenu(false);
    try {
      await quickLogin(targetRole);
      if (targetRole === 'admin') navigate('/admin/overview');
      else if (targetRole === 'technician') navigate('/technician/dashboard');
      else navigate('/customer/dashboard');
    } catch (err) {
      console.error('Role switch failed:', err);
    }
  };

  return (
    <header className="h-16 bg-surface border-b border-border px-4 sm:px-6 flex items-center justify-between sticky top-0 z-30 shadow-warmSm">
      {/* Brand logo & title */}
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-primary flex items-center justify-center text-white font-bold shadow-warmSm text-base">
          <WrenchIcon size={20} />
        </div>
        <div>
          <span className="text-lg font-bold tracking-tight text-text">
            Dispatch<span className="text-primary">Grid</span>
          </span>
          <span className="hidden sm:inline-block ml-2 text-[10px] font-bold px-1.5 py-0.5 bg-primary-tint text-primary rounded-full uppercase tracking-wider">
            {role}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-2 sm:gap-4">
        {/* Backend health pulse */}
        <div className="hidden lg:flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border border-border bg-surface-alt">
          <span
            className={`w-2 h-2 rounded-full ${
              backendHealthy === true
                ? 'bg-status-success animate-pulse'
                : backendHealthy === false
                ? 'bg-status-error'
                : 'bg-status-pending'
            }`}
          />
          <span className="text-text-muted font-medium text-[11px]">
            {backendHealthy === true
              ? 'Real-Time Sync'
              : backendHealthy === false
              ? 'Offline'
              : 'Connecting...'}
          </span>
        </div>

        {/* Notifications Icon Button */}
        {onOpenNotifications && (
          <button
            onClick={onOpenNotifications}
            aria-label="View notifications"
            className="relative p-2 rounded-full text-text-muted hover:text-text hover:bg-surface-alt transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
          >
            <BellIcon size={20} />
            {unreadNotificationsCount > 0 && (
              <span className="absolute top-2 right-2 w-4 h-4 rounded-full bg-status-error text-white text-[10px] font-bold flex items-center justify-center">
                {unreadNotificationsCount > 9 ? '9+' : unreadNotificationsCount}
              </span>
            )}
          </button>
        )}

        {/* Dark mode toggle */}
        <button
          onClick={toggleDarkMode}
          aria-label={isDarkMode ? 'Switch to light mode' : 'Switch to dark mode'}
          className="p-2 rounded-full text-text-muted hover:text-text hover:bg-surface-alt transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
        >
          {isDarkMode ? <SunIcon size={20} className="text-accent" /> : <MoonIcon size={20} />}
        </button>

        {/* Fast Role Switcher */}
        <div className="relative">
          <button
            onClick={() => setShowRoleMenu(!showRoleMenu)}
            aria-label="Switch active role"
            className="flex items-center gap-2 px-3 py-1.5 rounded-input border border-border bg-surface-alt text-xs font-semibold text-text hover:bg-border/60 transition min-h-[44px]"
          >
            <span className="text-text-muted hidden sm:inline">Role:</span>
            <span className="capitalize text-primary font-bold">{user?.role || 'Guest'}</span>
            <span className="text-text-muted text-[10px]">▼</span>
          </button>

          {showRoleMenu && (
            <div className="absolute right-0 mt-2 w-52 bg-surface border border-border rounded-modal shadow-warmXl py-2 z-50 animate-slide-up">
              <div className="px-3.5 py-1 text-[10px] font-bold text-text-muted uppercase tracking-wider">
                Switch Role Context
              </div>
              <button
                onClick={() => handleRoleSwitch('customer')}
                className={`w-full text-left px-3.5 py-2 text-xs font-medium flex items-center justify-between hover:bg-surface-alt ${
                  role === 'customer' ? 'text-primary font-bold bg-primary-tint/30' : 'text-text'
                }`}
              >
                <span>📦 Customer Portal</span>
                {role === 'customer' && <span className="text-primary font-bold">✓</span>}
              </button>
              <button
                onClick={() => handleRoleSwitch('technician')}
                className={`w-full text-left px-3.5 py-2 text-xs font-medium flex items-center justify-between hover:bg-surface-alt ${
                  role === 'technician' ? 'text-primary font-bold bg-primary-tint/30' : 'text-text'
                }`}
              >
                <span>👷 Technician App</span>
                {role === 'technician' && <span className="text-primary font-bold">✓</span>}
              </button>
              <button
                onClick={() => handleRoleSwitch('admin')}
                className={`w-full text-left px-3.5 py-2 text-xs font-medium flex items-center justify-between hover:bg-surface-alt ${
                  role === 'admin' ? 'text-primary font-bold bg-primary-tint/30' : 'text-text'
                }`}
              >
                <span>⚡ Admin Console</span>
                {role === 'admin' && <span className="text-primary font-bold">✓</span>}
              </button>
            </div>
          )}
        </div>

        {/* User Avatar & Logout */}
        <div className="flex items-center gap-2.5 pl-2 border-l border-border">
          <div className="w-8 h-8 rounded-full bg-primary-tint text-primary font-bold flex items-center justify-center text-xs border border-primary/20">
            {user?.name?.slice(0, 2).toUpperCase() || 'DG'}
          </div>
          <button
            onClick={() => {
              logout();
              navigate('/login');
            }}
            title="Sign out"
            className="text-xs font-semibold text-text-muted hover:text-status-error px-2 py-1.5 rounded-input hover:bg-surface-alt transition min-h-[44px] flex items-center"
          >
            Logout
          </button>
        </div>
      </div>
    </header>
  );
};
