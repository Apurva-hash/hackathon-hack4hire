import React, { useState, useEffect } from 'react';
import { api } from '../../services/apiClient';
import { RevenueStats, SLAStats, PaymentRecord } from '../../types';
import { Badge } from '../../components/common/Badge';
import { Card } from '../../components/common/Card';
import { Button } from '../../components/common/Button';
import { Skeleton } from '../../components/common/Skeleton';
import { useToast } from '../../components/common/Toast';
import { DownloadIcon, RefreshCwIcon, StarIcon } from '../../components/common/Icons';

export const Reports: React.FC = () => {
  const { success, error: toastError } = useToast();

  const [revenue, setRevenue] = useState<RevenueStats | null>(null);
  const [sla, setSla] = useState<SLAStats | null>(null);
  const [payments, setPayments] = useState<PaymentRecord[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchReports = async () => {
    setLoading(true);
    try {
      const [revData, slaData, payData] = await Promise.all([
        api.admin.getRevenueStats(),
        api.admin.getSLAStats(),
        api.admin.getPayments(),
      ]);
      setRevenue(revData);
      setSla(slaData);
      setPayments(payData.payments || []);
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
          {/* Revenue & Revenue Sharing Top Banner */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card padding="lg" className="border-border">
              <span className="text-[10px] font-bold uppercase text-text-muted">Total Gross Revenue</span>
              <div className="text-3xl font-bold text-text mt-1">
                ₹{revenue?.total_revenue || 0}
              </div>
              <p className="text-[11px] text-text-muted mt-1">Total customer booking volume</p>
            </Card>

            <Card padding="lg" className="border-primary/40 bg-primary-tint/10">
              <span className="text-[10px] font-bold uppercase text-primary">Admin Share (40%)</span>
              <div className="text-3xl font-bold text-primary mt-1">
                ₹{revenue?.admin_earnings || Math.round((revenue?.total_revenue || 0) * 0.4)}
              </div>
              <p className="text-[11px] text-text-muted mt-1">Platform operational revenue</p>
            </Card>

            <Card padding="lg" className="border-status-success/40 bg-status-success/5">
              <span className="text-[10px] font-bold uppercase text-status-success">Technician Payouts (60%)</span>
              <div className="text-3xl font-bold text-status-success mt-1">
                ₹{revenue?.technician_payouts || Math.round((revenue?.total_revenue || 0) * 0.6)}
              </div>
              <p className="text-[11px] text-text-muted mt-1">Fleet earnings disbursed</p>
            </Card>

            <Card padding="lg" className="border-border">
              <span className="text-[10px] font-bold uppercase text-text-muted">Completed Tickets</span>
              <div className="text-3xl font-bold text-text mt-1">
                {revenue?.total_completed_jobs || 0}
              </div>
              <p className="text-[11px] text-text-muted mt-1">SLA Compliance: {sla?.compliance_pct || 100}%</p>
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

          {/* Payment & Transaction History Table */}
          <Card padding="none" className="border-border overflow-hidden">
            <div className="p-4 sm:p-5 border-b border-border flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <h3 className="text-sm font-bold text-text">Payment & Revenue-Sharing History</h3>
                <p className="text-[11px] text-text-muted mt-0.5">
                  Live audit trail of customer payments, methods, and 40% Admin / 60% Tech splits
                </p>
              </div>
              <span className="text-xs font-bold text-primary bg-primary-tint px-2.5 py-1 rounded-full">
                {payments.length} Transactions
              </span>
            </div>

            {payments.length === 0 ? (
              <div className="p-8 text-center text-xs text-text-muted">
                No payment transactions recorded yet.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-surface-alt border-b border-border text-[11px] uppercase tracking-wider text-text-muted">
                    <tr>
                      <th className="p-3 pl-5">Transaction ID</th>
                      <th className="p-3">Customer & Service</th>
                      <th className="p-3">Technician</th>
                      <th className="p-3">Method</th>
                      <th className="p-3">Total Amount</th>
                      <th className="p-3">Admin (40%)</th>
                      <th className="p-3">Tech (60%)</th>
                      <th className="p-3 pr-5">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {payments.map((p) => (
                      <tr key={p.id} className="hover:bg-surface-alt/60 transition-colors">
                        <td className="p-3 pl-5 font-mono text-[11px] text-text font-bold">
                          {p.transaction_id || p.id.slice(0, 8)}
                        </td>
                        <td className="p-3">
                          <div className="font-bold text-text">{p.customer_name || 'Customer'}</div>
                          <div className="text-[11px] text-text-muted">{p.service_category || 'Service'}</div>
                        </td>
                        <td className="p-3 text-text font-medium">
                          {p.technician_name || 'Unassigned'}
                        </td>
                        <td className="p-3">
                          <span className="capitalize font-bold text-text">
                            {p.payment_method === 'gpay'
                              ? '🔵 Google Pay'
                              : p.payment_method === 'phonepe'
                              ? '🟣 PhonePe'
                              : '💵 Cash'}
                          </span>
                        </td>
                        <td className="p-3 font-bold text-text">
                          ₹{p.amount}
                        </td>
                        <td className="p-3 font-semibold text-primary">
                          ₹{p.admin_share}
                        </td>
                        <td className="p-3 font-semibold text-status-success">
                          ₹{p.technician_share}
                        </td>
                        <td className="p-3 pr-5">
                          <Badge
                            variant={
                              p.status === 'completed'
                                ? 'success'
                                : p.status === 'failed'
                                ? 'error'
                                : 'pending'
                            }
                            size="sm"
                          >
                            {p.status}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </>
      )}
    </div>
  );
};

