"""
Scheduling Engine - Orchestrates Greedy Insertion + ALNS optimization
Phase 5 & 6 Integration - Bug-fixed version
"""

import sys
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from typing import List, Dict, Optional, Set
from datetime import datetime
from sqlalchemy.orm import Session

from app.models import (
    Job, Technician, Assignment, SchedulingRun, SchedulingDecision,
    RunStatus, TriggerType, Feasibility, RejectionReason, JobPriority,
    AssignmentStatus
)
from app.models.base import generate_uuid
from app.scheduler.greedy_insertion import GreedyInsertion
from app.scheduler.alns_optimizer import ALNSOptimizer, ALNSConfig, Solution
from app.scheduler.scoring import ScheduleScorer
from app.config import Config


class SchedulingEngine:
    """
    Main scheduling engine that coordinates:
    1. Greedy Insertion (Phase 5) - Generate initial feasible schedule
    2. ALNS Optimization (Phase 6) - Refine schedule for optimality
    """

    def __init__(self, config: Config, alns_config: ALNSConfig = None):
        self.config = config
        self.alns_config = alns_config or ALNSConfig()
        self.scorer = ScheduleScorer()

    def run_scheduling(
        self,
        jobs: List[Job],
        technicians: List[Technician],
        db: Session,
        use_alns: bool = True,
        algorithm: str = "auto",
        trigger_type: TriggerType = TriggerType.INITIAL,
        trigger_description: Optional[str] = None,
        protected_job_ids: Optional[Set[str]] = None,
    ) -> Dict:
        """
        Execute complete scheduling workflow.

        Args:
            jobs: List of jobs to schedule
            technicians: List of available technicians
            db: Database session for persistence
            use_alns: If True, run ALNS after greedy (default: True)
            algorithm: "greedy", "alns", or "auto" (both)
            trigger_type: What triggered this scheduling run
            trigger_description: Human-readable description of trigger
            protected_job_ids: Job IDs that must not be re-assigned

        Returns:
            Dictionary with scheduling results and metrics
        """
        if protected_job_ids is None:
            protected_job_ids = set()

        print(f"\n{'='*60}")
        print(f"DispatchGrid Scheduling Engine - Starting")
        print(f"{'='*60}")
        print(f"Jobs to schedule: {len(jobs)}")
        print(f"Available technicians: {len(technicians)}")
        print(f"Algorithm: {algorithm}")
        print(f"{'='*60}\n")

        start_time = datetime.utcnow()

        # Create scheduling run record with correct field names
        scheduling_run = SchedulingRun(
            timestamp=start_time,
            trigger_type=trigger_type,
            trigger_description=trigger_description,
            algorithm_used=algorithm,
            algorithm_version="1.0.0",
            status=RunStatus.RUNNING,
        )
        db.add(scheduling_run)
        db.commit()
        db.refresh(scheduling_run)

        results = {
            "run_id": scheduling_run.id,
            "start_time": start_time,
            "jobs_count": len(jobs),
            "technicians_count": len(technicians),
            "algorithm": algorithm,
        }

        # Build per-phase greedy and ALNS instances (both need db)
        greedy = GreedyInsertion(db)
        alns = ALNSOptimizer(self.config, self.alns_config)

        try:
            # ============ Phase 5: Greedy Insertion ============
            if algorithm in ["greedy", "auto"]:
                print("\n" + "=" * 60)
                print("PHASE 5: GREEDY INSERTION (Least Flexible Job First)")
                print("=" * 60)

                # Returns Tuple[List[Assignment], List[Job], Dict[str, str]]
                assignments, unassigned_jobs, unassigned_reasons = greedy.generate_schedule(
                    jobs, technicians, protected_job_ids
                )

                greedy_metrics = self.scorer.calculate_schedule_metrics(
                    assignments, jobs, technicians
                )

                results["greedy"] = {
                    "assignments": assignments,
                    "assigned_count": len(assignments),
                    "unassigned_count": len(unassigned_jobs),
                    "unassigned_jobs": unassigned_jobs,
                    "unassigned_reasons": unassigned_reasons,
                    "metrics": greedy_metrics,
                    "execution_time": (datetime.utcnow() - start_time).total_seconds(),
                }

                print(f"\n{'='*60}")
                print("GREEDY INSERTION RESULTS")
                print(f"{'='*60}")
                print(f"Assigned: {len(assignments)}/{len(jobs)} jobs")
                print(f"Coverage: {greedy_metrics['job_coverage']:.1f}%")
                print(f"Total Score: {greedy_metrics['total_score']:.2f}")
                print(f"{'='*60}\n")

                # Save greedy decisions to DB with correct field names
                for assignment in assignments:
                    job = next((j for j in jobs if j.id == assignment.job_id), None)
                    candidate_score = self._get_priority_value(job.priority) if job else 0.0
                    decision = SchedulingDecision(
                        run_id=scheduling_run.id,           # correct field: run_id
                        job_id=assignment.job_id,
                        technician_id=assignment.technician_id,
                        scheduled_start=assignment.scheduled_start,
                        feasibility=Feasibility.FEASIBLE,   # correct field
                        candidate_count=1,
                        selected_score=candidate_score,
                        explanation_text="Assigned by greedy insertion",
                    )
                    db.add(decision)

                for unassigned in unassigned_jobs:
                    raw_reason = unassigned_reasons.get(unassigned.id, "")
                    rejection_reason = self._classify_rejection_reason(raw_reason)
                    decision = SchedulingDecision(
                        run_id=scheduling_run.id,           # correct field: run_id
                        job_id=unassigned.id,
                        technician_id=None,
                        scheduled_start=None,
                        feasibility=Feasibility.CURRENTLY_INFEASIBLE,  # correct field
                        rejection_reason=rejection_reason,
                        candidate_count=0,
                        explanation_text=raw_reason or "No feasible assignment found",
                    )
                    db.add(decision)

                db.commit()

            # ============ Phase 6: ALNS Optimization ============
            if algorithm in ["alns", "auto"] and use_alns:
                # Use greedy result as initial solution if available
                if "greedy" in results:
                    initial_assignments = results["greedy"]["assignments"]
                else:
                    print("\nRunning Greedy Insertion to generate initial solution...")
                    initial_assignments, unassigned_jobs, unassigned_reasons = greedy.generate_schedule(
                        jobs, technicians, protected_job_ids
                    )

                print("\n" + "=" * 60)
                print("PHASE 6: ALNS OPTIMIZATION (Adaptive Large Neighborhood Search)")
                print("=" * 60)

                initial_solution = Solution(initial_assignments, jobs, technicians, self.config)

                best_solution, alns_stats = alns.optimize(initial_solution)

                final_metrics = self.scorer.calculate_schedule_metrics(
                    best_solution.assignments, jobs, technicians
                )

                results["alns"] = {
                    "assignments": best_solution.assignments,
                    "assigned_count": len(best_solution.assigned_job_ids),
                    "unassigned_count": len(jobs) - len(best_solution.assigned_job_ids),
                    "unassigned_jobs": best_solution.get_unassigned_jobs(),
                    "metrics": final_metrics,
                    "stats": alns_stats,
                }

                print(f"\n{'='*60}")
                print("ALNS OPTIMIZATION RESULTS")
                print(f"{'='*60}")
                print(f"Assigned: {len(best_solution.assigned_job_ids)}/{len(jobs)} jobs")
                print(f"Coverage: {final_metrics['job_coverage']:.1f}%")
                print(f"Total Score: {final_metrics['total_score']:.2f}")
                print(f"Iterations: {alns_stats['iterations']}")
                print(f"Improvements: {alns_stats['improvements']}")
                print(f"Score Improvement: {alns_stats['improvement']:.2f}")
                print(f"{'='*60}\n")

                # Clear greedy decisions and save ALNS decisions
                if algorithm == "auto":
                    db.query(SchedulingDecision).filter(
                        SchedulingDecision.run_id == scheduling_run.id   # correct field
                    ).delete()

                for assignment in best_solution.assignments:
                    job = next((j for j in jobs if j.id == assignment.job_id), None)
                    candidate_score = self._get_priority_value(job.priority) if job else 0.0
                    decision = SchedulingDecision(
                        run_id=scheduling_run.id,           # correct field: run_id
                        job_id=assignment.job_id,
                        technician_id=assignment.technician_id,
                        scheduled_start=assignment.scheduled_start,
                        feasibility=Feasibility.FEASIBLE,   # correct field
                        candidate_count=1,
                        selected_score=candidate_score,
                        explanation_text="Assigned by ALNS optimizer",
                    )
                    db.add(decision)

                for unassigned in best_solution.get_unassigned_jobs():
                    decision = SchedulingDecision(
                        run_id=scheduling_run.id,           # correct field: run_id
                        job_id=unassigned.id,
                        technician_id=None,
                        scheduled_start=None,
                        feasibility=Feasibility.CURRENTLY_INFEASIBLE,  # correct field
                        rejection_reason=RejectionReason.NO_AVAILABLE_SLOT,
                        candidate_count=0,
                        explanation_text="Could not find feasible assignment after ALNS optimization",
                    )
                    db.add(decision)

                db.commit()

            # ============ Finalize ============
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds()

            # Determine final results based on algorithm choice
            if algorithm == "auto" and "alns" in results:
                final_results = results["alns"]
            elif algorithm == "alns" and "alns" in results:
                final_results = results["alns"]
            else:
                final_results = results["greedy"]

            # ---- Persist final assignments to DB and update job statuses ----
            final_assignment_objects = final_results.get("assignments", [])
            for a in final_assignment_objects:
                existing = db.query(Assignment).filter(Assignment.job_id == a.job_id).first()
                if existing:
                    existing.technician_id = a.technician_id
                    existing.scheduled_start = a.scheduled_start
                    existing.scheduled_end = a.scheduled_end
                    existing.travel_before_minutes = getattr(a, "travel_before_minutes", 0)
                    existing.status = AssignmentStatus.PENDING
                    existing.run_id = scheduling_run.id
                else:
                    a.run_id = scheduling_run.id
                    a.status = AssignmentStatus.PENDING
                    db.add(a)

                # Update job status to ASSIGNED
                from app.models.job import JobStatus as JS
                job_obj = db.query(Job).filter(Job.id == a.job_id).first()
                if job_obj:
                    job_obj.status = JS.ASSIGNED

            db.commit()

            # Update scheduling run with correct field names
            metrics = final_results["metrics"]
            scheduling_run.status = RunStatus.COMPLETED
            scheduling_run.objective_score = float(metrics.get("total_score", 0.0))
            scheduling_run.total_travel_minutes = int(metrics.get("total_travel_minutes", 0))
            scheduling_run.sla_violations = int(metrics.get("sla_violations", 0))
            scheduling_run.unassigned_high_priority = int(metrics.get("unassigned_high_priority", 0))
            scheduling_run.overtime_minutes = int(metrics.get("overtime_minutes", 0))
            db.commit()

            results["end_time"] = end_time
            results["execution_time"] = execution_time
            results["status"] = "completed"

            # ============ Comparison Report ============
            if algorithm == "auto" and "greedy" in results and "alns" in results:
                results["comparison"] = self._generate_comparison(
                    results["greedy"], results["alns"]
                )
                self._print_comparison(results["comparison"])

            print(f"\n{'='*60}")
            print("SCHEDULING COMPLETE")
            print(f"{'='*60}")
            print(f"Total Execution Time: {execution_time:.2f}s")
            print(f"Final Assigned Jobs: {final_results['assigned_count']}/{len(jobs)}")
            print(f"Final Score: {final_results['metrics']['total_score']:.2f}")
            print(f"Run ID: {scheduling_run.id}")
            print(f"{'='*60}\n")

            return results

        except Exception as e:
            # Handle errors
            scheduling_run.status = RunStatus.FAILED
            scheduling_run.error_message = str(e)
            db.commit()

            results["status"] = "failed"
            results["error"] = str(e)

            print(f"\n{'='*60}")
            print("SCHEDULING FAILED")
            print(f"{'='*60}")
            print(f"Error: {str(e)}")
            print(f"{'='*60}\n")

            raise

    def _classify_rejection_reason(self, reason_text: str) -> Optional[RejectionReason]:
        """Map free-text reason to RejectionReason enum."""
        if not reason_text:
            return RejectionReason.NO_AVAILABLE_SLOT
        reason_lower = reason_text.lower()
        if "skill" in reason_lower:
            return RejectionReason.MISSING_SKILL
        if "zone" in reason_lower:
            return RejectionReason.NO_ZONE_ELIGIBILITY
        if "shift" in reason_lower:
            return RejectionReason.SHIFT_CONFLICT
        if "travel" in reason_lower:
            return RejectionReason.TRAVEL_CONFLICT
        if "sla" in reason_lower or "deadline" in reason_lower:
            return RejectionReason.SLA_CONFLICT
        if "unavailable" in reason_lower:
            return RejectionReason.RESOURCE_UNAVAILABLE
        if "window" in reason_lower or "time" in reason_lower:
            return RejectionReason.TIME_WINDOW_CONFLICT
        return RejectionReason.NO_AVAILABLE_SLOT

    def _generate_comparison(self, greedy_result: Dict, alns_result: Dict) -> Dict:
        """Generate comparison between Greedy and ALNS results."""
        greedy_metrics = greedy_result["metrics"]
        alns_metrics = alns_result["metrics"]

        return {
            "assigned_jobs": {
                "greedy": greedy_result["assigned_count"],
                "alns": alns_result["assigned_count"],
                "improvement": alns_result["assigned_count"] - greedy_result["assigned_count"],
            },
            "total_score": {
                "greedy": greedy_metrics["total_score"],
                "alns": alns_metrics["total_score"],
                "improvement": alns_metrics["total_score"] - greedy_metrics["total_score"],
                "improvement_pct": (
                    (alns_metrics["total_score"] - greedy_metrics["total_score"])
                    / greedy_metrics["total_score"]
                    * 100
                )
                if greedy_metrics["total_score"] > 0
                else 0,
            },
            "job_coverage": {
                "greedy": greedy_metrics["job_coverage"],
                "alns": alns_metrics["job_coverage"],
                "improvement": alns_metrics["job_coverage"] - greedy_metrics["job_coverage"],
            },
            "travel_time": {
                "greedy": greedy_metrics["total_travel_time"],
                "alns": alns_metrics["total_travel_time"],
                "improvement": greedy_metrics["total_travel_time"] - alns_metrics["total_travel_time"],
            },
            "idle_time": {
                "greedy": greedy_metrics["total_idle_time"],
                "alns": alns_metrics["total_idle_time"],
                "improvement": greedy_metrics["total_idle_time"] - alns_metrics["total_idle_time"],
            },
            "priority_fulfillment": {
                "greedy": greedy_metrics["priority_fulfillment_rate"],
                "alns": alns_metrics["priority_fulfillment_rate"],
                "improvement": alns_metrics["priority_fulfillment_rate"] - greedy_metrics["priority_fulfillment_rate"],
            },
            "execution_time": {
                "greedy": greedy_result["execution_time"],
                "alns": alns_result["stats"]["iterations"] * 0.1,
                "total": greedy_result["execution_time"] + (alns_result["stats"]["iterations"] * 0.1),
            },
        }

    def _print_comparison(self, comparison: Dict):
        """Print formatted comparison report."""
        print(f"\n{'='*60}")
        print("ALGORITHM COMPARISON: GREEDY vs ALNS")
        print(f"{'='*60}")

        print(f"\n📊 Jobs Assigned:")
        print(f"  Greedy: {comparison['assigned_jobs']['greedy']}")
        print(f"  ALNS:   {comparison['assigned_jobs']['alns']}")
        print(f"  Δ:      {comparison['assigned_jobs']['improvement']:+d}")

        print(f"\n🎯 Total Score:")
        print(f"  Greedy: {comparison['total_score']['greedy']:.2f}")
        print(f"  ALNS:   {comparison['total_score']['alns']:.2f}")
        print(
            f"  Δ:      {comparison['total_score']['improvement']:+.2f} "
            f"({comparison['total_score']['improvement_pct']:+.1f}%)"
        )

        print(f"\n📈 Job Coverage:")
        print(f"  Greedy: {comparison['job_coverage']['greedy']:.1f}%")
        print(f"  ALNS:   {comparison['job_coverage']['alns']:.1f}%")
        print(f"  Δ:      {comparison['job_coverage']['improvement']:+.1f}%")

        print(f"\n🚗 Total Travel Time:")
        print(f"  Greedy: {comparison['travel_time']['greedy']:.0f} min")
        print(f"  ALNS:   {comparison['travel_time']['alns']:.0f} min")
        print(f"  Δ:      {comparison['travel_time']['improvement']:+.0f} min")

        print(f"\n⏱️  Total Idle Time:")
        print(f"  Greedy: {comparison['idle_time']['greedy']:.0f} min")
        print(f"  ALNS:   {comparison['idle_time']['alns']:.0f} min")
        print(f"  Δ:      {comparison['idle_time']['improvement']:+.0f} min")

        print(f"\n⭐ Priority Fulfillment:")
        print(f"  Greedy: {comparison['priority_fulfillment']['greedy']:.1f}%")
        print(f"  ALNS:   {comparison['priority_fulfillment']['alns']:.1f}%")
        print(f"  Δ:      {comparison['priority_fulfillment']['improvement']:+.1f}%")

        print(f"\n⏲️  Execution Time:")
        print(f"  Greedy: {comparison['execution_time']['greedy']:.2f}s")
        print(f"  ALNS:   {comparison['execution_time']['alns']:.2f}s")
        print(f"  Total:  {comparison['execution_time']['total']:.2f}s")

        print(f"\n{'='*60}")

        if comparison["total_score"]["improvement"] > 0:
            print("✅ ALNS provides significant improvement over Greedy")
        elif comparison["total_score"]["improvement"] == 0:
            print("⚖️  ALNS and Greedy produce equivalent results")
        else:
            print("⚠️  Greedy outperformed ALNS (unexpected)")

        print(f"{'='*60}\n")

    def _get_priority_value(self, priority) -> float:
        """Convert priority enum/string to numeric value."""
        priority_map = {
            "critical": 100.0,
            "CRITICAL": 100.0,
            "high": 75.0,
            "HIGH": 75.0,
            "URGENT": 100.0,
            "urgent": 100.0,
            "medium": 50.0,
            "MEDIUM": 50.0,
            "low": 25.0,
            "LOW": 25.0,
        }
        key = priority.value if hasattr(priority, "value") else str(priority)
        return priority_map.get(key, 50.0)
