import React, { useState, useEffect } from 'react';
import { api } from '../../services/apiClient';
import { RevenueStats, SLAStats } from '../../types';
import { Card } from '../../components/common/Card';
import { Button } from '../../components/common/Button';
import { Skeleton } from '../../components/common/Skeleton';
import { useToast } from '../../components/common/Toast';
import { DownloadIcon, RefreshCwIcon, StarIcon } from '../../components/common/Icons';

export const Reports: React.FC = () => {
  const { success, error: toastError } = useToast();

  const [revenue, setRevenue] = useState<RevenueStats | null>(null);
  const [sla, setSla] = useState<SLAStats | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchReports = async () => {
    setLoading(true);
    try {
      const [revData, slaData] = await Promise.all([
        api.admin.getRevenueStats(),
        api.admin.getSLAStats(),
      ]);
      setRevenue(revData);
      setSla(slaData);
    } catch (err: any) {
      toastError('Failed to load reports', err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, []);

  const handleExportJobs = () => {
    window.open(api.admin.getJobsExportUrl(), '_blank');
    success('Export Started', 'Downloading jobs registry CSV...');
  };

  const handleExportTechs = () => {
    window.open(api.admin.getTechniciansExportUrl(), '_blank');
    success('Export Started', 'Downloading fleet performance CSV...');
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-text">Reports & Business Analytics</h1>
          <p className="text-xs text-text-muted mt-0.5">
            Platform revenue, technician performance rankings, and compliance exports
          </p>
        </div>

        {/* CSV Export Buttons */}
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={handleExportJobs}
            icon={<DownloadIcon size={14} />}
          >
            Export Jobs CSV
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={handleExportTechs}
            icon={<DownloadIcon size={14} />}
          >
            Export Fleet CSV
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="space-y-4">
          <Skeleton height="120px" />
          <Skeleton height="260px" />
        </div>
      ) : (
        <>
          {/* Revenue Top Banner */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Card padding="lg" className="border-border">
              <span className="text-[10px] font-bold uppercase text-text-muted">Total Gross Volume</span>
              <div className="text-3xl font-bold text-status-success mt-1">
                ₹{revenue?.total_revenue || 0}
              </div>
              <p className="text-[11px] text-text-muted mt-1">Platform service fee & billing</p>
            </Card>

            <Card padding="lg" className="border-border">
              <span className="text-[10px] font-bold uppercase text-text-muted">Completed Tickets</span>
              <div className="text-3xl font-bold text-text mt-1">
                {revenue?.total_completed_jobs || 0}
              </div>
              <p className="text-[11px] text-text-muted mt-1">Fully closed & validated repairs</p>
            </Card>

            <Card padding="lg" className="border-border">
              <span className="text-[10px] font-bold uppercase text-text-muted">SLA Compliance</span>
              <div className="text-3xl font-bold text-primary mt-1">
                {sla?.compliance_pct || 100}%
              </div>
              <p className="text-[11px] text-text-muted mt-1">{sla?.breached_count || 0} total breaches</p>
            </Card>
          </div>

          {/* Top Earning Fleet Technicians */}
          <Card padding="none" className="border-border overflow-hidden">
            <div className="p-4 sm:p-5 border-b border-border flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-text">Top-Performing Technicians</h3>
                <p className="text-[11px] text-text-muted mt-0.5">Ranked by revenue volume and customer CSAT</p>
              </div>
            </div>

            {!revenue?.top_earning_technicians || revenue.top_earning_technicians.length === 0 ? (
              <div className="p-8 text-center text-xs text-text-muted">
                No revenue records available yet.
              </div>
            ) : (
              <div className="divide-y divide-border">
                {revenue.top_earning_technicians.map((t, idx) => (
                  <div
                    key={t.id}
                    className="p-4 sm:px-5 flex items-center justify-between text-xs hover:bg-surface-alt transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <span className="w-6 font-bold text-text-muted text-center">#{idx + 1}</span>
                      <div className="w-8 h-8 rounded-full bg-primary-tint text-primary font-bold flex items-center justify-center text-xs">
                        {t.name.charAt(0)}
                      </div>
                      <div>
                        <div className="font-bold text-text">{t.name}</div>
                        <div className="text-[10px] text-text-muted">
                          {t.total_jobs_completed} jobs completed
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-6">
                      <div className="flex items-center gap-1 font-bold text-accent">
                        <span>★ {t.avg_rating}</span>
                      </div>
                      <div className="text-right">
                        <span className="font-bold text-status-success text-sm">
                          ₹{t.total_earnings}
                        </span>
                        <div className="text-[10px] text-text-muted">Gross Earnings</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </>
      )}
    </div>
  );
};

