"""
Phase 6: Adaptive Large Neighborhood Search (ALNS) Optimizer - Bug-fixed version
Refines initial schedules using destroy/repair operators with adaptive selection.

Bug fixes:
- Removed ConstraintValidator (needs db session not available here)
- Fixed Assignment(travel_time_minutes=...) -> travel_before_minutes
- Fixed job.estimated_duration_minutes -> job.duration_minutes
- Fixed calculate_insertion_cost() call signature
- Replaced validate_assignment calls with inline feasibility checks
"""

import random
import math
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta, time

from app.models import Job, Technician, Assignment, AssignmentStatus
from app.models.base import generate_uuid
from app.scheduler.scoring import ScheduleScorer
from app.config import Config


@dataclass
class ALNSConfig:
    """Configuration for ALNS algorithm."""
    max_iterations: int = 100
    destroy_size_min: int = 5
    destroy_size_max: int = 20
    initial_temperature: float = 100.0
    cooling_rate: float = 0.95
    weight_update_frequency: int = 10
    random_seed: int = 42


class Solution:
    """Represents a scheduling solution with assignments."""

    def __init__(self, assignments: List[Assignment], jobs: List[Job],
                 technicians: List[Technician], config: Config):
        self.assignments = assignments
        self.jobs = jobs
        self.technicians = technicians
        self.config = config
        self.scorer = ScheduleScorer()
        # No ConstraintValidator here - it requires a db Session
        self._score: Optional[float] = None
        self._assigned_job_ids: Optional[Set[str]] = None

    @property
    def score(self) -> float:
        """Calculate and cache the solution score."""
        if self._score is None:
            metrics = self.scorer.calculate_schedule_metrics(
                self.assignments, self.jobs, self.technicians
            )
            self._score = metrics["total_score"]
        return self._score

    @property
    def assigned_job_ids(self) -> Set[str]:
        """Get set of assigned job IDs."""
        if self._assigned_job_ids is None:
            self._assigned_job_ids = {a.job_id for a in self.assignments}
        return self._assigned_job_ids

    def copy(self) -> "Solution":
        """Create a deep copy of the solution."""
        new_assignments = [
            Assignment(
                job_id=a.job_id,
                technician_id=a.technician_id,
                scheduled_start=a.scheduled_start,
                scheduled_end=a.scheduled_end,
                travel_before_minutes=getattr(a, "travel_before_minutes", 0),  # correct field
                status=AssignmentStatus.PENDING,
                run_id=getattr(a, "run_id", None) or "placeholder",
            )
            for a in self.assignments
        ]
        # Carry over ORM references so scoring still works
        for new_a, old_a in zip(new_assignments, self.assignments):
            if hasattr(old_a, "job") and old_a.job is not None:
                new_a.job = old_a.job
            if hasattr(old_a, "technician") and old_a.technician is not None:
                new_a.technician = old_a.technician
        new_sol = Solution(new_assignments, self.jobs, self.technicians, self.config)
        return new_sol

    def get_unassigned_jobs(self) -> List[Job]:
        """Get list of jobs not in current solution."""
        return [j for j in self.jobs if j.id not in self.assigned_job_ids]


