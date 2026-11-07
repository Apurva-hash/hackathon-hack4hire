"""
Phase 5: Greedy Insertion Algorithm

Generates an initial feasible schedule by inserting jobs one at a time
using a greedy heuristic with Least Flexible Job First (LFJ) strategy.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Set
from sqlalchemy.orm import Session

from app.models import Job, Technician, Assignment, JobPriority, JobStatus, AssignmentStatus
from app.scheduler.constraints import ConstraintValidator
from app.scheduler.scoring import ScheduleScorer
from app.utils.time_utils import generate_time_slots
from app.config import settings


class InsertionCandidate:
    """Represents a candidate insertion position for a job."""
    
    def __init__(
        self,
        job: Job,
        technician: Technician,
        start_time: datetime,
        cost: float
    ):
        self.job = job
        self.technician = technician
        self.start_time = start_time
        self.cost = cost


class GreedyInsertion:
    """Greedy Insertion scheduler with Least Flexible Job First strategy."""
    
    def __init__(self, db: Session):
        self.db = db
        self.validator = ConstraintValidator(db)
        self.scorer = ScheduleScorer()
    
    def generate_schedule(
        self,
        jobs: List[Job],
        technicians: List[Technician],
        protected_job_ids: Set[str] = None
    ) -> Tuple[List[Assignment], List[Job], Dict[str, str]]:
        """
        Generate initial schedule using Greedy Insertion with LFJ.
        
        Args:
            jobs: Jobs to schedule
            technicians: Available technicians
            protected_job_ids: Jobs that cannot be modified (completed/in-progress)
        
        Returns:
            Tuple of (assignments, unassigned_jobs, unassigned_reasons)
        """
        if protected_job_ids is None:
            protected_job_ids = set()
        
        # Initialize data structures
        assignments: List[Assignment] = []
        technician_assignments: Dict[str, List[Assignment]] = {
            tech.id: [] for tech in technicians
        }
        unassigned_jobs: List[Job] = []
        unassigned_reasons: Dict[str, str] = {}
        
        # Step 1: Filter and prioritize jobs using Least Flexible Job First
        schedulable_jobs = self._prioritize_jobs_lfj(jobs, technicians, protected_job_ids)
        
        print(f"\n🔄 Greedy Insertion: Scheduling {len(schedulable_jobs)} jobs...")
        
        # Step 2: Insert each job greedily
        for idx, job in enumerate(schedulable_jobs):
            if (idx + 1) % 10 == 0:
                print(f"  Progress: {idx + 1}/{len(schedulable_jobs)} jobs processed...")
            
            # Find best insertion position
            best_candidate = self._find_best_insertion(
                job,
                technicians,
                technician_assignments,
                protected_job_ids
            )
            
            if best_candidate:
                # Create assignment
                assignment = self._create_assignment(best_candidate)
                assignments.append(assignment)
                technician_assignments[best_candidate.technician.id].append(assignment)
            else:
                # Job cannot be assigned
                unassigned_jobs.append(job)
                reason = self._determine_unassigned_reason(job, technicians)
                unassigned_reasons[job.id] = reason
        
        print(f"✅ Greedy Insertion complete: {len(assignments)} assigned, {len(unassigned_jobs)} unassigned")
        
        return assignments, unassigned_jobs, unassigned_reasons
    
    def _prioritize_jobs_lfj(
        self,
        jobs: List[Job],
        technicians: List[Technician],
        protected_job_ids: Set[str]
    ) -> List[Job]:
        """
        Prioritize jobs using Least Flexible Job First (LFJ) strategy.
        
        Jobs are ordered by:
        1. Priority (Critical > High > Medium > Low)
        2. Flexibility (tighter time windows first)
        3. Number of eligible technicians (fewer = less flexible)
        4. SLA deadline (earliest first)
        5. Job ID (deterministic tie-breaker)
        
        Args:
            jobs: Jobs to prioritize
            technicians: Available technicians
            protected_job_ids: Protected jobs to exclude
        
        Returns:
            Sorted list of jobs
        """
        # Filter out protected jobs
        schedulable = [j for j in jobs if j.id not in protected_job_ids and j.status == JobStatus.PENDING]
        
        # Calculate flexibility metrics for each job
        job_metrics = []
        for job in schedulable:
            # Time window flexibility
            window_duration = (job.time_window_end - job.time_window_start).total_seconds() / 3600
            
            # Count eligible technicians
            eligible_count = 0
            required_skill_ids = set(skill.id for skill in job.required_skills)
            
            for tech in technicians:
                tech_skill_ids = set(skill.id for skill in tech.skills)
                tech_zone_ids = set(zone.id for zone in tech.service_zones)
                
                has_skills = required_skill_ids.issubset(tech_skill_ids)
                has_zone = job.service_zone_id in tech_zone_ids
                
                if has_skills and has_zone:
                    eligible_count += 1
            
            # Priority score (higher = more urgent)
            priority_score = {
                JobPriority.CRITICAL: 1000,
                JobPriority.HIGH: 100,
                JobPriority.MEDIUM: 10,
                JobPriority.LOW: 1
            }[job.priority]
            
            # Flexibility score (lower = less flexible = higher priority)
            # Combine: eligible techs, time window, SLA urgency
            flexibility_score = (eligible_count * 100) + (window_duration * 10)
            
            job_metrics.append({
                'job': job,
                'priority_score': priority_score,
                'flexibility_score': flexibility_score,
                'eligible_count': eligible_count,
                'window_duration': window_duration,
                'sla_deadline': job.sla_deadline
            })
        
        # Sort: High priority first, then low flexibility (LFJ), then early SLA
        sorted_jobs = sorted(
            job_metrics,
            key=lambda x: (
                -x['priority_score'],          # Higher priority first
                x['flexibility_score'],         # Less flexible first (LFJ)
                x['sla_deadline'],             # Earlier SLA first
                x['job'].id                    # Deterministic tie-breaker
            )
        )
        
        return [item['job'] for item in sorted_jobs]
    
    def _find_best_insertion(
        self,
        job: Job,
        technicians: List[Technician],
        technician_assignments: Dict[str, List[Assignment]],
        protected_job_ids: Set[str]
    ) -> Optional[InsertionCandidate]:
        """
        Find the best insertion position for a job.
        
        Evaluates all feasible technician/time combinations and selects
        the one with the lowest cost.
        
        Args:
            job: Job to insert
            technicians: Available technicians
            technician_assignments: Current assignments per technician
            protected_job_ids: Protected jobs
        
        Returns:
            Best insertion candidate, or None if no feasible position exists
        """
        best_candidate: Optional[InsertionCandidate] = None
        best_cost = float('inf')
        
        for technician in technicians:
            # Quick eligibility check
            if not self._is_eligible(job, technician):
                continue
            
            # Get existing assignments for this technician
            existing = technician_assignments.get(technician.id, [])
            
            # Generate candidate time slots
            time_slots = generate_time_slots(
                job.time_window_start,
                job.time_window_end,
                slot_interval_minutes=settings.schedule_time_slot_interval_minutes
            )
            
            for start_time in time_slots:
                # Validate all hard constraints
                violations = self.validator.validate_all_constraints(
                    job,
                    technician,
                    start_time,
                    existing,
                    protected_job_ids
                )
                
                if not violations:  # Feasible
                    # Calculate insertion cost
                    cost = self.scorer.calculate_insertion_cost(
                        job,
                        technician,
                        start_time,
                        existing
                    )
                    
                    if cost < best_cost:
                        best_cost = cost
                        best_candidate = InsertionCandidate(
                            job=job,
                            technician=technician,
                            start_time=start_time,
                            cost=cost
                        )
        
        return best_candidate
    
    def _is_eligible(self, job: Job, technician: Technician) -> bool:
        """Quick eligibility check (skills + zone)."""
        # Check skills
        required_skill_ids = set(skill.id for skill in job.required_skills)
        tech_skill_ids = set(skill.id for skill in technician.skills)
        
        if not required_skill_ids.issubset(tech_skill_ids):
            return False
        
        # Check zone
        tech_zone_ids = set(zone.id for zone in technician.service_zones)
        if job.service_zone_id not in tech_zone_ids:
            return False
        
        return True
    
    def _create_assignment(self, candidate: InsertionCandidate) -> Assignment:
        """Create an Assignment object from a candidate."""
        end_time = candidate.start_time + timedelta(minutes=candidate.job.duration_minutes)
        
        # Calculate travel time from previous job (if any)
        # This is stored for informational purposes
        travel_before = 0
        
        assignment = Assignment(
            job_id=candidate.job.id,
            technician_id=candidate.technician.id,
            scheduled_start=candidate.start_time,
            scheduled_end=end_time,
            travel_before_minutes=travel_before,
            status=AssignmentStatus.PENDING,  # Use enum, not string
            run_id="greedy-candidate",        # Placeholder; engine will persist to DB
        )
        
        # Note: assignment.job and assignment.technician will be set by relationships
        assignment.job = candidate.job
        assignment.technician = candidate.technician
        
        return assignment
    
    def _determine_unassigned_reason(
        self,
        job: Job,
        technicians: List[Technician]
    ) -> str:
        """Determine why a job couldn't be assigned."""
        # Check if job is impossible
        is_impossible, reason, message = self.validator.is_job_impossible(job, technicians)
        
        if is_impossible:
            return message
        
        # Job is feasible but couldn't find a slot
        return (
            f"No available time slot found within time window "
            f"({job.time_window_start.strftime('%Y-%m-%d %H:%M')} - "
            f"{job.time_window_end.strftime('%H:%M')}) "
            f"that satisfies all constraints (shift, availability, travel time)"
        )


def run_greedy_insertion(
    db: Session,
    jobs: List[Job],
    technicians: List[Technician],
    protected_job_ids: Set[str] = None
) -> Tuple[List[Assignment], List[Job], Dict[str, str], Dict[str, float]]:
    """
    Convenience function to run Greedy Insertion and calculate metrics.
    
    Args:
        db: Database session
        jobs: Jobs to schedule
        technicians: Available technicians
        protected_job_ids: Protected jobs
    
    Returns:
        Tuple of (assignments, unassigned_jobs, unassigned_reasons, metrics)
    """
    scheduler = GreedyInsertion(db)
    
    # Generate schedule
    assignments, unassigned_jobs, unassigned_reasons = scheduler.generate_schedule(
        jobs,
        technicians,
        protected_job_ids
    )
    
    # Calculate metrics
    scorer = ScheduleScorer()
    metrics = scorer.calculate_schedule_metrics(assignments, jobs, technicians)
    
    return assignments, unassigned_jobs, unassigned_reasons, metrics
