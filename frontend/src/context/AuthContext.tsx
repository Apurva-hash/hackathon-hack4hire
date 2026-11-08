import React, { createContext, useContext, useState, useEffect } from 'react';
import { User, UserRole } from '../types';
import { api, getToken, removeToken } from '../services/apiClient';

interface AuthContextType {
  user: User | null;
  role: UserRole;
  login: (email: string, password: string) => Promise<User>;
  quickLogin: (role: UserRole) => Promise<User>;
  registerCustomer: (payload: { email: string; password: string; name: string; phone?: string }) => Promise<User>;
  registerTechnician: (payload: {
    email: string;
    password: string;
    name: string;
    phone?: string;
    bio?: string;
    certification_level?: number;
    service_radius_km?: number;
  }) => Promise<{ user: User; message?: string }>;
  logout: () => void;
  isAuthenticated: boolean;
  isLoading: boolean;
  // Dark mode
  isDarkMode: boolean;
  toggleDarkMode: () => void;
}



const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(() => {
    const saved = localStorage.getItem('dispatchgrid_user');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (e) {
        return null;
      }
    }
    return null;
  });

  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Dark mode state
  const [isDarkMode, setIsDarkMode] = useState<boolean>(() => {
    const saved = localStorage.getItem('dispatchgrid_theme');
    if (saved) return saved === 'dark';
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('dispatchgrid_theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('dispatchgrid_theme', 'light');
    }
  }, [isDarkMode]);

  const toggleDarkMode = () => {
    setIsDarkMode((prev) => !prev);
  };

  // Check current session on mount
  useEffect(() => {
    const initAuth = async () => {
      const token = getToken();
      if (token) {
        try {
          const me = await api.auth.getMe();
          const authUser: User = {
            id: me.id,
            email: me.email,
            role: me.role as UserRole,
            name: me.profile?.name || me.email.split('@')[0],
            phone: me.profile?.phone,
          };
          setUser(authUser);
          localStorage.setItem('dispatchgrid_user', JSON.stringify(authUser));
        } catch (err: any) {
          console.warn('Session check failed:', err);
          // Only discard token if server explicitly rejected auth (401 or 403)
          const status = err?.response?.status;
          if (status === 401 || status === 403) {
            removeToken();
            setUser(null);
          }
        }
      }
      setIsLoading(false);
    };

    initAuth();
  }, []);

  const login = async (email: string, pass: string): Promise<User> => {
    const data = await api.auth.login(email, pass);
    const authUser: User = {
      id: data.user_id,
      email: email.toLowerCase(),
      role: data.role as UserRole,
      name: data.name || email.split('@')[0],
      token: data.access_token,
    };
    setUser(authUser);
    localStorage.setItem('dispatchgrid_user', JSON.stringify(authUser));
    return authUser;
  };

  const registerCustomer = async (payload: { email: string; password: string; name: string; phone?: string }): Promise<User> => {
    const data = await api.auth.registerCustomer(payload);
    const authUser: User = {
      id: data.user_id,
      email: payload.email.toLowerCase(),
      role: 'customer',
      name: data.name || payload.name,
      token: data.access_token,
    };
    setUser(authUser);
    localStorage.setItem('dispatchgrid_user', JSON.stringify(authUser));
    return authUser;
  };

  const registerTechnician = async (payload: {
    email: string;
    password: string;
    name: string;
    phone?: string;
    bio?: string;
    certification_level?: number;
    service_radius_km?: number;
  }): Promise<{ user: User; message?: string }> => {
    const data = await api.auth.registerTechnician(payload);
    const authUser: User = {
      id: data.user_id,
      email: payload.email.toLowerCase(),
      role: 'technician',
      name: data.name || payload.name,
      token: data.access_token,
    };
    setUser(authUser);
    localStorage.setItem('dispatchgrid_user', JSON.stringify(authUser));
    return { user: authUser, message: data.message };
  };

  const quickLogin = async (_targetRole: UserRole): Promise<User> => {
    throw new Error('Demo login is disabled');
  };

  const logout = () => {
    api.auth.logout().catch(() => {});
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        role: (user?.role || 'customer') as UserRole,
        login,
        quickLogin,
        registerCustomer,
        registerTechnician,
        logout,
        isAuthenticated: !!user,
        isLoading,
        isDarkMode,
        toggleDarkMode,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
