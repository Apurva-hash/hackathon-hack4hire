import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../../services/apiClient';
import { ServiceCategory, NearbyTechnician, RequestUrgency } from '../../types';
import { InteractiveMap, MapMarker } from '../../components/common/InteractiveMap';
import { Card } from '../../components/common/Card';
import { Button } from '../../components/common/Button';
import { Input } from '../../components/common/Input';
import { Badge } from '../../components/common/Badge';
import { Skeleton } from '../../components/common/Skeleton';
import { useToast } from '../../components/common/Toast';
import { StarIcon, ClockIcon, NavigationIcon } from '../../components/common/Icons';

export const BookService: React.FC = () => {
  const navigate = useNavigate();
  const { success, error: toastError } = useToast();

  const [categories, setCategories] = useState<ServiceCategory[]>([]);
  const [selectedCatId, setSelectedCatId] = useState<string>('');
  const [nearbyTechs, setNearbyTechs] = useState<NearbyTechnician[]>([]);
  const [loadingCats, setLoadingCats] = useState(true);
  const [loadingTechs, setLoadingTechs] = useState(false);

  // Customer Location & Form fields
  const [customerLat, setCustomerLat] = useState<number>(12.9716);
  const [customerLng, setCustomerLng] = useState<number>(77.5946);
  const [address, setAddress] = useState<string>('Brigade Road, Bangalore Center');
  const [description, setDescription] = useState<string>('');
  const [urgency, setUrgency] = useState<RequestUrgency>('normal');
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);

  // Submitting & Matching Screen State
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [matchingBookingId, setMatchingBookingId] = useState<string | null>(null);
  const [matchingSeconds, setMatchingSeconds] = useState(0);

  // Load Categories on mount
  useEffect(() => {
    const fetchCats = async () => {
      try {
        const data = await api.customer.getCategories();
        const catsList: ServiceCategory[] = Array.isArray(data)
          ? data
          : (data as any)?.categories || (data as any)?.data || [];
        setCategories(catsList);
        if (catsList.length > 0) {
          setSelectedCatId((prev) => prev || catsList[0].id);
        }
      } catch (err: any) {
        toastError('Failed to load categories', err.message);
      } finally {
        setLoadingCats(false);
      }
    };
    fetchCats();
  }, []);

  // Fetch Nearby Technicians when category or location changes
  useEffect(() => {
    if (!selectedCatId) return;
    const fetchNearby = async () => {
      setLoadingTechs(true);
      try {
        const data = await api.customer.getNearbyTechnicians({
          lat: customerLat,
          lng: customerLng,
          category_id: selectedCatId,
          radius_km: 25,
        });
        setNearbyTechs(data.technicians || []);
      } catch (err: any) {
        console.error('Nearby techs error:', err);
      } finally {
        setLoadingTechs(false);
      }
    };
    fetchNearby();
  }, [selectedCatId, customerLat, customerLng]);

  // Matching timer effect
  useEffect(() => {
    let timer: any;
    if (matchingBookingId) {
      timer = setInterval(() => {
        setMatchingSeconds((s) => s + 1);
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [matchingBookingId]);

  // Handle Photo selection preview
  const handlePhotoUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setPhotoPreview(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const selectedCategory = categories.find((c) => c.id === selectedCatId);

  // Price estimate calculation: 45 min baseline duration × category rate
  const estimatedDuration = urgency === 'critical' ? 30 : 45;
  const priceEstimate = selectedCategory
    ? Math.round(estimatedDuration * selectedCategory.price_per_minute * 10)
    : 150;

  // Closest technician estimate
  const closestTech = nearbyTechs.length > 0 ? nearbyTechs[0] : null;

  const handleBook = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCatId || !address) {
      toastError('Missing fields', 'Please select a category and confirm your address.');
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await api.customer.createBooking({
        category_id: selectedCatId,
        description: description || `Diagnostic and repair request for ${selectedCategory?.name || 'appliance'}.`,
        address,
        lat: customerLat,
        lng: customerLng,
        urgency,
      });

      success('Booking Created!', 'DispatchGrid is finding the best technician...');
      setMatchingBookingId(res.booking_id);
    } catch (err: any) {
      toastError('Booking Failed', err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancelMatching = async () => {
    if (matchingBookingId) {
      try {
        await api.customer.cancelBooking(matchingBookingId);
        success('Request Cancelled', 'Your service booking request has been withdrawn.');
        setMatchingBookingId(null);
        setMatchingSeconds(0);
      } catch (err: any) {
        toastError('Cancellation Failed', err.message);
      }
    }
  };

  // Convert nearby techs to map markers
  const techMarkers: MapMarker[] = nearbyTechs.map((t, idx) => ({
    id: t.id,
    title: t.name,
    subtitle: `${t.distance_km} km • ~${t.eta_minutes} min`,
    type: 'technician',
    lat: customerLat + (idx === 0 ? 0.015 : idx === 1 ? -0.012 : 0.02) * (idx % 2 === 0 ? 1 : -1),
    lng: customerLng + (idx === 0 ? -0.018 : idx === 1 ? 0.014 : -0.015) * (idx % 2 === 0 ? -1 : 1),
    eta_minutes: t.eta_minutes,
    distance_km: t.distance_km,
    rating: t.avg_rating,
  }));

  // ── MATCHING SCREEN (Finding your technician) ────────────────────────────────
  if (matchingBookingId) {
    return (
      <div className="max-w-xl mx-auto py-8 px-4 text-center">
        <Card padding="lg" className="border-primary/40 relative overflow-hidden">
          <div className="w-20 h-20 rounded-full bg-primary-tint text-primary flex items-center justify-center mx-auto mb-5 radar-animation">
            <span className="text-3xl animate-bounce">⚡</span>
          </div>

          <Badge variant="progress" size="md" className="mb-2">
            Searching Nearby Certified Techs
          </Badge>

          <h2 className="text-xl font-bold text-text mt-2">
            Matching with the Best Technician...
          </h2>
          <p className="text-xs text-text-muted mt-1 max-w-sm mx-auto">
            DispatchGrid is evaluating real-time distance, skill level, ratings, and current workload.
          </p>

          <div className="my-6 p-4 rounded-card bg-surface-alt border border-border inline-flex items-center gap-4 text-left">
            <div className="text-2xl">{selectedCategory?.icon || '🛠️'}</div>
            <div>
              <div className="text-xs font-bold text-text">{selectedCategory?.name}</div>
              <div className="text-[11px] text-text-muted">{address}</div>
              <div className="text-[11px] font-semibold text-primary mt-0.5">
                Urgency: <span className="capitalize">{urgency}</span> • Elapsed: {matchingSeconds}s
              </div>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <Button
              variant="outline"
              size="md"
              onClick={handleCancelMatching}
              className="w-full sm:w-auto"
            >
              Cancel Request
            </Button>
            <Button
              variant="primary"
              size="md"
              onClick={() => navigate('/customer/dashboard')}
              className="w-full sm:w-auto"
            >
              Go to Live Tracking →
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  // ── BOOKING SCREEN (Map + Bottom Sheet) ──────────────────────────────────────
  return (
    <div className="max-w-4xl mx-auto space-y-5">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-text">
          Book On-Demand Service
        </h1>
        <p className="text-xs text-text-muted mt-0.5">
          Uber-style live technician matching with SLA guarantee and transparent pricing.
        </p>
      </div>

      {/* Map View showing nearby technicians */}
      <div className="relative">
        <InteractiveMap
          customerLocation={{ lat: customerLat, lng: customerLng, label: address }}
          technicians={techMarkers}
          height="320px"
        />

        {/* Floating ETA preview card */}
        <div className="absolute top-3 left-3 bg-surface/95 backdrop-blur-sm px-3.5 py-2 rounded-card border border-border shadow-warmMd flex items-center gap-2.5 z-10">
          <div className="w-2.5 h-2.5 rounded-full bg-status-success animate-pulse" />
          <div className="text-xs">
            <span className="font-bold text-text">
              {closestTech ? `~${closestTech.eta_minutes} min away` : 'Matching nearby'}
            </span>
            <span className="text-[11px] text-text-muted ml-1.5">
              ({nearbyTechs.length} available)
            </span>
          </div>
        </div>
      </div>

      {/* Booking Form Card */}
      <form onSubmit={handleBook} className="space-y-6">
        <Card padding="lg" className="space-y-6">
          {/* 1. Service Category Picker */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-bold text-text uppercase tracking-wider">
                1. Select Appliance / Category
              </label>
              {selectedCategory && (
                <span className="text-xs font-bold text-primary">
                  ₹{selectedCategory.price_per_minute * 10}/hr rate
                </span>
              )}
            </div>

            {loadingCats ? (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                {[1, 2, 3, 4].map((i) => (
                  <Skeleton key={i} height="80px" />
                ))}
              </div>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                {categories.map((cat) => {
                  const isSelected = cat.id === selectedCatId;
                  return (
                    <button
                      key={cat.id}
                      type="button"
                      onClick={() => setSelectedCatId(cat.id)}
                      className={`p-3.5 rounded-card border text-left transition-all min-h-[48px] select-none ${
                        isSelected
                          ? 'border-primary bg-primary-tint text-text shadow-warmSm ring-2 ring-primary/30'
                          : 'border-border bg-surface hover:bg-surface-alt text-text'
                      }`}
                    >
                      <div className="text-2xl mb-1">{cat.icon || '🔧'}</div>
                      <div className="font-bold text-xs leading-snug">{cat.name}</div>
                      <div className="text-[10px] text-text-muted mt-0.5 line-clamp-1">
                        {cat.description || 'Verified Service'}
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* 2. Problem Description & Photo Upload */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-text uppercase tracking-wider mb-1">
                2. Describe the Issue (Optional)
              </label>
              <textarea
                rows={3}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="e.g. AC compressor humming loudly and not cooling room properly"
                className="w-full px-3.5 py-2 rounded-input bg-surface text-text border border-border text-xs focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-text uppercase tracking-wider mb-1">
                Attach Photo / Proof
              </label>
              <div className="flex items-center gap-3">
                <label className="flex-1 border-2 border-dashed border-border rounded-input p-3 text-center cursor-pointer hover:bg-surface-alt transition-colors min-h-[76px] flex flex-col items-center justify-center">
                  <span className="text-xs font-semibold text-primary">+ Upload Photo</span>
                  <span className="text-[10px] text-text-muted">JPG or PNG (optional)</span>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handlePhotoUpload}
                    className="hidden"
                  />
                </label>
                {photoPreview && (
                  <div className="relative w-16 h-16 rounded-card overflow-hidden border border-border flex-shrink-0">
                    <img
                      src={photoPreview}
                      alt="Uploaded proof"
                      className="w-full h-full object-cover"
                    />
                    <button
                      type="button"
                      onClick={() => setPhotoPreview(null)}
                      className="absolute top-0 right-0 bg-black/60 text-white w-4 h-4 text-[10px] flex items-center justify-center"
                    >
                      ✕
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* 3. Address & Urgency Selector */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-text uppercase tracking-wider mb-1">
                3. Service Location *
              </label>
              <Input
                type="text"
                required
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                placeholder="Street address, apartment, or landmark"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-text uppercase tracking-wider mb-1">
                4. Urgency & SLA Priority
              </label>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { id: 'normal', label: 'Normal', note: 'Standard SLA' },
                  { id: 'high', label: 'Urgent', note: 'Within 30m' },
                  { id: 'critical', label: 'Emergency', note: 'Top priority' },
                ].map((u) => {
                  const isSelected = urgency === u.id;
                  return (
                    <button
                      key={u.id}
                      type="button"
                      onClick={() => setUrgency(u.id as RequestUrgency)}
                      className={`p-2 rounded-input border text-left transition-all min-h-[44px] ${
                        isSelected
                          ? u.id === 'critical'
                            ? 'border-status-error bg-status-error/15 text-status-error font-bold'
                            : 'border-primary bg-primary-tint text-primary font-bold'
                          : 'border-border bg-surface text-text hover:bg-surface-alt'
                      }`}
                    >
                      <div className="text-xs font-bold">{u.label}</div>
                      <div className="text-[10px] text-text-muted font-normal">{u.note}</div>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* 4. Price & ETA Summary Bar */}
          <div className="p-4 rounded-card bg-surface-alt border border-border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div>
              <div className="text-xs text-text-muted">Estimated Cost & Arrival</div>
              <div className="flex items-baseline gap-2 mt-0.5">
                <span className="text-xl font-bold text-text">₹{priceEstimate}</span>
                <span className="text-xs text-text-muted">
                  (~{estimatedDuration} min diagnostic)
                </span>
              </div>
            </div>

            <div className="text-right text-xs">
              <span className="text-text-muted">Estimated Arrival:</span>
              <span className="ml-1 font-bold text-status-success">
                {closestTech ? `~${closestTech.eta_minutes} mins` : 'Immediate dispatch'}
              </span>
            </div>
          </div>

          {/* Submit Button */}
          <Button
            type="submit"
            variant="primary"
            size="lg"
            loading={isSubmitting}
            className="w-full text-base"
          >
            Book Now • Find Technician
          </Button>
        </Card>
      </form>
    </div>
  );
};
