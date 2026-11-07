import React, { useState, useEffect } from 'react';
import { apiService } from '../../services/api';
import { SchedulingRun } from '../../types';

export const Explainability: React.FC = () => {
  const [runs, setRuns] = useState<SchedulingRun[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string>('');
  const [runDetails, setRunDetails] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState<'all' | 'assigned' | 'unassigned'>('all');

  useEffect(() => {
    apiService.getSchedulingRuns(15).then((data) => {
      setRuns(data);
      if (data.length > 0) {
        setSelectedRunId(data[0].id);
      }
      setLoading(false);
    });
  }, []);

  useEffect(() => {
    if (!selectedRunId) return;
    setLoading(true);
    apiService.getSchedulingRunDetails(selectedRunId)
      .then((data) => setRunDetails(data))
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, [selectedRunId]);

  const assignedDecisions = runDetails?.assigned_decisions || [];
  const unassignedDecisions = runDetails?.unassigned_decisions || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900">Explainable AI & Decision Audit</h1>
          <p className="text-xs text-gray-500 mt-0.5">
            Transparent scheduling rationale: inspect constraint proofs and why assignments succeeded or failed
          </p>
        </div>

        {/* Run Selector */}
        <div className="flex items-center space-x-2">
          <span className="text-xs font-medium text-gray-500">Run:</span>
          <select
            value={selectedRunId}
            onChange={(e) => setSelectedRunId(e.target.value)}
            className="px-3 py-1.5 border rounded-lg text-xs bg-white text-gray-900 font-medium"
          >
            {runs.map((r) => (
              <option key={r.id} value={r.id}>
                Run {r.id.slice(0, 8)} ({r.algorithm_used} - Score: {r.objective_score ?? 'N/A'})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <div className="text-[11px] font-semibold text-gray-400 uppercase">Algorithm Applied</div>
          <div className="text-lg font-bold text-gray-900 mt-1 uppercase tracking-wide">
            {runDetails?.algorithm_used || 'Auto'} (v{runDetails?.algorithm_version || '1.0.0'})
          </div>
          <div className="text-[10px] text-gray-500 mt-0.5">Trigger: {runDetails?.trigger_type || 'Initial'}</div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <div className="text-[11px] font-semibold text-gray-400 uppercase">Feasible Assignments</div>
          <div className="text-lg font-bold text-emerald-600 mt-1">
            {assignedDecisions.length} Decisions Approved
          </div>
          <div className="text-[10px] text-emerald-600 mt-0.5">Constraint verified (shift, travel, skills)</div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <div className="text-[11px] font-semibold text-gray-400 uppercase">Infeasible / Blocked</div>
          <div className="text-lg font-bold text-rose-600 mt-1">
            {unassignedDecisions.length} Jobs Unassigned
          </div>
          <div className="text-[10px] text-rose-500 mt-0.5">Categorized rejection reasons</div>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center space-x-2 border-b pb-2">
        <button
          onClick={() => setFilterType('all')}
          className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition ${
            filterType === 'all' ? 'bg-blue-600 text-white shadow-sm' : 'text-gray-600 hover:bg-gray-100'
          }`}
        >
          All Decisions ({assignedDecisions.length + unassignedDecisions.length})
        </button>
        <button
          onClick={() => setFilterType('assigned')}
          className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition ${
            filterType === 'assigned' ? 'bg-emerald-600 text-white shadow-sm' : 'text-gray-600 hover:bg-gray-100'
          }`}
        >
          Assigned Rationale ({assignedDecisions.length})
        </button>
        <button
          onClick={() => setFilterType('unassigned')}
          className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition ${
            filterType === 'unassigned' ? 'bg-rose-600 text-white shadow-sm' : 'text-gray-600 hover:bg-gray-100'
          }`}
        >
          Unassigned Explanations ({unassignedDecisions.length})
        </button>
      </div>

      {/* Decisions List */}
      {loading ? (
        <div className="py-12 text-center text-xs text-gray-500">Loading decision rationale...</div>
      ) : (
      <div className="space-y-3">
        {(filterType === 'all' || filterType === 'assigned') && (
          <div className="space-y-2">
            <h3 className="text-xs font-bold uppercase tracking-wider text-emerald-800">
              Approved Job Assignments ({assignedDecisions.length})
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {assignedDecisions.map((d: any, idx: number) => (
                <div key={idx} className="p-3.5 bg-white border border-emerald-100 rounded-xl shadow-sm text-xs space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-gray-900">Job: {d.job_id.slice(0, 8)}...</span>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 uppercase">
                      Feasible Match
                    </span>
                  </div>
                  <div className="text-gray-600">
                    Assigned to Tech: <strong className="text-gray-900">{d.technician_id?.slice(0, 8)}...</strong>
                  </div>
                  <div className="text-gray-500 text-[11px]">
                    Scheduled: {d.scheduled_start ? new Date(d.scheduled_start).toLocaleTimeString() : 'N/A'} | Priority Score: {d.selected_score}
                  </div>
                  <div className="p-2 bg-emerald-50/60 rounded text-[11px] text-emerald-800">
                    <strong>Reasoning:</strong> {d.explanation_text || 'Qualified skill certificate, zone coverage, and minimum travel delay.'}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {(filterType === 'all' || filterType === 'unassigned') && (
          <div className="space-y-2 pt-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-rose-800">
              Unassigned Jobs & Constraint Violations ({unassignedDecisions.length})
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {unassignedDecisions.map((d: any, idx: number) => (
                <div key={idx} className="p-3.5 bg-white border border-rose-100 rounded-xl shadow-sm text-xs space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-gray-900">Job: {d.job_id.slice(0, 8)}...</span>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-rose-100 text-rose-800 uppercase">
                      {d.rejection_reason || 'Infeasible'}
                    </span>
                  </div>
                  <div className="p-2 bg-rose-50/60 rounded text-[11px] text-rose-900">
                    <strong>Constraint Barrier:</strong> {d.explanation_text || 'No available technician slot found within requested time window that satisfies all skill and travel constraints.'}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
      )}
    </div>
  );
};
