import React, { useState, useEffect } from 'react';
import { api } from '../../services/apiClient';
import { ServiceRequest, TechnicianProfile } from '../../types';
import { Card } from '../../components/common/Card';
import { Button } from '../../components/common/Button';
import { StatusBadge, Badge } from '../../components/common/Badge';
import { Drawer } from '../../components/common/Drawer';
import { Modal } from '../../components/common/Modal';
import { Skeleton } from '../../components/common/Skeleton';
import { EmptyState } from '../../components/common/EmptyState';
import { useToast } from '../../components/common/Toast';
import {
  AlertTriangleIcon,
  ClockIcon,
  RefreshCwIcon,
  SearchIcon,
  CheckIcon,
  UserIcon,
  WrenchIcon,
  MapPinIcon,
} from '../../components/common/Icons';

export const Escalations: React.FC = () => {
  const { success, error: toastError, warning } = useToast();

  const [jobs, setJobs] = useState<ServiceRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [urgencyFilter, setUrgencyFilter] = useState<'all' | 'emergency' | 'urgent' | 'normal'>('all');
  const [slaFilter, setSlaFilter] = useState<'all' | 'breached' | 'at_risk'>('all');

  // Selected job for detail drawer & assignment
  const [selectedJob, setSelectedJob] = useState<ServiceRequest | null>(null);
  const [technicians, setTechnicians] = useState<TechnicianProfile[]>([]);
  const [selectedTechId, setSelectedTechId] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  // Cancellation modal
  const [cancelModalOpen, setCancelModalOpen] = useState(false);
  const [jobToCancel, setJobToCancel] = useState<string | null>(null);

  const fetchEscalations = async () => {
    setLoading(true);
    try {
      // Fetch active jobs (pending, matching, requested)
      const res = await api.admin.getJobs({ limit: 50 });
      const allJobs = res.jobs || [];

      // Filter to jobs that are escalated, breached, at-risk, or high-risk unassigned
      const escalatedList = allJobs.filter((j: ServiceRequest) => {
        const isEscalated = (j as any).escalated === true;
        const isBreached = j.sla_status === 'breached';
        const isAtRisk = j.sla_status === 'at_risk';
        const isEmergencyPending = (j.urgency === 'emergency' || j.urgency === 'urgent') && ['requested', 'matching'].includes(j.status);
        const hasHighAttempts = ((j as any).offer_attempts || 0) >= 2;

        return isEscalated || isBreached || isAtRisk || isEmergencyPending || hasHighAttempts;
      });

      setJobs(escalatedList);
    } catch (err: any) {
      toastError('Failed to load escalations', err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchTechnicians = async () => {
    try {
      const res = await api.admin.getTechnicians({ is_online: true, is_approved: true, limit: 20 });
      setTechnicians(res.technicians || []);
      if (res.technicians?.length > 0) {
        setSelectedTechId(res.technicians[0].id);
      }
    } catch (err: any) {
      console.error('Failed to load technicians:', err);
    }
  };

  useEffect(() => {
    fetchEscalations();
    fetchTechnicians();
  }, []);

  const handleManualAssign = async () => {
    if (!selectedJob || !selectedTechId) return;
    setActionLoading(true);
    try {
      await api.admin.assignJob(selectedJob.id, selectedTechId);
      success('Job Assigned', `Job ${selectedJob.id.slice(0, 8)} manually assigned to technician.`);
      setSelectedJob(null);
      fetchEscalations();
    } catch (err: any) {
      toastError('Assignment Failed', err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleReassign = async (jobId: string) => {
    setActionLoading(true);
    try {
      await api.admin.reassignJob(jobId);
      success('Re-Dispatch Triggered', 'Job has been placed back into the dispatch matching engine.');
      if (selectedJob?.id === jobId) setSelectedJob(null);
      fetchEscalations();
    } catch (err: any) {
      toastError('Re-Dispatch Failed', err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancelJob = async () => {
    if (!jobToCancel) return;
    setActionLoading(true);
    try {
      await api.admin.cancelJob(jobToCancel);
      warning('Job Cancelled', `Escalated job ${jobToCancel.slice(0, 8)} was cancelled by admin.`);
      setCancelModalOpen(false);
      setJobToCancel(null);
      if (selectedJob?.id === jobToCancel) setSelectedJob(null);
      fetchEscalations();
    } catch (err: any) {
      toastError('Cancellation Failed', err.message);
    } finally {
      setActionLoading(false);
    }
  };

  // Filtered list
  const filteredJobs = jobs.filter((j) => {
    const matchesSearch =
      searchTerm === '' ||
      j.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (j.category?.name && j.category.name.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (j.category_name && j.category_name.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (j.description && j.description.toLowerCase().includes(searchTerm.toLowerCase()));

    const matchesUrgency = urgencyFilter === 'all' || j.urgency === urgencyFilter;

    const matchesSla =
      slaFilter === 'all' ||
      (slaFilter === 'breached' && j.sla_status === 'breached') ||
      (slaFilter === 'at_risk' && j.sla_status === 'at_risk');

    return matchesSearch && matchesUrgency && matchesSla;
  });

  const breachedCount = jobs.filter((j) => j.sla_status === 'breached').length;
  const atRiskCount = jobs.filter((j) => j.sla_status === 'at_risk').length;
  const emergencyCount = jobs.filter((j) => j.urgency === 'emergency').length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-text">Escalation Inbox</h1>
            <Badge variant="error" size="sm">
              <AlertTriangleIcon className="w-3.5 h-3.5" />
              <span>{jobs.length} Incidents</span>
            </Badge>
          </div>
          <p className="text-xs text-text-muted mt-1">
            Prioritize and resolve jobs with failed offer cycles, SLA breaches, or high-risk urgency.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={fetchEscalations}
            disabled={loading}
            className="flex items-center gap-2 min-h-[44px]"
          >
            <RefreshCwIcon className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </Button>
        </div>
      </div>

      {/* KPI Stats Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="p-4 border-l-4 border-l-status-breached">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-text-muted">
            Total Escalated
          </div>
          <div className="text-2xl font-extrabold text-status-breached mt-1">{jobs.length}</div>
          <p className="text-[11px] text-text-muted mt-1">Awaiting dispatch resolution</p>
        </Card>

        <Card className="p-4 border-l-4 border-l-status-breached">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-text-muted">
            SLA Breached
          </div>
          <div className="text-2xl font-extrabold text-status-breached mt-1">{breachedCount}</div>
          <p className="text-[11px] text-text-muted mt-1">Past target resolution deadline</p>
        </Card>

        <Card className="p-4 border-l-4 border-l-status-pending">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-text-muted">
            At Risk SLA
          </div>
          <div className="text-2xl font-extrabold text-status-pending mt-1">{atRiskCount}</div>
          <p className="text-[11px] text-text-muted mt-1">&gt;80% of window elapsed</p>
        </Card>

        <Card className="p-4 border-l-4 border-l-primary">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-text-muted">
            Emergency Urgency
          </div>
          <div className="text-2xl font-extrabold text-primary mt-1">{emergencyCount}</div>
          <p className="text-[11px] text-text-muted mt-1">Shortest dispatch timeouts</p>
        </Card>
      </div>

      {/* Search and Filters */}
      <Card className="p-4">
        <div className="flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
          <div className="relative flex-1">
            <SearchIcon className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-text-muted" />
            <input
              type="text"
              placeholder="Search by Job ID, category, or problem description..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 bg-bg border border-border rounded-input text-xs text-text placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-primary min-h-[44px]"
            />
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <select
              value={urgencyFilter}
              onChange={(e) => setUrgencyFilter(e.target.value as any)}
              className="px-3 py-2 bg-bg border border-border rounded-input text-xs text-text focus:outline-none focus:ring-2 focus:ring-primary min-h-[44px]"
            >
              <option value="all">All Urgencies</option>
              <option value="emergency">Emergency</option>
              <option value="urgent">Urgent</option>
              <option value="normal">Normal</option>
            </select>

            <select
              value={slaFilter}
              onChange={(e) => setSlaFilter(e.target.value as any)}
              className="px-3 py-2 bg-bg border border-border rounded-input text-xs text-text focus:outline-none focus:ring-2 focus:ring-primary min-h-[44px]"
            >
              <option value="all">All SLA States</option>
              <option value="breached">Breached Only</option>
              <option value="at_risk">At Risk Only</option>
            </select>
          </div>
        </div>
      </Card>

      {/* Escalation Incidents List */}
      <Card className="overflow-hidden">
        {loading ? (
          <div className="p-6 space-y-4">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-14 w-full" />
            <Skeleton className="h-14 w-full" />
            <Skeleton className="h-14 w-full" />
          </div>
        ) : filteredJobs.length === 0 ? (
          <EmptyState
            title="No Active Escalations"
            description={
              searchTerm || urgencyFilter !== 'all' || slaFilter !== 'all'
                ? 'No escalated jobs match the active filters.'
                : 'All jobs are smoothly being processed within SLA targets.'
            }
            actionLabel="Reset Filters"
            onAction={() => {
              setSearchTerm('');
              setUrgencyFilter('all');
              setSlaFilter('all');
            }}
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-surface-alt border-b border-border text-[10px] text-text-muted uppercase tracking-wider">
                  <th className="py-3.5 px-4 font-semibold">Job ID</th>
                  <th className="py-3.5 px-4 font-semibold">Urgency & SLA</th>
                  <th className="py-3.5 px-4 font-semibold">Category & Issue</th>
                  <th className="py-3.5 px-4 font-semibold">Status</th>
                  <th className="py-3.5 px-4 font-semibold">Attempts</th>
                  <th className="py-3.5 px-4 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filteredJobs.map((job) => {
                  const isBreached = job.sla_status === 'breached';
                  const isAtRisk = job.sla_status === 'at_risk';

                  return (
                    <tr
                      key={job.id}
                      className="hover:bg-surface-alt/60 transition cursor-pointer"
                      onClick={() => setSelectedJob(job)}
                    >
                      <td className="py-3.5 px-4 font-mono font-bold text-text">
                        <span className="text-primary hover:underline">
                          #{job.id.slice(0, 8)}
                        </span>
                      </td>

                      <td className="py-3.5 px-4 space-y-1">
                        <div className="flex items-center gap-1.5">
                          <StatusBadge status={job.urgency || 'normal'} size="sm" />
                          {isBreached && (
                            <Badge variant="error" size="sm">
                              <AlertTriangleIcon className="w-3 h-3" />
                              <span>Breached</span>
                            </Badge>
                          )}
                          {isAtRisk && !isBreached && (
                            <Badge variant="warning" size="sm">
                              <ClockIcon className="w-3 h-3" />
                              <span>At Risk</span>
                            </Badge>
                          )}
                        </div>
                        {job.sla_deadline && (
                          <div className="text-[10px] text-text-muted flex items-center gap-1">
                            <ClockIcon className="w-3 h-3 text-status-breached" />
                            <span>Due: {new Date(job.sla_deadline).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                          </div>
                        )}
                      </td>

                      <td className="py-3.5 px-4 max-w-xs">
                        <div className="font-semibold text-text">{job.category?.name || 'General Service'}</div>
                        <p className="text-[11px] text-text-muted truncate mt-0.5">{job.description}</p>
                      </td>

                      <td className="py-3.5 px-4">
                        <StatusBadge status={job.status} size="sm" />
                      </td>

                      <td className="py-3.5 px-4">
                        <span className="font-mono text-xs px-2 py-0.5 rounded-full bg-surface-alt border border-border">
                          {(job as any).offer_attempts || 0} cycles
                        </span>
                      </td>

                      <td className="py-3.5 px-4 text-right" onClick={(e) => e.stopPropagation()}>
                        <div className="flex items-center justify-end gap-1.5">
                          <Button
                            variant="secondary"
                            size="sm"
                            className="min-h-[36px] text-xs px-2.5"
                            onClick={() => setSelectedJob(job)}
                          >
                            Triage
                          </Button>
                          <Button
                            variant="primary"
                            size="sm"
                            className="min-h-[36px] text-xs px-2.5"
                            onClick={() => handleReassign(job.id)}
                            disabled={actionLoading}
                          >
                            Re-Dispatch
                          </Button>
                          <Button
                            variant="danger"
                            size="sm"
                            className="min-h-[36px] text-xs px-2"
                            onClick={() => {
                              setJobToCancel(job.id);
                              setCancelModalOpen(true);
                            }}
                            title="Cancel Job"
                          >
                            Cancel
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Triage & Manual Assignment Drawer */}
      <Drawer
        isOpen={!!selectedJob}
        onClose={() => setSelectedJob(null)}
        title={selectedJob ? `Triage Incident #${selectedJob.id.slice(0, 8)}` : 'Incident Details'}
        size="lg"
      >
        {selectedJob && (
          <div className="space-y-6">
            {/* Status & Alerts */}
            <div className="p-4 rounded-card bg-surface-alt border border-border space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-text-muted font-medium">Job Status</span>
                <StatusBadge status={selectedJob.status} />
              </div>

              <div className="flex items-center justify-between">
                <span className="text-xs text-text-muted font-medium">Urgency Tier</span>
                <StatusBadge status={selectedJob.urgency || 'normal'} />
              </div>

              <div className="flex items-center justify-between">
                <span className="text-xs text-text-muted font-medium">SLA Compliance</span>
                {selectedJob.sla_status === 'breached' ? (
                  <Badge variant="error" size="sm">Breached Deadline</Badge>
                ) : selectedJob.sla_status === 'at_risk' ? (
                  <Badge variant="warning" size="sm">At Risk (&gt;80% used)</Badge>
                ) : (
                  <Badge variant="success" size="sm">Within Limits</Badge>
                )}
              </div>

              {selectedJob.sla_deadline && (
                <div className="flex items-center justify-between text-xs pt-1 border-t border-border">
                  <span className="text-text-muted">Target Resolution</span>
                  <span className="font-semibold text-text">
                    {new Date(selectedJob.sla_deadline).toLocaleString()}
                  </span>
                </div>
              )}
            </div>

            {/* Problem Details */}
            <div className="space-y-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-text-muted">Problem Scope</h3>
              <div className="p-3.5 rounded-card bg-surface border border-border space-y-2">
                <div className="flex items-center gap-2 text-xs font-bold text-text">
                  <WrenchIcon className="w-4 h-4 text-primary" />
                  <span>{selectedJob.category?.name || 'General'}</span>
                </div>
                <p className="text-xs text-text leading-relaxed">{selectedJob.description}</p>
                {selectedJob.address && (
                  <div className="flex items-center gap-1.5 text-xs text-text-muted pt-2 border-t border-border">
                    <MapPinIcon className="w-3.5 h-3.5 text-primary" />
                    <span>{selectedJob.address}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Manual Assignment Form */}
            <div className="space-y-3 pt-2 border-t border-border">
              <h3 className="text-xs font-bold uppercase tracking-wider text-text">
                Manual Override Assignment
              </h3>
              <p className="text-xs text-text-muted">
                Directly force-assign this job to any approved technician currently online:
              </p>

              {technicians.length === 0 ? (
                <div className="p-3 bg-surface-alt rounded-card text-xs text-text-muted text-center">
                  No online technicians currently available.
                </div>
              ) : (
                <div className="space-y-2">
                  <select
                    value={selectedTechId}
                    onChange={(e) => setSelectedTechId(e.target.value)}
                    className="w-full px-3 py-2.5 bg-bg border border-border rounded-input text-xs text-text focus:outline-none focus:ring-2 focus:ring-primary min-h-[44px]"
                  >
                    {technicians.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.user?.name || 'Technician'} • Rating: ⭐{t.rating?.toFixed(1) || '5.0'} • Active: {t.active_jobs_count || 0}/{t.max_concurrent_jobs || 3}
                      </option>
                    ))}
                  </select>

                  <Button
                    variant="primary"
                    className="w-full min-h-[44px] flex items-center justify-center gap-2"
                    onClick={handleManualAssign}
                    disabled={actionLoading || !selectedTechId}
                  >
                    <CheckIcon className="w-4 h-4" />
                    <span>Assign Selected Technician</span>
                  </Button>
                </div>
              )}
            </div>

            {/* Automated Re-Dispatch Option */}
            <div className="pt-2 border-t border-border space-y-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-text">
                Automated Re-Dispatch
              </h3>
              <p className="text-xs text-text-muted">
                Reset offer cycle counters and broadcast immediately with wider radius matching.
              </p>
              <Button
                variant="secondary"
                className="w-full min-h-[44px] flex items-center justify-center gap-2"
                onClick={() => handleReassign(selectedJob.id)}
                disabled={actionLoading}
              >
                <RefreshCwIcon className={`w-4 h-4 ${actionLoading ? 'animate-spin' : ''}`} />
                <span>Trigger Auto Re-Dispatch</span>
              </Button>
            </div>

            {/* Cancel Action */}
            <div className="pt-2 border-t border-border">
              <Button
                variant="danger"
                className="w-full min-h-[44px]"
                onClick={() => {
                  setJobToCancel(selectedJob.id);
                  setCancelModalOpen(true);
                }}
              >
                Cancel Service Request
              </Button>
            </div>
          </div>
        )}
      </Drawer>

      {/* Confirmation Modal for Cancellation */}
      <Modal
        isOpen={cancelModalOpen}
        onClose={() => setCancelModalOpen(false)}
        title="Confirm Job Cancellation"
        size="sm"
      >
        <div className="space-y-4">
          <p className="text-xs text-text leading-relaxed">
            Are you sure you want to cancel this escalated request? This action will notify the
            customer and cannot be undone.
          </p>
          <div className="flex items-center justify-end gap-2 pt-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setCancelModalOpen(false)}
              disabled={actionLoading}
            >
              Back
            </Button>
            <Button
              variant="danger"
              size="sm"
              onClick={handleCancelJob}
              disabled={actionLoading}
            >
              Confirm Cancel
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
