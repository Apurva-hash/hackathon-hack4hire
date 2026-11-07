import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/apiClient';
import { TechnicianProfile as TechProfileType, Rating } from '../../types';
import { Card } from '../../components/common/Card';
import { Button } from '../../components/common/Button';
import { Input } from '../../components/common/Input';
import { Badge } from '../../components/common/Badge';
import { Modal } from '../../components/common/Modal';
import { Skeleton } from '../../components/common/Skeleton';
import { useToast } from '../../components/common/Toast';
import { StarIcon, ShieldCheckIcon, UserIcon } from '../../components/common/Icons';

export const TechnicianProfile: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { success, error: toastError } = useToast();

  const [profile, setProfile] = useState<TechProfileType | null>(null);
  const [ratings, setRatings] = useState<Rating[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Form editable fields
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [bio, setBio] = useState('');
  const [radiusKm, setRadiusKm] = useState(15);
  const [maxJobs, setMaxJobs] = useState(3);

  const [logoutModalOpen, setLogoutModalOpen] = useState(false);

  useEffect(() => {
    Promise.all([api.technician.getProfile(), api.technician.getRatings()])
      .then(([profData, ratingsData]) => {
        setProfile(profData);
        setName(profData.name || '');
        setPhone(profData.phone || '');
        setBio(profData.bio || '');
        setRadiusKm(profData.service_radius_km || 15);
        setMaxJobs(profData.max_concurrent_jobs || 3);
        setRatings(ratingsData.ratings || []);
      })
      .catch((e) => toastError('Failed to load profile', e.message))
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.technician.updateProfile({
        name,
        phone,
        bio,
        service_radius_km: radiusKm,
        max_concurrent_jobs: maxJobs,
      });
      success('Profile Saved', 'Your dispatch preferences have been updated.');
    } catch (err: any) {
      toastError('Save failed', err.message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-2xl mx-auto space-y-4">
        <Skeleton height="180px" />
        <Skeleton height="200px" />
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-text">Technician Fleet Profile</h1>
        <p className="text-xs text-text-muted mt-0.5">
          Your certification level, service coverage radius, and verified reviews
        </p>
      </div>

      <form onSubmit={handleSave} className="space-y-6">
        <Card padding="lg" className="space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b border-border">
            <div className="w-14 h-14 rounded-full bg-primary text-white font-bold text-xl flex items-center justify-center shadow-warmSm">
              {name.charAt(0) || 'T'}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-text">{name || 'Technician'}</h2>
                <Badge variant={profile?.is_approved ? 'success' : 'pending'} size="sm">
                  {profile?.is_approved ? 'Approved Pro' : 'Pending Verification'}
                </Badge>
              </div>
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
              placeholder="+91 90000 00001"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-text uppercase tracking-wider mb-1">
              Professional Bio & Skills
            </label>
            <textarea
              rows={2}
              value={bio}
              onChange={(e) => setBio(e.target.value)}
              placeholder="e.g. Certified HVAC technician with 8 years of residential compressor repairs."
              className="w-full px-3.5 py-2 rounded-input bg-surface text-text border border-border text-xs focus:ring-2 focus:ring-primary focus:outline-none"
            />
          </div>

          {/* Service Radius Slider */}
          <div className="p-4 rounded-card bg-surface-alt border border-border space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-xs font-bold text-text block">Service Coverage Radius</span>
                <span className="text-[11px] text-text-muted">
                  Max travel distance from your current location
                </span>
              </div>
              <span className="text-sm font-bold text-primary">{radiusKm} km</span>
            </div>
            <input
              type="range"
              min="5"
              max="50"
              step="5"
              value={radiusKm}
              onChange={(e) => setRadiusKm(parseInt(e.target.value))}
              className="w-full accent-primary cursor-pointer"
            />
          </div>

          {/* Certification Badge Display */}
          <div className="p-4 rounded-card bg-primary-tint/30 border border-primary/20 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <ShieldCheckIcon size={20} className="text-primary flex-shrink-0" />
              <div>
                <div className="text-xs font-bold text-text">
                  Skill Certification: Level {profile?.certification_level || 3} of 5
                </div>
                <div className="text-[11px] text-text-muted">
                  Eligible for high-risk and emergency priority calls
                </div>
              </div>
            </div>
            <span className="text-xs font-bold text-primary bg-surface px-2.5 py-1 rounded-full border border-primary/30">
              Verified ✓
            </span>
          </div>

          <div className="flex justify-end pt-2">
            <Button variant="primary" size="md" type="submit" loading={saving}>
              Save Changes
            </Button>
          </div>
        </Card>
      </form>

      {/* Customer Reviews & Feedback Card */}
      <Card padding="lg" className="space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-border">
          <div>
            <h3 className="text-sm font-bold text-text">Customer Reviews & Ratings</h3>
            <p className="text-xs text-text-muted mt-0.5">
              Average: {profile?.avg_rating || 5.0} ★ based on {ratings.length} reviews
            </p>
          </div>
          <span className="text-sm font-bold text-accent flex items-center gap-1">
            <StarIcon size={18} filled className="text-accent" />
            <span>{profile?.avg_rating || 5.0}</span>
          </span>
        </div>

        {ratings.length === 0 ? (
          <div className="text-center py-6 text-xs text-text-muted">
            No customer ratings recorded yet. Ratings will show up after completing jobs.
          </div>
        ) : (
          <div className="divide-y divide-border">
            {ratings.map((r) => (
              <div key={r.id} className="py-3 text-xs space-y-1">
                <div className="flex items-center justify-between">
                  <span className="flex items-center text-accent font-bold">
                    {'★'.repeat(Math.round(r.score))}
                  </span>
                  <span className="text-[10px] text-text-muted">
                    {new Date(r.created_at).toLocaleDateString()}
                  </span>
                </div>
                <p className="text-text font-medium">{r.feedback_text || 'Professional service.'}</p>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Sign out */}
      <Button
        variant="danger"
        size="md"
        className="w-full"
        onClick={() => setLogoutModalOpen(true)}
      >
        Sign Out of Technician Portal
      </Button>

      {/* Logout Confirmation */}
      <Modal
        isOpen={logoutModalOpen}
        onClose={() => setLogoutModalOpen(false)}
        title="Sign Out"
        description="Are you sure you want to go offline and end your technician shift?"
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
