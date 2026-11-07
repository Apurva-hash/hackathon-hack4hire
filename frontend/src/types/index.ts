// Domain Types for DispatchGrid v2

export type UserRole = 'admin' | 'technician' | 'customer';

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  phone?: string;
  technicianId?: string;
  token?: string;
}

export type RequestStatus =
  | 'requested'
  | 'matching'
  | 'assigned'
  | 'accepted'
  | 'en_route'
  | 'in_progress'
  | 'completed'
  | 'cancelled'
  | 'escalated';

export type RequestUrgency = 'critical' | 'high' | 'normal' | 'low' | 'emergency' | 'urgent';

export type OfferStatus = 'pending' | 'accepted' | 'rejected' | 'expired';

export interface ServiceCategory {
  id: string;
  name: string;
  description?: string;
  icon?: string;
  price_per_minute: number;
  required_certification_level: number;
  is_active?: boolean;
  skill_id?: string;
}

export interface SLATier {
  id: string;
  name: string;
  priority_level: number;
  response_time_minutes: number;
  resolution_time_minutes: number;
  is_default: boolean;
}

export interface SavedAddress {
  label: string;
  address: string;
  lat: number;
  lng: number;
}

export interface CustomerProfile {
  id: string;
  user_id: string;
  email: string;
  name: string;
  phone?: string;
  avg_rating: number;
  total_bookings: number;
  saved_addresses: SavedAddress[];
}

export interface TechnicianProfile {
  id: string;
  user_id: string;
  email: string;
  name: string;
  phone?: string;
  bio?: string;
  is_online: boolean;
  is_approved: boolean;
  is_suspended: boolean;
  lat?: number;
  lng?: number;
  service_radius_km: number;
  max_concurrent_jobs: number;
  certification_level: number;
  avg_rating: number;
  rating?: number;
  total_jobs_completed: number;
  total_jobs_rejected: number;
  acceptance_rate: number;
  total_earnings: number;
  active_jobs_count?: number;
  user?: {
    name: string;
    email: string;
  };
}

export interface NearbyTechnician {
  id: string;
  name: string;
  avg_rating: number;
  certification_level: number;
  distance_km: number;
  eta_minutes: number;
}

export interface ServiceRequest {
  id: string;
  status: RequestStatus;
  urgency: RequestUrgency;
  category_id: string;
  category_name?: string;
  category?: ServiceCategory;
  description?: string;
  address: string;
  lat: number;
  lng: number;
  estimated_price?: number;
  sla_status?: 'ok' | 'at_risk' | 'breached';
  sla_deadline?: string;
  sla_response_deadline?: string;
  sla_resolution_deadline?: string;
  sla_response_met?: boolean;
  sla_resolution_met?: boolean;
  preferred_time_start?: string;
  preferred_time_end?: string;
  completed_at?: string;
  completion_notes?: string;
  created_at: string;
  customer_id?: string;
  assigned_technician_id?: string;
  offer_attempt?: number;
  offer_attempts?: number;
  escalated?: boolean;
  assigned_technician?: {
    id: string;
    name: string;
    phone?: string;
    avg_rating: number;
    certification_level: number;
  };
  offers?: JobOfferSummary[];
}

export interface JobOfferSummary {
  id: string;
  technician_id: string;
  status: OfferStatus;
  attempt_number: number;
  offered_at?: string;
  rejection_reason?: string;
}

export interface TechnicianJobOffer {
  offer_id: string;
  expires_at: string;
  attempt_number: number;
  service_request: ServiceRequest;
}

export interface Rating {
  id: string;
  score: number;
  feedback_text?: string;
  technician_id?: string;
  technician_profile_id?: string;
  service_request_id: string;
  created_at: string;
}

export type NotificationType =
  | 'job_assigned'
  | 'offer_received'
  | 'offer_accepted'
  | 'offer_rejected'
  | 'status_changed'
  | 'sla_at_risk'
  | 'sla_breached'
  | 'job_completed'
  | 'job_cancelled'
  | 'new_rating'
  | 'admin_action'
  | 'system';

export interface NotificationItem {
  id: string;
  type: NotificationType;
  title: string;
  body: string;
  is_read: boolean;
  entity_type?: string;
  entity_id?: string;
  created_at: string;
}

export interface MatchingConfig {
  weight_distance: number;
  weight_rating: number;
  weight_workload: number;
  weight_skill_level: number;
  weight_acceptance_rate: number;
  offer_timeout_seconds: number;
  max_offer_attempts: number;
  high_risk_min_certification: number;
  high_risk_wider_radius_km: number;
  high_risk_offer_timeout_seconds: number;
}

export interface AdminOverview {
  customers: { total: number };
  technicians: {
    total: number;
    online: number;
    offline: number;
    approved: number;
    suspended: number;
  };
  jobs: {
    total: number;
    by_status: Record<string, number>;
    escalated: number;
  };
  oldest_pending?: {
    id: string;
    created_at?: string;
    age_hours?: number;
  } | null;
}

export interface DispatchMetrics {
  total_offers: number;
  accepted: number;
  rejected: number;
  expired: number;
  reassignment_count: number;
  assignment_rate_pct: number;
  acceptance_rate_pct: number;
  rejection_rate_pct: number;
  avg_time_to_assign_minutes?: number | null;
}

