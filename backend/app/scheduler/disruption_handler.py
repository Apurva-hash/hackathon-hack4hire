"""
Phase 7: Disruption Handling & Re-optimization
Detects and handles schedule disruptions with recovery strategies.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Set, Tuple
from enum import Enum
import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.job import Job, JobStatus
from app.models.technician import Technician
from app.models.assignment import Assignment, AssignmentStatus
from app.models.disruption_event import DisruptionEvent, DisruptionType, ImpactLevel
from app.models.scheduling_run import SchedulingRun
from app.scheduler.constraints import ConstraintValidator
from app.scheduler.greedy_insertion import GreedyInsertion
from app.scheduler.alns_optimizer import ALNSOptimizer, ALNSConfig
from app.scheduler.scoring import ScheduleScorer

logger = logging.getLogger(__name__)


class RecoveryStrategy(Enum):
    """Recovery strategies for different disruption types."""
    FULL_REOPTIMIZATION = "full_reoptimization"  # Complete schedule rebuild
    PARTIAL_REOPTIMIZATION = "partial_reoptimization"  # Only affected assignments
    INCREMENTAL_INSERT = "incremental_insert"  # Insert new job into existing schedule
    REASSIGN_JOBS = "reassign_jobs"  # Reassign affected jobs to other techs
    NO_ACTION = "no_action"  # Disruption handled, no changes needed


@dataclass
class DisruptionImpact:
    """Analysis of disruption impact on schedule."""
    affected_assignments: List[Assignment]
    affected_jobs: List[Job]
    affected_technicians: List[Technician]
    downstream_conflicts: List[Assignment]  # Jobs scheduled after disruption
    impact_score: float  # 0-100, severity of impact
    recovery_strategy: RecoveryStrategy
    reason: str


class DisruptionDetector:
    """Detects various types of schedule disruptions."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def detect_technician_unavailability(
        self,
        technician_id: str,
        unavailable_from: datetime,
        unavailable_until: Optional[datetime] = None
    ) -> Optional[DisruptionEvent]:
        """
        Detect when a technician becomes unavailable.
        
        Args:
            technician_id: Technician UUID
            unavailable_from: Start of unavailability
            unavailable_until: End of unavailability (None = indefinite)
        
        Returns:
            DisruptionEvent if there are affected assignments, None otherwise
        """
        # Find all assignments for this technician after unavailable_from
        affected_assignments = self.db.query(Assignment).filter(
            and_(
                Assignment.technician_id == technician_id,
                Assignment.scheduled_start >= unavailable_from,
                Assignment.status.in_([AssignmentStatus.SCHEDULED, AssignmentStatus.TRAVELING])
            )
        ).all()
        
        if not affected_assignments:
            return None
        
        # Determine impact level
        critical_count = sum(1 for a in affected_assignments if a.job.priority == 'CRITICAL')
        impact_level = ImpactLevel.HIGH if critical_count > 0 else (
            ImpactLevel.MEDIUM if len(affected_assignments) > 5 else ImpactLevel.LOW
        )
        
        # Create disruption event
        event = DisruptionEvent(
            disruption_type=DisruptionType.TECHNICIAN_UNAVAILABLE,
            detected_at=datetime.utcnow(),
            technician_id=technician_id,
            impact_level=impact_level,
            description=f"Technician unavailable from {unavailable_from}" + 
                       (f" until {unavailable_until}" if unavailable_until else " indefinitely"),
            metadata={
                "unavailable_from": unavailable_from.isoformat(),
                "unavailable_until": unavailable_until.isoformat() if unavailable_until else None,
                "affected_assignment_count": len(affected_assignments)
            }
        )
        
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        
        logger.info(f"Detected technician unavailability: {event.id}, {len(affected_assignments)} assignments affected")
        return event
    
    def detect_job_cancellation(self, job_id: str) -> Optional[DisruptionEvent]:
        """
        Detect when a job is cancelled.
        
        Args:
            job_id: Job UUID
        
        Returns:
            DisruptionEvent if job had an assignment, None otherwise
        """
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.warning(f"Job {job_id} not found for cancellation detection")
            return None
        
        # Check if job has an active assignment
        assignment = self.db.query(Assignment).filter(
            and_(
                Assignment.job_id == job_id,
                Assignment.status.in_([AssignmentStatus.SCHEDULED, AssignmentStatus.TRAVELING])
            )
        ).first()
        
        if not assignment:
            # Job wasn't scheduled, minimal impact
            return None
        
        # Determine impact level based on priority
        impact_map = {
            'CRITICAL': ImpactLevel.HIGH,
            'HIGH': ImpactLevel.MEDIUM,
            'MEDIUM': ImpactLevel.LOW,
            'LOW': ImpactLevel.LOW
        }
        impact_level = impact_map.get(job.priority, ImpactLevel.LOW)
        
        # Create disruption event
        event = DisruptionEvent(
            disruption_type=DisruptionType.JOB_CANCELLED,
            detected_at=datetime.utcnow(),
            job_id=job_id,
            technician_id=assignment.technician_id,
            impact_level=impact_level,
            description=f"Job '{job.title}' cancelled, was scheduled with technician",
            metadata={
                "job_priority": job.priority,
                "assignment_id": str(assignment.id),
                "scheduled_start": assignment.scheduled_start.isoformat()
            }
        )
        
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        
        logger.info(f"Detected job cancellation: {event.id}")
        return event
    
    def detect_emergency_job(self, job_id: str) -> Optional[DisruptionEvent]:
        """
        Detect when an emergency job is added that requires immediate scheduling.
        
        Args:
            job_id: Job UUID
        
        Returns:
            DisruptionEvent for emergency job
        """
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.warning(f"Job {job_id} not found for emergency detection")
            return None
        
        # Emergency jobs are CRITICAL priority with tight time windows
        if job.priority != 'CRITICAL':
            return None
        
        # Create disruption event
        event = DisruptionEvent(
            disruption_type=DisruptionType.EMERGENCY_JOB,
            detected_at=datetime.utcnow(),
            job_id=job_id,
            impact_level=ImpactLevel.HIGH,
            description=f"Emergency job '{job.title}' requires immediate scheduling",
            metadata={
                "job_title": job.title,
                "earliest_start": job.earliest_start.isoformat(),
                "latest_end": job.latest_end.isoformat(),
                "required_skills": [s.name for s in job.required_skills]
            }
        )
        
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        
        logger.info(f"Detected emergency job: {event.id}")
        return event
    
    def detect_schedule_conflict(
        self,
        assignment_id: str,
        conflict_reason: str
    ) -> Optional[DisruptionEvent]:
        """
        Detect when a schedule conflict is discovered (overlapping times, constraint violations, etc).
        
        Args:
            assignment_id: Assignment UUID with conflict
            conflict_reason: Description of the conflict
        
        Returns:
            DisruptionEvent for the conflict
        """
        assignment = self.db.query(Assignment).filter(Assignment.id == assignment_id).first()
        if not assignment:
            logger.warning(f"Assignment {assignment_id} not found for conflict detection")
            return None
        
        # Create disruption event
        event = DisruptionEvent(
            disruption_type=DisruptionType.SCHEDULE_CONFLICT,
            detected_at=datetime.utcnow(),
            job_id=assignment.job_id,
            technician_id=assignment.technician_id,
            impact_level=ImpactLevel.MEDIUM,
            description=f"Schedule conflict detected: {conflict_reason}",
            metadata={
                "assignment_id": str(assignment_id),
                "conflict_reason": conflict_reason
            }
        )
        
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        
        logger.info(f"Detected schedule conflict: {event.id}")
        return event


