import React, { useState, useEffect } from 'react';
import { api } from '../../services/apiClient';
import {
  TechnicianProfile,
  TechnicianJobOffer,
  ServiceRequest,
} from '../../types';
import { Card } from '../../components/common/Card';
import { Button } from '../../components/common/Button';
import { Badge, StatusBadge } from '../../components/common/Badge';
import { Modal } from '../../components/common/Modal';
import { Skeleton } from '../../components/common/Skeleton';
import { EmptyState } from '../../components/common/EmptyState';
import { useToast } from '../../components/common/Toast';
import {
  PhoneIcon,
  NavigationIcon,
  ClockIcon,
  CheckIcon,
  AlertTriangleIcon,
  StarIcon,
} from '../../components/common/Icons';

export const MySchedule: React.FC = () => {
  const { success, error: toastError, warning } = useToast();

  const [profile, setProfile] = useState<TechnicianProfile | null>(null);
  const [activeJobs, setActiveJobs] = useState<ServiceRequest[]>([]);
  const [offers, setOffers] = useState<TechnicianJobOffer[]>([]);
  const [loading, setLoading] = useState(true);

  // Availability Toggle
  const [togglingOnline, setTogglingOnline] = useState(false);

  // Incoming Offer countdown
  const [offerCountdown, setOfferCountdown] = useState<number>(120);

  // Reject Offer Modal
  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [selectedOfferId, setSelectedOfferId] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState('Too far from current location');
  const [rejectLoading, setRejectLoading] = useState(false);

  // Active Job Action Loading
  const [actionLoading, setActionLoading] = useState(false);

  // Add Note Modal
  const [noteModalOpen, setNoteModalOpen] = useState(false);
  const [noteText, setNoteText] = useState('');
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);

  // Reassignment / Issue report
  const [issueModalOpen, setIssueModalOpen] = useState(false);
  const [issueReason, setIssueReason] = useState('Equipment / Tool Breakdown');

  const fetchTechState = async () => {
    try {
      const [profData, jobsData, offersData] = await Promise.all([
        api.technician.getProfile(),
        api.technician.getJobs({ limit: 20 }),
        api.technician.getOffers(),
      ]);
      setProfile(profData);
      setActiveJobs(
        (jobsData.jobs || []).filter((j) =>
          ['accepted', 'en_route', 'in_progress'].includes(j.status)
        )
      );
      setOffers(offersData.offers || []);
    } catch (err: any) {
      console.error('Fetch tech error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTechState();
    // Poll offers and active jobs every 3 seconds for immediate dispatch reception!
    const interval = setInterval(fetchTechState, 3000);
    return () => clearInterval(interval);
  }, []);

  // Countdown timer for pending offer
  useEffect(() => {
    let timer: any;
    if (offers.length > 0) {
      const activeOffer = offers[0];
      const expiryTime = new Date(activeOffer.expires_at).getTime();
      const remainingSecs = Math.max(0, Math.floor((expiryTime - Date.now()) / 1000));
      setOfferCountdown(remainingSecs);

      timer = setInterval(() => {
        setOfferCountdown((prev) => {
          if (prev <= 1) {
            clearInterval(timer);
            fetchTechState();
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [offers]);

  // Online / Offline Toggle
  const handleToggleOnline = async () => {
    if (!profile) return;
    if (!profile.is_approved) {
      warning('Approval Required', 'Your technician account is pending admin approval.');
      return;
    }
    if (profile.is_suspended) {
      toastError('Account Suspended', 'Please contact support.');
      return;
    }

    setTogglingOnline(true);
    try {
      const nextState = !profile.is_online;
      const res = await api.technician.setAvailability(nextState);
      setProfile((prev) => (prev ? { ...prev, is_online: res.is_online } : null));
      success(
        res.is_online ? 'You are Online' : 'You are Offline',
        res.is_online
          ? 'Live location sharing is active. Ready to receive dispatch offers.'
          : 'You will not receive new incoming job offers.'
      );
    } catch (err: any) {
      toastError('Status update failed', err.message);
    } finally {
      setTogglingOnline(false);
    }
  };

  // Accept Offer
  const handleAcceptOffer = async (offerId: string) => {
    setActionLoading(true);
    try {
      await api.technician.acceptOffer(offerId);
      success('Offer Accepted!', 'Job added to your active cockpit. Navigate to customer.');
      await fetchTechState();
    } catch (err: any) {
      toastError('Could not accept', err.message);
    } finally {
      setActionLoading(false);
    }
  };

  // Reject Offer
  const handleConfirmReject = async () => {
    if (!selectedOfferId) return;
    setRejectLoading(true);
    try {
      await api.technician.rejectOffer(selectedOfferId, rejectReason);
      warning('Offer Declined', 'Job passed to next eligible technician.');
      setRejectModalOpen(false);
      await fetchTechState();
    } catch (err: any) {
      toastError('Decline failed', err.message);
    } finally {
      setRejectLoading(false);
    }
  };

  // Single Action Button strictly advancing job status
  const handleAdvanceJobStatus = async (job: ServiceRequest) => {
    setActionLoading(true);
    try {
      let nextStatus: 'en_route' | 'in_progress' | 'completed' = 'en_route';
      if (job.status === 'accepted') nextStatus = 'en_route';
      else if (job.status === 'en_route') nextStatus = 'in_progress';
      else if (job.status === 'in_progress') nextStatus = 'completed';

      await api.technician.updateJobStatus(job.id, nextStatus);
      success(
        'Status Advanced',
        nextStatus === 'en_route'
          ? 'Marked En Route. Customer notified of your travel.'
          : nextStatus === 'in_progress'
          ? 'Work Started. Diagnostic timer running.'
          : 'Job Finished! Earnings credited to your profile.'
      );
      await fetchTechState();
    } catch (err: any) {
      toastError('Update failed', err.message);
    } finally {
      setActionLoading(false);
    }
  };

  // Add Job Note
  const handleAddNote = async () => {
    if (!selectedJobId || !noteText.trim()) return;
    try {
      await api.technician.addJobNote(selectedJobId, noteText.trim());
      success('Note Added', 'Diagnostic observation recorded.');
      setNoteModalOpen(false);
      setNoteText('');
      await fetchTechState();
    } catch (err: any) {
      toastError('Failed to add note', err.message);
    }
  };

  const currentJob = activeJobs.length > 0 ? activeJobs[0] : null;
  const currentOffer = offers.length > 0 ? offers[0] : null;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Top Banner: Status, Online Toggle & Metrics */}
      <Card padding="lg" className="border-border">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-border">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-primary text-white font-bold flex items-center justify-center text-lg shadow-warmSm">
              {profile?.name?.charAt(0) || 'T'}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-bold text-text">{profile?.name || 'Technician'}</h1>
                <Badge variant={profile?.is_approved ? 'success' : 'pending'} size="sm">
                  {profile?.is_approved ? 'Verified Pro' : 'Pending Approval'}
                </Badge>
              </div>
              <p className="text-xs text-text-muted mt-0.5">
                Cert Level {profile?.certification_level || 3} • Radius: {profile?.service_radius_km || 20} km
              </p>
            </div>
          </div>

          {/* Large Online/Offline Toggle */}
          <div className="flex items-center gap-3">
            <button
              onClick={handleToggleOnline}
              disabled={togglingOnline || !profile?.is_approved}
              className={`flex items-center gap-2.5 px-5 py-2.5 rounded-full font-bold text-xs uppercase tracking-wider transition-all min-h-[48px] shadow-warmSm ${
                profile?.is_online
                  ? 'bg-status-success text-white hover:opacity-90'
                  : 'bg-surface-alt text-text border border-border hover:bg-border/60'
              }`}
            >
              <span
                className={`w-3 h-3 rounded-full ${
                  profile?.is_online ? 'bg-white animate-pulse' : 'bg-status-neutral'
                }`}
              />
              <span>{profile?.is_online ? 'Online (Accepting Jobs)' : 'Offline (Paused)'}</span>
            </button>
          </div>
        </div>

        {/* Real-time KPI Stats Bar */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-4 text-xs">
          <div className="p-3 rounded-card bg-surface-alt border border-border">
            <span className="text-[10px] font-bold text-text-muted uppercase">Today's Earnings</span>
            <div className="text-base font-bold text-text mt-0.5">
              ₹{profile?.total_earnings || 0}
            </div>
          </div>

          <div className="p-3 rounded-card bg-surface-alt border border-border">
            <span className="text-[10px] font-bold text-text-muted uppercase">Jobs Completed</span>
            <div className="text-base font-bold text-text mt-0.5">
              {profile?.total_jobs_completed || 0}
            </div>
          </div>

          <div className="p-3 rounded-card bg-surface-alt border border-border">
            <span className="text-[10px] font-bold text-text-muted uppercase">Customer Rating</span>
            <div className="text-base font-bold text-accent mt-0.5 flex items-center gap-1">
              ★ {profile?.avg_rating || 5.0}
            </div>
          </div>

          <div className="p-3 rounded-card bg-surface-alt border border-border">
            <span className="text-[10px] font-bold text-text-muted uppercase">Capacity Meter</span>
            <div className="text-base font-bold text-text mt-0.5">
              {activeJobs.length} / {profile?.max_concurrent_jobs || 3} Active
            </div>
          </div>
        </div>
      </Card>

      {/* ── INCOMING JOB OFFER FULL-ALERT / BANNER ────────────────────────────── */}
      {currentOffer && (
        <Card
          padding="lg"
          className="border-2 border-primary bg-primary-tint/20 animate-slide-up shadow-warmLg relative overflow-hidden"
        >
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-primary/20">
            <div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-status-error animate-ping" />
                <Badge variant="error" size="sm">
                  Priority Dispatch Offer #{currentOffer.attempt_number}
                </Badge>
              </div>
              <h2 className="text-xl font-bold text-text mt-1">
                {currentOffer.service_request?.category_name || 'Appliance'} Service
              </h2>
              <p className="text-xs text-text-muted mt-0.5">
                📍 {currentOffer.service_request?.address}
              </p>
            </div>

            {/* Countdown Clock */}
            <div className="flex items-center gap-2 bg-surface px-4 py-2 rounded-card border border-border shadow-warmSm self-start sm:self-auto">
              <ClockIcon size={18} className="text-primary" />
              <div className="text-right">
                <span className="text-[10px] font-bold uppercase text-text-muted block">
                  Time to Accept
                </span>
                <span
                  className={`text-base font-bold ${
                    offerCountdown <= 15 ? 'text-status-error animate-pulse' : 'text-primary'
                  }`}
                >
                  {offerCountdown}s
                </span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 my-4 text-xs">
            <div className="p-3 rounded-card bg-surface border border-border">
              <span className="text-[10px] text-text-muted uppercase font-bold">Estimated Payout</span>
              <div className="text-sm font-bold text-status-success mt-0.5">
                ₹{currentOffer.service_request?.estimated_price || 250}
              </div>
            </div>
            <div className="p-3 rounded-card bg-surface border border-border">
              <span className="text-[10px] text-text-muted uppercase font-bold">Urgency</span>
              <div className="text-sm font-bold text-text capitalize mt-0.5">
                {currentOffer.service_request?.urgency || 'Normal'}
              </div>
            </div>
            <div className="p-3 rounded-card bg-surface border border-border col-span-2 sm:col-span-1">
              <span className="text-[10px] text-text-muted uppercase font-bold">Problem Note</span>
              <div className="text-xs text-text line-clamp-1 mt-0.5">
                {currentOffer.service_request?.description || 'Diagnostics requested'}
              </div>
            </div>
          </div>

          {/* Accept / Reject Buttons */}
          <div className="flex items-center justify-end gap-3 pt-2">
            <Button
              variant="outline"
              size="lg"
              onClick={() => {
                setSelectedOfferId(currentOffer.offer_id);
                setRejectModalOpen(true);
              }}
              className="border-status-error text-status-error hover:bg-status-error/10 min-h-[48px]"
            >
              Decline Offer
            </Button>
            <Button
              variant="primary"
              size="lg"
              loading={actionLoading}
              onClick={() => handleAcceptOffer(currentOffer.offer_id)}
              className="bg-status-success hover:bg-status-success/90 min-h-[48px] px-8 text-base font-bold"
            >
              Accept Job ✓
            </Button>
          </div>
        </Card>
      )}

      {/* ── ACTIVE JOB COCKPIT CARD ─────────────────────────────────────────── */}
      {currentJob ? (
        <Card padding="lg" className="border-border space-y-5">
          <div className="flex items-start justify-between pb-3 border-b border-border">
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-primary">
                Active Assignment In Progress
              </span>
              <h2 className="text-lg font-bold text-text mt-0.5">
                {currentJob.category_name || 'Appliance'} • #{currentJob.id.slice(0, 8)}
              </h2>
              <p className="text-xs text-text-muted">📍 {currentJob.address}</p>
            </div>
            <StatusBadge status={currentJob.status} size="md" />
          </div>

          {/* Navigation & Customer Contacts */}
          <div className="p-4 rounded-card bg-surface-alt border border-border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <div className="text-xs font-bold text-text">Customer Residence</div>
              <div className="text-xs text-text-muted mt-0.5">{currentJob.address}</div>
              {currentJob.description && (
                <div className="text-xs text-text font-medium mt-1 italic">
                  "{currentJob.description}"
                </div>
              )}
            </div>

            <div className="flex items-center gap-2 w-full sm:w-auto">
              <a
                href={`https://www.google.com/maps/dir/?api=1&destination=${currentJob.lat},${currentJob.lng}`}
                target="_blank"
                rel="noreferrer"
                className="flex-1 sm:flex-none inline-flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-input bg-primary text-white text-xs font-bold shadow-warmSm hover:bg-primary-hover transition min-h-[44px]"
              >
                <NavigationIcon size={16} />
                <span>Navigate</span>
              </a>
              <a
                href="tel:+919876543210"
                className="flex-1 sm:flex-none inline-flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-input bg-surface border border-border text-xs font-bold text-text hover:bg-surface-alt transition shadow-warmSm min-h-[44px]"
              >
                <PhoneIcon size={16} />
                <span>Call</span>
              </a>
            </div>
          </div>

          {/* Diagnostic Notes Trail */}
          {currentJob.completion_notes && (
            <div className="p-3.5 rounded-card bg-surface border border-border text-xs">
              <span className="font-bold text-text block mb-1">Diagnostic Log:</span>
              <p className="text-text-muted whitespace-pre-line leading-relaxed">
                {currentJob.completion_notes}
              </p>
            </div>
          )}

          {/* Primary Action Button Bar: Strictly advances valid lifecycle */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-3 border-t border-border">
            <div className="flex items-center gap-2 w-full sm:w-auto">
              <Button
                variant="secondary"
                size="md"
                onClick={() => {
                  setSelectedJobId(currentJob.id);
                  setNoteModalOpen(true);
                }}
              >
                + Add Diagnostic Note
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setSelectedJobId(currentJob.id);
                  setIssueModalOpen(true);
                }}
                className="text-status-error"
              >
                Report Issue
              </Button>
            </div>

            {/* Single primary advancing button */}
            <Button
              variant="primary"
              size="lg"
              loading={actionLoading}
              onClick={() => handleAdvanceJobStatus(currentJob)}
              className="w-full sm:w-auto min-h-[48px] px-8 text-sm font-bold"
            >
              {currentJob.status === 'accepted'
                ? 'Start Travel (En Route) →'
                : currentJob.status === 'en_route'
                ? 'Mark Arrived at Location ✓'
                : currentJob.status === 'in_progress'
                ? 'Complete Job & Submit Proof ✓'
                : 'Finished'}
            </Button>
          </div>
        </Card>
      ) : (
        <EmptyState
          title="No Active Job"
          description={
            profile?.is_online
              ? 'You are online and waiting for the dispatch engine. New matching orders will appear here automatically.'
              : 'You are currently offline. Toggle your status to online above to start receiving jobs.'
          }
          actionLabel={profile?.is_online ? 'Refresh Queue' : 'Go Online Now'}
          onAction={profile?.is_online ? fetchTechState : handleToggleOnline}
        />
      )}

      {/* Reject Offer Modal */}
      <Modal
        isOpen={rejectModalOpen}
        onClose={() => setRejectModalOpen(false)}
        title="Decline Job Offer"
        description="Please select a reason so the dispatch engine can recalibrate matching."
      >
        <div className="space-y-4 py-2">
          <div className="space-y-2">
            {[
              'Too far from current location',
              'Vehicle / transit issue',
              'Personal emergency',
              'Job outside specialization',
              'At maximum workload capacity',
            ].map((reason) => (
              <label
                key={reason}
                className="flex items-center gap-2.5 p-2.5 rounded-input border border-border hover:bg-surface-alt cursor-pointer text-xs font-semibold text-text"
              >
                <input
                  type="radio"
                  name="reject_reason"
                  checked={rejectReason === reason}
                  onChange={() => setRejectReason(reason)}
                  className="text-primary focus:ring-primary"
                />
                <span>{reason}</span>
              </label>
            ))}
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-border">
            <Button variant="secondary" size="md" onClick={() => setRejectModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              size="md"
              loading={rejectLoading}
              onClick={handleConfirmReject}
            >
              Confirm Decline
            </Button>
          </div>
        </div>
      </Modal>

      {/* Add Diagnostic Note Modal */}
      <Modal
        isOpen={noteModalOpen}
        onClose={() => setNoteModalOpen(false)}
        title="Add Diagnostic Note"
        description="Record findings, part replacements, or issues for customer proof."
      >
        <div className="space-y-4 py-2">
          <textarea
            rows={4}
            value={noteText}
            onChange={(e) => setNoteText(e.target.value)}
            placeholder="e.g. Replaced capacitor, cleaned air filters, verified refrigerant gas pressure."
            className="w-full px-3 py-2 rounded-input bg-surface text-text border border-border text-xs focus:ring-2 focus:ring-primary focus:outline-none"
          />
          <div className="flex justify-end gap-2">
            <Button variant="secondary" size="md" onClick={() => setNoteModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" size="md" onClick={handleAddNote}>
              Save Note
            </Button>
          </div>
        </div>
      </Modal>

      {/* Report Issue Modal */}
      <Modal
        isOpen={issueModalOpen}
        onClose={() => setIssueModalOpen(false)}
        title="Report Service Issue"
        description="Notify the dispatcher if you cannot complete this assignment."
        isConfirmation
        confirmLabel="Request Reassignment"
        confirmVariant="danger"
        onConfirm={() => {
          success('Issue Dispatched', 'Admin dispatcher notified. Job returned to matching.');
          setIssueModalOpen(false);
          fetchTechState();
        }}
      >
        <div className="space-y-2 text-xs">
          <label className="block text-text-muted font-bold uppercase mb-1">Issue Type</label>
          {['Customer not at home', 'Equipment breakdown', 'Severe weather', 'Safety concern'].map(
            (iss) => (
              <label
                key={iss}
                className="flex items-center gap-2 p-2 rounded-input border border-border cursor-pointer hover:bg-surface-alt font-medium text-text"
              >
                <input
                  type="radio"
                  name="issue_type"
                  checked={issueReason === iss}
                  onChange={() => setIssueReason(iss)}
                  className="text-primary focus:ring-primary"
                />
                <span>{iss}</span>
              </label>
            )
          )}
        </div>
      </Modal>
    </div>
  );
};
