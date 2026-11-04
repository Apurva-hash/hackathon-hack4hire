import axios, { AxiosError } from 'axios';
import {
  User,
  CustomerProfile,
  TechnicianProfile,
  ServiceCategory,
  SLATier,
  NearbyTechnician,
  ServiceRequest,
  TechnicianJobOffer,
  Rating,
  NotificationItem,
  MatchingConfig,
  AdminOverview,
  DispatchMetrics,
  TechnicianWorkloadItem,
  SLAStats,
  FeedbackStats,
  RevenueStats,
  DemandStats,
  AuditLogEntry,
} from '../types';

export const API_BASE_URL = '';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Centralized Token Management
export const getToken = (): string | null => {
  return localStorage.getItem('dispatchgrid_token');
};

export const setToken = (token: string) => {
  localStorage.setItem('dispatchgrid_token', token);
};

export const removeToken = () => {
  localStorage.removeItem('dispatchgrid_token');
  localStorage.removeItem('dispatchgrid_refresh_token');
  localStorage.removeItem('dispatchgrid_user');
};

// Request interceptor: attach bearer token
apiClient.interceptors.request.use((config) => {
  const token = getToken();
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: handle 401 & error extracting
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ detail?: string }>) => {
    if (error.response?.status === 401) {
      // Don't auto-logout if we're attempting login itself
      if (!error.config?.url?.includes('/api/auth/login')) {
        removeToken();
        // Redirect to login if not already there
        if (window.location.pathname !== '/login') {
          window.location.href = '/login';
        }
      }
    }
    const message =
      error.response?.data?.detail || error.message || 'An error occurred with the request';
    return Promise.reject(new Error(message));
  }
);

// ── API SERVICE METHODS ───────────────────────────────────────────────────────

