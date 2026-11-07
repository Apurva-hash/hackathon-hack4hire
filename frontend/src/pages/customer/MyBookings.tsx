import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../../services/apiClient';
import { ServiceRequest, RequestStatus } from '../../types';
import { Card } from '../../components/common/Card';
import { Button } from '../../components/common/Button';
import { Badge, StatusBadge } from '../../components/common/Badge';
import { Stepper } from '../../components/common/Stepper';
import { InteractiveMap, MapMarker } from '../../components/common/InteractiveMap';
import { Modal } from '../../components/common/Modal';
import { Tabs } from '../../components/common/Tabs';
import { EmptyState } from '../../components/common/EmptyState';
import { ErrorState } from '../../components/common/ErrorState';
import { Skeleton } from '../../components/common/Skeleton';
import { useToast } from '../../components/common/Toast';
import {
  PhoneIcon,
  MessageSquareIcon,
  StarIcon,
  ClockIcon,
  CheckIcon,
  AlertTriangleIcon,
} from '../../components/common/Icons';

export const MyBookings: React.FC = () => {
  const navigate = useNavigate();
  const { success, error: toastError, info } = useToast();

  const [activeTab, setActiveTab] = useState<'active' | 'history'>('active');
  const [bookings, setBookings] = useState<ServiceRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Selected booking for detailed live tracking view
  const [selectedBookingId, setSelectedBookingId] = useState<string | null>(null);

  // Live technician location data for selected booking
  const [techLocation, setTechLocation] = useState<{
    lat: number;
    lng: number;
    distance_to_job_km: number;
    eta_minutes: number;
  } | null>(null);

  // Cancel Modal state
  const [cancelModalOpen, setCancelModalOpen] = useState(false);
  const [cancelBookingId, setCancelBookingId] = useState<string | null>(null);
  const [cancelLoading, setCancelLoading] = useState(false);

  // Rating Modal state
  const [ratingModalOpen, setRatingModalOpen] = useState(false);
  const [rateBookingId, setRateBookingId] = useState<string | null>(null);
  const [rateScore, setRateScore] = useState<number>(5);
  const [rateFeedback, setRateFeedback] = useState<string>('');
  const [selectedTip, setSelectedTip] = useState<number>(50);
  const [ratingLoading, setRatingLoading] = useState(false);

  // Message modal state
  const [messageModalOpen, setMessageModalOpen] = useState(false);
  const [chatMessage, setChatMessage] = useState('');
  const [chatLogs, setChatLogs] = useState<string[]>([
    'Technician: Hello! I am on my way to your location with diagnostic tools.',
  ]);

  const fetchBookings = async () => {
    try {
      const data = await api.customer.getBookings({ limit: 50 });
      setBookings(data.bookings || []);
      setErrorMsg(null);

      // Auto-select the first active booking if none selected
      if (!selectedBookingId && data.bookings?.length > 0) {
        const firstActive = data.bookings.find((b) =>
          ['requested', 'matching', 'assigned', 'accepted', 'en_route', 'in_progress'].includes(b.status)
        );
        if (firstActive) {
          setSelectedBookingId(firstActive.id);
        } else {
          setSelectedBookingId(data.bookings[0].id);
        }
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load bookings');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBookings();
  }, []);

  // Poll active bookings and technician location every 4 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      fetchBookings();

      if (selectedBookingId) {
        api.customer
          .getTechnicianLocation(selectedBookingId)
          .then((loc) => setTechLocation(loc))
          .catch(() => setTechLocation(null));
      }
    }, 4000);

    return () => clearInterval(interval);
  }, [selectedBookingId]);

  const activeBookings = bookings.filter((b) =>
    ['requested', 'matching', 'assigned', 'accepted', 'en_route', 'in_progress'].includes(b.status)
  );

  const pastBookings = bookings.filter((b) =>
    ['completed', 'cancelled', 'escalated'].includes(b.status)
  );

  const displayedList = activeTab === 'active' ? activeBookings : pastBookings;
  const currentBooking = bookings.find((b) => b.id === selectedBookingId);

  // Handle Cancellation
  const handleConfirmCancel = async () => {
    if (!cancelBookingId) return;
    setCancelLoading(true);
    try {
      await api.customer.cancelBooking(cancelBookingId);
      success('Booking Cancelled', 'Your request has been cancelled.');
      setCancelModalOpen(false);
      fetchBookings();
    } catch (err: any) {
      toastError('Cancellation Error', err.message);
    } finally {
      setCancelLoading(false);
    }
  };

  // Handle Rating Submission
  const handleConfirmRate = async () => {
    if (!rateBookingId) return;
    setRatingLoading(true);
    try {
      await api.customer.rateBooking(rateBookingId, {
        score: rateScore,
        feedback_text: `${rateFeedback}${selectedTip > 0 ? ` (Includes tip of ₹${selectedTip})` : ''}`,
      });
      success('Thank you!', `Rating of ${rateScore}★ submitted successfully.`);
      setRatingModalOpen(false);
      setRateFeedback('');
      fetchBookings();
    } catch (err: any) {
      toastError('Rating Failed', err.message);
    } finally {
      setRatingLoading(false);
    }
  };

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatMessage.trim()) return;
    setChatLogs((prev) => [...prev, `You: ${chatMessage.trim()}`]);
    setChatMessage('');
    info('Message Delivered', 'Technician notified.');
  };

  const steps = [
    { id: 'requested', label: 'Requested' },
    { id: 'assigned', label: 'Assigned' },
    { id: 'accepted', label: 'Accepted' },
    { id: 'en_route', label: 'En Route' },
    { id: 'in_progress', label: 'Working' },
    { id: 'completed', label: 'Done' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-text">Service Cockpit</h1>
          <p className="text-xs text-text-muted mt-0.5">
            Real-time technician tracking, SLA monitoring, and booking history
          </p>
        </div>
        <Button
          variant="primary"
          size="md"
          onClick={() => navigate('/customer/book')}
          icon={<span>＋</span>}
        >
          Book New Service
        </Button>
      </div>

      {/* Tabs */}
      <Tabs
        tabs={[
          { id: 'active', label: 'Active Services', count: activeBookings.length },
          { id: 'history', label: 'Completed & History', count: pastBookings.length },
        ]}
        activeTab={activeTab}
        onChange={(id) => setActiveTab(id as any)}
      />

      {loading ? (
        <div className="space-y-4">
          <Skeleton height="140px" />
          <Skeleton height="140px" />
        </div>
      ) : errorMsg ? (
        <ErrorState message={errorMsg} onRetry={fetchBookings} />
      ) : displayedList.length === 0 ? (
        <EmptyState
          title={activeTab === 'active' ? 'No Active Services' : 'No History Yet'}
          description={
            activeTab === 'active'
              ? 'You have no service orders in flight. Book an appliance repair and track your technician in real time.'
              : 'Completed bookings with receipts and ratings will appear here.'
          }
          actionLabel="Book a Service"
          onAction={() => navigate('/customer/book')}
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Bookings List (4 cols) */}
          <div className="lg:col-span-5 space-y-3">
            {displayedList.map((b) => {
              const isSelected = b.id === selectedBookingId;
              return (
                <Card
                  key={b.id}
                  variant={isSelected ? 'interactive' : 'default'}
                  padding="md"
                  onClick={() => setSelectedBookingId(b.id)}
                  className={`border transition-all ${
                    isSelected ? 'ring-2 ring-primary/40 border-primary bg-primary-tint/10' : ''
                  }`}
                >
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div>
                      <div className="text-[10px] font-bold uppercase tracking-wider text-text-muted">
                        #{b.id.slice(0, 8)} • {b.category_name || 'Appliance'}
                      </div>
                      <h3 className="text-sm font-bold text-text mt-0.5">{b.address}</h3>
                    </div>
                    <StatusBadge status={b.status} size="sm" />
                  </div>

                  <p className="text-xs text-text-muted line-clamp-1 mb-3">
                    {b.description || 'General diagnosis and service repair'}
                  </p>

                  <div className="flex items-center justify-between text-[11px] pt-2 border-t border-border text-text-muted">
                    <span className="flex items-center gap-1 font-semibold text-text">
                      ₹{b.estimated_price || 150}
                    </span>
                    <span>
                      {new Date(b.created_at).toLocaleDateString([], {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>
                  </div>
                </Card>
              );
            })}
          </div>

          {/* Right Column: Active Live Tracking Cockpit (7 cols) */}
          {currentBooking && (
            <div className="lg:col-span-7 space-y-4">
              <Card padding="lg" className="space-y-5 border-primary/20">
                {/* Status Bar */}
                <div className="flex items-center justify-between pb-3 border-b border-border">
                  <div>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-text-muted">
                      Live Booking Status
                    </span>
                    <h2 className="text-lg font-bold text-text">
                      {currentBooking.category_name || 'Appliance'} Service
                    </h2>
                  </div>
                  <StatusBadge status={currentBooking.status} size="md" />
                </div>

                {/* Status Stepper */}
                <Stepper steps={steps} currentStepId={currentBooking.status} />

                {/* Live Map with Technician Pin */}
                <div className="rounded-card overflow-hidden border border-border">
                  <InteractiveMap
                    customerLocation={{
                      lat: currentBooking.lat,
                      lng: currentBooking.lng,
                      label: currentBooking.address,
                    }}
                    assignedTechnician={
                      techLocation
                        ? {
                            id: 'live-tech',
                            lat: techLocation.lat,
                            lng: techLocation.lng,
                            title: currentBooking.assigned_technician?.name || 'Assigned Technician',
                            type: 'technician',
                            eta_minutes: techLocation.eta_minutes,
                            distance_km: techLocation.distance_to_job_km,
                          }
                        : undefined
                    }
                    height="240px"
                  />
                </div>

                {/* Technician Card (if assigned) */}
                {currentBooking.assigned_technician ? (
                  <div className="p-4 rounded-card bg-surface-alt border border-border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 rounded-full bg-primary text-white font-bold flex items-center justify-center text-base shadow-warmSm">
                        {currentBooking.assigned_technician.name.charAt(0)}
                      </div>
                      <div>
                        <div className="flex items-center gap-1.5">
                          <h4 className="text-sm font-bold text-text">
                            {currentBooking.assigned_technician.name}
                          </h4>
                          <span className="flex items-center text-[11px] font-bold text-accent">
                            ★ {currentBooking.assigned_technician.avg_rating}
                          </span>
                        </div>
                        <div className="text-xs text-text-muted">
                          Certified Level {currentBooking.assigned_technician.certification_level} Expert
                        </div>
                        {techLocation && (
                          <div className="text-xs font-semibold text-primary mt-0.5">
                            📍 ~{techLocation.eta_minutes} mins away ({techLocation.distance_to_job_km} km)
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Action buttons (Call & Chat) */}
                    <div className="flex items-center gap-2 w-full sm:w-auto">
                      <a
                        href={`tel:${currentBooking.assigned_technician.phone || '+919000000001'}`}
                        className="flex-1 sm:flex-none inline-flex items-center justify-center gap-1.5 px-3.5 py-2 rounded-input bg-surface border border-border text-xs font-bold text-text hover:bg-surface-alt transition shadow-warmSm min-h-[44px]"
                      >
                        <PhoneIcon size={16} />
                        <span>Call</span>
                      </a>
                      <Button
                        variant="secondary"
                        size="md"
                        onClick={() => setMessageModalOpen(true)}
                        icon={<MessageSquareIcon size={16} />}
                        className="flex-1 sm:flex-none"
                      >
                        Message
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="p-4 rounded-card bg-surface-alt border border-border text-center text-xs text-text-muted">
                    ⚡ DispatchGrid algorithm is currently offering your job to the highest ranked technician.
                  </div>
                )}

                {/* SLA Arrival Guarantee & Notice */}
                <div className="p-3.5 rounded-card bg-primary-tint/30 border border-primary/20 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <ClockIcon size={16} className="text-primary flex-shrink-0" />
                    <div>
                      <span className="font-bold text-text">Target SLA Arrival:</span>
                      <span className="text-text-muted ml-1">
                        {currentBooking.sla_response_deadline
                          ? new Date(currentBooking.sla_response_deadline).toLocaleTimeString([], {
                              hour: '2-digit',
                              minute: '2-digit',
                            })
                          : 'Within 30 mins'}
                      </span>
                    </div>
                  </div>
                  {currentBooking.sla_response_met === false && (
                    <span className="text-xs font-bold text-status-error flex items-center gap-1">
                      <AlertTriangleIcon size={14} /> Delayed (Escalated)
                    </span>
                  )}
                </div>

                {/* Actions Footer */}
                <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-border">
                  {/* Cancel Button */}
                  {['requested', 'matching', 'assigned', 'accepted'].includes(currentBooking.status) && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        setCancelBookingId(currentBooking.id);
                        setCancelModalOpen(true);
                      }}
                      className="text-status-error hover:bg-status-error/10"
                    >
                      Cancel Request
                    </Button>
                  )}

                  {/* Rate Button if Completed */}
                  {currentBooking.status === 'completed' && (
                    <Button
                      variant="primary"
                      size="md"
                      onClick={() => {
                        setRateBookingId(currentBooking.id);
                        setRatingModalOpen(true);
                      }}
                      icon={<StarIcon size={16} />}
                    >
                      Rate & Leave Feedback
                    </Button>
                  )}

                  {/* Book Again */}
                  {['completed', 'cancelled'].includes(currentBooking.status) && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => navigate('/customer/book')}
                    >
                      Book This Service Again
                    </Button>
                  )}
                </div>
              </Card>
            </div>
          )}
        </div>
      )}

      {/* Confirmation Modal for Booking Cancellation */}
      <Modal
        isOpen={cancelModalOpen}
        onClose={() => setCancelModalOpen(false)}
        title="Cancel Service Booking"
        description="Are you sure you want to withdraw this service request? This cannot be undone."
        isConfirmation
        confirmLabel="Yes, Cancel Booking"
        confirmVariant="danger"
        confirmLoading={cancelLoading}
        onConfirm={handleConfirmCancel}
      >
        <p className="text-xs text-text-muted">
          Your assigned technician will be released to accept other requests in their queue.
        </p>
      </Modal>

      {/* Rating & Feedback Modal */}
      <Modal
        isOpen={ratingModalOpen}
        onClose={() => setRatingModalOpen(false)}
        title="Rate Your Technician"
        description="Your feedback helps maintain quality and rewards top technicians."
      >
        <div className="space-y-4 py-2">
          {/* Star selector */}
          <div className="flex justify-center gap-2 my-2">
            {[1, 2, 3, 4, 5].map((star) => (
              <button
                key={star}
                type="button"
                onClick={() => setRateScore(star)}
                className="p-1 text-2xl transition-transform hover:scale-125 focus:outline-none"
              >
                <StarIcon
                  size={32}
                  filled={star <= rateScore}
                  className={star <= rateScore ? 'text-accent' : 'text-border'}
                />
              </button>
            ))}
          </div>

          <div>
            <label className="block text-xs font-bold text-text uppercase tracking-wider mb-1">
              Written Feedback
            </label>
            <textarea
              rows={3}
              value={rateFeedback}
              onChange={(e) => setRateFeedback(e.target.value)}
              placeholder="Was the technician professional, punctual, and effective?"
              className="w-full px-3 py-2 rounded-input bg-surface text-text border border-border text-xs focus:ring-2 focus:ring-primary focus:outline-none"
            />
          </div>

          {/* Optional Tip Selector */}
          <div>
            <label className="block text-xs font-bold text-text uppercase tracking-wider mb-1.5">
              Add a Tip for the Technician (Optional)
            </label>
            <div className="grid grid-cols-4 gap-2">
              {[0, 50, 100, 200].map((tip) => (
                <button
                  key={tip}
                  type="button"
                  onClick={() => setSelectedTip(tip)}
                  className={`py-2 rounded-input border text-xs font-bold transition min-h-[44px] ${
                    selectedTip === tip
                      ? 'border-primary bg-primary text-white shadow-warmSm'
                      : 'border-border bg-surface text-text hover:bg-surface-alt'
                  }`}
                >
                  {tip === 0 ? 'No Tip' : `₹${tip}`}
                </button>
              ))}
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-border">
            <Button variant="secondary" size="md" onClick={() => setRatingModalOpen(false)}>
              Skip
            </Button>
            <Button
              variant="primary"
              size="md"
              loading={ratingLoading}
              onClick={handleConfirmRate}
            >
              Submit Rating
            </Button>
          </div>
        </div>
      </Modal>

      {/* In-App Messaging Modal */}
      <Modal
        isOpen={messageModalOpen}
        onClose={() => setMessageModalOpen(false)}
        title="Direct Chat with Technician"
        description="Quick coordination regarding arrival and tools"
      >
        <div className="space-y-4">
          <div className="h-44 overflow-y-auto space-y-2 p-3 bg-surface-alt rounded-card border border-border text-xs">
            {chatLogs.map((log, idx) => (
              <div
                key={idx}
                className={`p-2 rounded-input max-w-[85%] ${
                  log.startsWith('You:')
                    ? 'ml-auto bg-primary text-white'
                    : 'bg-surface text-text border border-border'
                }`}
              >
                {log}
              </div>
            ))}
          </div>

          <form onSubmit={handleSendMessage} className="flex gap-2">
            <input
              type="text"
              value={chatMessage}
              onChange={(e) => setChatMessage(e.target.value)}
              placeholder="e.g. Ring the doorbell on 2nd floor"
              className="flex-1 px-3 py-2 rounded-input bg-surface text-text border border-border text-xs"
            />
            <Button variant="primary" size="md" type="submit">
              Send
            </Button>
          </form>
        </div>
      </Modal>
    </div>
  );
};
