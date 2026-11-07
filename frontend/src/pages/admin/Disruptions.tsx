import React, { useState, useEffect } from 'react';
import { apiService } from '../../services/api';
import { DisruptionEvent, Technician, Job } from '../../types';

export const Disruptions: React.FC = () => {
  const [disruptions, setDisruptions] = useState<DisruptionEvent[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [technicians, setTechnicians] = useState<Technician[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [reportSuccess, setReportSuccess] = useState<string | null>(null);

  // Form state
  const [eventType, setEventType] = useState('technician_unavailable');
  const [affectedEntityType, setAffectedEntityType] = useState<'technician' | 'job'>('technician');
  const [affectedEntityId, setAffectedEntityId] = useState('');
  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [disruptRes, statsRes, techRes, jobRes] = await Promise.all([
        apiService.getDisruptions({ limit: 50 }),
        apiService.getDisruptionStats(),
        apiService.getTechnicians({ limit: 100 }),
        apiService.getJobs({ limit: 100 }),
      ]);
      setDisruptions(disruptRes);
      setStats(statsRes);
      setTechnicians(techRes.technicians);
      setJobs(jobRes.jobs);

      // Set default selected entity ID
      if (techRes.technicians.length > 0 && affectedEntityType === 'technician') {
        setAffectedEntityId(techRes.technicians[0].id);
      }
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleEntityTypeChange = (type: 'technician' | 'job') => {
    setAffectedEntityType(type);
    if (type === 'technician') {
      setEventType('technician_unavailable');
      if (technicians.length > 0) setAffectedEntityId(technicians[0].id);
    } else {
      setEventType('urgent_job');
      if (jobs.length > 0) setAffectedEntityId(jobs[0].id);
    }
  };

  const handleReportDisruption = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!affectedEntityId) return;
    try {
      setSubmitting(true);
      setReportSuccess(null);
      await apiService.reportDisruption({
        event_type: eventType,
        affected_entity_type: affectedEntityType,
        affected_entity_id: affectedEntityId,
        payload: { reason, timestamp: new Date().toISOString() },
      });
      setReportSuccess('Disruption event reported successfully. Click "Process & Recover" to initiate dynamic re-dispatch.');
      setReason('');
      await fetchData();
    } catch (err: any) {
      alert(`Failed to report disruption: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const handleProcess = async (disruptionId: string) => {
    try {
      setProcessingId(disruptionId);
      const res = await apiService.processDisruption(disruptionId);
      alert(`Recovery complete! ${res.message}. Jobs reassigned: ${res.jobs_reassigned}`);
      await fetchData();
    } catch (err: any) {
      alert(`Processing error: ${err.message}`);
    } finally {
      setProcessingId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900">Disruption Recovery Engine</h1>
          <p className="text-xs text-gray-500 mt-0.5">
            Handle real-time operational shocks: technician sick leave, vehicle breakdowns, urgent jobs, cancellations
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-xs font-semibold px-3 py-1 bg-amber-50 text-amber-800 border border-amber-200 rounded-lg">
            Unprocessed: {stats?.unprocessed ?? 0}
          </span>
          <span className="text-xs font-semibold px-3 py-1 bg-emerald-50 text-emerald-800 border border-emerald-200 rounded-lg">
            Recovered: {stats?.processed ?? 0}
          </span>
        </div>
      </div>

      {reportSuccess && (
        <div className="p-3.5 bg-emerald-50 border border-emerald-200 text-emerald-900 text-xs rounded-xl flex items-center justify-between">
          <span>{reportSuccess}</span>
          <button onClick={() => setReportSuccess(null)} className="text-emerald-600 font-bold ml-4">✕</button>
        </div>
      )}

      {/* Report Disruption Form */}
      <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
        <h2 className="text-sm font-bold text-gray-900 mb-3 flex items-center space-x-2">
          <span>🚨</span>
          <span>Inject / Report Disruption Event</span>
        </h2>
        <form onSubmit={handleReportDisruption} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Target Entity Type</label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => handleEntityTypeChange('technician')}
                  className={`py-2 text-xs font-semibold rounded-lg border transition ${
                    affectedEntityType === 'technician'
                      ? 'bg-blue-600 text-white border-blue-600'
                      : 'bg-white text-gray-700 border-gray-200 hover:bg-gray-50'
                  }`}
                >
                  Technician
                </button>
                <button
                  type="button"
                  onClick={() => handleEntityTypeChange('job')}
                  className={`py-2 text-xs font-semibold rounded-lg border transition ${
                    affectedEntityType === 'job'
                      ? 'bg-blue-600 text-white border-blue-600'
                      : 'bg-white text-gray-700 border-gray-200 hover:bg-gray-50'
                  }`}
                >
                  Job Request
                </button>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Disruption Event Type</label>
              <select
                value={eventType}
                onChange={(e) => setEventType(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg text-xs bg-white text-gray-900"
              >
                {affectedEntityType === 'technician' ? (
                  <>
                    <option value="technician_unavailable">Technician Unavailable (Sick / Breakdown)</option>
                  </>
                ) : (
                  <>
                    <option value="urgent_job">Urgent High-Priority Job Arrival</option>
                    <option value="job_cancellation">Customer Job Cancellation</option>
                    <option value="duration_change">Duration Extension / Change</option>
                    <option value="early_completion">Job Completed Early</option>
                    <option value="late_completion">Job Delayed / Overrun</option>
                  </>
                )}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Select Affected Entity</label>
              <select
                value={affectedEntityId}
                onChange={(e) => setAffectedEntityId(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg text-xs bg-white text-gray-900"
                required
              >
                {affectedEntityType === 'technician'
                  ? technicians.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.name} ({t.status})
                      </option>
                    ))
                  : jobs.slice(0, 50).map((j) => (
                      <option key={j.id} value={j.id}>
                        [{j.priority.toUpperCase()}] {j.title.slice(0, 30)}
                      </option>
                    ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Notes / Reason (Optional)</label>
            <input
              type="text"
              placeholder="e.g. Van engine overheating on Highway 101, needs immediate recovery"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg text-xs"
            />
          </div>

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={submitting}
              className="px-5 py-2 bg-rose-600 hover:bg-rose-700 text-white font-semibold text-xs rounded-lg shadow-md shadow-rose-500/20 disabled:opacity-50 transition"
            >
              {submitting ? 'Reporting...' : 'Publish Disruption'}
            </button>
          </div>
        </form>
      </div>

      {/* Disruption Events Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-sm font-bold text-gray-900">Disruption Log & Recovery Pipeline</h2>
          <span className="text-xs text-gray-500">{disruptions.length} Total Events</span>
        </div>

        {loading ? (
          <div className="py-12 text-center text-xs text-gray-500">Loading disruptions...</div>
        ) : disruptions.length === 0 ? (
          <div className="py-12 text-center text-xs text-gray-500">No disruptions reported. Schedule running smoothly.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200 text-[10px] text-gray-500 uppercase tracking-wider">
                  <th className="py-3 px-4">Event Type</th>
                  <th className="py-3 px-4">Entity</th>
                  <th className="py-3 px-4">Timestamp</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {disruptions.map((d) => (
                  <tr key={d.id} className="hover:bg-gray-50 transition">
                    <td className="py-3 px-4 font-semibold text-gray-900 capitalize">
                      {d.event_type.replace(/_/g, ' ')}
                    </td>
                    <td className="py-3 px-4 text-gray-600">
                      <span className="capitalize font-medium text-gray-800">{d.affected_entity_type}:</span>{' '}
                      <span className="font-mono text-[11px]">{d.affected_entity_id.slice(0, 8)}...</span>
                    </td>
                    <td className="py-3 px-4 text-gray-500">
                      {new Date(d.event_time).toLocaleTimeString()} - {new Date(d.event_time).toLocaleDateString()}
                    </td>
                    <td className="py-3 px-4">
                      {d.processed_run_id ? (
                        <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-emerald-100 text-emerald-800">
                          Processed (Run {d.processed_run_id.slice(0, 6)})
                        </span>
                      ) : (
                        <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-amber-100 text-amber-800 animate-pulse">
                          Awaiting Recovery
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right">
                      {!d.processed_run_id ? (
                        <button
                          onClick={() => handleProcess(d.id)}
                          disabled={processingId === d.id}
                          className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded font-semibold text-[11px] shadow-sm disabled:opacity-50"
                        >
                          {processingId === d.id ? 'Re-optimizing...' : 'Process & Recover'}
                        </button>
                      ) : (
                        <span className="text-gray-400 text-xs font-medium">Recovered ✓</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
