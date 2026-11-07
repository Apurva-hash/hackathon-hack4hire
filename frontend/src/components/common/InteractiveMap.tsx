import React, { useState } from 'react';
import { NavigationIcon, MapPinIcon } from './Icons';

export interface MapMarker {
  id: string;
  lat: number;
  lng: number;
  title: string;
  subtitle?: string;
  type: 'customer' | 'technician';
  status?: string;
  eta_minutes?: number;
  distance_km?: number;
  rating?: number;
  onClick?: () => void;
}

export interface InteractiveMapProps {
  customerLocation?: { lat: number; lng: number; label?: string };
  technicians?: MapMarker[];
  assignedTechnician?: MapMarker;
  height?: string;
  zoom?: number;
  interactive?: boolean;
  className?: string;
  onSelectTechnician?: (tech: MapMarker) => void;
}

export const InteractiveMap: React.FC<InteractiveMapProps> = ({
  customerLocation = { lat: 12.9716, lng: 77.5946, label: 'Current Location' },
  technicians = [],
  assignedTechnician,
  height = '400px',
  className = '',
  onSelectTechnician,
}) => {
  const [selectedMarker, setSelectedMarker] = useState<MapMarker | null>(null);

  // Center coordinate
  const centerLat = customerLocation.lat;
  const centerLng = customerLocation.lng;

  // Convert lat/lng offset to pixel coordinates on our 1000x1000 coordinate plane
  const toPoint = (lat: number, lng: number) => {
    const scale = 8000; // zoom factor for city scale (~10-15 km)
    const x = 500 + (lng - centerLng) * scale;
    const y = 500 - (lat - centerLat) * scale;
    return {
      x: Math.max(40, Math.min(960, x)),
      y: Math.max(40, Math.min(960, y)),
    };
  };

  const customerPoint = toPoint(customerLocation.lat, customerLocation.lng);

  return (
    <div
      style={{ height }}
      className={`relative w-full overflow-hidden rounded-card border border-border bg-[#F5ECE1] dark:bg-[#1E1712] select-none ${className}`}
    >
      {/* Warm-toned stylized map background */}
      <svg
        className="w-full h-full object-cover"
        viewBox="0 0 1000 1000"
        preserveAspectRatio="xMidYMid slice"
      >
        <defs>
          <pattern id="street-grid" width="100" height="100" patternUnits="userSpaceOnUse">
            <path
              d="M 100 0 L 0 0 0 100"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              className="text-[#E5D7C6]/60 dark:text-[#2D211A]/80"
            />
            <path
              d="M 0 50 L 100 50 M 50 0 L 50 100"
              fill="none"
              stroke="currentColor"
              strokeWidth="0.8"
              strokeDasharray="4,4"
              className="text-[#E5D7C6]/40 dark:text-[#2D211A]/50"
            />
          </pattern>
        </defs>

        {/* Base Map fill */}
        <rect width="1000" height="1000" fill="url(#street-grid)" />

        {/* Major roads / avenues */}
        <path
          d="M 0 450 Q 500 480 1000 420"
          fill="none"
          stroke="currentColor"
          strokeWidth="12"
          className="text-[#EADBCA] dark:text-[#382B21]"
        />
        <path
          d="M 460 0 Q 520 500 480 1000"
          fill="none"
          stroke="currentColor"
          strokeWidth="12"
          className="text-[#EADBCA] dark:text-[#382B21]"
        />
        <path
          d="M 100 900 Q 500 500 900 100"
          fill="none"
          stroke="currentColor"
          strokeWidth="8"
          className="text-[#EADBCA]/80 dark:text-[#382B21]/80"
        />

        {/* Route Line if an active technician is assigned */}
        {assignedTechnician && (
          <g>
            <path
              d={`M ${customerPoint.x} ${customerPoint.y} Q ${
                (customerPoint.x + toPoint(assignedTechnician.lat, assignedTechnician.lng).x) / 2 + 30
              } ${
                (customerPoint.y + toPoint(assignedTechnician.lat, assignedTechnician.lng).y) / 2 - 30
              } ${toPoint(assignedTechnician.lat, assignedTechnician.lng).x} ${
                toPoint(assignedTechnician.lat, assignedTechnician.lng).y
              }`}
              fill="none"
              stroke="var(--primary)"
              strokeWidth="5"
              strokeLinecap="round"
              strokeDasharray="8,8"
              className="animate-pulse"
            />
          </g>
        )}

        {/* Customer Pin (Dark Brown / Dark Cream) */}
        <g transform={`translate(${customerPoint.x}, ${customerPoint.y})`}>
          {/* Pulse ring */}
          <circle r="20" fill="var(--primary)" opacity="0.25" className="radar-animation" />
          <circle r="10" fill="#2B2118" stroke="#FFFFFF" strokeWidth="2.5" />
          <circle r="4" fill="var(--primary)" />
        </g>

        {/* Technician Pins (Terracotta) */}
        {(assignedTechnician ? [assignedTechnician] : technicians).map((tech) => {
          const pt = toPoint(tech.lat, tech.lng);
          const isSelected = selectedMarker?.id === tech.id;

          return (
            <g
              key={tech.id}
              transform={`translate(${pt.x}, ${pt.y})`}
              className="cursor-pointer transition-transform hover:scale-125"
              onClick={() => {
                setSelectedMarker(tech);
                onSelectTechnician?.(tech);
              }}
            >
              {/* Outer pulse */}
              <circle r="18" fill="var(--primary)" opacity="0.2" className="radar-animation" />
              {/* Pin bubble */}
              <circle
                r="12"
                fill="var(--primary)"
                stroke="#FFFFFF"
                strokeWidth="2.5"
                className={isSelected ? 'stroke-accent' : ''}
              />
              <path
                d="M -4 -4 L 4 0 L -4 4 Z"
                fill="#FFFFFF"
                transform="rotate(-45)"
              />
            </g>
          );
        })}
      </svg>

      {/* Floating Status & Marker Info Overlay */}
      {selectedMarker && (
        <div className="absolute top-4 left-4 right-4 sm:right-auto sm:w-72 bg-surface text-text p-3.5 rounded-card border border-border shadow-warmLg flex items-center justify-between gap-3 animate-slide-up z-20">
          <div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-status-success" />
              <h4 className="text-xs font-bold text-text">{selectedMarker.title}</h4>
            </div>
            <div className="text-[11px] text-text-muted mt-0.5 flex items-center gap-2">
              {selectedMarker.distance_km !== undefined && (
                <span>{selectedMarker.distance_km} km away</span>
              )}
              {selectedMarker.eta_minutes !== undefined && (
                <span className="font-semibold text-primary">~{selectedMarker.eta_minutes} min ETA</span>
              )}
            </div>
          </div>
          <button
            onClick={() => setSelectedMarker(null)}
            className="text-text-muted hover:text-text p-1 text-xs font-bold"
          >
            ✕
          </button>
        </div>
      )}

      {/* Bottom map legend */}
      <div className="absolute bottom-3 left-3 bg-surface/90 backdrop-blur-sm px-3 py-1.5 rounded-full border border-border text-[11px] font-medium text-text flex items-center gap-3 shadow-warmSm">
        <span className="flex items-center gap-1">
          <span className="w-2.5 h-2.5 rounded-full bg-[#2B2118]" />
          <span>You</span>
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2.5 h-2.5 rounded-full bg-primary" />
          <span>Technicians</span>
        </span>
      </div>
    </div>
  );
};

