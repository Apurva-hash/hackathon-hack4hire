import React, { useState, useEffect } from 'react';
import { api } from '../../services/apiClient';
import { Card } from '../../components/common/Card';
import { Skeleton } from '../../components/common/Skeleton';
import { EmptyState } from '../../components/common/EmptyState';

export const Earnings: React.FC = () => {
  const [earningsData, setEarningsData] = useState<{
    total_earnings: number;
    admin_commission_deducted?: number;
    gross_revenue?: number;
    total_jobs_completed: number;
    daily_breakdown: { date: string; earnings: number }[];
    payout_history?: {
      booking_id: string;
      service_name: string;
      customer_name: string;
      completed_at?: string;
      booking_amount: number;
      technician_share: number;
      admin_share: number;
      payment_method: string;
      payment_status: string;
      transaction_id: string;
    }[];
  } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.technician
      .getEarnings()
      .then((data) => setEarningsData(data))
      .catch((e) => console.error(e))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-text">Earnings & Payouts</h1>
        <p className="text-xs text-text-muted mt-0.5">
          Track completed repairs, commission, and daily payout transfers
        </p>
      </div>

      {loading ? (
        <div className="space-y-4">
          <Skeleton height="100px" />
          <Skeleton height="200px" />
        </div>
      ) : (
        <>
          {/* Big Earnings Metric Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card padding="lg" className="border-status-success/40 bg-status-success/5">
              <span className="text-[10px] font-bold uppercase text-status-success">My Earnings (60%)</span>
              <div className="text-3xl font-bold text-status-success mt-1">
                ₹{earningsData?.total_earnings || 0}
              </div>
              <p className="text-[11px] text-text-muted mt-1">Your 60% share of completed jobs</p>
            </Card>

            <Card padding="lg" className="border-border">
              <span className="text-[10px] font-bold uppercase text-text-muted">Gross Booking Volume</span>
              <div className="text-3xl font-bold text-text mt-1">
                ₹{earningsData?.gross_revenue || Math.round((earningsData?.total_earnings || 0) / 0.6)}
              </div>
              <p className="text-[11px] text-text-muted mt-1">Total customer invoice amount</p>
            </Card>

            <Card padding="lg" className="border-border">
              <span className="text-[10px] font-bold uppercase text-text-muted">Admin Platform Fee (40%)</span>
              <div className="text-3xl font-bold text-primary mt-1">
                ₹{earningsData?.admin_commission_deducted || Math.round((earningsData?.total_earnings || 0) * 0.4 / 0.6)}
              </div>
              <p className="text-[11px] text-text-muted mt-1">40% platform service fee</p>
            </Card>

            <Card padding="lg" className="border-border">
              <span className="text-[10px] font-bold uppercase text-text-muted">Completed Jobs</span>
              <div className="text-3xl font-bold text-text mt-1">
                {earningsData?.total_jobs_completed || 0}
              </div>
              <p className="text-[11px] text-text-muted mt-1">Verified service orders</p>
            </Card>
          </div>

          {/* Daily Breakdown List */}
          <Card padding="none" className="overflow-hidden">
            <div className="p-4 sm:p-5 border-b border-border">
              <h3 className="text-sm font-bold text-text">Daily Earnings Breakdown</h3>
            </div>

            {!earningsData?.daily_breakdown || earningsData.daily_breakdown.length === 0 ? (
              <EmptyState
                title="No Earnings Recorded"
                description="Complete active service orders to see daily earnings breakdown."
              />
            ) : (
              <div className="divide-y divide-border">
                {earningsData.daily_breakdown.map((row) => (
                  <div
                    key={row.date}
                    className="p-4 flex items-center justify-between text-xs hover:bg-surface-alt transition-colors"
                  >
                    <div>
                      <span className="font-bold text-text">
                        {new Date(row.date).toLocaleDateString([], {
                          weekday: 'short',
                          month: 'short',
                          day: 'numeric',
                        })}
                      </span>
                    </div>
                    <div className="text-right font-bold text-status-success text-sm">
                      +₹{row.earnings}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* Individual Booking Earnings & Payout History Table */}
          <Card padding="none" className="overflow-hidden border-border">
            <div className="p-4 sm:p-5 border-b border-border flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-text">Individual Booking Earnings (60% Share)</h3>
                <p className="text-[11px] text-text-muted mt-0.5">
                  Detailed breakdown of earnings per completed service request
                </p>
              </div>
              <span className="text-xs font-bold text-status-success bg-status-success/10 px-2.5 py-1 rounded-full">
                {earningsData?.payout_history?.length || 0} Payouts
              </span>
            </div>

            {!earningsData?.payout_history || earningsData.payout_history.length === 0 ? (
              <div className="p-8 text-center text-xs text-text-muted">
                No payout history recorded yet. Complete jobs to receive your 60% revenue share.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-surface-alt border-b border-border text-[11px] uppercase tracking-wider text-text-muted">
                    <tr>
                      <th className="p-3 pl-5">Booking / Service</th>
                      <th className="p-3">Customer</th>
                      <th className="p-3">Method</th>
                      <th className="p-3">Total Amount</th>
                      <th className="p-3">Admin (40%)</th>
                      <th className="p-3 pr-5 font-bold text-status-success">My 60% Share</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {earningsData.payout_history.map((item) => (
                      <tr key={item.booking_id} className="hover:bg-surface-alt/60 transition-colors">
                        <td className="p-3 pl-5">
                          <div className="font-bold text-text">{item.service_name}</div>
                          <div className="text-[10px] text-text-muted font-mono">
                            #{item.booking_id.slice(0, 8)} • {item.transaction_id}
                          </div>
                        </td>
                        <td className="p-3 text-text font-medium">
                          {item.customer_name}
                        </td>
                        <td className="p-3">
                          <span className="capitalize font-bold text-text">
                            {item.payment_method === 'gpay'
                              ? '🔵 GPay'
                              : item.payment_method === 'phonepe'
                              ? '🟣 PhonePe'
                              : '💵 Cash'}
                          </span>
                        </td>
                        <td className="p-3 font-medium text-text">
                          ₹{item.booking_amount}
                        </td>
                        <td className="p-3 text-text-muted">
                          -₹{item.admin_share}
                        </td>
                        <td className="p-3 pr-5 font-bold text-status-success text-sm">
                          +₹{item.technician_share}
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