class DisruptionRecovery:
    """Handles recovery from schedule disruptions."""
    
    def __init__(self, db: Session):
        self.db = db
        self.detector = DisruptionDetector(db)
        self.validator = ConstraintValidator(db)
        self.scorer = ScheduleScorer()
    
    def analyze_impact(self, event: DisruptionEvent) -> DisruptionImpact:
        """
        Analyze the impact of a disruption event on the schedule.
        
        Args:
            event: The disruption event
        
        Returns:
            DisruptionImpact analysis
        """
        if event.disruption_type == DisruptionType.TECHNICIAN_UNAVAILABLE:
            return self._analyze_technician_unavailability_impact(event)
        
        elif event.disruption_type == DisruptionType.JOB_CANCELLED:
            return self._analyze_job_cancellation_impact(event)
        
        elif event.disruption_type == DisruptionType.EMERGENCY_JOB:
            return self._analyze_emergency_job_impact(event)
        
        elif event.disruption_type == DisruptionType.SCHEDULE_CONFLICT:
            return self._analyze_schedule_conflict_impact(event)
        
        else:
            return DisruptionImpact(
                affected_assignments=[],
                affected_jobs=[],
                affected_technicians=[],
                downstream_conflicts=[],
                impact_score=0,
                recovery_strategy=RecoveryStrategy.NO_ACTION,
                reason="Unknown disruption type"
            )
    
    def _analyze_technician_unavailability_impact(self, event: DisruptionEvent) -> DisruptionImpact:
        """Analyze impact of technician becoming unavailable."""
        # Get all affected assignments
        unavailable_from = datetime.fromisoformat(event.metadata["unavailable_from"])
        
        affected_assignments = self.db.query(Assignment).filter(
            and_(
                Assignment.technician_id == event.technician_id,
                Assignment.scheduled_start >= unavailable_from,
                Assignment.status.in_([AssignmentStatus.SCHEDULED, AssignmentStatus.TRAVELING])
            )
        ).all()
        
        if not affected_assignments:
            return DisruptionImpact(
                affected_assignments=[],
                affected_jobs=[],
                affected_technicians=[],
                downstream_conflicts=[],
                impact_score=0,
                recovery_strategy=RecoveryStrategy.NO_ACTION,
                reason="No active assignments affected"
            )
        
        affected_jobs = [a.job for a in affected_assignments]
        technician = self.db.query(Technician).filter(Technician.id == event.technician_id).first()
        
        # Calculate impact score
        critical_jobs = sum(1 for j in affected_jobs if j.priority == 'CRITICAL')
        high_jobs = sum(1 for j in affected_jobs if j.priority == 'HIGH')
        impact_score = min(100, (critical_jobs * 30) + (high_jobs * 15) + (len(affected_jobs) * 5))
        
        # Determine recovery strategy
        if len(affected_jobs) > 10 or critical_jobs > 3:
            strategy = RecoveryStrategy.FULL_REOPTIMIZATION
            reason = f"{len(affected_jobs)} jobs need reassignment, full reoptimization required"
        elif len(affected_jobs) > 0:
            strategy = RecoveryStrategy.REASSIGN_JOBS
            reason = f"{len(affected_jobs)} jobs need reassignment to other technicians"
        else:
            strategy = RecoveryStrategy.NO_ACTION
            reason = "No jobs affected"
        
        return DisruptionImpact(
            affected_assignments=affected_assignments,
            affected_jobs=affected_jobs,
            affected_technicians=[technician] if technician else [],
            downstream_conflicts=[],
            impact_score=impact_score,
            recovery_strategy=strategy,
            reason=reason
        )
    
    def _analyze_job_cancellation_impact(self, event: DisruptionEvent) -> DisruptionImpact:
        """Analyze impact of job cancellation."""
        assignment = self.db.query(Assignment).filter(
            and_(
                Assignment.job_id == event.job_id,
                Assignment.status.in_([AssignmentStatus.SCHEDULED, AssignmentStatus.TRAVELING])
            )
        ).first()
        
        if not assignment:
            return DisruptionImpact(
                affected_assignments=[],
                affected_jobs=[],
                affected_technicians=[],
                downstream_conflicts=[],
                impact_score=0,
                recovery_strategy=RecoveryStrategy.NO_ACTION,
                reason="Job had no active assignment"
            )
        
        # Find downstream assignments (jobs scheduled after this one for same tech)
        downstream = self.db.query(Assignment).filter(
            and_(
                Assignment.technician_id == assignment.technician_id,
                Assignment.scheduled_start > assignment.scheduled_end,
                Assignment.status == AssignmentStatus.SCHEDULED
            )
        ).order_by(Assignment.scheduled_start).all()
        
        job = assignment.job
        technician = assignment.technician
        
        # Calculate impact - cancelled job frees up time
        impact_score = 10  # Minimal impact, creates opportunity
        
        # Strategy: Partial reoptimization to fill the gap
        strategy = RecoveryStrategy.PARTIAL_REOPTIMIZATION
        reason = f"Job cancelled, {len(downstream)} downstream jobs may be optimized"
        
        return DisruptionImpact(
            affected_assignments=[assignment],
            affected_jobs=[job],
            affected_technicians=[technician],
            downstream_conflicts=downstream,
            impact_score=impact_score,
            recovery_strategy=strategy,
            reason=reason
        )
    
    def _analyze_emergency_job_impact(self, event: DisruptionEvent) -> DisruptionImpact:
        """Analyze impact of emergency job requiring immediate scheduling."""
        job = self.db.query(Job).filter(Job.id == event.job_id).first()
        
        if not job:
            return DisruptionImpact(
                affected_assignments=[],
                affected_jobs=[],
                affected_technicians=[],
                downstream_conflicts=[],
                impact_score=0,
                recovery_strategy=RecoveryStrategy.NO_ACTION,
                reason="Emergency job not found"
            )
        
        # Find technicians with required skills in the job's service zone
        eligible_technicians = self.validator.get_eligible_technicians(job)
        
        if not eligible_technicians:
            impact_score = 100
            strategy = RecoveryStrategy.NO_ACTION
            reason = "No eligible technicians available for emergency job"
        else:
            impact_score = 70  # High impact, may require moving other jobs
            strategy = RecoveryStrategy.INCREMENTAL_INSERT
            reason = f"Emergency job needs insertion, {len(eligible_technicians)} eligible technicians"
        
        return DisruptionImpact(
            affected_assignments=[],
            affected_jobs=[job],
            affected_technicians=eligible_technicians[:5],  # Top 5 candidates
            downstream_conflicts=[],
            impact_score=impact_score,
            recovery_strategy=strategy,
            reason=reason
        )
    
    def _analyze_schedule_conflict_impact(self, event: DisruptionEvent) -> DisruptionImpact:
        """Analyze impact of schedule conflict."""
        assignment_id = event.metadata.get("assignment_id")
        if not assignment_id:
            return DisruptionImpact(
                affected_assignments=[],
                affected_jobs=[],
                affected_technicians=[],
                downstream_conflicts=[],
                impact_score=0,
                recovery_strategy=RecoveryStrategy.NO_ACTION,
                reason="No assignment specified in conflict"
            )
        
        assignment = self.db.query(Assignment).filter(Assignment.id == assignment_id).first()
        if not assignment:
            return DisruptionImpact(
                affected_assignments=[],
                affected_jobs=[],
                affected_technicians=[],
                downstream_conflicts=[],
                impact_score=0,
                recovery_strategy=RecoveryStrategy.NO_ACTION,
                reason="Conflicting assignment not found"
            )
        
        impact_score = 50  # Medium impact
        strategy = RecoveryStrategy.REASSIGN_JOBS
        reason = f"Schedule conflict requires reassignment: {event.metadata.get('conflict_reason', 'Unknown')}"
        
        return DisruptionImpact(
            affected_assignments=[assignment],
            affected_jobs=[assignment.job],
            affected_technicians=[assignment.technician],
            downstream_conflicts=[],
            impact_score=impact_score,
            recovery_strategy=strategy,
            reason=reason
        )
    
    def recover_from_disruption(
        self,
        event: DisruptionEvent,
        impact: DisruptionImpact
    ) -> SchedulingRun:
        """
        Execute recovery strategy for a disruption.
        
        Args:
            event: The disruption event
            impact: Impact analysis
        
        Returns:
            SchedulingRun for the recovery operation
        """
        logger.info(f"Starting recovery for disruption {event.id}, strategy: {impact.recovery_strategy.value}")
        
        if impact.recovery_strategy == RecoveryStrategy.FULL_REOPTIMIZATION:
            return self._execute_full_reoptimization(event, impact)
        
        elif impact.recovery_strategy == RecoveryStrategy.PARTIAL_REOPTIMIZATION:
            return self._execute_partial_reoptimization(event, impact)
        
        elif impact.recovery_strategy == RecoveryStrategy.INCREMENTAL_INSERT:
            return self._execute_incremental_insert(event, impact)
        
        elif impact.recovery_strategy == RecoveryStrategy.REASSIGN_JOBS:
            return self._execute_reassign_jobs(event, impact)
        
        else:  # NO_ACTION
            # Still create a scheduling run to track that we analyzed it
            run = SchedulingRun(
                algorithm="no_action",
                status="completed",
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                config={
                    "disruption_event_id": str(event.id),
                    "recovery_strategy": impact.recovery_strategy.value,
                    "reason": impact.reason
                },
                metrics={
                    "action_taken": False,
                    "impact_score": impact.impact_score
                }
            )
            self.db.add(run)
            self.db.commit()
            self.db.refresh(run)
            return run
    
    def _execute_full_reoptimization(
        self,
        event: DisruptionEvent,
        impact: DisruptionImpact
    ) -> SchedulingRun:
        """Execute full schedule reoptimization."""
        logger.info("Executing full reoptimization")
        
        # Cancel all affected assignments
        for assignment in impact.affected_assignments:
            assignment.status = AssignmentStatus.CANCELLED
            assignment.job.status = JobStatus.PENDING
        
        self.db.commit()
        
        # Get all unscheduled jobs
        unscheduled_jobs = self.db.query(Job).filter(
            Job.status == JobStatus.PENDING
        ).all()
        
        # Get all available technicians (excluding unavailable one if applicable)
        technicians = self.db.query(Technician).filter(
            Technician.is_active == True
        ).all()
        
        if event.technician_id:
            technicians = [t for t in technicians if str(t.id) != str(event.technician_id)]
        
        # Create scheduling run
        run = SchedulingRun(
            algorithm="full_reoptimization_greedy_alns",
            status="running",
            started_at=datetime.utcnow(),
            config={
                "disruption_event_id": str(event.id),
                "recovery_strategy": RecoveryStrategy.FULL_REOPTIMIZATION.value,
                "jobs_to_schedule": len(unscheduled_jobs),
                "available_technicians": len(technicians)
            }
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        
        # Run greedy insertion
        greedy = GreedyInsertion(self.db)
        greedy_result = greedy.run(
            jobs=unscheduled_jobs,
            technicians=technicians,
            scheduling_run_id=run.id
        )
        
        # Run ALNS optimization
        alns_config = ALNSConfig(
            max_iterations=100,
            destroy_fraction=0.25,
            temperature_start=1000.0,
            temperature_end=1.0
        )
        alns = ALNSOptimizer(self.db, alns_config)
        alns_result = alns.optimize(
            initial_assignments=greedy_result["assignments"],
            all_jobs=unscheduled_jobs,
            all_technicians=technicians,
            scheduling_run_id=run.id
        )
        
        # Update run
        run.status = "completed"
        run.completed_at = datetime.utcnow()
        run.metrics = {
            "greedy_assigned": len(greedy_result["assignments"]),
            "alns_assigned": len(alns_result["assignments"]),
            "improvement_pct": alns_result["improvement_pct"],
            "recovery_successful": len(alns_result["assignments"]) >= len(impact.affected_jobs)
        }
        
        self.db.commit()
        logger.info(f"Full reoptimization complete: {len(alns_result['assignments'])} jobs scheduled")
        
        return run
    
    def _execute_partial_reoptimization(
        self,
        event: DisruptionEvent,
        impact: DisruptionImpact
    ) -> SchedulingRun:
        """Execute partial reoptimization for affected region."""
        logger.info("Executing partial reoptimization")
        
        # Cancel affected assignments
        for assignment in impact.affected_assignments:
            assignment.status = AssignmentStatus.CANCELLED
            assignment.job.status = JobStatus.PENDING
        
        # Also consider downstream assignments for reoptimization
        affected_tech_ids = {a.technician_id for a in impact.affected_assignments}
        
        self.db.commit()
        
        # Get jobs that need rescheduling
        jobs_to_reschedule = [a.job for a in impact.affected_assignments]
        
        # Get affected technicians plus a few neighbors
        technicians = self.db.query(Technician).filter(
            and_(
                Technician.is_active == True,
                or_(
                    Technician.id.in_(affected_tech_ids),
                    Technician.id != event.technician_id  # Anyone except unavailable one
                )
            )
        ).limit(10).all()  # Limit scope
        
        # Create scheduling run
        run = SchedulingRun(
            algorithm="partial_reoptimization_greedy",
            status="running",
            started_at=datetime.utcnow(),
            config={
                "disruption_event_id": str(event.id),
                "recovery_strategy": RecoveryStrategy.PARTIAL_REOPTIMIZATION.value,
                "jobs_to_schedule": len(jobs_to_reschedule),
                "available_technicians": len(technicians)
            }
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        
        # Run greedy insertion for affected jobs only
        greedy = GreedyInsertion(self.db)
        result = greedy.run(
            jobs=jobs_to_reschedule,
            technicians=technicians,
            scheduling_run_id=run.id
        )
        
        # Update run
        run.status = "completed"
        run.completed_at = datetime.utcnow()
        run.metrics = {
            "jobs_to_reschedule": len(jobs_to_reschedule),
            "jobs_rescheduled": len(result["assignments"]),
            "jobs_still_unassigned": len(result["unassigned_jobs"]),
            "recovery_successful": len(result["unassigned_jobs"]) == 0
        }
        
        self.db.commit()
        logger.info(f"Partial reoptimization complete: {len(result['assignments'])} jobs rescheduled")
        
        return run
    
    def _execute_incremental_insert(
        self,
        event: DisruptionEvent,
        impact: DisruptionImpact
    ) -> SchedulingRun:
        """Insert emergency job into existing schedule."""
        logger.info("Executing incremental insertion for emergency job")
        
        if not impact.affected_jobs:
            logger.warning("No job to insert")
            return self._create_no_action_run(event, impact, "No job specified for insertion")
        
        emergency_job = impact.affected_jobs[0]
        
        # Create scheduling run
        run = SchedulingRun(
            algorithm="incremental_insert_greedy",
            status="running",
            started_at=datetime.utcnow(),
            config={
                "disruption_event_id": str(event.id),
                "recovery_strategy": RecoveryStrategy.INCREMENTAL_INSERT.value,
                "emergency_job_id": str(emergency_job.id),
                "eligible_technicians": len(impact.affected_technicians)
            }
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        
        # Try to insert into existing schedules
        greedy = GreedyInsertion(self.db)
        result = greedy.run(
            jobs=[emergency_job],
            technicians=impact.affected_technicians if impact.affected_technicians else 
                       self.db.query(Technician).filter(Technician.is_active == True).all(),
            scheduling_run_id=run.id
        )
        
        # Update run
        run.status = "completed"
        run.completed_at = datetime.utcnow()
        run.metrics = {
            "emergency_job_assigned": len(result["assignments"]) > 0,
            "assigned_to": str(result["assignments"][0].technician_id) if result["assignments"] else None,
            "scheduled_start": result["assignments"][0].scheduled_start.isoformat() if result["assignments"] else None,
            "recovery_successful": len(result["assignments"]) > 0
        }
        
        self.db.commit()
        logger.info(f"Incremental insertion complete: {'Success' if result['assignments'] else 'Failed'}")
        
        return run
    
    def _execute_reassign_jobs(
        self,
        event: DisruptionEvent,
        impact: DisruptionImpact
    ) -> SchedulingRun:
        """Reassign affected jobs to other technicians."""
        logger.info("Executing job reassignment")
        
        # Cancel affected assignments
        for assignment in impact.affected_assignments:
            assignment.status = AssignmentStatus.CANCELLED
            assignment.job.status = JobStatus.PENDING
        
        self.db.commit()
        
        jobs_to_reassign = impact.affected_jobs
        
        # Get available technicians (excluding the one with the disruption)
        technicians = self.db.query(Technician).filter(
            Technician.is_active == True
        ).all()
        
        if event.technician_id:
            technicians = [t for t in technicians if str(t.id) != str(event.technician_id)]
        
        # Create scheduling run
        run = SchedulingRun(
            algorithm="reassign_jobs_greedy",
            status="running",
            started_at=datetime.utcnow(),
            config={
                "disruption_event_id": str(event.id),
                "recovery_strategy": RecoveryStrategy.REASSIGN_JOBS.value,
                "jobs_to_reassign": len(jobs_to_reassign),
                "available_technicians": len(technicians)
            }
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        
        # Run greedy insertion
        greedy = GreedyInsertion(self.db)
        result = greedy.run(
            jobs=jobs_to_reassign,
            technicians=technicians,
            scheduling_run_id=run.id
        )
        
        # Update run
        run.status = "completed"
        run.completed_at = datetime.utcnow()
        run.metrics = {
            "jobs_to_reassign": len(jobs_to_reassign),
            "jobs_reassigned": len(result["assignments"]),
            "jobs_still_unassigned": len(result["unassigned_jobs"]),
            "recovery_successful": len(result["unassigned_jobs"]) == 0
        }
        
        self.db.commit()
        logger.info(f"Reassignment complete: {len(result['assignments'])} jobs reassigned")
        
        return run
    
    def _create_no_action_run(
        self,
        event: DisruptionEvent,
        impact: DisruptionImpact,
        reason: str
    ) -> SchedulingRun:
        """Create a no-action scheduling run."""
        run = SchedulingRun(
            algorithm="no_action",
            status="completed",
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            config={
                "disruption_event_id": str(event.id),
                "recovery_strategy": RecoveryStrategy.NO_ACTION.value,
                "reason": reason
            },
            metrics={
                "action_taken": False,
                "impact_score": impact.impact_score
            }
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run
