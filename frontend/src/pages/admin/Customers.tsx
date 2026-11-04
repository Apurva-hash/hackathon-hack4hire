import React, { useState, useEffect } from 'react';
import { api } from '../../services/apiClient';
import { Card } from '../../components/common/Card';
import { Button } from '../../components/common/Button';
import { Badge } from '../../components/common/Badge';
import { Drawer } from '../../components/common/Drawer';
import { Skeleton } from '../../components/common/Skeleton';
import { EmptyState } from '../../components/common/EmptyState';
import { useToast } from '../../components/common/Toast';
import { SearchIcon, RefreshCwIcon, UserIcon } from '../../components/common/Icons';

export const Customers: React.FC = () => {
  const { success, error: toastError } = useToast();

  const [customers, setCustomers] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  // Selected customer for detail drawer
  const [selectedCustomerId, setSelectedCustomerId] = useState<string | null>(null);
  const [customerDetail, setCustomerDetail] = useState<any | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const fetchCustomers = async () => {
    setLoading(true);
    try {
      const data = await api.admin.getCustomers({ search: searchTerm || undefined, limit: 50 });
      setCustomers(data.customers || []);
      setTotal(data.total || 0);
    } catch (err: any) {
      toastError('Failed to load customers', err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCustomers();
  }, []);

  useEffect(() => {
    if (selectedCustomerId) {
      setDetailLoading(true);
      api.admin
        .getCustomer(selectedCustomerId)
        .then((res) => setCustomerDetail(res))
        .catch((e) => toastError('Detail load error', e.message))
        .finally(() => setDetailLoading(false));
    } else {
      setCustomerDetail(null);
    }
  }, [selectedCustomerId]);

  const handleToggleActive = async (cust: any) => {
    try {
      const nextActive = !cust.is_active;
      await api.admin.updateCustomer(cust.id, { is_active: nextActive });
      success(
        nextActive ? 'Account Activated' : 'Account Suspended',
        `${cust.name} status updated.`
      );
      fetchCustomers();
      if (customerDetail?.id === cust.id) {
        setCustomerDetail((prev: any) => ({ ...prev, is_active: nextActive }));
      }
    } catch (err: any) {
      toastError('Status update failed', err.message);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-text">Customer Registry</h1>
          <p className="text-xs text-text-muted mt-0.5">
            Registered customer accounts, booking volumes, and service histories
          </p>
        </div>

        <Button
          variant="secondary"
          size="sm"
          onClick={fetchCustomers}
          icon={<RefreshCwIcon size={14} />}
        >
          Refresh List
        </Button>
      </div>

      {/* Search Bar */}
      <Card padding="md" className="border-border">
        <div className="relative w-full sm:w-96">
          <input
            type="text"
            placeholder="Search by customer name, phone, email..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3.5 py-2 rounded-input bg-surface text-text border border-border text-xs min-h-[44px]"
          />
          <div className="absolute left-3 top-3 text-text-muted pointer-events-none">
            <SearchIcon size={16} />
          </div>
        </div>
      </Card>

      {/* Customer Table */}
      <Card padding="none" className="border-border overflow-hidden">
        {loading ? (
          <div className="p-6 space-y-3">
            <Skeleton height="50px" />
            <Skeleton height="50px" />
            <Skeleton height="50px" />
          </div>
        ) : customers.length === 0 ? (
          <EmptyState
            title="No Customers Found"
            description="No customer accounts match your search query."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-surface-alt border-b border-border text-text-muted font-bold uppercase tracking-wider">
                  <th className="py-3 px-4">Customer</th>
                  <th className="py-3 px-4">Phone</th>
                  <th className="py-3 px-4">Total Bookings</th>
                  <th className="py-3 px-4">Account Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {customers.map((cust) => (
                  <tr
                    key={cust.id}
                    onClick={() => setSelectedCustomerId(cust.id)}
                    className="hover:bg-surface-alt/70 transition-colors cursor-pointer"
                  >
                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-full bg-primary-tint text-primary font-bold flex items-center justify-center text-xs">
                          {cust.name.charAt(0)}
                        </div>
                        <span className="font-bold text-text">{cust.name}</span>
                      </div>
                    </td>
                    <td className="py-3.5 px-4 text-text-muted">{cust.phone || '—'}</td>
                    <td className="py-3.5 px-4 font-bold text-text">{cust.total_bookings} orders</td>
                    <td className="py-3.5 px-4">
                      <Badge variant={cust.is_active ? 'success' : 'neutral'} size="sm">
                        {cust.is_active ? 'Active' : 'Suspended'}
                      </Badge>
                    </td>
                    <td className="py-3.5 px-4 text-right space-x-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleToggleActive(cust);
                        }}
                        className={cust.is_active ? 'text-status-error' : 'text-status-success'}
                      >
                        {cust.is_active ? 'Suspend' : 'Activate'}
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedCustomerId(cust.id);
                        }}
                      >
                        History →
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Customer Detail Drawer */}
      <Drawer
        isOpen={!!selectedCustomerId}
        onClose={() => setSelectedCustomerId(null)}
        title={customerDetail?.name || 'Customer Account'}
        size="md"
      >
        {detailLoading || !customerDetail ? (
          <div className="space-y-4">
            <Skeleton height="80px" />
            <Skeleton height="120px" />
          </div>
        ) : (
          <div className="space-y-5">
            <div className="p-4 rounded-card bg-surface-alt border border-border space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-text-muted">Account Status:</span>
                <Badge variant={customerDetail.is_active ? 'success' : 'neutral'} size="sm">
                  {customerDetail.is_active ? 'Active' : 'Suspended'}
                </Badge>
              </div>
              <div className="flex justify-between">
                <span className="text-text-muted">Contact Phone:</span>
                <span className="font-bold text-text">{customerDetail.phone || '—'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-muted">Lifetime Orders:</span>
                <span className="font-bold text-text">{customerDetail.total_bookings}</span>
              </div>
            </div>

            {/* Saved Addresses */}
            <div>
              <h4 className="text-xs font-bold text-text uppercase tracking-wider mb-2">
                Saved Locations ({customerDetail.saved_addresses?.length || 0})
              </h4>
              <div className="space-y-2">
                {customerDetail.saved_addresses?.map((addr: any, idx: number) => (
                  <div
                    key={idx}
                    className="p-3 rounded-card bg-surface border border-border text-xs"
                  >
                    <span className="font-bold text-primary text-[10px] uppercase">
                      {addr.label}
                    </span>
                    <p className="text-text mt-0.5">{addr.address}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Booking History */}
            <div>
              <h4 className="text-xs font-bold text-text uppercase tracking-wider mb-2">
                Recent Service History
              </h4>
              {!customerDetail.booking_history || customerDetail.booking_history.length === 0 ? (
                <div className="text-xs text-text-muted py-4 text-center">
                  No service bookings on record.
                </div>
              ) : (
                <div className="space-y-2 max-h-56 overflow-y-auto">
                  {customerDetail.booking_history.map((b: any) => (
                    <div
                      key={b.id}
                      className="p-3 rounded-card bg-surface-alt border border-border text-xs flex items-center justify-between"
                    >
                      <div>
                        <span className="font-bold text-text">Order #{b.id.slice(0, 8)}</span>
                        <div className="text-[10px] text-text-muted mt-0.5">
                          {b.created_at ? new Date(b.created_at).toLocaleDateString() : ''}
                        </div>
                      </div>
                      <span className="font-semibold text-primary capitalize">{b.status}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
};

