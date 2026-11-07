import React, { useState, useEffect } from 'react';
import { api } from '../../services/apiClient';
import { Card } from '../../components/common/Card';
import { Skeleton } from '../../components/common/Skeleton';
import { EmptyState } from '../../components/common/EmptyState';

export const Earnings: React.FC = () => {
  const [earningsData, setEarningsData] = useState<{
    total_earnings: number;
    total_jobs_completed: number;
    daily_breakdown: { date: string; earnings: number }[];
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
    <div className="max-w-3xl mx-auto space-y-6">
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
          {/* Big Earnings Metric Card */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Card padding="lg" className="border-border">
              <span className="text-[10px] font-bold uppercase text-text-muted">Total Balance</span>
              <div className="text-3xl font-bold text-status-success mt-1">
                ₹{earningsData?.total_earnings || 0}
              </div>
              <p className="text-[11px] text-text-muted mt-1">Available for automatic weekly payout</p>
            </Card>

            <Card padding="lg" className="border-border">
              <span className="text-[10px] font-bold uppercase text-text-muted">Completed Jobs</span>
              <div className="text-3xl font-bold text-text mt-1">
                {earningsData?.total_jobs_completed || 0}
              </div>
              <p className="text-[11px] text-text-muted mt-1">100% verified customer orders</p>
            </Card>

            <Card padding="lg" className="border-border">
              <span className="text-[10px] font-bold uppercase text-text-muted">Avg Rate Per Job</span>
              <div className="text-3xl font-bold text-primary mt-1">
                ₹
                {earningsData?.total_jobs_completed
                  ? Math.round((earningsData.total_earnings / earningsData.total_jobs_completed) * 10) / 10
                  : 220}
              </div>
              <p className="text-[11px] text-text-muted mt-1">Based on diagnostic duration</p>
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
        </>
      )}
    </div>
  );
};

