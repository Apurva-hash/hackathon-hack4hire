import React, { useState, useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import { Navbar } from './Navbar';
import { Sidebar } from './Sidebar';
import { Drawer } from '../common/Drawer';
import { ToastProvider } from '../common/Toast';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/apiClient';
import { NotificationItem } from '../../types';
import { StatusBadge } from '../common/Badge';

export const DashboardLayout: React.FC = () => {
  const { role, user } = useAuth();
  const [notifOpen, setNotifOpen] = useState(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);

  const fetchNotifications = async () => {
    try {
      if (role === 'customer') {
        const data = await api.customer.getNotifications({ limit: 20 });
        setNotifications(data.notifications || []);
        setUnreadCount(data.notifications?.filter((n) => !n.is_read).length || 0);
      } else if (role === 'technician') {
        const data = await api.technician.getNotifications();
        setNotifications(data.notifications || []);
        setUnreadCount(data.notifications?.filter((n) => !n.is_read).length || 0);
      }
    } catch (err) {
      // Background notifications fetch fails silently
    }
  };

  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 10000); // 10s poll for in-app alerts
    return () => clearInterval(interval);
  }, [role]);

  const handleMarkAsRead = async (id: string) => {
    try {
      if (role === 'customer') {
        await api.customer.markNotificationRead(id);
      } else if (role === 'technician') {
        await api.technician.markNotificationRead(id);
      }
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <ToastProvider>
      <div className="min-h-screen bg-bg flex flex-col font-sans text-text selection:bg-primary-tint">
        <Navbar
          onOpenNotifications={() => setNotifOpen(true)}
          unreadNotificationsCount={unreadCount}
        />
        <div className="flex-1 flex overflow-hidden">
          <Sidebar />
          <main className="flex-1 overflow-y-auto p-4 sm:p-6 md:p-8 w-full max-w-7xl mx-auto pb-20 md:pb-8">
            <Outlet />
          </main>
        </div>

        {/* Global Notifications Drawer */}
        <Drawer
          isOpen={notifOpen}
          onClose={() => setNotifOpen(false)}
          title="Notifications & Alerts"
          position="right"
          size="sm"
        >
          {notifications.length === 0 ? (
            <div className="text-center py-12 text-text-muted text-xs">
              No notifications yet.
            </div>
          ) : (
            <div className="space-y-3">
              {notifications.map((n) => (
                <div
                  key={n.id}
                  onClick={() => !n.is_read && handleMarkAsRead(n.id)}
                  className={`p-3.5 rounded-card border transition-all cursor-pointer ${n.is_read
                      ? 'bg-surface border-border opacity-70'
                      : 'bg-primary-tint/20 border-primary/40 shadow-warmSm'
                    }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="text-xs font-bold text-text">{n.title}</span>
                    <span className="text-[10px] text-text-muted">
                      {n.created_at ? new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}
                    </span>
                  </div>
                  <p className="text-xs text-text-muted leading-relaxed">{n.body}</p>
                  {!n.is_read && (
                    <div className="mt-2 text-[10px] text-primary font-bold flex items-center gap-1">
                      <span>• Mark as read</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </Drawer>
      </div>
    </ToastProvider>
  );
};
