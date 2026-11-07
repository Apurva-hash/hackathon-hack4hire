import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../../services/apiClient';
import { InteractiveMap, MapMarker } from '../../components/common/InteractiveMap';
import { Card } from '../../components/common/Card';
import { Button } from '../../components/common/Button';
import { Badge, StatusBadge } from '../../components/common/Badge';
import { Skeleton } from '../../components/common/Skeleton';
import { useToast } from '../../components/common/Toast';
import {
  RefreshCwIcon,
  NavigationIcon,
  PhoneIcon,
  WrenchIcon,
} from '../../components/common/Icons';

export const LiveMap: React.FC = () => {
  const navigate = useNavigate();
  const { success, error: toastError } = useToast();

  const [techMarkers, setTechMarkers] = useState<MapMarker[]>([]);
  const [activeJobs, setActiveJobs] = useState<any[]>([]);
  const [selectedPin, setSelectedPin] = useState<MapMarker | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchLiveFleet = async () => {
    try {
      const [techRes, jobsRes] = await Promise.all([
        api.admin.getTechnicians({ limit: 100 }),
        api.admin.getJobs({ limit: 50 }),
      ]);

      // Center coords in Bangalore
      const centerLat = 12.9716;
      const centerLng = 77.5946;

      const markers: MapMarker[] = (techRes.technicians || []).map((t: any, idx: number) => {
        const angle = (idx / 5) * 2 * Math.PI;
        const radius = 0.02 + (idx % 3) * 0.01;
        return {
          id: t.id,
          lat: t.lat || centerLat + radius * Math.sin(angle),
          lng: t.lng || centerLng + radius * Math.cos(angle),
          title: t.name,
          subtitle: t.is_online ? 'Online & Available' : 'Currently Offline',
          type: 'technician',
          status: t.is_online ? 'online' : 'offline',
          rating: t.avg_rating,
        };
      });

      setTechMarkers(markers);
      setActiveJobs(
        (jobsRes.jobs || []).filter((j: any) =>
          ['requested', 'matching', 'assigned', 'accepted', 'en_route', 'in_progress'].includes(
            j.status
          )
        )
      );
    } catch (err: any) {
      toastError('Live Map Error', err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLiveFleet();
    const interval = setInterval(fetchLiveFleet, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-text">Fleet Real-Time Live Map</h1>
          <p className="text-xs text-text-muted mt-0.5">
            Geographic dispersion of technicians, active assignments, and incoming demand
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={fetchLiveFleet}
            icon={<RefreshCwIcon size={14} />}
          >
            Refresh Coordinates
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={() => navigate('/admin/jobs')}
          >
            Manage Jobs
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Main Map Canvas (8 cols) */}
        <div className="lg:col-span-8">
          <Card padding="none" className="overflow-hidden border-border">
            <InteractiveMap
              customerLocation={{ lat: 12.9716, lng: 77.5946, label: 'Central Hub' }}
              technicians={techMarkers}
              height="500px"
              onSelectTechnician={(tech) => setSelectedPin(tech)}
            />
          </Card>
        </div>

        {/* Selected Pin & Active Jobs Feed (4 cols) */}
        <div className="lg:col-span-4 space-y-4">
          {/* Selected Pin Detail */}
          {selectedPin ? (
            <Card padding="md" className="border-primary/40 bg-primary-tint/20 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold uppercase text-primary">Selected Fleet Unit</span>
                <button
                  onClick={() => setSelectedPin(null)}
                  className="text-xs text-text-muted hover:text-text font-bold"
                >
                  ✕
                </button>
              </div>
              <h3 className="text-base font-bold text-text">{selectedPin.title}</h3>
              <div className="flex items-center gap-2">
                <Badge variant={selectedPin.status === 'online' ? 'success' : 'neutral'} size="sm">
                  {selectedPin.status || 'Active'}
                </Badge>
                {selectedPin.rating && (
                  <span className="text-xs font-bold text-accent">★ {selectedPin.rating}</span>
                )}
              </div>
              <Button
                variant="primary"
                size="sm"
                onClick={() => navigate(`/admin/technicians`)}
                className="w-full mt-2"
              >
                Inspect Profile & Jobs
              </Button>
            </Card>
          ) : (
            <div className="p-4 rounded-card bg-surface border border-border text-xs text-text-muted text-center">
              Click any pin on the map to inspect live technician metrics.
            </div>
          )}

          {/* Active Jobs in transit */}
          <Card padding="md" className="border-border space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-border">
              <h4 className="text-xs font-bold text-text uppercase">Active Jobs In Flight</h4>
              <span className="text-[10px] font-bold text-primary">{activeJobs.length} active</span>
            </div>

            {activeJobs.length === 0 ? (
              <div className="text-center py-6 text-xs text-text-muted">
                No active jobs in transit right now.
              </div>
            ) : (
              <div className="space-y-2.5 max-h-72 overflow-y-auto">
                {activeJobs.map((job) => (
                  <div
                    key={job.id}
                    onClick={() => navigate('/admin/jobs')}
                    className="p-2.5 rounded-card bg-surface-alt border border-border hover:border-primary/40 transition cursor-pointer text-xs"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-text">{job.category || 'Service'}</span>
                      <StatusBadge status={job.status} size="sm" />
                    </div>
                    <div className="text-[11px] text-text-muted mt-0.5 line-clamp-1">
                      📍 {job.address}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
};

