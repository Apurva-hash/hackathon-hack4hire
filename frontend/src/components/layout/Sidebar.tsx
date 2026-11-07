import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import {
  MapPinIcon,
  ClockIcon,
  UserIcon,
  SettingsIcon,
  WrenchIcon,
  AlertTriangleIcon,
  NavigationIcon,
} from '../common/Icons';

export const Sidebar: React.FC = () => {
  const { role } = useAuth();

  // Navigation Items per Role
  const adminNav = [
    { to: '/admin/overview', label: 'Dashboard', icon: '📊' },
    { to: '/admin/live-map', label: 'Live Map', icon: '🗺️' },
    { to: '/admin/jobs', label: 'Jobs & Dispatch', icon: '📋' },
    { to: '/admin/escalations', label: 'Escalation Inbox', icon: '🚨' },
    { to: '/admin/technicians', label: 'Technicians', icon: '👷' },
    { to: '/admin/customers', label: 'Customers', icon: '👥' },
    { to: '/admin/feedback', label: 'Feedback & Reviews', icon: '⭐' },
    { to: '/admin/reports', label: 'Reports & Revenue', icon: '📈' },
    { to: '/admin/settings', label: 'Settings & SLA', icon: '⚙️' },
    { to: '/admin/audit', label: 'Audit History', icon: '📜' },
  ];

  const customerNav = [
    { to: '/customer/book', label: 'Book Service', icon: '🛠️' },
    { to: '/customer/dashboard', label: 'Active & History', icon: '📦' },
    { to: '/customer/profile', label: 'Saved Addresses', icon: '📍' },
  ];

  const technicianNav = [
    { to: '/technician/dashboard', label: 'Job Cockpit', icon: '⚡' },
    { to: '/technician/history', label: 'Job History', icon: '📋' },
    { to: '/technician/earnings', label: 'Earnings & Pay', icon: '💰' },
    { to: '/technician/profile', label: 'My Profile', icon: '👤' },
  ];

  if (role === 'admin') {
    return (
      <aside className="w-64 bg-[#2B2118] text-[#F5EBE0] flex flex-col shrink-0 min-h-[calc(100vh-4rem)] border-r border-[#3A2E25] select-none">
        <div className="p-4 border-b border-[#3A2E25]">
          <div className="text-[10px] font-bold tracking-wider uppercase text-[#B8A898]">
            Console Workspace
          </div>
          <div className="text-sm font-bold text-white mt-0.5 flex items-center gap-2">
            <span>Admin Control Center</span>
          </div>
        </div>

        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          {adminNav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3.5 py-2.5 rounded-card text-xs font-semibold transition-all min-h-[44px] ${
                  isActive
                    ? 'bg-primary text-white shadow-warmSm font-bold'
                    : 'text-[#B8A898] hover:text-white hover:bg-[#3A2E25]'
                }`
              }
            >
              <span className="text-base">{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        {/* Footer Info */}
        <div className="p-4 border-t border-[#3A2E25] text-xs text-[#B8A898]">
          <div className="flex items-center justify-between text-[11px] font-medium">
            <span>SLA Engine</span>
            <span className="text-status-success font-bold">Online</span>
          </div>
          <p className="mt-1 text-[10px] text-[#8A7F76]">DispatchGrid v2.0 • Auto-Dispatch</p>
        </div>
      </aside>
    );
  }

  // Mobile Bottom Navigation Bar for Customer & Technician apps
  const currentNav = role === 'technician' ? technicianNav : customerNav;

  return (
    <>
      {/* Desktop/Tablet Sidebar for Customer/Tech */}
      <aside className="hidden md:flex w-56 bg-surface text-text flex-col shrink-0 min-h-[calc(100vh-4rem)] border-r border-border select-none p-3 space-y-1">
        <div className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-text-muted">
          Navigation
        </div>
        {currentNav.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3.5 py-2.5 rounded-card text-xs font-semibold transition-all min-h-[44px] ${
                isActive
                  ? 'bg-primary-tint text-primary font-bold border-l-4 border-primary'
                  : 'text-text-muted hover:text-text hover:bg-surface-alt'
              }`
            }
          >
            <span className="text-base">{item.icon}</span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </aside>

      {/* Mobile Bottom Navigation Bar (<768px) */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 h-16 bg-surface border-t border-border flex items-center justify-around z-40 px-2 shadow-warmLg">
        {currentNav.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `flex flex-col items-center justify-center flex-1 py-1 text-[11px] font-semibold transition-colors min-h-[48px] ${
                isActive ? 'text-primary font-bold' : 'text-text-muted hover:text-text'
              }`
            }
          >
            <span className="text-lg leading-none mb-1">{item.icon}</span>
            <span className="truncate max-w-[80px]">{item.label}</span>
          </NavLink>
        ))}
      </nav>
    </>
  );
};
