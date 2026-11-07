import React, { useState, useEffect } from 'react';
import { apiService } from '../../services/api';
import { Assignment, Technician } from '../../types';

export const Scheduling: React.FC = () => {
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [technicians, setTechnicians] = useState<Technician[]>([]);
  const [loading, setLoading] = useState(true);
  const [optimizing, setOptimizing] = useState(false);
  const [algorithm, setAlgorithm] = useState<'auto' | 'greedy' | 'alns'>('auto');
  const [iterations, setIterations] = useState(50);
  const [lastRunResult, setLastRunResult] = useState<any>(null);
  const [selectedTechFilter, setSelectedTechFilter] = useState('all');

  const fetchSchedule = async () => {
    try {
      setLoading(true);
      const [assigns, techRes] = await Promise.all([
        apiService.getAssignments({ limit: 200 }),
        apiService.getTechnicians({ limit: 100 }),
      ]);
      setAssignments(assigns);
      setTechnicians(techRes.technicians);
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSchedule();
  }, []);

  const handleRunScheduling = async () => {
    try {
      setOptimizing(true);
      setLastRunResult(null);
      const res = await apiService.runScheduling({
        algorithm,
        use_alns: algorithm !== 'greedy',
        max_iterations: iterations,
      });
      setLastRunResult(res);
      await fetchSchedule();
    } catch (err: any) {
      alert(`Scheduling execution failed: ${err.message}`);
    } finally {
      setOptimizing(false);
    }
  };

  const handleRemoveAssignment = async (assignmentId: string) => {
    if (!window.confirm('Remove this assignment? The job will revert to unassigned status.')) return;
    try {
      await apiService.deleteAssignment(assignmentId);
      await fetchSchedule();
    } catch (err: any) {
      alert(`Failed to remove assignment: ${err.message}`);
    }
  };

  // Group assignments by technician
  const assignmentsByTech: Record<string, Assignment[]> = {};
  assignments.forEach((a) => {
    if (!assignmentsByTech[a.technician_id]) {
      assignmentsByTech[a.technician_id] = [];
    }
    assignmentsByTech[a.technician_id].push(a);
  });

  const filteredTechs = technicians.filter((tech) => {
    if (selectedTechFilter !== 'all' && tech.id !== selectedTechFilter) return false;
    return true;
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900">Scheduling & Dispatch Engine</h1>
          <p className="text-xs text-gray-500 mt-0.5">
            Phase 5 Greedy LFJ + Phase 6 ALNS Multi-Operator Simulated Annealing Scheduler
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-xs text-gray-500">Live Dispatches:</span>
          <span className="text-xs font-bold text-emerald-600 px-2 py-1 bg-emerald-50 rounded-lg border border-emerald-200">
            {assignments.length} Jobs Dispatched
          </span>
        </div>
      </div>

      {/* Engine Controls Panel */}
      <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
        <h2 className="text-xs font-bold uppercase tracking-wider text-gray-500 mb-3">
          Optimization Engine Parameters
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 items-end">
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Algorithm Strategy</label>
            <select
              value={algorithm}
              onChange={(e) => setAlgorithm(e.target.value as any)}
              className="w-full px-3 py-2 border rounded-lg text-xs bg-white text-gray-900"
            >
              <option value="auto">Auto (Greedy + ALNS Refinement)</option>
              <option value="greedy">Greedy LFJ Only (Fastest)</option>
              <option value="alns">ALNS Optimization Only</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">
              ALNS Destroy / Repair Iterations
            </label>
            <input
              type="number"
              min={10}
              max={200}
              value={iterations}
              onChange={(e) => setIterations(Number(e.target.value))}
              className="w-full px-3 py-2 border rounded-lg text-xs text-gray-900"
            />
          </div>

          <div>
            <button
              onClick={handleRunScheduling}
              disabled={optimizing}
              className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs rounded-lg shadow-md shadow-blue-500/20 disabled:opacity-50 transition flex items-center justify-center space-x-2"
            >
              <span>⚡</span>
              <span>{optimizing ? 'Computing Optimal Routes...' : 'Execute Dispatch Run'}</span>
            </button>
          </div>
        </div>

        {lastRunResult && (
          <div className="mt-4 p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-xs space-y-1">
            <div className="font-bold text-emerald-800 flex items-center justify-between">
              <span>Optimization Succeeded!</span>
              <span>Run ID: {lastRunResult.run_id}</span>
            </div>
            <div className="text-emerald-700">
              Assigned: <strong>{lastRunResult.assigned_count}</strong> of {lastRunResult.jobs_count} jobs in{' '}
              <strong>{lastRunResult.execution_time?.toFixed(2)}s</strong> | Total Score:{' '}
              <strong>{lastRunResult.metrics?.total_score?.toFixed(1)}</strong>
            </div>
          </div>
        )}
      </div>

      {/* Technician Filter & View Selector */}
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-bold text-gray-900">Technician Route Timelines</h2>
        <div className="flex items-center space-x-2">
          <span className="text-xs text-gray-500">Filter Technician:</span>
          <select
            value={selectedTechFilter}
            onChange={(e) => setSelectedTechFilter(e.target.value)}
            className="px-3 py-1.5 border rounded-lg text-xs bg-white text-gray-800"
          >
            <option value="all">All Technicians ({technicians.length})</option>
            {technicians.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name} ({(assignmentsByTech[t.id] || []).length} jobs)
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Technician-Wise Schedule Timelines */}
      {loading ? (
        <div className="py-12 text-center text-xs text-gray-500">Loading route schedule...</div>
      ) : filteredTechs.length === 0 ? (
        <div className="py-12 text-center text-xs text-gray-500 bg-white rounded-xl border">No technician routes available.</div>
      ) : (
        <div className="space-y-4">
          {filteredTechs.map((tech) => {
            const techAssignments = assignmentsByTech[tech.id] || [];
            return (
              <div key={tech.id} className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
                <div className="flex items-center justify-between border-b pb-3 mb-3">
                  <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-800 font-bold flex items-center justify-center text-xs">
                      {tech.name.slice(0, 2).toUpperCase()}
                    </div>
                    <div>
                      <h3 className="font-bold text-gray-900 text-sm">{tech.name}</h3>
                      <div className="text-[11px] text-gray-500">
                        Shift: {tech.shift_start?.slice(0, 5)} - {tech.shift_end?.slice(0, 5)} |{' '}
                        {techAssignments.length} jobs assigned
                      </div>
                    </div>
                  </div>
                  <span
                    className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${
                      tech.status === 'available'
                        ? 'bg-emerald-100 text-emerald-800'
                        : 'bg-amber-100 text-amber-800'
                    }`}
                  >
                    {tech.status}
                  </span>
                </div>

                {techAssignments.length === 0 ? (
                  <div className="py-4 text-center text-xs text-gray-400 bg-gray-50/50 rounded-lg">
                    No jobs currently dispatched to this technician today.
                  </div>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                    {techAssignments.map((a, idx) => (
                      <div
                        key={a.id}
                        className="p-3 rounded-lg border border-gray-200 bg-gray-50/70 hover:bg-white hover:shadow-sm transition text-xs space-y-1.5"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-gray-500 text-[10px]">Stop #{idx + 1}</span>
                          <span
                            className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${
                              a.status === 'completed'
                                ? 'bg-emerald-100 text-emerald-800'
                                : a.status === 'in_progress'
                                ? 'bg-amber-100 text-amber-800'
                                : 'bg-blue-100 text-blue-800'
                            }`}
                          >
                            {a.status}
                          </span>
                        </div>

                        <div className="font-semibold text-gray-900 line-clamp-1">
                          {a.job?.title || a.job_title || `Job ID: ${a.job_id.slice(0, 8)}`}
                        </div>

                        <div className="text-[11px] text-gray-600 flex items-center justify-between">
                          <span>
                            ⏰ {new Date(a.scheduled_start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} -{' '}
                            {new Date(a.scheduled_end).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>

                        <div className="text-[10px] text-purple-700 flex items-center justify-between">
                          <span>🚗 Travel: {a.travel_before_minutes} mins</span>
                          <button
                            onClick={() => handleRemoveAssignment(a.id)}
                            className="text-red-500 hover:text-red-700 font-semibold"
                          >
                            Unassign
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
