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
  SearchIcon,
  RefreshCwIcon,
  ClockIcon,
  AlertTriangleIcon,
  CheckIcon,
} from '../../components/common/Icons';

export const Jobs: React.FC = () => {
  const { success, error: toastError, warning } = useToast();

  const [jobs, setJobs] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  // Filters & Pagination
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [urgencyFilter, setUrgencyFilter] = useState('');
  const [page, setPage] = useState(0);
  const limit = 15;

  // Detail Drawer state
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [selectedJob, setSelectedJob] = useState<any | null>(null);
  const [drawerLoading, setDrawerLoading] = useState(false);

  // Available Technicians for Manual Reassignment
  const [techCandidates, setTechCandidates] = useState<TechnicianProfile[]>([]);
  const [selectedAssignTechId, setSelectedAssignTechId] = useState('');
  const [assignLoading, setAssignLoading] = useState(false);

  // Cancel Modal state
  const [cancelModalOpen, setCancelModalOpen] = useState(false);
  const [cancellingJobId, setCancellingJobId] = useState<string | null>(null);

  const fetchJobs = async () => {
    setLoading(true);
    try {
      const data = await api.admin.getJobs({
        status: statusFilter || undefined,
        urgency: urgencyFilter || undefined,
        offset: page * limit,
        limit,
      });
      setJobs(data.jobs || []);
      setTotal(data.total || 0);
    } catch (err: any) {
      toastError('Failed to load jobs', err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, [statusFilter, urgencyFilter, page]);

  // Load candidates when drawer opens
  useEffect(() => {
    if (selectedJobId) {
      setDrawerLoading(true);
      Promise.all([
        api.admin.getJob(selectedJobId),
        api.admin.getTechnicians({ is_online: true, is_approved: true, limit: 10 }),
      ])
        .then(([jobData, techData]) => {
          setSelectedJob(jobData);
          setTechCandidates(techData.technicians || []);
          if (techData.technicians?.length > 0) {
            setSelectedAssignTechId(techData.technicians[0].id);
          }
        })
        .catch((e) => toastError('Could not load details', e.message))
        .finally(() => setDrawerLoading(false));
    } else {
      setSelectedJob(null);
    }
  }, [selectedJobId]);

  const handleManualAssign = async () => {
    if (!selectedJobId || !selectedAssignTechId) return;
    setAssignLoading(true);
    try {
      await api.admin.assignJob(selectedJobId, selectedAssignTechId);
      success('Job Assigned', 'Technician assigned successfully.');
      fetchJobs();
      const updated = await api.admin.getJob(selectedJobId);
      setSelectedJob(updated);
    } catch (err: any) {
      toastError('Assign failed', err.message);
    } finally {
      setAssignLoading(false);
    }
  };

  const handleReassign = async () => {
    if (!selectedJobId) return;
    setAssignLoading(true);
    try {
      await api.admin.reassignJob(selectedJobId);
      success('Re-Dispatch Triggered', 'Matching engine searching for next eligible candidate.');
      fetchJobs();
      const updated = await api.admin.getJob(selectedJobId);
      setSelectedJob(updated);
    } catch (err: any) {
      toastError('Re-dispatch failed', err.message);
    } finally {
      setAssignLoading(false);
    }
  };

  const handleConfirmCancel = async () => {
    if (!cancellingJobId) return;
    try {
      await api.admin.cancelJob(cancellingJobId);
      warning('Job Cancelled', 'Service request has been cancelled by admin.');
      setCancelModalOpen(false);
      fetchJobs();
      if (selectedJobId === cancellingJobId) {
        setSelectedJobId(null);
      }
    } catch (err: any) {
      toastError('Cancel failed', err.message);
    }
  };

  const filteredJobs = jobs.filter((j) => {
    if (!searchTerm.trim()) return true;
    const q = searchTerm.toLowerCase();
    return (
      j.id.toLowerCase().includes(q) ||
      (j.category || '').toLowerCase().includes(q) ||
      (j.address || '').toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-text">Jobs & Dispatch Registry</h1>
          <p className="text-xs text-text-muted mt-0.5">
            Real-time tracking of all customer service requests, offers, and assignment overrides
          </p>
        </div>

        <Button
          variant="secondary"
          size="sm"
          onClick={fetchJobs}
          icon={<RefreshCwIcon size={14} />}
        >
          Refresh Registry
        </Button>
      </div>

      {/* Filter Toolbar */}
      <Card padding="md" className="border-border">
        <div className="flex flex-col md:flex-row items-center justify-between gap-3">
          {/* Search */}
          <div className="relative w-full md:w-80">
            <input
              type="text"
              placeholder="Search by ticket ID, category, address..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3.5 py-2 rounded-input bg-surface text-text border border-border text-xs min-h-[44px]"
            />
            <div className="absolute left-3 top-3 text-text-muted pointer-events-none">
              <SearchIcon size={16} />
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
            {/* Status Filter */}
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-text-muted">Status:</span>
              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setPage(0);
                }}
                className="px-3 py-2 rounded-input border border-border text-xs bg-surface text-text min-h-[44px]"
              >
                <option value="">All Statuses</option>
                <option value="requested">Requested</option>
                <option value="matching">Matching</option>
                <option value="assigned">Assigned</option>
                <option value="accepted">Accepted</option>
                <option value="en_route">En Route</option>
                <option value="in_progress">In Progress</option>
                <option value="completed">Completed</option>
                <option value="cancelled">Cancelled</option>
                <option value="escalated">Escalated</option>
              </select>
            </div>

            {/* Urgency Filter */}
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-text-muted">Urgency:</span>
              <select
                value={urgencyFilter}
                onChange={(e) => {
                  setUrgencyFilter(e.target.value);
                  setPage(0);
                }}
                className="px-3 py-2 rounded-input border border-border text-xs bg-surface text-text min-h-[44px]"
              >
                <option value="">All Priorities</option>
                <option value="normal">Normal</option>
                <option value="high">High / Urgent</option>
                <option value="critical">Critical / Emergency</option>
              </select>
            </div>
          </div>
        </div>
      </Card>

      {/* Jobs Table */}
      <Card padding="none" className="border-border overflow-hidden">
        {loading ? (
          <div className="p-6 space-y-3">
            <Skeleton height="50px" />
            <Skeleton height="50px" />
            <Skeleton height="50px" />
          </div>
        ) : filteredJobs.length === 0 ? (
          <EmptyState
            title="No Service Requests Found"
            description="No jobs match your filter criteria."
            actionLabel="Clear Filters"
            onAction={() => {
              setStatusFilter('');
              setUrgencyFilter('');
              setSearchTerm('');
            }}
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-surface-alt border-b border-border text-text-muted font-bold uppercase tracking-wider">
                  <th className="py-3 px-4">Ticket</th>
                  <th className="py-3 px-4">Service Category</th>
                  <th className="py-3 px-4">Location</th>
                  <th className="py-3 px-4">Urgency</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Dispatch Attempts</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filteredJobs.map((job) => (
                  <tr
                    key={job.id}
                    onClick={() => setSelectedJobId(job.id)}
                    className="hover:bg-surface-alt/70 transition-colors cursor-pointer"
                  >
                    <td className="py-3.5 px-4 font-mono font-bold text-text">
                      #{job.id.slice(0, 8)}
                    </td>
                    <td className="py-3.5 px-4 font-bold text-text">
                      {job.category || 'Appliance Repair'}
                    </td>
                    <td className="py-3.5 px-4 text-text-muted max-w-[200px] truncate">
                      {job.address}
                    </td>
                    <td className="py-3.5 px-4 capitalize">
                      <span
                        className={`font-semibold ${
                          job.urgency === 'critical'
                            ? 'text-status-error'
                            : job.urgency === 'high'
                            ? 'text-status-pending'
                            : 'text-text'
                        }`}
                      >
                        {job.urgency}
                      </span>
                    </td>
                    <td className="py-3.5 px-4">
                      <StatusBadge status={job.status} size="sm" />
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="font-semibold text-text">
                        {job.offer_attempt} attempt{job.offer_attempt === 1 ? '' : 's'}
                      </span>
                      {job.escalated && (
                        <span className="ml-1.5 text-[10px] text-status-error font-bold">
                          [Escalated]
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedJobId(job.id);
                        }}
                      >
                        Inspect →
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Bar */}
        <div className="p-4 border-t border-border flex items-center justify-between text-xs text-text-muted">
          <span>
            Showing {filteredJobs.length} of {total} jobs
          </span>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              size="sm"
              disabled={page === 0}
              onClick={() => setPage((p) => Math.max(0, p - 1))}
            >
              Previous
            </Button>
            <Button
              variant="secondary"
              size="sm"
              disabled={(page + 1) * limit >= total}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      </Card>

      {/* ── JOB DETAIL & OVERRIDE DRAWER ────────────────────────────────────── */}
      <Drawer
        isOpen={!!selectedJobId}
        onClose={() => setSelectedJobId(null)}
        title={`Service Ticket #${selectedJobId?.slice(0, 8)}`}
        size="lg"
      >
        {drawerLoading || !selectedJob ? (
          <div className="space-y-4">
            <Skeleton height="80px" />
            <Skeleton height="120px" />
            <Skeleton height="120px" />
          </div>
        ) : (
          <div className="space-y-6">
            {/* Header Status & Price */}
            <div className="flex items-center justify-between pb-3 border-b border-border">
              <div>
                <h3 className="text-base font-bold text-text">
                  {selectedJob.category || 'Appliance'} Service
                </h3>
                <p className="text-xs text-text-muted mt-0.5">📍 {selectedJob.address}</p>
              </div>
              <StatusBadge status={selectedJob.status} size="md" />
            </div>

            {/* Diagnostic notes / Problem */}
            <div className="p-3.5 rounded-card bg-surface-alt border border-border text-xs space-y-1">
              <span className="font-bold text-text uppercase text-[10px]">Customer Request</span>
              <p className="text-text-muted">{selectedJob.description || 'General repair requested.'}</p>
            </div>

            {/* SLA & Time Metrics */}
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-3 rounded-card bg-surface border border-border">
                <span className="text-[10px] uppercase font-bold text-text-muted">
                  SLA Response Target
                </span>
                <div className="font-bold text-text mt-0.5">
                  {selectedJob.sla_response_deadline
                    ? new Date(selectedJob.sla_response_deadline).toLocaleTimeString()
                    : 'Within 30m'}
                </div>
              </div>

              <div className="p-3 rounded-card bg-surface border border-border">
                <span className="text-[10px] uppercase font-bold text-text-muted">
                  SLA Resolution Target
                </span>
                <div className="font-bold text-text mt-0.5">
                  {selectedJob.sla_resolution_deadline
                    ? new Date(selectedJob.sla_resolution_deadline).toLocaleTimeString()
                    : 'Within 2h'}
                </div>
              </div>
            </div>

            {/* Offer History & Attempts */}
            <div>
              <h4 className="text-xs font-bold text-text uppercase tracking-wider mb-2">
                Dispatch Offer History ({selectedJob.offers?.length || 0})
              </h4>
              {!selectedJob.offers || selectedJob.offers.length === 0 ? (
                <div className="p-3 rounded-card bg-surface-alt border border-border text-xs text-text-muted text-center">
                  No offers sent yet. Job is in initial queue.
                </div>
              ) : (
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {selectedJob.offers.map((off: any, idx: number) => (
                    <div
                      key={off.id}
                      className="p-2.5 rounded-card bg-surface-alt border border-border text-xs flex items-center justify-between"
                    >
                      <div>
                        <span className="font-bold text-text">Attempt #{off.attempt_number}</span>
                        {off.rejection_reason && (
                          <div className="text-[10px] text-status-error mt-0.5">
                            Reason: {off.rejection_reason}
                          </div>
                        )}
                      </div>
                      <StatusBadge status={off.status} size="sm" />
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Manual Assign / Reassign Actions */}
            <div className="p-4 rounded-card bg-surface border border-border space-y-3">
              <h4 className="text-xs font-bold text-text uppercase tracking-wider">
                Admin Dispatch Actions
              </h4>

              {/* Technician dropdown */}
              <div>
                <label className="block text-[11px] font-semibold text-text-muted mb-1">
                  Manual Assign to Online Technician:
                </label>
                <div className="flex gap-2">
                  <select
                    value={selectedAssignTechId}
                    onChange={(e) => setSelectedAssignTechId(e.target.value)}
                    className="flex-1 px-3 py-2 rounded-input border border-border text-xs bg-surface text-text"
                  >
                    {techCandidates.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.name} (Cert L{t.certification_level} • ★{t.avg_rating})
                      </option>
                    ))}
                  </select>
                  <Button
                    variant="primary"
                    size="sm"
                    loading={assignLoading}
                    onClick={handleManualAssign}
                  >
                    Assign
                  </Button>
                </div>
              </div>

              {/* Re-dispatch / Auto Match */}
              <div className="pt-2 flex items-center justify-between gap-3 border-t border-border">
                <Button
                  variant="outline"
                  size="sm"
                  loading={assignLoading}
                  onClick={handleReassign}
                >
                  ⚡ Trigger Auto-Redispatch
                </Button>

                {['requested', 'matching', 'assigned', 'accepted'].includes(selectedJob.status) && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setCancellingJobId(selectedJob.id);
                      setCancelModalOpen(true);
                    }}
                    className="text-status-error hover:bg-status-error/10"
                  >
                    Cancel Job
                  </Button>
                )}
              </div>
            </div>
          </div>
        )}
      </Drawer>

      {/* Cancel Confirmation Modal */}
      <Modal
        isOpen={cancelModalOpen}
        onClose={() => setCancelModalOpen(false)}
        title="Admin Job Cancellation"
        description="Are you sure you want to cancel this service request? This will retract active offers and notify the customer."
        isConfirmation
        confirmLabel="Yes, Cancel Service"
        confirmVariant="danger"
        onConfirm={handleConfirmCancel}
      />
    </div>
  );
};
