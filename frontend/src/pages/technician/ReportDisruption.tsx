import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiService } from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import { Technician } from '../../types';

export const ReportDisruption: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [tech, setTech] = useState<Technician | null>(null);
  const [reasonType, setReasonType] = useState('sick_leave');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    apiService.getTechnicians({ limit: 100 }).then((techRes) => {
      const currentTech = techRes.technicians.find((t) => t.id === user?.technicianId) || techRes.technicians[0];
      setTech(currentTech);
    });
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tech) return;
    try {
      setSubmitting(true);
      await apiService.reportDisruption({
        event_type: 'technician_unavailable',
        affected_entity_type: 'technician',
        affected_entity_id: tech.id,
        payload: {
          reason: reasonType,
          notes,
          technician_name: tech.name,
          reported_at: new Date().toISOString(),
        },
      });
      // Also mark tech off duty
      await apiService.updateTechnicianStatus(tech.id, 'off_duty');
      alert('Unavailability report submitted! The dispatch engine has been notified to re-route your assigned jobs.');
      navigate('/technician/dashboard');
    } catch (err: any) {
      alert(`Report failed: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-gray-900">Report Emergency / Unavailability</h1>
        <p className="text-xs text-gray-500 mt-0.5">
          Notify dispatch dispatchers immediately if you experience illness, vehicle issues, or unexpected emergency
        </p>
      </div>

      <form onSubmit={handleSubmit} className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 space-y-4">
        <div>
          <label className="block text-xs font-semibold text-gray-700 mb-1">Reason for Unavailability</label>
          <select
            value={reasonType}
            onChange={(e) => setReasonType(e.target.value)}
            className="w-full px-3 py-2 border rounded-lg text-xs bg-white text-gray-900"
          >
            <option value="sick_leave">Sudden Sickness / Medical Emergency</option>
            <option value="vehicle_breakdown">Service Vehicle Breakdown / Accident</option>
            <option value="equipment_failure">Diagnostic Equipment Failure</option>
            <option value="family_emergency">Personal / Family Emergency</option>
          </select>
        </div>

        <div>
          <label className="block text-xs font-semibold text-gray-700 mb-1">Explanation & Location Notes</label>
          <textarea
            rows={3}
            required
            placeholder="e.g. Engine stall on 5th Ave, towing requested, unable to reach next stop."
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="w-full px-3 py-2 border rounded-lg text-xs"
          />
        </div>

        <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-800">
          ⚠️ <strong>Automatic Recovery:</strong> Submitting this will trigger the ALNS re-optimization engine to reassign all your remaining pending jobs to eligible fleet peers.
        </div>

        <button
          type="submit"
          disabled={submitting}
          className="w-full py-2.5 bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs rounded-lg shadow-md shadow-rose-500/20 disabled:opacity-50"
        >
          {submitting ? 'Submitting Disruption Notice...' : 'Submit Emergency Notice'}
        </button>
      </form>
    </div>
  );
};
