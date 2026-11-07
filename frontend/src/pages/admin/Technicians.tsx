import React, { useState, useEffect } from 'react';
import { api } from '../../services/apiClient';
import { TechnicianProfile } from '../../types';
import { Card } from '../../components/common/Card';
import { Button } from '../../components/common/Button';
import { StatusBadge, Badge } from '../../components/common/Badge';
import { Drawer } from '../../components/common/Drawer';
import { Modal } from '../../components/common/Modal';
import { Input } from '../../components/common/Input';
import { Skeleton } from '../../components/common/Skeleton';
import { EmptyState } from '../../components/common/EmptyState';
import { useToast } from '../../components/common/Toast';
import { SearchIcon, RefreshCwIcon, StarIcon, CheckIcon } from '../../components/common/Icons';

export const Technicians: React.FC = () => {
  const { success, error: toastError, warning } = useToast();

  const [techs, setTechs] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  // Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [onlineFilter, setOnlineFilter] = useState('');
  const [approvalFilter, setApprovalFilter] = useState('');

  // Edit / Inspect Modal State
  const [selectedTech, setSelectedTech] = useState<any | null>(null);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editName, setEditName] = useState('');
  const [editPhone, setEditPhone] = useState('');
  const [editCert, setEditCert] = useState(3);
  const [editRadius, setEditRadius] = useState(15);
  const [editMaxJobs, setEditMaxJobs] = useState(3);
  const [savingEdit, setSavingEdit] = useState(false);

  // Suspend / Approve confirmation
  const [actionTech, setActionTech] = useState<any | null>(null);
  const [actionType, setActionType] = useState<'approve' | 'suspend' | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  const fetchTechnicians = async () => {
    setLoading(true);
    try {
      const data = await api.admin.getTechnicians({
        search: searchTerm || undefined,
        is_online: onlineFilter === '' ? undefined : onlineFilter === 'true',
        is_approved: approvalFilter === '' ? undefined : approvalFilter === 'true',
        limit: 100,
      });
      setTechs(data.technicians || []);
      setTotal(data.total || 0);
    } catch (err: any) {
      toastError('Failed to load fleet', err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTechnicians();
  }, [onlineFilter, approvalFilter]);

  const openEditModal = (t: any) => {
    setSelectedTech(t);
    setEditName(t.name);
    setEditPhone(t.phone || '');
    setEditCert(t.certification_level || 3);
    setEditRadius(t.service_radius_km || 15);
    setEditMaxJobs(t.max_concurrent_jobs || 3);
    setEditModalOpen(true);
  };

  const handleSaveEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTech) return;
    setSavingEdit(true);
    try {
      await api.admin.updateTechnician(selectedTech.id, {
        name: editName,
        phone: editPhone,
        certification_level: editCert,
        service_radius_km: editRadius,
        max_concurrent_jobs: editMaxJobs,
      });
      success('Technician Updated', 'Profile modifications saved.');
      setEditModalOpen(false);
      fetchTechnicians();
    } catch (err: any) {
      toastError('Update failed', err.message);
    } finally {
      setSavingEdit(false);
    }
  };

  const handleConfirmAction = async () => {
    if (!actionTech || !actionType) return;
    setActionLoading(true);
    try {
      if (actionType === 'approve') {
        await api.admin.approveTechnician(actionTech.id);
        success('Technician Approved', `${actionTech.name} is now approved to accept jobs.`);
      } else {
        await api.admin.suspendTechnician(actionTech.id);
        warning('Technician Suspended', `${actionTech.name} has been paused from dispatch.`);
      }
      setActionType(null);
      setActionTech(null);
      fetchTechnicians();
    } catch (err: any) {
      toastError('Action failed', err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const filteredTechs = techs.filter((t) => {
    if (!searchTerm.trim()) return true;
    const q = searchTerm.toLowerCase();
    return (
      t.name.toLowerCase().includes(q) ||
      (t.phone || '').toLowerCase().includes(q) ||
      t.id.toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-text">Technician Fleet Management</h1>
          <p className="text-xs text-text-muted mt-0.5">
            Approve registered technicians, manage skill certifications, and inspect performance
          </p>
        </div>

        <Button
          variant="secondary"
          size="sm"
          onClick={fetchTechnicians}
          icon={<RefreshCwIcon size={14} />}
        >
          Refresh Fleet
        </Button>
      </div>

      {/* Filter Toolbar */}
      <Card padding="md" className="border-border">
        <div className="flex flex-col md:flex-row items-center justify-between gap-3">
          <div className="relative w-full md:w-80">
            <input
              type="text"
              placeholder="Search by name, phone, ID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3.5 py-2 rounded-input bg-surface text-text border border-border text-xs min-h-[44px]"
            />
            <div className="absolute left-3 top-3 text-text-muted pointer-events-none">
              <SearchIcon size={16} />
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
            {/* Availability */}
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-text-muted">Duty:</span>
              <select
                value={onlineFilter}
                onChange={(e) => setOnlineFilter(e.target.value)}
                className="px-3 py-2 rounded-input border border-border text-xs bg-surface text-text min-h-[44px]"
              >
                <option value="">All Duty States</option>
                <option value="true">Online (On Duty)</option>
                <option value="false">Offline (Off Duty)</option>
              </select>
            </div>

            {/* Approval */}
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-text-muted">Approval:</span>
              <select
                value={approvalFilter}
                onChange={(e) => setApprovalFilter(e.target.value)}
                className="px-3 py-2 rounded-input border border-border text-xs bg-surface text-text min-h-[44px]"
              >
                <option value="">All Verification States</option>
                <option value="true">Approved</option>
                <option value="false">Pending Approval</option>
              </select>
            </div>
          </div>
        </div>
      </Card>

      {/* Technicians Table */}
      <Card padding="none" className="border-border overflow-hidden">
        {loading ? (
          <div className="p-6 space-y-3">
            <Skeleton height="50px" />
            <Skeleton height="50px" />
            <Skeleton height="50px" />
          </div>
        ) : filteredTechs.length === 0 ? (
          <EmptyState
            title="No Technicians Found"
            description="No fleet technicians match your query."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-surface-alt border-b border-border text-text-muted font-bold uppercase tracking-wider">
                  <th className="py-3 px-4">Technician</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Verification</th>
                  <th className="py-3 px-4">Certification</th>
                  <th className="py-3 px-4">Performance</th>
                  <th className="py-3 px-4">Acceptance</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filteredTechs.map((tech) => (
                  <tr key={tech.id} className="hover:bg-surface-alt/70 transition-colors">
                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-primary-tint text-primary font-bold flex items-center justify-center text-xs">
                          {tech.name.charAt(0)}
                        </div>
                        <div>
                          <div className="font-bold text-text">{tech.name}</div>
                          <div className="text-[11px] text-text-muted">{tech.phone || 'No phone'}</div>
                        </div>
                      </div>
                    </td>
                    <td className="py-3.5 px-4">
                      <span
                        className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-bold ${
                          tech.is_online
                            ? 'bg-status-success/15 text-status-success'
                            : 'bg-status-neutral/15 text-status-neutral'
                        }`}
                      >
                        <span
                          className={`w-1.5 h-1.5 rounded-full ${
                            tech.is_online ? 'bg-status-success animate-pulse' : 'bg-status-neutral'
                          }`}
                        />
                        <span>{tech.is_online ? 'Online' : 'Offline'}</span>
                      </span>
                    </td>
                    <td className="py-3.5 px-4">
                      {tech.is_suspended ? (
                        <Badge variant="error" size="sm">
                          Suspended
                        </Badge>
                      ) : tech.is_approved ? (
                        <Badge variant="success" size="sm">
                          Approved
                        </Badge>
                      ) : (
                        <Badge variant="pending" size="sm">
                          Pending
                        </Badge>
                      )}
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="font-bold text-text">
                        Level {tech.certification_level || 1}
                      </span>
                      <span className="text-[10px] text-text-muted block">
                        Radius: {tech.service_radius_km} km
                      </span>
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-1 font-bold text-accent">
                        <span>★ {tech.avg_rating}</span>
                      </div>
                      <span className="text-[10px] text-text-muted">
                        {tech.total_jobs_completed} jobs done
                      </span>
                    </td>
                    <td className="py-3.5 px-4 font-bold text-text">
                      {Math.round((tech.acceptance_rate || 1) * 100)}%
                    </td>
                    <td className="py-3.5 px-4 text-right space-x-1.5">
                      {!tech.is_approved ? (
                        <Button
                          variant="primary"
                          size="sm"
                          onClick={() => {
                            setActionTech(tech);
                            setActionType('approve');
                          }}
                        >
                          Approve ✓
                        </Button>
                      ) : tech.is_suspended ? (
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => {
                            setActionTech(tech);
                            setActionType('approve');
                          }}
                        >
                          Reactivate
                        </Button>
                      ) : (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setActionTech(tech);
                            setActionType('suspend');
                          }}
                          className="text-status-error"
                        >
                          Suspend
                        </Button>
                      )}

                      <Button variant="outline" size="sm" onClick={() => openEditModal(tech)}>
                        Edit
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Edit Technician Modal */}
      <Modal
        isOpen={editModalOpen}
        onClose={() => setEditModalOpen(false)}
        title="Edit Technician Fleet Profile"
        description="Modify operational boundaries, certification level, and max capacity."
      >
        <form onSubmit={handleSaveEdit} className="space-y-4 py-2">
          <Input
            label="Technician Name"
            type="text"
            required
            value={editName}
            onChange={(e) => setEditName(e.target.value)}
          />
          <Input
            label="Phone Number"
            type="tel"
            value={editPhone}
            onChange={(e) => setEditPhone(e.target.value)}
          />

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-text uppercase tracking-wider mb-1">
                Certification (1-5)
              </label>
              <input
                type="number"
                min="1"
                max="5"
                value={editCert}
                onChange={(e) => setEditCert(parseInt(e.target.value) || 1)}
                className="w-full min-h-[44px] px-3.5 py-2.5 rounded-input bg-surface text-text border border-border text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-text uppercase tracking-wider mb-1">
                Radius (km)
              </label>
              <input
                type="number"
                min="5"
                max="50"
                value={editRadius}
                onChange={(e) => setEditRadius(parseFloat(e.target.value) || 15)}
                className="w-full min-h-[44px] px-3.5 py-2.5 rounded-input bg-surface text-text border border-border text-sm"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-text uppercase tracking-wider mb-1">
              Max Concurrent Jobs
            </label>
            <input
              type="number"
              min="1"
              max="10"
              value={editMaxJobs}
              onChange={(e) => setEditMaxJobs(parseInt(e.target.value) || 3)}
              className="w-full min-h-[44px] px-3.5 py-2.5 rounded-input bg-surface text-text border border-border text-sm"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-border">
            <Button variant="secondary" size="md" onClick={() => setEditModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" size="md" type="submit" loading={savingEdit}>
              Save Changes
            </Button>
          </div>
        </form>
      </Modal>

      {/* Confirmation Modal for Approve / Suspend */}
      <Modal
        isOpen={!!actionType}
        onClose={() => {
          setActionType(null);
          setActionTech(null);
        }}
        title={actionType === 'approve' ? 'Approve Technician Pro' : 'Suspend Technician Access'}
        description={
          actionType === 'approve'
            ? `Authorize ${actionTech?.name} to receive live dispatch requests and go online.`
            : `Are you sure you want to suspend ${actionTech?.name}? Active offers will be cancelled and the technician will be forced offline.`
        }
        isConfirmation
        confirmLabel={actionType === 'approve' ? 'Approve' : 'Suspend'}
        confirmVariant={actionType === 'approve' ? 'primary' : 'danger'}
        confirmLoading={actionLoading}
        onConfirm={handleConfirmAction}
      />
    </div>
  );
};