class ALNSOptimizer:
    """
    Adaptive Large Neighborhood Search optimizer for schedule refinement.
    Uses multiple destroy/repair operators with adaptive weight selection.
    """

    def __init__(self, config: Config, alns_config: ALNSConfig = None):
        self.config = config
        self.alns_config = alns_config or ALNSConfig()
        self.scorer = ScheduleScorer()
        random.seed(self.alns_config.random_seed)

        # Operator weights (start equal, adapt based on performance)
        self.destroy_operators = {
            "random": self._destroy_random,
            "worst": self._destroy_worst,
            "related": self._destroy_related,
            "technician": self._destroy_technician,
        }

        self.repair_operators = {
            "greedy": self._repair_greedy,
            "regret": self._repair_regret,
            "priority": self._repair_priority,
        }

        self.destroy_weights = {name: 1.0 for name in self.destroy_operators}
        self.repair_weights = {name: 1.0 for name in self.repair_operators}

        self.destroy_scores = {name: [] for name in self.destroy_operators}
        self.repair_scores = {name: [] for name in self.repair_operators}

    def optimize(self, initial_solution: Solution) -> Tuple[Solution, Dict]:
        """
        Main ALNS optimization loop.

        Returns:
            Tuple of (best_solution, statistics)
        """
        current = initial_solution.copy()
        best = initial_solution.copy()

        temperature = self.alns_config.initial_temperature
        iteration = 0

        stats = {
            "iterations": 0,
            "improvements": 0,
            "acceptances": 0,
            "initial_score": initial_solution.score,
            "best_score": best.score,
            "final_score": 0,
            "score_history": [initial_solution.score],
            "operator_performance": {},
        }

        print(f"ALNS Starting - Initial Score: {initial_solution.score:.2f}")

        for iteration in range(self.alns_config.max_iterations):
            # Select operators
            destroy_op_name = self._select_operator(self.destroy_weights)
            repair_op_name = self._select_operator(self.repair_weights)

            destroy_op = self.destroy_operators[destroy_op_name]
            repair_op = self.repair_operators[repair_op_name]

            # Apply destroy-repair
            candidate = current.copy()
            destroyed_jobs = destroy_op(candidate)
            repair_op(candidate, destroyed_jobs)

            # Evaluate and decide acceptance
            if self._accept_solution(candidate, current, best, temperature):
                improvement = candidate.score - current.score

                # Track operator performance
                self.destroy_scores[destroy_op_name].append(improvement)
                self.repair_scores[repair_op_name].append(improvement)

                current = candidate
                stats["acceptances"] += 1

                if candidate.score > best.score:
                    best = candidate.copy()
                    stats["improvements"] += 1
                    print(
                        f"Iteration {iteration}: New Best = {best.score:.2f} "
                        f"(destroy={destroy_op_name}, repair={repair_op_name})"
                    )

            # Update operator weights periodically
            if (iteration + 1) % self.alns_config.weight_update_frequency == 0:
                self._update_operator_weights()

            # Cool down temperature
            temperature *= self.alns_config.cooling_rate
            stats["score_history"].append(current.score)

        stats["iterations"] = iteration + 1
        stats["final_score"] = best.score
        stats["improvement"] = best.score - initial_solution.score
        stats["operator_performance"] = {
            "destroy": {
                k: sum(v) / len(v) if v else 0 for k, v in self.destroy_scores.items()
            },
            "repair": {
                k: sum(v) / len(v) if v else 0 for k, v in self.repair_scores.items()
            },
        }

        print(f"\nALNS Complete:")
        print(f"  Initial Score: {stats['initial_score']:.2f}")
        print(f"  Final Score: {stats['final_score']:.2f}")
        print(f"  Improvement: {stats['improvement']:.2f}")
        print(f"  Iterations: {stats['iterations']}")
        print(f"  Improvements: {stats['improvements']}")

        return best, stats

    # ====================== Operator Selection ======================

    def _select_operator(self, weights: Dict[str, float]) -> str:
        """Roulette wheel selection based on weights."""
        total = sum(weights.values())
        if total == 0:
            return random.choice(list(weights.keys()))

        r = random.uniform(0, total)
        cumsum = 0
        for name, weight in weights.items():
            cumsum += weight
            if r <= cumsum:
                return name
        return list(weights.keys())[-1]

    def _update_operator_weights(self):
        """Update operator weights based on recent performance."""

        def update_weights(weights: Dict[str, float], scores: Dict[str, List[float]]):
            for name in weights:
                if scores[name]:
                    avg_improvement = sum(scores[name]) / len(scores[name])
                    if avg_improvement > 0:
                        weights[name] = max(0.1, weights[name] * 1.1)
                    else:
                        weights[name] = max(0.1, weights[name] * 0.9)
                    scores[name].clear()

        update_weights(self.destroy_weights, self.destroy_scores)
        update_weights(self.repair_weights, self.repair_scores)

    def _accept_solution(
        self, candidate: Solution, current: Solution, best: Solution, temperature: float
    ) -> bool:
        """Simulated Annealing acceptance criterion."""
        delta = candidate.score - current.score

        if delta > 0:
            return True

        # Accept worse solution with probability based on temperature
        if temperature > 0:
            probability = math.exp(delta / temperature)
            return random.random() < probability

        return False

    # ====================== Destroy Operators ======================

    def _destroy_random(self, solution: Solution) -> List[Job]:
        """Randomly remove jobs from solution."""
        if not solution.assignments:
            return []

        destroy_count = random.randint(
            self.alns_config.destroy_size_min,
            min(self.alns_config.destroy_size_max, len(solution.assignments)),
        )

        to_remove = random.sample(solution.assignments, destroy_count)
        removed_job_ids = {a.job_id for a in to_remove}

        solution.assignments = [
            a for a in solution.assignments if a.job_id not in removed_job_ids
        ]
        solution._score = None
        solution._assigned_job_ids = None

        return [j for j in solution.jobs if j.id in removed_job_ids]

    def _destroy_worst(self, solution: Solution) -> List[Job]:
        """Remove jobs with worst insertion costs."""
        if not solution.assignments:
            return []

        # Calculate insertion cost for each assignment
        assignment_costs = []
        for assignment in solution.assignments:
            job = next((j for j in solution.jobs if j.id == assignment.job_id), None)
            tech = next(
                (t for t in solution.technicians if t.id == assignment.technician_id), None
            )
            if job is None or tech is None:
                continue

            existing = [a for a in solution.assignments if a.technician_id == tech.id and a.job_id != job.id]
            # Correct signature: (job, technician, proposed_start, existing_assignments)
            cost = self.scorer.calculate_insertion_cost(
                job, tech, assignment.scheduled_start, existing
            )
            assignment_costs.append((assignment, cost))

        # Sort by cost (higher = worse)
        assignment_costs.sort(key=lambda x: x[1], reverse=True)

        destroy_count = random.randint(
            self.alns_config.destroy_size_min,
            min(self.alns_config.destroy_size_max, len(solution.assignments)),
        )

        to_remove = [ac[0] for ac in assignment_costs[:destroy_count]]
        removed_job_ids = {a.job_id for a in to_remove}

        solution.assignments = [
            a for a in solution.assignments if a.job_id not in removed_job_ids
        ]
        solution._score = None
        solution._assigned_job_ids = None

        return [j for j in solution.jobs if j.id in removed_job_ids]

    def _destroy_related(self, solution: Solution) -> List[Job]:
        """Remove related jobs (same zone or similar time windows)."""
        if not solution.assignments:
            return []

        # Pick a seed assignment
        seed = random.choice(solution.assignments)
        seed_job = next((j for j in solution.jobs if j.id == seed.job_id), None)
        if seed_job is None:
            return self._destroy_random(solution)

        # Find related jobs (same zone or overlapping time windows)
        related = []
        for assignment in solution.assignments:
            if assignment.job_id == seed_job.id:
                continue

            job = next((j for j in solution.jobs if j.id == assignment.job_id), None)
            if job is None:
                continue

            # Same zone or time window overlap
            if job.service_zone_id == seed_job.service_zone_id or self._time_windows_overlap(
                seed_job, job
            ):
                related.append(assignment)

        if not related:
            return self._destroy_random(solution)

        destroy_count = min(
            random.randint(
                self.alns_config.destroy_size_min, self.alns_config.destroy_size_max
            ),
            len(related),
        )

        to_remove = random.sample(related, destroy_count)
        removed_job_ids = {a.job_id for a in to_remove}

        solution.assignments = [
            a for a in solution.assignments if a.job_id not in removed_job_ids
        ]
        solution._score = None
        solution._assigned_job_ids = None

        return [j for j in solution.jobs if j.id in removed_job_ids]

    def _destroy_technician(self, solution: Solution) -> List[Job]:
        """Remove all jobs from a randomly selected technician."""
        if not solution.assignments:
            return []

        # Select random technician
        tech_ids = list(set(a.technician_id for a in solution.assignments))
        if not tech_ids:
            return []

        selected_tech_id = random.choice(tech_ids)

        to_remove = [a for a in solution.assignments if a.technician_id == selected_tech_id]
        removed_job_ids = {a.job_id for a in to_remove}

        solution.assignments = [
            a for a in solution.assignments if a.technician_id != selected_tech_id
        ]
        solution._score = None
        solution._assigned_job_ids = None

        return [j for j in solution.jobs if j.id in removed_job_ids]

    # ====================== Repair Operators ======================

    def _repair_greedy(self, solution: Solution, removed_jobs: List[Job]) -> bool:
        """Greedy insertion: insert each job at best position."""
        inserted_count = 0

        for job in removed_jobs:
            best_assignment = None
            best_cost = float("inf")

            for tech in solution.technicians:
                if not self._is_eligible(job, tech):
                    continue

                # Try insertion at different time slots
                candidate = self._find_best_insertion_time(job, tech, solution)
                if candidate is None:
                    continue

                existing = [a for a in solution.assignments if a.technician_id == tech.id]
                # Correct signature: (job, technician, proposed_start, existing_assignments)
                cost = self.scorer.calculate_insertion_cost(
                    job, tech, candidate.scheduled_start, existing
                )

                if cost < best_cost:
                    best_cost = cost
                    best_assignment = candidate

            if best_assignment:
                solution.assignments.append(best_assignment)
                solution._assigned_job_ids = None
                inserted_count += 1

        solution._score = None
        return inserted_count > 0

    def _repair_regret(self, solution: Solution, removed_jobs: List[Job]) -> bool:
        """Regret-2 insertion: prioritize jobs with high regret."""
        inserted_count = 0
        remaining = list(removed_jobs)

        while remaining:
            best_job = None
            best_assignment = None
            best_regret = -1.0

            for job in remaining:
                # Find best and second-best cost across technicians
                costs = []
                candidates = []
                for tech in solution.technicians:
                    if not self._is_eligible(job, tech):
                        continue
                    cand = self._find_best_insertion_time(job, tech, solution)
                    if cand is None:
                        continue
                    existing = [a for a in solution.assignments if a.technician_id == tech.id]
                    cost = self.scorer.calculate_insertion_cost(
                        job, tech, cand.scheduled_start, existing
                    )
                    costs.append(cost)
                    candidates.append(cand)

                if not candidates:
                    continue

                sorted_pairs = sorted(zip(costs, candidates), key=lambda x: x[0])
                best_cost = sorted_pairs[0][0]
                second_best_cost = sorted_pairs[1][0] if len(sorted_pairs) > 1 else float("inf")
                regret = self.scorer.calculate_regret(job, best_cost, second_best_cost)

                if regret > best_regret:
                    best_regret = regret
                    best_job = job
                    best_assignment = sorted_pairs[0][1]

            if best_assignment and best_job:
                solution.assignments.append(best_assignment)
                solution._assigned_job_ids = None
                remaining.remove(best_job)
                inserted_count += 1
            else:
                break

        solution._score = None
        return inserted_count > 0

    def _repair_priority(self, solution: Solution, removed_jobs: List[Job]) -> bool:
        """Priority-aware insertion: high-priority jobs first."""
        inserted_count = 0

        # Sort by priority
        priority_order = {"critical": 0, "CRITICAL": 0, "high": 1, "HIGH": 1, "medium": 2, "MEDIUM": 2, "low": 3, "LOW": 3}

        def _priority_key(j: Job) -> int:
            v = j.priority.value if hasattr(j.priority, "value") else str(j.priority)
            return priority_order.get(v, 99)

        sorted_jobs = sorted(removed_jobs, key=_priority_key)

        for job in sorted_jobs:
            best_assignment = None
            best_cost = float("inf")

            for tech in solution.technicians:
                if not self._is_eligible(job, tech):
                    continue

                candidate = self._find_best_insertion_time(job, tech, solution)
                if candidate is None:
                    continue

                existing = [a for a in solution.assignments if a.technician_id == tech.id]
                cost = self.scorer.calculate_insertion_cost(
                    job, tech, candidate.scheduled_start, existing
                )

                if cost < best_cost:
                    best_cost = cost
                    best_assignment = candidate

            if best_assignment:
                solution.assignments.append(best_assignment)
                solution._assigned_job_ids = None
                inserted_count += 1

        solution._score = None
        return inserted_count > 0

    # ====================== Helper Methods ======================

    def _is_eligible(self, job: Job, tech: Technician) -> bool:
        """Check if technician is eligible for job (skills + zone)."""
        job_skill_ids = {s.id for s in job.required_skills}
        tech_skill_ids = {s.id for s in tech.skills}
        if not job_skill_ids.issubset(tech_skill_ids):
            return False

        if job.service_zone_id not in [z.id for z in tech.service_zones]:
            return False

        return True

    def _is_feasible_inline(
        self,
        job: Job,
        tech: Technician,
        start: datetime,
        end: datetime,
        existing_assignments: List[Assignment],
    ) -> bool:
        """
        Lightweight feasibility check (no db needed).
        Checks: time window, shift boundary, no overlap.
        """
        # Time window check
        if start < job.time_window_start or start > job.time_window_end:
            return False
        if end > job.time_window_end:
            return False

        # Shift boundary check
        shift_start_dt = datetime.combine(start.date(), tech.shift_start)
        shift_end_dt = datetime.combine(start.date(), tech.shift_end)
        if start < shift_start_dt or end > shift_end_dt:
            return False

        # No overlap with existing assignments for this tech
        for a in existing_assignments:
            # Overlap: not (a.end <= start or a.start >= end)
            if not (a.scheduled_end <= start or a.scheduled_start >= end):
                return False

        return True

    def _make_assignment(
        self, job: Job, tech: Technician, start: datetime, end: datetime
    ) -> Assignment:
        """Build a transient Assignment object for ALNS candidate evaluation."""
        a = Assignment(
            job_id=job.id,
            technician_id=tech.id,
            scheduled_start=start,
            scheduled_end=end,
            travel_before_minutes=0,   # correct field name
            status=AssignmentStatus.PENDING,
            run_id="alns-candidate",
        )
        a.job = job
        a.technician = tech
        return a

    def _find_best_insertion_time(
        self, job: Job, tech: Technician, solution: Solution
    ) -> Optional[Assignment]:
        """Find best time slot to insert job for technician."""
        tech_assignments = sorted(
            [a for a in solution.assignments if a.technician_id == tech.id],
            key=lambda a: a.scheduled_start,
        )
        existing = tech_assignments  # same list for overlap checking

        candidates = []

        if not tech_assignments:
            # No assignments yet: try at earliest time window
            c = self._try_insert_at_earliest(job, tech, existing)
            if c:
                candidates.append(c)
        else:
            # Try before first
            c = self._try_insert_before(job, tech, tech_assignments[0], existing)
            if c:
                candidates.append(c)

            # Try between consecutive
            for i in range(len(tech_assignments) - 1):
                c = self._try_insert_between(
                    job, tech, tech_assignments[i], tech_assignments[i + 1], existing
                )
                if c:
                    candidates.append(c)

            # Try after last
            c = self._try_insert_after(job, tech, tech_assignments[-1], existing)
            if c:
                candidates.append(c)

        if not candidates:
            return None

        # Return candidate with lowest insertion cost
        best = min(
            candidates,
            key=lambda c: self.scorer.calculate_insertion_cost(
                job, tech, c.scheduled_start, existing
            ),
        )
        return best

    def _try_insert_at_earliest(
        self, job: Job, tech: Technician, existing: List[Assignment]
    ) -> Optional[Assignment]:
        """Try inserting at earliest possible time."""
        shift_start_dt = None  # will be computed from job window
        start = job.time_window_start
        end = start + timedelta(minutes=job.duration_minutes)   # correct field

        if self._is_feasible_inline(job, tech, start, end, existing):
            return self._make_assignment(job, tech, start, end)
        return None

    def _try_insert_before(
        self,
        job: Job,
        tech: Technician,
        next_assignment: Assignment,
        existing: List[Assignment],
    ) -> Optional[Assignment]:
        """Try inserting before next assignment."""
        end = next_assignment.scheduled_start
        start = end - timedelta(minutes=job.duration_minutes)  # correct field

        if start < job.time_window_start:
            return None

        if self._is_feasible_inline(job, tech, start, end, existing):
            return self._make_assignment(job, tech, start, end)
        return None

    def _try_insert_after(
        self,
        job: Job,
        tech: Technician,
        prev_assignment: Assignment,
        existing: List[Assignment],
    ) -> Optional[Assignment]:
        """Try inserting after previous assignment."""
        start = prev_assignment.scheduled_end
        end = start + timedelta(minutes=job.duration_minutes)  # correct field

        if end > job.time_window_end:
            return None

        if self._is_feasible_inline(job, tech, start, end, existing):
            return self._make_assignment(job, tech, start, end)
        return None

    def _try_insert_between(
        self,
        job: Job,
        tech: Technician,
        prev_assignment: Assignment,
        next_assignment: Assignment,
        existing: List[Assignment],
    ) -> Optional[Assignment]:
        """Try inserting between two assignments."""
        start = prev_assignment.scheduled_end
        end = start + timedelta(minutes=job.duration_minutes)  # correct field

        if end > next_assignment.scheduled_start or end > job.time_window_end:
            return None

        if self._is_feasible_inline(job, tech, start, end, existing):
            return self._make_assignment(job, tech, start, end)
        return None

    def _time_windows_overlap(self, job1: Job, job2: Job) -> bool:
        """Check if two jobs have overlapping time windows."""
        return not (
            job1.time_window_end <= job2.time_window_start
            or job2.time_window_end <= job1.time_window_start
        )
