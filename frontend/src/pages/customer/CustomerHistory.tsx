import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../../services/apiClient';
import { ServiceRequest } from '../../types';
import { Card } from '../../components/common/Card';
import { StatusBadge } from '../../components/common/Badge';
import { Button } from '../../components/common/Button';
import { EmptyState } from '../../components/common/EmptyState';
import { Skeleton } from '../../components/common/Skeleton';

export const CustomerHistory: React.FC = () => {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState<ServiceRequest[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.customer
      .getBookings({ limit: 50 })
      .then((res) => {
        setJobs(
          (res.bookings || []).filter(
            (b) => b.status === 'completed' || b.status === 'cancelled'
          )
        );
      })
      .catch((e) => console.error(e))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-text">Service History & Receipts</h1>
          <p className="text-xs text-text-muted mt-0.5">
            Archived records of completed service orders and diagnostics
          </p>
        </div>
        <Button variant="primary" size="md" onClick={() => navigate('/customer/book')}>
          Book New Service
        </Button>
      </div>

      <Card padding="none" className="overflow-hidden">
        {loading ? (
          <div className="p-6 space-y-3">
            <Skeleton height="60px" />
            <Skeleton height="60px" />
            <Skeleton height="60px" />
          </div>
        ) : jobs.length === 0 ? (
          <EmptyState
            title="No Past Orders"
            description="When your appliance service bookings are completed, receipts and technician notes will be stored here."
            actionLabel="Book a Service"
            onAction={() => navigate('/customer/book')}
          />
        ) : (
          <div className="divide-y divide-border">
            {jobs.map((job) => (
              <div
                key={job.id}
                className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-surface-alt transition-colors"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-sm text-text">
                      {job.category_name || 'Appliance'} Service
                    </span>
                    <span className="text-[10px] text-text-muted">#{job.id.slice(0, 8)}</span>
                  </div>
                  <div className="text-xs text-text-muted mt-0.5">📍 {job.address}</div>
                  {job.completion_notes && (
                    <div className="text-xs text-text-muted mt-1 italic">
                      Notes: {job.completion_notes}
                    </div>
                  )}
                </div>

                <div className="flex items-center justify-between sm:justify-end gap-4">
                  <div className="text-left sm:text-right">
                    <div className="text-sm font-bold text-text">
                      ₹{job.estimated_price || 150}
                    </div>
                    <div className="text-[10px] text-text-muted">
                      {new Date(job.created_at).toLocaleDateString([], {
                        month: 'short',
                        day: 'numeric',
                        year: 'numeric',
                      })}
                    </div>
                  </div>
                  <StatusBadge status={job.status} size="sm" />
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
};
