import React, { useState, useEffect } from 'react';
import { api } from '../../services/apiClient';
import { ServiceRequest } from '../../types';
import { Card } from '../../components/common/Card';
import { StatusBadge } from '../../components/common/Badge';
import { Tabs } from '../../components/common/Tabs';
import { EmptyState } from '../../components/common/EmptyState';
import { Skeleton } from '../../components/common/Skeleton';
import { SearchIcon } from '../../components/common/Icons';

export const JobHistory: React.FC = () => {
  const [jobs, setJobs] = useState<ServiceRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');

  const fetchJobs = async () => {
    setLoading(true);
    try {
      const data = await api.technician.getJobs({ limit: 50 });
      setJobs(data.jobs || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, []);

  const filteredJobs = jobs.filter((j) => {
    const matchesStatus =
      statusFilter === 'all'
        ? true
        : statusFilter === 'completed'
        ? j.status === 'completed'
        : ['accepted', 'en_route', 'in_progress'].includes(j.status);

    const matchesSearch =
      !searchQuery.trim() ||
      j.address.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (j.category_name || '').toLowerCase().includes(searchQuery.toLowerCase());

    return matchesStatus && matchesSearch;
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-text">Technician Job History</h1>
          <p className="text-xs text-text-muted mt-0.5">
            Log of all dispatched jobs, completion timestamps, and payouts
          </p>
        </div>

        {/* Search */}
        <div className="relative w-full sm:w-64">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by address or category..."
            className="w-full pl-9 pr-3 py-2 rounded-input bg-surface text-text border border-border text-xs min-h-[44px]"
          />
          <div className="absolute left-3 top-3 text-text-muted">
            <SearchIcon size={16} />
          </div>
        </div>
      </div>

      <Tabs
        tabs={[
          { id: 'all', label: 'All Jobs', count: jobs.length },
          { id: 'active', label: 'In Progress', count: jobs.filter((j) => ['accepted', 'en_route', 'in_progress'].includes(j.status)).length },
          { id: 'completed', label: 'Completed', count: jobs.filter((j) => j.status === 'completed').length },
        ]}
        activeTab={statusFilter}
        onChange={(id) => setStatusFilter(id)}
      />

      <Card padding="none" className="overflow-hidden">
        {loading ? (
          <div className="p-6 space-y-3">
            <Skeleton height="60px" />
            <Skeleton height="60px" />
            <Skeleton height="60px" />
          </div>
        ) : filteredJobs.length === 0 ? (
          <EmptyState
            title="No Jobs Found"
            description="You don't have any jobs matching the selected status filter."
            actionLabel="Refresh List"
            onAction={fetchJobs}
          />
        ) : (
          <div className="divide-y divide-border">
            {filteredJobs.map((job) => (
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
                    <div className="text-sm font-bold text-status-success">
                      +₹{job.estimated_price || 200}
                    </div>
                    <div className="text-[10px] text-text-muted">
                      {new Date(job.created_at).toLocaleDateString([], {
                        month: 'short',
                        day: 'numeric',
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