export interface TechnicianWorkloadItem {
  technician_id: string;
  name: string;
  is_online: boolean;
  active_jobs: number;
  max_concurrent_jobs: number;
  utilization_pct: number;
  capacity_left: number;
  total_completed: number;
  avg_rating: number;
}

export interface SLAStats {
  compliance_pct: number;
  at_risk_count: number;
  breached_count: number;
  avg_response_minutes?: number | null;
  avg_resolution_minutes?: number | null;
  total_evaluated: number;
}

export interface FeedbackStats {
  total_reviews: number;
  avg_rating?: number | null;
  distribution: Record<string, number>;
  low_rating_count: number;
  recent_reviews: Rating[];
}

export interface RevenueStats {
  total_revenue: number;
  total_completed_jobs: number;
  top_earning_technicians: {
    id: string;
    name: string;
    total_earnings: number;
    total_jobs_completed: number;
    avg_rating: number;
  }[];
}

export interface DemandStats {
  by_hour: { hour: number; count: number }[];
  by_category: { category: string; count: number }[];
  by_urgency: Record<string, number>;
}

export interface AuditLogEntry {
  id: string;
  admin_user_id?: string;
  action: string;
  entity_type: string;
  entity_id?: string;
  old_value?: any;
  new_value?: any;
  occurred_at: string;
}

// ── Legacy Phase 1-7 Types (Maintained for backward compatibility) ───────────
export type JobPriority = 'critical' | 'high' | 'medium' | 'low';
export type JobStatus = 'pending' | 'assigned' | 'in_progress' | 'completed' | 'cancelled' | 'unassigned';
export type TechnicianStatus = 'available' | 'busy' | 'off_duty';
export type AssignmentStatus = 'pending' | 'in_progress' | 'completed';

export interface Skill {
  id: string;
  name: string;
  description?: string;
}

export interface ServiceZone {
  id: string;
  name: string;
  code?: string;
  center_lat?: number;
  center_lng?: number;
  radius_km?: number;
}

export interface Technician {
  id: string;
  name: string;
  email?: string;
  phone?: string;
  status: TechnicianStatus;
  current_location?: string;
  shift_start: string;
  shift_end: string;
  skills: Skill[];
  service_zones: ServiceZone[];
  assignments?: Assignment[];
}

export interface Job {
  id: string;
  title: string;
  description?: string;
  location: string;
  service_zone_id: string;
  service_zone?: ServiceZone;
  duration_minutes: number;
  time_window_start: string;
  time_window_end: string;
  sla_deadline: string;
  priority: JobPriority;
  status: JobStatus;
  required_skills: Skill[];
  assignment?: Assignment;
  created_at?: string;
  updated_at?: string;
}

export interface Assignment {
  id: string;
  job_id: string;
  technician_id: string;
  scheduled_start: string;
  scheduled_end: string;
  travel_before_minutes: number;
  status: AssignmentStatus;
  run_id?: string;
  job?: Job;
  technician?: Technician;
  job_title?: string;
  job_location?: string;
  job_priority?: JobPriority;
  technician_name?: string;
}

export interface DisruptionEvent {
  id: string;
  event_type: 'technician_unavailable' | 'urgent_job' | 'duration_change' | 'job_cancellation' | 'early_completion' | 'late_completion';
  affected_entity_type: 'technician' | 'job';
  affected_entity_id: string;
  event_time: string;
  payload?: string;
  processed_run_id?: string;
  created_at: string;
}

export interface DashboardOverview {
  total_jobs: number;
  total_technicians: number;
  total_assignments: number;
  jobs_by_status: { status: string; count: number }[];
  jobs_by_priority: { priority: string; count: number; assigned: number; unassigned: number }[];
  coverage_pct: number;
  sla_at_risk_count: number;
  last_run_id?: string;
  last_run_timestamp?: string;
  last_run_score?: number;
}

export interface ScheduleAssignmentItem {
  assignment_id: string;
  job_id: string;
  job_title: string;
  job_location: string;
  job_priority: string;
  technician_id: string;
  technician_name: string;
  scheduled_start: string;
  scheduled_end: string;
  travel_before_minutes: number;
  status: string;
}

export interface TechnicianWorkload {
  technician_id: string;
  technician_name: string;
  status: string;
  assignments_today: number;
  total_scheduled_minutes: number;
  utilization_pct: number;
  next_job_start?: string;
}

export interface PerformanceKPIs {
  total_scheduling_runs: number;
  avg_objective_score?: number;
  avg_sla_violations?: number;
  avg_travel_minutes?: number;
  best_run_id?: string;
  best_score?: number;
  recent_runs: any[];
}

export interface AlertItem {
  alert_id: string;
  severity: 'critical' | 'warning' | 'info';
  category: 'sla' | 'unassigned' | 'technician';
  message: string;
  entity_id?: string;
  entity_type?: string;
  created_at: string;
}

export interface SchedulingRun {
  id: string;
  timestamp?: string;
  status: string;
  algorithm_used: string;
  objective_score?: number;
  total_travel_minutes?: number;
  sla_violations?: number;
  unassigned_high_priority?: number;
  trigger_type: string;
}

export interface SchedulingDecision {
  job_id: string;
  technician_id?: string;
  scheduled_start?: string;
  feasibility?: string;
  selected_score?: number;
  candidate_count?: number;
  rejection_reason?: string;
  explanation_text?: string;
}
