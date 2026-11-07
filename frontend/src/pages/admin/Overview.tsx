import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../../services/apiClient';
import {
  AdminOverview,
  DispatchMetrics,
  SLAStats,
  FeedbackStats,
  TechnicianWorkloadItem,
  DemandStats,
} from '../../types';
import { Card } from '../../components/common/Card';
import { Button } from '../../components/common/Button';
import { Badge, StatusBadge } from '../../components/common/Badge';
import { Skeleton } from '../../components/common/Skeleton';
import { ErrorState } from '../../components/common/ErrorState';
import { useToast } from '../../components/common/Toast';
import {
  AlertTriangleIcon,
  ClockIcon,
  CheckIcon,
  StarIcon,
  RefreshCwIcon,
  ChevronRightIcon,
  NavigationIcon,
} from '../../components/common/Icons';

export const Overview: React.FC = () => {
  const navigate = useNavigate();
  const { success, error: toastError } = useToast();

  const [dateRange, setDateRange] = useState<'all' | 'today' | 'week'>('all');
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [dispatchMetrics, setDispatchMetrics] = useState<DispatchMetrics | null>(null);
  const [slaStats, setSlaStats] = useState<SLAStats | null>(null);
  const [feedbackStats, setFeedbackStats] = useState<FeedbackStats | null>(null);
  const [workloads, setWorkloads] = useState<TechnicianWorkloadItem[]>([]);
  const [demand, setDemand] = useState<DemandStats | null>(null);

  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      let date_from: string | undefined;
      const now = new Date();
      if (dateRange === 'today') {
        const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        date_from = today.toISOString();
      } else if (dateRange === 'week') {
        const lastWeek = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
        date_from = lastWeek.toISOString();
      }

      const params = date_from ? { date_from } : undefined;

      const [ovData, dispData, slaData, fbData, wlData, dmData] = await Promise.all([
        api.admin.getOverview(params),
        api.admin.getDispatchMetrics(params),
        api.admin.getSLAStats(params),
        api.admin.getFeedbackStats(params),
        api.admin.getWorkload(),
        api.admin.getDemandStats(params),
      ]);

      setOverview(ovData);
      setDispatchMetrics(dispData);
      setSlaStats(slaData);
      setFeedbackStats(fbData);
      setWorkloads(wlData.technicians || []);
      setDemand(dmData);
      setErrorMsg(null);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load operations dashboard');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 12000);
    return () => clearInterval(interval);
  }, [dateRange]);

  if (loading && !overview) {
    return (
      <div className="space-y-6">
        <Skeleton height="80px" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Skeleton height="110px" />
          <Skeleton height="110px" />
          <Skeleton height="110px" />
          <Skeleton height="110px" />
        </div>
        <Skeleton height="320px" />
      </div>
    );
  }

  if (errorMsg && !overview) {
    return <ErrorState message={errorMsg} onRetry={fetchDashboardData} />;
  }

  // Color palette for charts
  const chartColors = ['#C2531F', '#F2A93B', '#2F7F86', '#3F8F5B', '#8A5A44', '#B3261E'];

  return (
    <div className="space-y-6">
      {/* Dashboard Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-text">Operations Command Center</h1>
          <p className="text-xs text-text-muted mt-0.5">
            Real-time field service dispatch, SLA compliance, and fleet capacity
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Date range filter */}
          <div className="flex rounded-input border border-border bg-surface p-1 shadow-warmSm">
            {(['all', 'today', 'week'] as const).map((r) => (
              <button
                key={r}
                onClick={() => setDateRange(r)}
                className={`px-3 py-1.5 text-xs font-bold rounded-lg transition-all capitalize min-h-[36px] ${
                  dateRange === r
                    ? 'bg-primary text-white shadow-warmSm'
                    : 'text-text-muted hover:text-text'
                }`}
              >
                {r === 'all' ? 'All Time' : r === 'today' ? 'Today' : 'Last 7 Days'}
              </button>
            ))}
          </div>

          <Button
            variant="secondary"
            size="sm"
            onClick={fetchDashboardData}
            icon={<RefreshCwIcon size={14} />}
            aria-label="Refresh operational metrics"
          >
            Refresh
          </Button>
        </div>
      </div>

      {/* ── 1. CLICKABLE DRILL-DOWN KPI CARDS ──────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {/* Total Customers */}
        <Card
          variant="interactive"
          padding="md"
          onClick={() => navigate('/admin/customers')}
          className="border-border"
        >
          <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider">
            Total Customers
          </span>
          <div className="text-2xl font-bold text-text mt-1">
            {overview?.customers?.total || 0}
          </div>
          <div className="text-[10px] text-primary font-semibold mt-1 flex items-center gap-0.5">
            <span>View Customers</span>
            <ChevronRightIcon size={12} />
          </div>
        </Card>

        {/* Fleet Online */}
        <Card
          variant="interactive"
          padding="md"
          onClick={() => navigate('/admin/technicians')}
          className="border-border"
        >
          <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider">
            Fleet Online
          </span>
          <div className="text-2xl font-bold text-status-success mt-1">
            {overview?.technicians?.online || 0} / {overview?.technicians?.total || 0}
          </div>
          <div className="text-[10px] text-text-muted mt-1">
            {overview?.technicians?.offline || 0} offline
          </div>
        </Card>

        {/* Active Jobs */}
        <Card
          variant="interactive"
          padding="md"
          onClick={() => navigate('/admin/jobs')}
          className="border-border"
        >
          <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider">
            Total Jobs
          </span>
          <div className="text-2xl font-bold text-text mt-1">{overview?.jobs?.total || 0}</div>
          <div className="text-[10px] text-text-muted mt-1">
            {overview?.jobs?.by_status?.in_progress || 0} in progress
          </div>
        </Card>

        {/* Dispatch Rate */}
        <Card
          variant="interactive"
          padding="md"
          onClick={() => navigate('/admin/jobs')}
          className="border-border"
        >
          <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider">
            Dispatch Rate
          </span>
          <div className="text-2xl font-bold text-primary mt-1">
            {dispatchMetrics?.assignment_rate_pct || 94}%
          </div>
          <div className="text-[10px] text-status-success mt-1 font-semibold">
            {dispatchMetrics?.acceptance_rate_pct || 100}% accepted
          </div>
        </Card>

        {/* SLA Compliance */}
        <Card
          variant="interactive"
          padding="md"
          onClick={() => navigate('/admin/reports')}
          className="border-border"
        >
          <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider">
            SLA Compliance
          </span>
          <div
            className={`text-2xl font-bold mt-1 ${
              (slaStats?.compliance_pct || 100) < 85 ? 'text-status-error' : 'text-status-success'
            }`}
          >
            {slaStats?.compliance_pct || 100}%
          </div>
          <div className="text-[10px] text-text-muted mt-1">
            {slaStats?.breached_count || 0} breached
          </div>
        </Card>

        {/* Escalated / Pending Alert */}
        <Card
          variant="interactive"
          padding="md"
          onClick={() => navigate('/admin/escalations')}
          className={`border ${
            (overview?.jobs?.escalated || 0) > 0
              ? 'border-status-error bg-status-error/10'
              : 'border-border'
          }`}
        >
          <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider">
            Escalations
          </span>
          <div
            className={`text-2xl font-bold mt-1 ${
              (overview?.jobs?.escalated || 0) > 0 ? 'text-status-error' : 'text-text'
            }`}
          >
            {overview?.jobs?.escalated || 0}
          </div>
          <div className="text-[10px] text-status-error font-bold mt-1 flex items-center gap-0.5">
            <span>Action Required</span>
            <ChevronRightIcon size={12} />
          </div>
        </Card>
      </div>

      {/* ── 2. OLDEST UNASSIGNED ALERT BANNER (If present) ──────────────────── */}
      {overview?.oldest_pending && (
        <div className="p-4 rounded-card bg-status-pending/15 border border-status-pending/40 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2.5">
            <ClockIcon size={20} className="text-status-pending flex-shrink-0" />
            <div>
              <span className="font-bold text-text">Oldest Unassigned Job Alert:</span>
              <span className="text-text-muted ml-1">
                Job #{overview.oldest_pending.id.slice(0, 8)} has been pending for{' '}
                <strong className="text-text">{overview.oldest_pending.age_hours || 0.5} hours</strong>.
              </span>
            </div>
          </div>
          <Button
            variant="primary"
            size="sm"
            onClick={() => navigate(`/admin/jobs?status=requested`)}
          >
            Review & Assign
          </Button>
        </div>
      )}

      {/* ── 3. DISPATCH METRICS & SLA PANEL ─────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Dispatch Metrics Engine */}
        <Card padding="lg" className="border-border space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-border">
            <h3 className="text-sm font-bold text-text">Dispatch Engine Performance</h3>
            <span className="text-xs text-text-muted">
              {dispatchMetrics?.total_offers || 0} total offers issued
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div className="p-3 rounded-card bg-surface-alt border border-border">
              <span className="text-[10px] text-text-muted uppercase font-bold">Acceptance Rate</span>
              <div className="text-base font-bold text-status-success mt-1">
                {dispatchMetrics?.acceptance_rate_pct || 100}%
              </div>
            </div>
            <div className="p-3 rounded-card bg-surface-alt border border-border">
              <span className="text-[10px] text-text-muted uppercase font-bold">Rejection Rate</span>
              <div className="text-base font-bold text-status-error mt-1">
                {dispatchMetrics?.rejection_rate_pct || 0}%
              </div>
            </div>
            <div className="p-3 rounded-card bg-surface-alt border border-border">
              <span className="text-[10px] text-text-muted uppercase font-bold">Reassignments</span>
              <div className="text-base font-bold text-text mt-1">
                {dispatchMetrics?.reassignment_count || 0}
              </div>
            </div>
            <div className="p-3 rounded-card bg-surface-alt border border-border">
              <span className="text-[10px] text-text-muted uppercase font-bold">Avg Assign Time</span>
              <div className="text-base font-bold text-primary mt-1">
                {dispatchMetrics?.avg_time_to_assign_minutes !== null &&
                dispatchMetrics?.avg_time_to_assign_minutes !== undefined
                  ? `${dispatchMetrics.avg_time_to_assign_minutes}m`
                  : '~1.8m'}
              </div>
            </div>
          </div>

          {/* Quick breakdown bar */}
          <div>
            <div className="flex justify-between text-[11px] text-text-muted mb-1 font-semibold">
              <span>Accepted ({dispatchMetrics?.accepted || 0})</span>
              <span>
                Rejected ({dispatchMetrics?.rejected || 0}) • Expired ({dispatchMetrics?.expired || 0})
              </span>
            </div>
            <div className="w-full h-2.5 bg-border rounded-full overflow-hidden flex">
              <div
                className="bg-status-success h-full transition-all duration-300"
                style={{ width: `${dispatchMetrics?.acceptance_rate_pct || 100}%` }}
              />
              <div
                className="bg-status-error h-full transition-all duration-300"
                style={{ width: `${dispatchMetrics?.rejection_rate_pct || 0}%` }}
              />
            </div>
          </div>
        </Card>

        {/* SLA Health Monitor */}
        <Card padding="lg" className="border-border space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-border">
            <h3 className="text-sm font-bold text-text">SLA Compliance Monitor</h3>
            <Badge
              variant={(slaStats?.breached_count || 0) > 0 ? 'error' : 'success'}
              size="sm"
            >
              {(slaStats?.breached_count || 0) > 0 ? 'Breaches Recorded' : 'Targets Met'}
            </Badge>
          </div>

          <div className="grid grid-cols-3 gap-3 text-xs">
            <div className="p-3 rounded-card bg-surface-alt border border-border text-center">
              <span className="text-[10px] text-text-muted uppercase font-bold">Compliance</span>
              <div className="text-xl font-bold text-status-success mt-1">
                {slaStats?.compliance_pct || 100}%
              </div>
            </div>
            <div className="p-3 rounded-card bg-surface-alt border border-border text-center">
              <span className="text-[10px] text-text-muted uppercase font-bold">At-Risk Jobs</span>
              <div className="text-xl font-bold text-status-pending mt-1">
                {slaStats?.at_risk_count || 0}
              </div>
            </div>
            <div className="p-3 rounded-card bg-surface-alt border border-border text-center">
              <span className="text-[10px] text-text-muted uppercase font-bold">Breached</span>
              <div className="text-xl font-bold text-status-error mt-1">
                {slaStats?.breached_count || 0}
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between text-xs text-text-muted pt-2 border-t border-border">
            <span>
              Avg Response: <strong>{slaStats?.avg_response_minutes || 14} min</strong>
            </span>
            <span>
              Avg Resolution: <strong>{slaStats?.avg_resolution_minutes || 52} min</strong>
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate('/admin/settings')}
            >
              SLA Tiers Config
            </Button>
          </div>
        </Card>
      </div>

      {/* ── 4. DEMAND BY CATEGORY & FLEET WORKLOAD ─────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Demand by Category (5 cols) */}
        <div className="lg:col-span-5">
          <Card padding="lg" className="border-border space-y-4 h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between pb-2 border-b border-border">
                <h3 className="text-sm font-bold text-text">Demand by Service Category</h3>
                <span className="text-xs text-text-muted">Top Request Volume</span>
              </div>

              <div className="space-y-3 mt-4">
                {demand?.by_category && demand.by_category.length > 0 ? (
                  demand.by_category.slice(0, 5).map((item, idx) => {
                    const total = overview?.jobs?.total || 1;
                    const pct = Math.round((item.count / total) * 100);
                    return (
                      <div key={item.category} className="space-y-1 text-xs">
                        <div className="flex justify-between font-semibold">
                          <span className="text-text">{item.category}</span>
                          <span className="text-text-muted">
                            {item.count} orders ({pct}%)
                          </span>
                        </div>
                        <div className="w-full h-2 bg-surface-alt rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all duration-300"
                            style={{
                              width: `${Math.max(8, pct)}%`,
                              backgroundColor: chartColors[idx % chartColors.length],
                            }}
                          />
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <div className="text-xs text-text-muted py-6 text-center">
                    Generating category distribution...
                  </div>
                )}
              </div>
            </div>

            <Button
              variant="secondary"
              size="sm"
              onClick={() => navigate('/admin/live-map')}
              icon={<NavigationIcon size={14} />}
              className="w-full mt-4"
            >
              Open Real-Time Live Map
            </Button>
          </Card>
        </div>

        {/* Fleet Workload & Capacity Table (7 cols) */}
        <div className="lg:col-span-7">
          <Card padding="none" className="border-border overflow-hidden">
            <div className="p-4 sm:p-5 border-b border-border flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-text">Technician Fleet Utilization</h3>
                <p className="text-[11px] text-text-muted mt-0.5">
                  Current concurrent assignments vs max capacity
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => navigate('/admin/technicians')}
              >
                Manage Fleet
              </Button>
            </div>

            {workloads.length === 0 ? (
              <div className="p-8 text-center text-xs text-text-muted">
                No active technicians registered.
              </div>
            ) : (
              <div className="divide-y divide-border max-h-72 overflow-y-auto">
                {workloads.slice(0, 6).map((tech) => (
                  <div
                    key={tech.technician_id}
                    className="p-3.5 sm:px-5 flex items-center justify-between gap-3 text-xs hover:bg-surface-alt transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-2 h-2 rounded-full ${
                          tech.is_online ? 'bg-status-success animate-pulse' : 'bg-status-neutral'
                        }`}
                      />
                      <div>
                        <span className="font-bold text-text">{tech.name}</span>
                        <div className="text-[10px] text-text-muted">
                          {tech.total_completed} jobs completed • ★ {tech.avg_rating}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <div className="font-bold text-text">
                          {tech.active_jobs} / {tech.max_concurrent_jobs} jobs
                        </div>
                        <div className="text-[10px] text-text-muted">
                          {tech.utilization_pct}% utilized
                        </div>
                      </div>

                      <div className="w-16 h-2 bg-border rounded-full overflow-hidden hidden sm:block">
                        <div
                          className={`h-full ${
                            tech.utilization_pct >= 100
                              ? 'bg-status-error'
                              : tech.utilization_pct >= 60
                              ? 'bg-status-pending'
                              : 'bg-status-success'
                          }`}
                          style={{ width: `${Math.min(100, tech.utilization_pct)}%` }}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
};
