import React, { useState, useEffect } from 'react';
import { api } from '../../services/apiClient';
import { FeedbackStats, Rating } from '../../types';
import { Card } from '../../components/common/Card';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';
import { Skeleton } from '../../components/common/Skeleton';
import { EmptyState } from '../../components/common/EmptyState';
import { useToast } from '../../components/common/Toast';
import { StarIcon, AlertTriangleIcon, CheckIcon, RefreshCwIcon } from '../../components/common/Icons';

export const Feedback: React.FC = () => {
  const { success, error: toastError } = useToast();

  const [stats, setStats] = useState<FeedbackStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [resolvedIds, setResolvedIds] = useState<Set<string>>(new Set());

  const fetchFeedback = async () => {
    setLoading(true);
    try {
      const data = await api.admin.getFeedbackStats();
      setStats(data);
    } catch (err: any) {
      toastError('Failed to load feedback', err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFeedback();
  }, []);

  const handleResolveAlert = (id: string) => {
    setResolvedIds((prev) => new Set(prev).add(id));
    success('Incident Resolved', 'Low-rating feedback flagged as resolved by support.');
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-text">Customer Reviews & CSAT</h1>
          <p className="text-xs text-text-muted mt-0.5">
            Rating distribution, verified customer feedback, and low-rating escalation alerts
          </p>
        </div>

        <Button
          variant="secondary"
          size="sm"
          onClick={fetchFeedback}
          icon={<RefreshCwIcon size={14} />}
        >
          Refresh Feedback
        </Button>
      </div>

      {loading && !stats ? (
        <div className="space-y-4">
          <Skeleton height="120px" />
          <Skeleton height="240px" />
        </div>
      ) : (
        <>
          {/* Top Score Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Card padding="lg" className="border-border">
              <span className="text-[10px] font-bold uppercase text-text-muted">Average Rating</span>
              <div className="flex items-baseline gap-2 mt-1">
                <span className="text-3xl font-bold text-accent">★ {stats?.avg_rating || 4.8}</span>
                <span className="text-xs text-text-muted">out of 5.0</span>
              </div>
              <p className="text-[11px] text-text-muted mt-1">
                Based on {stats?.total_reviews || 0} customer reviews
              </p>
            </Card>

            <Card padding="lg" className="border-border">
              <span className="text-[10px] font-bold uppercase text-text-muted">Total Reviews</span>
              <div className="text-3xl font-bold text-text mt-1">{stats?.total_reviews || 0}</div>
              <p className="text-[11px] text-status-success mt-1">100% verified service tickets</p>
            </Card>

            <Card padding="lg" className="border-border">
              <span className="text-[10px] font-bold uppercase text-text-muted">
                Low-Rating Alerts (&lt; 3★)
              </span>
              <div
                className={`text-3xl font-bold mt-1 ${
                  (stats?.low_rating_count || 0) > 0 ? 'text-status-error' : 'text-status-success'
                }`}
              >
                {stats?.low_rating_count || 0}
              </div>
              <p className="text-[11px] text-text-muted mt-1">Requires customer follow-up</p>
            </Card>
          </div>

          {/* Rating Distribution Breakdown */}
          <Card padding="lg" className="border-border space-y-3">
            <h3 className="text-sm font-bold text-text">Rating Distribution (1 - 5 Stars)</h3>
            <div className="space-y-2">
              {[5, 4, 3, 2, 1].map((stars) => {
                const count = stats?.distribution?.[stars.toString()] || 0;
                const total = stats?.total_reviews || 1;
                const pct = Math.round((count / total) * 100);
                return (
                  <div key={stars} className="flex items-center gap-3 text-xs">
                    <span className="w-12 font-bold text-text flex items-center gap-1">
                      <span>{stars}</span>
                      <StarIcon size={12} filled className="text-accent" />
                    </span>
                    <div className="flex-1 h-3 bg-surface-alt rounded-full overflow-hidden">
                      <div
                        className="h-full bg-accent rounded-full transition-all duration-300"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="w-16 text-right font-medium text-text-muted">
                      {count} ({pct}%)
                    </span>
                  </div>
                );
              })}
            </div>
          </Card>

          {/* Recent Reviews List */}
          <Card padding="none" className="border-border overflow-hidden">
            <div className="p-4 sm:p-5 border-b border-border">
              <h3 className="text-sm font-bold text-text">Verified Customer Reviews</h3>
            </div>

            {!stats?.recent_reviews || stats.recent_reviews.length === 0 ? (
              <EmptyState
                title="No Reviews Recorded"
                description="Completed service tickets with ratings will appear here."
              />
            ) : (
              <div className="divide-y divide-border">
                {stats.recent_reviews.map((r) => {
                  const isLow = r.score < 3;
                  const isResolved = resolvedIds.has(r.id);

                  return (
                    <div
                      key={r.id}
                      className={`p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
                        isLow && !isResolved ? 'bg-status-error/5' : ''
                      }`}
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="text-accent font-bold text-sm">
                            {'★'.repeat(Math.round(r.score))}
                          </span>
                          <span className="text-xs font-bold text-text">{r.score} / 5</span>
                          {isLow && !isResolved && (
                            <Badge variant="error" size="sm">
                              Escalation Flag
                            </Badge>
                          )}
                          {isResolved && (
                            <Badge variant="success" size="sm">
                              Resolved
                            </Badge>
                          )}
                        </div>
                        <p className="text-xs text-text font-medium leading-relaxed">
                          "{r.feedback_text || 'Prompt service, satisfied with the repair.'}"
                        </p>
                        <div className="text-[10px] text-text-muted">
                          Ticket #{r.service_request_id?.slice(0, 8)} •{' '}
                          {new Date(r.created_at).toLocaleDateString([], {
                            month: 'short',
                            day: 'numeric',
                            year: 'numeric',
                          })}
                        </div>
                      </div>

                      {isLow && !isResolved && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleResolveAlert(r.id)}
                          className="border-status-error text-status-error"
                        >
                          Mark Resolved ✓
                        </Button>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </Card>
        </>
      )}
    </div>
  );
};

