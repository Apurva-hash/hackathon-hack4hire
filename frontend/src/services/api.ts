import axios from 'axios';
import { API_BASE_URL, getToken } from './apiClient';
import {
  Job,
  Technician,
  Skill,
  ServiceZone,
  Assignment,
  DisruptionEvent,
  DashboardOverview,
  ScheduleAssignmentItem,
  TechnicianWorkload,
  PerformanceKPIs,
  AlertItem,
  SchedulingRun,
} from '../types';

const API = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor: attach bearer token
API.interceptors.request.use((config) => {
  const token = getToken();
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor for consistent error extraction
API.interceptors.response.use(
  (response) => response,
  (error) => {
    let message = 'An error occurred';
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string') {
      message = detail;
    } else if (Array.isArray(detail)) {
      message = detail.map((d: any) => d.msg || JSON.stringify(d)).join('; ');
    } else if (detail && typeof detail === 'object') {
      message = JSON.stringify(detail);
    } else if (error.message) {
      message = error.message;
    }
    return Promise.reject(new Error(message));
  }
);

export const apiService = {
  // Health
  checkHealth: async () => {
    const res = await API.get('/health');
    return res.data;
  },

  // Jobs
  getJobs: async (params?: { status?: string; priority?: string; skip?: number; limit?: number }) => {
    const res = await API.get<{ total: number; jobs: Job[] }>('/jobs', { params });
    return res.data;
  },

  getJobById: async (id: string) => {
    const res = await API.get<Job>(`/jobs/${id}`);
    return res.data;
  },

  createJob: async (jobData: {
    title: string;
    description?: string;
    location: string;
    service_zone_id: string;
    duration_minutes: number;
    time_window_start: string;
    time_window_end: string;
    sla_deadline: string;
    priority?: string;
    required_skill_ids?: string[];
  }) => {
    const res = await API.post<Job>('/jobs/', jobData);
    return res.data;
  },

  updateJob: async (id: string, updates: Partial<Job>) => {
    const res = await API.patch<Job>(`/jobs/${id}`, updates);
    return res.data;
  },

  cancelJob: async (id: string) => {
    const res = await API.post<Job>(`/jobs/${id}/cancel`);
    return res.data;
  },

  // Technicians
  getTechnicians: async (params?: { status?: string; zone_id?: string; skip?: number; limit?: number }) => {
    const res = await API.get<{ total: number; technicians: Technician[] }>('/technicians', { params });
    return res.data;
  },

  getTechnicianById: async (id: string) => {
    const res = await API.get<Technician>(`/technicians/${id}`);
    return res.data;
  },

  createTechnician: async (techData: {
    name: string;
    email?: string;
    phone?: string;
    current_location?: string;
    shift_start: string;
    shift_end: string;
    skill_ids?: string[];
    service_zone_ids?: string[];
  }) => {
    const res = await API.post<Technician>('/technicians', techData);
    return res.data;
  },

  updateTechnician: async (id: string, techData: {
    name?: string;
    email?: string;
    phone?: string;
    current_location?: string;
    shift_start?: string;
    shift_end?: string;
    status?: string;
    skill_ids?: string[];
    service_zone_ids?: string[];
  }) => {
    const res = await API.patch<Technician>(`/technicians/${id}`, techData);
    return res.data;
  },

  updateTechnicianStatus: async (id: string, status: 'available' | 'busy' | 'off_duty') => {
    const res = await API.patch<Technician>(`/technicians/${id}`, { status });
    return res.data;
  },

  deleteTechnician: async (id: string) => {
    await API.delete(`/technicians/${id}`);
  },

  getTechniciansBySkill: async (skillName: string) => {
    const res = await API.get<Technician[]>('/technicians/by-skill', { params: { skill_name: skillName } });
    return res.data;
  },

  // Skills & Zones
  getSkills: async () => {
    const res = await API.get<Skill[]>('/skills');
    return res.data;
  },

  getServiceZones: async () => {
    const res = await API.get<ServiceZone[]>('/service-zones');
    return res.data;
  },

  // Assignments
  getAssignments: async (params?: { status?: string; run_id?: string; limit?: number }) => {
    const res = await API.get<Assignment[]>('/assignments/', { params });
    return res.data;
  },

  getTechnicianAssignments: async (technicianId: string) => {
    const res = await API.get<Assignment[]>(`/assignments/technician/${technicianId}`);
    return res.data;
  },

  updateAssignment: async (id: string, updates: { status?: string; scheduled_start?: string; scheduled_end?: string }) => {
    const res = await API.patch<Assignment>(`/assignments/${id}`, updates);
    return res.data;
  },

  deleteAssignment: async (id: string) => {
    const res = await API.delete(`/assignments/${id}`);
    return res.data;
  },

  // Scheduling Engine
  runScheduling: async (payload: {
    algorithm?: 'auto' | 'greedy' | 'alns';
    use_alns?: boolean;
    max_iterations?: number;
    job_ids?: string[];
    technician_ids?: string[];
  }) => {
    const res = await API.post('/scheduling/run', {
      algorithm: payload.algorithm || 'auto',
      use_alns: payload.use_alns !== false,
      max_iterations: payload.max_iterations || 50,
      ...payload,
    });
    return res.data;
  },

  getSchedulingRuns: async (limit: number = 10) => {
    const res = await API.get<SchedulingRun[]>('/scheduling/runs', { params: { limit } });
    return res.data;
  },

  getSchedulingRunDetails: async (runId: string) => {
    const res = await API.get(`/scheduling/runs/${runId}`);
    return res.data;
  },

  compareRuns: async (runId1: string, runId2: string) => {
    const res = await API.get(`/scheduling/compare/${runId1}/vs/${runId2}`);
    return res.data;
  },

  // Disruptions
  getDisruptions: async (params?: { limit?: number; processed?: boolean }) => {
    const res = await API.get<DisruptionEvent[]>('/disruptions/', { params });
    return res.data;
  },

  getDisruptionStats: async () => {
    const res = await API.get<{
      total_disruptions: number;
      processed: number;
      unprocessed: number;
      by_type: Record<string, number>;
    }>('/disruptions/stats');
    return res.data;
  },

  reportDisruption: async (payload: {
    event_type: string;
    affected_entity_type: 'technician' | 'job';
    affected_entity_id: string;
    payload?: Record<string, any>;
  }) => {
    const res = await API.post<DisruptionEvent>('/disruptions/', payload);
    return res.data;
  },

  processDisruption: async (disruptionId: string) => {
    const res = await API.post<{
      disruption_id: string;
      run_id?: string;
      status: string;
      message: string;
      jobs_reassigned: number;
      jobs_unassigned: number;
    }>(`/disruptions/${disruptionId}/process`);
    return res.data;
  },

  // Dashboard Analytics
  getOverview: async () => {
    const res = await API.get<DashboardOverview>('/dashboard/overview');
    return res.data;
  },

  getSchedule: async (dateStr?: string) => {
    const res = await API.get<ScheduleAssignmentItem[]>('/dashboard/schedule', {
      params: dateStr ? { target_date: dateStr } : undefined,
    });
    return res.data;
  },

  getTechnicianWorkloads: async (dateStr?: string) => {
    const res = await API.get<TechnicianWorkload[]>('/dashboard/technicians', {
      params: dateStr ? { target_date: dateStr } : undefined,
    });
    return res.data;
  },

  getPerformanceKPIs: async () => {
    const res = await API.get<PerformanceKPIs>('/dashboard/performance');
    return res.data;
  },

  getUnassignedJobs: async () => {
    const res = await API.get<any[]>('/dashboard/jobs/unassigned');
    return res.data;
  },

  getAlerts: async () => {
    const res = await API.get<AlertItem[]>('/dashboard/alerts');
    return res.data;
  },
};
