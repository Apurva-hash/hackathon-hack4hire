import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/apiClient';
import { CustomerProfile as CustomerProfileType, SavedAddress } from '../../types';
import { Card } from '../../components/common/Card';
import { Button } from '../../components/common/Button';
import { Input } from '../../components/common/Input';
import { Modal } from '../../components/common/Modal';
import { Skeleton } from '../../components/common/Skeleton';
import { useToast } from '../../components/common/Toast';
import { MapPinIcon, UserIcon, BellIcon } from '../../components/common/Icons';

export const CustomerProfile: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { success, error: toastError } = useToast();

  const [profile, setProfile] = useState<CustomerProfileType | null>(null);
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [addresses, setAddresses] = useState<SavedAddress[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Add Address Modal
  const [addressModalOpen, setAddressModalOpen] = useState(false);
  const [newLabel, setNewLabel] = useState('Home');
  const [newAddress, setNewAddress] = useState('');
  const [newLat, setNewLat] = useState(12.9716);
  const [newLng, setNewLng] = useState(77.5946);
  const [addingAddress, setAddingAddress] = useState(false);

  // Notification Preferences (local state)
  const [smsAlerts, setSmsAlerts] = useState(true);
  const [emailReceipts, setEmailReceipts] = useState(true);

  // Logout confirmation
  const [logoutModalOpen, setLogoutModalOpen] = useState(false);

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const data = await api.customer.getProfile();
        setProfile(data);
        setName(data.name || '');
        setPhone(data.phone || '');
        setAddresses(data.saved_addresses || []);
      } catch (err: any) {
        toastError('Failed to load profile', err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchProfile();
  }, []);

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.customer.updateProfile({ name, phone });
      success('Profile Saved', 'Your contact details have been updated.');
    } catch (err: any) {
      toastError('Update Failed', err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleAddAddress = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newAddress.trim()) return;
    setAddingAddress(true);
    try {
      const res = await api.customer.addAddress({
        label: newLabel,
        address: newAddress,
        lat: newLat,
        lng: newLng,
      });
      setAddresses(res.addresses || []);
      success('Address Saved', `${newLabel} address added.`);
      setAddressModalOpen(false);
      setNewAddress('');
    } catch (err: any) {
      toastError('Failed to save address', err.message);
    } finally {
      setAddingAddress(false);
    }
  };

  const handleDeleteAddress = async (index: number) => {
    try {
      const res = await api.customer.deleteAddress(index);
      setAddresses(res.addresses || []);
      success('Address Removed', 'Saved address deleted.');
    } catch (err: any) {
      toastError('Delete Failed', err.message);
    }
  };

  if (loading) {
    return (
      <div className="max-w-2xl mx-auto space-y-4">
        <Skeleton height="160px" />
        <Skeleton height="160px" />
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-text">Customer Profile & Settings</h1>
        <p className="text-xs text-text-muted mt-0.5">
          Manage your account information, default addresses, and service alerts
        </p>
      </div>

      {/* Account Info Card */}
      <form onSubmit={handleSaveProfile}>
        <Card padding="lg" className="space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b border-border">
            <div className="w-12 h-12 rounded-full bg-primary text-white font-bold text-lg flex items-center justify-center shadow-warmSm">
              {name.charAt(0) || 'U'}
            </div>
            <div>
              <h2 className="text-base font-bold text-text">{name || 'Customer'}</h2>
              <p className="text-xs text-text-muted">{profile?.email || user?.email}</p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Full Name"
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            <Input
              label="Phone Number"
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+91 98765 43210"
            />
          </div>

          <div className="flex justify-end pt-2">
            <Button variant="primary" size="md" type="submit" loading={saving}>
              Save Profile Changes
            </Button>
          </div>
        </Card>
      </form>

      {/* Saved Addresses Card */}
      <Card padding="lg" className="space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-border">
          <div>
            <h3 className="text-sm font-bold text-text">Saved Service Addresses</h3>
            <p className="text-xs text-text-muted mt-0.5">Quickly select when booking technicians</p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setAddressModalOpen(true)}
            icon={<span>＋</span>}
          >
            Add Address
          </Button>
        </div>

        {addresses.length === 0 ? (
          <div className="text-center py-6 text-xs text-text-muted">
            No saved addresses yet. Add your home or office for 1-click booking.
          </div>
        ) : (
          <div className="space-y-2.5">
            {addresses.map((addr, idx) => (
              <div
                key={idx}
                className="p-3.5 rounded-card bg-surface-alt border border-border flex items-center justify-between gap-3"
              >
                <div className="flex items-start gap-2.5">
                  <MapPinIcon size={18} className="text-primary flex-shrink-0 mt-0.5" />
                  <div>
                    <span className="text-xs font-bold text-text bg-primary-tint/60 text-primary px-1.5 py-0.5 rounded text-[10px] uppercase">
                      {addr.label}
                    </span>
                    <p className="text-xs text-text font-medium mt-1">{addr.address}</p>
                  </div>
                </div>
                <button
                  onClick={() => handleDeleteAddress(idx)}
                  className="text-xs text-status-error font-semibold hover:underline px-2 py-1"
                >
                  Delete
                </button>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Notification Preferences */}
      <Card padding="lg" className="space-y-4">
        <h3 className="text-sm font-bold text-text pb-2 border-b border-border">
          Notification Preferences
        </h3>
        <div className="space-y-3">
          <label className="flex items-center justify-between cursor-pointer py-1">
            <div>
              <div className="text-xs font-bold text-text">SMS & In-App Status Updates</div>
              <div className="text-[11px] text-text-muted">
                Receive real-time alerts when technician accepts and arrives
              </div>
            </div>
            <input
              type="checkbox"
              checked={smsAlerts}
              onChange={(e) => setSmsAlerts(e.target.checked)}
              className="w-4 h-4 text-primary rounded border-border focus:ring-primary"
            />
          </label>

          <label className="flex items-center justify-between cursor-pointer py-1">
            <div>
              <div className="text-xs font-bold text-text">Email Invoices & Service Proof</div>
              <div className="text-[11px] text-text-muted">
                Get itemized digital receipts after service completion
              </div>
            </div>
            <input
              type="checkbox"
              checked={emailReceipts}
              onChange={(e) => setEmailReceipts(e.target.checked)}
              className="w-4 h-4 text-primary rounded border-border focus:ring-primary"
            />
          </label>
        </div>
      </Card>

      {/* Log Out */}
      <div className="pt-2">
        <Button
          variant="danger"
          size="md"
          className="w-full"
          onClick={() => setLogoutModalOpen(true)}
        >
          Sign Out of DispatchGrid
        </Button>
      </div>

      {/* Add Address Modal */}
      <Modal
        isOpen={addressModalOpen}
        onClose={() => setAddressModalOpen(false)}
        title="Add Saved Address"
        description="Enter label and address coordinates for quick service dispatch."
      >
        <form onSubmit={handleAddAddress} className="space-y-4 py-2">
          <div>
            <label className="block text-xs font-semibold text-text uppercase tracking-wider mb-1">
              Address Label
            </label>
            <div className="grid grid-cols-3 gap-2">
              {['Home', 'Office', 'Other'].map((l) => (
                <button
                  key={l}
                  type="button"
                  onClick={() => setNewLabel(l)}
                  className={`py-2 rounded-input border text-xs font-bold transition min-h-[44px] ${
                    newLabel === l
                      ? 'border-primary bg-primary-tint text-primary'
                      : 'border-border bg-surface text-text hover:bg-surface-alt'
                  }`}
                >
                  {l}
                </button>
              ))}
            </div>
          </div>

          <Input
            label="Street Address / Landmark *"
            type="text"
            required
            value={newAddress}
            onChange={(e) => setNewAddress(e.target.value)}
            placeholder="e.g. Flat 302, Palm Heights, Indiranagar"
          />

          <div className="flex justify-end gap-2 pt-2 border-t border-border">
            <Button
              variant="secondary"
              size="md"
              type="button"
              onClick={() => setAddressModalOpen(false)}
            >
              Cancel
            </Button>
            <Button variant="primary" size="md" type="submit" loading={addingAddress}>
              Save Address
            </Button>
          </div>
        </form>
      </Modal>

      {/* Logout Confirmation Modal */}
      <Modal
        isOpen={logoutModalOpen}
        onClose={() => setLogoutModalOpen(false)}
        title="Sign Out"
        description="Are you sure you want to end your current session?"
        isConfirmation
        confirmLabel="Sign Out"
        confirmVariant="danger"
        onConfirm={() => {
          logout();
          navigate('/login');
        }}
      />
    </div>
  );
};