export const api = {
  // ── Auth APIs ──────────────────────────────────────────────────────────────
  auth: {
    registerCustomer: async (payload: { email: string; password: string; name: string; phone?: string }) => {
      const res = await apiClient.post('/api/auth/register/customer', payload);
      if (res.data.access_token) setToken(res.data.access_token);
      return res.data;
    },

    registerTechnician: async (payload: {
      email: string;
      password: string;
      name: string;
      phone?: string;
      bio?: string;
      certification_level?: number;
      service_radius_km?: number;
    }) => {
      const res = await apiClient.post('/api/auth/register/technician', payload);
      if (res.data.access_token) setToken(res.data.access_token);
      return res.data;
    },

    login: async (email: string, password: string) => {
      const res = await apiClient.post('/api/auth/login', { email, password });
      if (res.data.access_token) {
        setToken(res.data.access_token);
        if (res.data.refresh_token) {
          localStorage.setItem('dispatchgrid_refresh_token', res.data.refresh_token);
        }
      }
      return res.data;
    },

    getMe: async () => {
      const res = await apiClient.get('/api/auth/me');
      return res.data;
    },

    logout: async () => {
      try {
        await apiClient.post('/api/auth/logout');
      } finally {
        removeToken();
      }
    },
  },

  // ── Customer APIs ──────────────────────────────────────────────────────────
  customer: {
    getProfile: async (): Promise<CustomerProfile> => {
      const res = await apiClient.get<CustomerProfile>('/api/customer/profile');
      return res.data;
    },

    updateProfile: async (payload: { name?: string; phone?: string }) => {
      const res = await apiClient.patch('/api/customer/profile', payload);
      return res.data;
    },

    getAddresses: async (): Promise<{ addresses: any[] }> => {
      const res = await apiClient.get('/api/customer/addresses');
      return res.data;
    },

    addAddress: async (payload: { label: string; address: string; lat: number; lng: number }) => {
      const res = await apiClient.post('/api/customer/addresses', payload);
      return res.data;
    },

    deleteAddress: async (index: number) => {
      const res = await apiClient.delete(`/api/customer/addresses/${index}`);
      return res.data;
    },

    getCategories: async (): Promise<ServiceCategory[]> => {
      const res = await apiClient.get<ServiceCategory[]>('/api/customer/categories');
      return res.data;
    },

    getNearbyTechnicians: async (params: {
      lat: number;
      lng: number;
      category_id?: string;
      radius_km?: number;
    }): Promise<{ count: number; technicians: NearbyTechnician[] }> => {
      const res = await apiClient.get('/api/customer/nearby-technicians', { params });
      return res.data;
    },

    createBooking: async (payload: {
      category_id: string;
      description?: string;
      address: string;
      lat: number;
      lng: number;
      urgency?: string;
      preferred_time_start?: string;
      preferred_time_end?: string;
      sla_tier_id?: string;
    }): Promise<{ message: string; booking_id: string; status: string; sla_response_deadline?: string; sla_resolution_deadline?: string }> => {
      const res = await apiClient.post('/api/customer/bookings', payload);
      return res.data;
    },

    getBookings: async (params?: { status?: string; limit?: number; offset?: number }): Promise<{ total: number; bookings: ServiceRequest[] }> => {
      const res = await apiClient.get('/api/customer/bookings', { params });
      return res.data;
    },

    getBooking: async (bookingId: string): Promise<ServiceRequest> => {
      const res = await apiClient.get<ServiceRequest>(`/api/customer/bookings/${bookingId}`);
      return res.data;
    },

    cancelBooking: async (bookingId: string) => {
      const res = await apiClient.post(`/api/customer/bookings/${bookingId}/cancel`);
      return res.data;
    },

    rateBooking: async (bookingId: string, payload: { score: number; feedback_text?: string }) => {
      const res = await apiClient.post(`/api/customer/bookings/${bookingId}/rate`, payload);
      return res.data;
    },

    getTechnicianLocation: async (bookingId: string) => {
      const res = await apiClient.get(`/api/customer/bookings/${bookingId}/technician-location`);
      return res.data;
    },

    getNotifications: async (params?: { unread_only?: boolean; limit?: number }): Promise<{ total: number; notifications: NotificationItem[] }> => {
      const res = await apiClient.get('/api/customer/notifications', { params });
      return res.data;
    },

    markNotificationRead: async (id: string) => {
      const res = await apiClient.patch(`/api/customer/notifications/${id}/read`);
      return res.data;
    },
  },

  // ── Technician APIs ────────────────────────────────────────────────────────
  technician: {
    getProfile: async (): Promise<TechnicianProfile> => {
      const res = await apiClient.get<TechnicianProfile>('/api/technician/profile');
      return res.data;
    },

    updateProfile: async (payload: { name?: string; phone?: string; bio?: string; service_radius_km?: number; max_concurrent_jobs?: number }) => {
      const res = await apiClient.patch('/api/technician/profile', payload);
      return res.data;
    },

    setAvailability: async (is_online: boolean): Promise<{ is_online: boolean }> => {
      const res = await apiClient.patch('/api/technician/availability', { is_online });
      return res.data;
    },

    updateLocation: async (lat: number, lng: number) => {
      const res = await apiClient.patch('/api/technician/location', { lat, lng });
      return res.data;
    },

    getOffers: async (): Promise<{ count: number; offers: TechnicianJobOffer[] }> => {
      const res = await apiClient.get('/api/technician/offers');
      return res.data;
    },

    acceptOffer: async (offerId: string) => {
      const res = await apiClient.post(`/api/technician/offers/${offerId}/accept`);
      return res.data;
    },

    rejectOffer: async (offerId: string, reason: string) => {
      const res = await apiClient.post(`/api/technician/offers/${offerId}/reject`, { reason });
      return res.data;
    },

    getJobs: async (params?: { status?: string; limit?: number; offset?: number }): Promise<{ total: number; jobs: ServiceRequest[] }> => {
      const res = await apiClient.get('/api/technician/jobs', { params });
      return res.data;
    },

    getJob: async (jobId: string): Promise<ServiceRequest> => {
      const res = await apiClient.get<ServiceRequest>(`/api/technician/jobs/${jobId}`);
      return res.data;
    },

    updateJobStatus: async (jobId: string, status: 'en_route' | 'in_progress' | 'completed') => {
      const res = await apiClient.patch(`/api/technician/jobs/${jobId}/status`, { status });
      return res.data;
    },

    addJobNote: async (jobId: string, note: string) => {
      const res = await apiClient.post(`/api/technician/jobs/${jobId}/notes`, { note });
      return res.data;
    },

    getEarnings: async () => {
      const res = await apiClient.get('/api/technician/earnings');
      return res.data;
    },

    getRatings: async (): Promise<{ avg_rating: number; total: number; ratings: Rating[] }> => {
      const res = await apiClient.get('/api/technician/ratings');
      return res.data;
    },

    getNotifications: async (): Promise<{ total: number; notifications: NotificationItem[] }> => {
      const res = await apiClient.get('/api/technician/notifications');
      return res.data;
    },

    markNotificationRead: async (id: string) => {
      const res = await apiClient.patch(`/api/technician/notifications/${id}/read`);
      return res.data;
    },
  },

  // ── Admin APIs ─────────────────────────────────────────────────────────────
  admin: {
    getOverview: async (params?: { date_from?: string; date_to?: string }): Promise<AdminOverview> => {
      const res = await apiClient.get<AdminOverview>('/api/admin/dashboard/overview', { params });
      return res.data;
    },

    getDispatchMetrics: async (params?: { date_from?: string; date_to?: string }): Promise<DispatchMetrics> => {
      const res = await apiClient.get<DispatchMetrics>('/api/admin/dashboard/dispatch', { params });
      return res.data;
    },

    getWorkload: async (): Promise<{ technicians: TechnicianWorkloadItem[] }> => {
      const res = await apiClient.get('/api/admin/dashboard/workload');
      return res.data;
    },

    getSLAStats: async (params?: { date_from?: string; date_to?: string }): Promise<SLAStats> => {
      const res = await apiClient.get<SLAStats>('/api/admin/dashboard/sla', { params });
      return res.data;
    },

    getFeedbackStats: async (params?: { date_from?: string; date_to?: string }): Promise<FeedbackStats> => {
      const res = await apiClient.get<FeedbackStats>('/api/admin/dashboard/feedback', { params });
      return res.data;
    },

    getRevenueStats: async (params?: { date_from?: string; date_to?: string }): Promise<RevenueStats> => {
      const res = await apiClient.get<RevenueStats>('/api/admin/dashboard/revenue', { params });
      return res.data;
    },

    getDemandStats: async (params?: { date_from?: string; date_to?: string }): Promise<DemandStats> => {
      const res = await apiClient.get<DemandStats>('/api/admin/dashboard/demand', { params });
      return res.data;
    },

    // Customers CRUD
    getCustomers: async (params?: { search?: string; is_active?: boolean; limit?: number; offset?: number }) => {
      const res = await apiClient.get('/api/admin/customers', { params });
      return res.data;
    },

    getCustomer: async (customerId: string) => {
      const res = await apiClient.get(`/api/admin/customers/${customerId}`);
      return res.data;
    },

    updateCustomer: async (customerId: string, payload: { name?: string; is_active?: boolean }) => {
      const res = await apiClient.patch(`/api/admin/customers/${customerId}`, payload);
      return res.data;
    },

    // Technicians CRUD
    getTechnicians: async (params?: {
      search?: string;
      is_online?: boolean;
      is_approved?: boolean;
      is_suspended?: boolean;
      limit?: number;
      offset?: number;
    }) => {
      const res = await apiClient.get('/api/admin/technicians', { params });
      return res.data;
    },

    getTechnician: async (techId: string) => {
      const res = await apiClient.get(`/api/admin/technicians/${techId}`);
      return res.data;
    },

    updateTechnician: async (techId: string, payload: Partial<TechnicianProfile>) => {
      const res = await apiClient.patch(`/api/admin/technicians/${techId}`, payload);
      return res.data;
    },

    approveTechnician: async (techId: string) => {
      const res = await apiClient.patch(`/api/admin/technicians/${techId}/approve`);
      return res.data;
    },

    suspendTechnician: async (techId: string) => {
      const res = await apiClient.patch(`/api/admin/technicians/${techId}/suspend`);
      return res.data;
    },

    // Jobs CRUD
    getJobs: async (params?: {
      status?: string;
      urgency?: string;
      category_id?: string;
      date_from?: string;
      date_to?: string;
      limit?: number;
      offset?: number;
    }) => {
      const res = await apiClient.get('/api/admin/jobs', { params });
      return res.data;
    },

    getJob: async (jobId: string): Promise<ServiceRequest> => {
      const res = await apiClient.get<ServiceRequest>(`/api/admin/jobs/${jobId}`);
      return res.data;
    },

    assignJob: async (jobId: string, technicianProfileId: string) => {
      const res = await apiClient.patch(`/api/admin/jobs/${jobId}/assign`, {
        technician_profile_id: technicianProfileId,
      });
      return res.data;
    },

    reassignJob: async (jobId: string) => {
      const res = await apiClient.patch(`/api/admin/jobs/${jobId}/reassign`);
      return res.data;
    },

    cancelJob: async (jobId: string) => {
      const res = await apiClient.patch(`/api/admin/jobs/${jobId}/cancel`);
      return res.data;
    },

    // Configuration: SLA Tiers
    getSLATiers: async (): Promise<SLATier[]> => {
      const res = await apiClient.get<SLATier[]>('/api/admin/config/sla-tiers');
      return res.data;
    },

    createSLATier: async (payload: Omit<SLATier, 'id'>) => {
      const res = await apiClient.post('/api/admin/config/sla-tiers', payload);
      return res.data;
    },

    updateSLATier: async (id: string, payload: Partial<SLATier>) => {
      const res = await apiClient.patch(`/api/admin/config/sla-tiers/${id}`, payload);
      return res.data;
    },

    deleteSLATier: async (id: string) => {
      const res = await apiClient.delete(`/api/admin/config/sla-tiers/${id}`);
      return res.data;
    },

    // Configuration: Matching
    getMatchingConfig: async (): Promise<MatchingConfig> => {
      const res = await apiClient.get<MatchingConfig>('/api/admin/config/matching');
      return res.data;
    },

    updateMatchingConfig: async (payload: Partial<MatchingConfig>) => {
      const res = await apiClient.patch('/api/admin/config/matching', payload);
      return res.data;
    },

    // Configuration: Categories
    getCategories: async (): Promise<ServiceCategory[]> => {
      const res = await apiClient.get<ServiceCategory[]>('/api/admin/config/categories');
      return res.data;
    },

    createCategory: async (payload: Partial<ServiceCategory>) => {
      const res = await apiClient.post('/api/admin/config/categories', payload);
      return res.data;
    },

    updateCategory: async (id: string, payload: Partial<ServiceCategory>) => {
      const res = await apiClient.patch(`/api/admin/config/categories/${id}`, payload);
      return res.data;
    },

    deleteCategory: async (id: string) => {
      const res = await apiClient.delete(`/api/admin/config/categories/${id}`);
      return res.data;
    },

    // Audit Log
    getAuditLog: async (params?: { entity_type?: string; action?: string; limit?: number; offset?: number }): Promise<{ total: number; entries: AuditLogEntry[] }> => {
      const res = await apiClient.get('/api/admin/audit-log', { params });
      return res.data;
    },

    // Export CSV URLs
    getJobsExportUrl: () => `${API_BASE_URL}/api/admin/export/jobs`,
    getTechniciansExportUrl: () => `${API_BASE_URL}/api/admin/export/technicians`,
  },
};

