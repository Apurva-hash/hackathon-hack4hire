import React, { useState, useEffect } from 'react';
import { api } from '../../services/apiClient';
import { AuditLogEntry } from '../../types';
import { Card } from '../../components/common/Card';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';
import { Modal } from '../../components/common/Modal';
import { Skeleton } from '../../components/common/Skeleton';
import { EmptyState } from '../../components/common/EmptyState';
import { useToast } from '../../components/common/Toast';
import {
  RefreshCwIcon,
  SearchIcon,
  ClockIcon,
  CheckIcon,
  AlertTriangleIcon,
} from '../../components/common/Icons';

export const AuditHistory: React.FC = () => {
  const { error: toastError } = useToast();

  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  // Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [entityFilter, setEntityFilter] = useState('all');
  const [actionFilter, setActionFilter] = useState('all');

  // Inspection Modal state
  const [selectedEntry, setSelectedEntry] = useState<AuditLogEntry | null>(null);

  const fetchAuditLogs = async () => {
    setLoading(true);
    try {
      const res = await api.admin.getAuditLog({
        entity_type: entityFilter !== 'all' ? entityFilter : undefined,
        action: actionFilter !== 'all' ? actionFilter : undefined,
        limit: 50,
      });
      setLogs(res.entries || []);
      setTotal(res.total || 0);
    } catch (err: any) {
      toastError('Failed to load audit logs', err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAuditLogs();
  }, [entityFilter, actionFilter]);

  const filteredLogs = logs.filter((entry) => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      entry.action.toLowerCase().includes(term) ||
      entry.entity_type.toLowerCase().includes(term) ||
      (entry.entity_id && entry.entity_id.toLowerCase().includes(term)) ||
      (entry.admin_user_id && entry.admin_user_id.toLowerCase().includes(term))
    );
  });

  const getActionBadgeVariant = (action: string) => {
    const act = action.toLowerCase();
    if (act.includes('create') || act.includes('approve') || act.includes('accept')) return 'success';
    if (act.includes('update') || act.includes('assign')) return 'info';
    if (act.includes('reassign') || act.includes('offer')) return 'warning';
    if (act.includes('cancel') || act.includes('suspend') || act.includes('reject')) return 'error';
    return 'neutral';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-text">System Audit Trail</h1>
            <Badge variant="info" size="sm">
              <span>{total} Events</span>
            </Badge>
          </div>
          <p className="text-xs text-text-muted mt-1">
            Immutable log of all dispatch assignments, algorithm executions, manual overrides, and config changes.
          </p>
        </div>

        <Button
          variant="secondary"
          size="sm"
          onClick={fetchAuditLogs}
          disabled={loading}
          className="flex items-center gap-2 min-h-[44px]"
        >
          <RefreshCwIcon className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </Button>
      </div>

      {/* Filter Toolbar */}
      <Card className="p-4">
        <div className="flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
          <div className="relative flex-1">
            <SearchIcon className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-text-muted" />
            <input
              type="text"
              placeholder="Search by action, entity ID, or admin user..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 bg-bg border border-border rounded-input text-xs text-text placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-primary min-h-[44px]"
            />
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <select
              value={entityFilter}
              onChange={(e) => setEntityFilter(e.target.value)}
              className="px-3 py-2 bg-bg border border-border rounded-input text-xs text-text focus:outline-none focus:ring-2 focus:ring-primary min-h-[44px]"
            >
              <option value="all">All Entity Types</option>
              <option value="job">Service Job</option>
              <option value="technician">Technician</option>
              <option value="customer">Customer</option>
              <option value="sla_tier">SLA Tier</option>
              <option value="matching_config">Matching Config</option>
              <option value="category">Category</option>
            </select>

            <select
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
              className="px-3 py-2 bg-bg border border-border rounded-input text-xs text-text focus:outline-none focus:ring-2 focus:ring-primary min-h-[44px]"
            >
              <option value="all">All Actions</option>
              <option value="create">Create</option>
              <option value="update">Update</option>
              <option value="assign">Assign</option>
              <option value="reassign">Reassign</option>
              <option value="cancel">Cancel</option>
              <option value="approve">Approve</option>
              <option value="suspend">Suspend</option>
            </select>
          </div>
        </div>
      </Card>

      {/* Audit Log Table */}
      <Card className="overflow-hidden">
        {loading ? (
          <div className="p-6 space-y-4">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
          </div>
        ) : filteredLogs.length === 0 ? (
          <EmptyState
            title="No Audit Entries Found"
            description={
              searchTerm || entityFilter !== 'all' || actionFilter !== 'all'
                ? 'No audit log entries match your active filters.'
                : 'No administrative or dispatch events have been recorded yet.'
            }
            actionLabel="Reset Filters"
            onAction={() => {
              setSearchTerm('');
              setEntityFilter('all');
              setActionFilter('all');
            }}
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-surface-alt border-b border-border text-[10px] text-text-muted uppercase tracking-wider">
                  <th className="py-3 px-4 font-semibold">Timestamp</th>
                  <th className="py-3 px-4 font-semibold">Action</th>
                  <th className="py-3 px-4 font-semibold">Entity Type</th>
                  <th className="py-3 px-4 font-semibold">Target Entity</th>
                  <th className="py-3 px-4 font-semibold">Triggered By</th>
                  <th className="py-3 px-4 font-semibold text-right">Payload Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filteredLogs.map((entry) => (
                  <tr key={entry.id} className="hover:bg-surface-alt/60 transition">
                    <td className="py-3.5 px-4 text-text-muted whitespace-nowrap">
                      <div className="font-medium text-text">
                        {new Date(entry.occurred_at).toLocaleDateString()}
                      </div>
                      <div className="text-[10px] text-text-muted">
                        {new Date(entry.occurred_at).toLocaleTimeString()}
                      </div>
                    </td>

                    <td className="py-3.5 px-4">
                      <Badge variant={getActionBadgeVariant(entry.action)} size="sm">
                        <span>{entry.action.replace(/_/g, ' ')}</span>
                      </Badge>
                    </td>

                    <td className="py-3.5 px-4 font-semibold text-text uppercase tracking-wider text-[11px]">
                      {entry.entity_type}
                    </td>

                    <td className="py-3.5 px-4 font-mono text-[11px] text-text">
                      {entry.entity_id ? (
                        <span className="bg-surface-alt px-2 py-0.5 rounded border border-border">
                          {entry.entity_id.slice(0, 10)}...
                        </span>
                      ) : (
                        <span className="text-text-muted">—</span>
                      )}
                    </td>

                    <td className="py-3.5 px-4 text-text-muted">
                      {entry.admin_user_id ? (
                        <span className="font-mono text-[11px] text-text">
                          Admin ({entry.admin_user_id.slice(0, 6)})
                        </span>
                      ) : (
                        <span className="text-[11px] text-text-muted italic">System Automated</span>
                      )}
                    </td>

                    <td className="py-3.5 px-4 text-right">
                      {(entry.old_value || entry.new_value) ? (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="min-h-[36px] text-xs px-2.5 font-semibold text-primary hover:bg-primary-tint"
                          onClick={() => setSelectedEntry(entry)}
                        >
                          View Changes
                        </Button>
                      ) : (
                        <span className="text-[11px] text-text-muted">No payload</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* State Changes Inspection Modal */}
      <Modal
        isOpen={!!selectedEntry}
        onClose={() => setSelectedEntry(null)}
        title={selectedEntry ? `Audit Event Details: ${selectedEntry.action.toUpperCase()}` : 'Audit Event'}
        size="lg"
      >
        {selectedEntry && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3 p-3 bg-surface-alt rounded-card text-xs">
              <div>
                <span className="text-text-muted">Entity:</span>{' '}
                <span className="font-bold text-text uppercase">{selectedEntry.entity_type}</span>
              </div>
              <div>
                <span className="text-text-muted">Entity ID:</span>{' '}
                <span className="font-mono text-text">{selectedEntry.entity_id || 'N/A'}</span>
              </div>
              <div>
                <span className="text-text-muted">Triggered At:</span>{' '}
                <span className="text-text">{new Date(selectedEntry.occurred_at).toLocaleString()}</span>
              </div>
              <div>
                <span className="text-text-muted">Actor:</span>{' '}
                <span className="text-text font-medium">{selectedEntry.admin_user_id ? `Admin (${selectedEntry.admin_user_id})` : 'System Engine'}</span>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Old Value */}
              <div>
                <div className="text-xs font-bold uppercase tracking-wider text-text-muted mb-1.5">
                  Previous State (Old)
                </div>
                <div className="p-3 bg-bg rounded-card border border-border text-[11px] font-mono text-text overflow-auto max-h-64">
                  {selectedEntry.old_value ? (
                    <pre>{JSON.stringify(selectedEntry.old_value, null, 2)}</pre>
                  ) : (
                    <span className="text-text-muted italic">null (Newly created)</span>
                  )}
                </div>
              </div>

              {/* New Value */}
              <div>
                <div className="text-xs font-bold uppercase tracking-wider text-text-muted mb-1.5">
                  Applied State (New)
                </div>
                <div className="p-3 bg-bg rounded-card border border-border text-[11px] font-mono text-text overflow-auto max-h-64">
                  {selectedEntry.new_value ? (
                    <pre>{JSON.stringify(selectedEntry.new_value, null, 2)}</pre>
                  ) : (
                    <span className="text-text-muted italic">null (Deleted/Terminated)</span>
                  )}
                </div>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <Button variant="secondary" size="sm" onClick={() => setSelectedEntry(null)}>
                Close
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};
