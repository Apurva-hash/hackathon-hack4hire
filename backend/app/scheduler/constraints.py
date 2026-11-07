"""
Hard constraint validation for scheduling engine.

All constraints defined here are NEVER-VIOLATE rules.
A candidate assignment must pass ALL constraints to be feasible.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Set
from sqlalchemy.orm import Session

from app.models import Job, Technician, Assignment, AvailabilityBlock, Skill
from app.models.scheduling_decision import RejectionReason
from app.utils.time_utils import intervals_overlap, time_fits_within_shift
from app.utils.travel import estimate_travel_time


class ConstraintViolation:
    """Represents a constraint violation with reason."""
    
    def __init__(self, reason: RejectionReason, message: str):
        self.reason = reason
        self.message = message
    
    def __repr__(self):
        return f"<ConstraintViolation({self.reason}: {self.message})>"


class ConstraintValidator:
    """Validates scheduling constraints."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def validate_all_constraints(
        self,
        job: Job,
        technician: Technician,
        proposed_start: datetime,
        existing_assignments: List[Assignment],
        protected_job_ids: Set[str]
    ) -> List[ConstraintViolation]:
        """
        Validate all hard constraints for a proposed assignment.
        
        Args:
            job: Job to assign
            technician: Technician to assign to
            proposed_start: Proposed job start time
            existing_assignments: Current assignments for this technician
            protected_job_ids: IDs of jobs that cannot be modified (completed/in-progress)
        
        Returns:
            List of constraint violations (empty if all constraints pass)
        """
        violations = []
        
        # HC1: Skill Match
        violation = self.validate_skill_match(job, technician)
        if violation:
            violations.append(violation)
        
        # HC2: Zone Eligibility
        violation = self.validate_zone_eligibility(job, technician)
        if violation:
            violations.append(violation)
        
        # HC3: Availability
        violation = self.validate_availability(technician, proposed_start, job.duration_minutes)
        if violation:
            violations.append(violation)
        
        # HC4: Shift Boundary
        violation = self.validate_shift_boundary(technician, proposed_start, job.duration_minutes)
        if violation:
            violations.append(violation)
        
        # HC5: Job Time Window
        violation = self.validate_time_window(job, proposed_start)
        if violation:
            violations.append(violation)
        
        # HC6: No Overlap
        violation = self.validate_no_overlap(
            proposed_start,
            job.duration_minutes,
            existing_assignments,
            protected_job_ids
        )
        if violation:
            violations.append(violation)
        
        # HC7: Travel Feasibility
        violation = self.validate_travel_feasibility(
            job,
            technician,
            proposed_start,
            existing_assignments
        )
        if violation:
            violations.append(violation)
        
        # HC8: SLA Deadline (if configured as hard constraint)
        violation = self.validate_sla_deadline(job, proposed_start)
        if violation:
            violations.append(violation)
        
        return violations
    
    def validate_skill_match(
        self,
        job: Job,
        technician: Technician
    ) -> Optional[ConstraintViolation]:
        """
        HC1: Technician must possess ALL required skills.
        
        Args:
            job: Job with required skills
            technician: Technician with skills
        
        Returns:
            Violation if skill mismatch, None if valid
        """
        required_skills = set(skill.id for skill in job.required_skills)
        technician_skills = set(skill.id for skill in technician.skills)
        
        missing_skills = required_skills - technician_skills
        
        if missing_skills:
            missing_skill_names = [
                skill.name for skill in job.required_skills
                if skill.id in missing_skills
            ]
            return ConstraintViolation(
                RejectionReason.MISSING_SKILL,
                f"Technician lacks required skills: {', '.join(missing_skill_names)}"
            )
        
        return None
    
    def validate_zone_eligibility(
        self,
        job: Job,
        technician: Technician
    ) -> Optional[ConstraintViolation]:
        """
        HC2: Technician must be eligible for job's service zone.
        
        Args:
            job: Job with service zone
            technician: Technician with eligible zones
        
        Returns:
            Violation if zone mismatch, None if valid
        """
        technician_zone_ids = set(zone.id for zone in technician.service_zones)
        
        if job.service_zone_id not in technician_zone_ids:
            return ConstraintViolation(
                RejectionReason.NO_ZONE_ELIGIBILITY,
                f"Technician not authorized for zone: {job.service_zone.name}"
            )
        
        return None
    
    def validate_availability(
        self,
        technician: Technician,
        proposed_start: datetime,
        duration_minutes: int
    ) -> Optional[ConstraintViolation]:
        """
        HC3: Technician must be available (no unavailable blocks).
        
        Args:
            technician: Technician to check
            proposed_start: Proposed job start
            duration_minutes: Job duration
        
        Returns:
            Violation if unavailable, None if valid
        """
        proposed_end = proposed_start + timedelta(minutes=duration_minutes)
        
        # Check availability blocks
        for block in technician.availability_blocks:
            if intervals_overlap(
                proposed_start, proposed_end,
                block.start_time, block.end_time
            ):
                return ConstraintViolation(
                    RejectionReason.RESOURCE_UNAVAILABLE,
                    f"Technician unavailable: {block.reason or 'scheduled time off'} "
                    f"({block.start_time.strftime('%H:%M')} - {block.end_time.strftime('%H:%M')})"
                )
        
        return None
    
    def validate_shift_boundary(
        self,
        technician: Technician,
        proposed_start: datetime,
        duration_minutes: int
    ) -> Optional[ConstraintViolation]:
        """
        HC4: Job must fit within technician's shift.
        
        Args:
            technician: Technician with shift
            proposed_start: Proposed job start
            duration_minutes: Job duration
        
        Returns:
            Violation if outside shift, None if valid
        """
        if not time_fits_within_shift(
            proposed_start,
            duration_minutes,
            technician.shift_start,
            technician.shift_end
        ):
            proposed_end = proposed_start + timedelta(minutes=duration_minutes)
            return ConstraintViolation(
                RejectionReason.SHIFT_CONFLICT,
                f"Job ({proposed_start.strftime('%H:%M')} - {proposed_end.strftime('%H:%M')}) "
                f"does not fit within shift "
                f"({technician.shift_start.strftime('%H:%M')} - {technician.shift_end.strftime('%H:%M')})"
            )
        
        return None
    
    def validate_time_window(
        self,
        job: Job,
        proposed_start: datetime
    ) -> Optional[ConstraintViolation]:
        """
        HC5: Job must start within allowed time window.
        
        Args:
            job: Job with time window
            proposed_start: Proposed start time
        
        Returns:
            Violation if outside window, None if valid
        """
        if proposed_start < job.time_window_start:
            return ConstraintViolation(
                RejectionReason.TIME_WINDOW_CONFLICT,
                f"Job cannot start before window opens "
                f"(window: {job.time_window_start.strftime('%Y-%m-%d %H:%M')} - "
                f"{job.time_window_end.strftime('%H:%M')})"
            )
        
        if proposed_start > job.time_window_end:
            return ConstraintViolation(
                RejectionReason.TIME_WINDOW_CONFLICT,
                f"Job cannot start after window closes "
                f"(window: {job.time_window_start.strftime('%Y-%m-%d %H:%M')} - "
                f"{job.time_window_end.strftime('%H:%M')})"
            )
        
        return None
    
    def validate_no_overlap(
        self,
        proposed_start: datetime,
        duration_minutes: int,
        existing_assignments: List[Assignment],
        protected_job_ids: Set[str]
    ) -> Optional[ConstraintViolation]:
        """
        HC6: No overlapping assignments for same technician.
        
        Args:
            proposed_start: Proposed job start
            duration_minutes: Job duration
            existing_assignments: Current technician assignments
            protected_job_ids: Jobs that cannot be moved
        
        Returns:
            Violation if overlap, None if valid
        """
        proposed_end = proposed_start + timedelta(minutes=duration_minutes)
        
        for assignment in existing_assignments:
            # Check if this assignment overlaps
            if intervals_overlap(
                proposed_start, proposed_end,
                assignment.scheduled_start, assignment.scheduled_end
            ):
                # If it's a protected job, this is a violation
                if assignment.job_id in protected_job_ids:
                    return ConstraintViolation(
                        RejectionReason.NO_AVAILABLE_SLOT,
                        f"Overlaps with protected job {assignment.job.title} "
                        f"({assignment.scheduled_start.strftime('%H:%M')} - "
                        f"{assignment.scheduled_end.strftime('%H:%M')})"
                    )
                # If not protected, the scheduling engine can potentially move it
                # But we still report it as a violation for this specific slot
                else:
                    return ConstraintViolation(
                        RejectionReason.NO_AVAILABLE_SLOT,
                        f"Overlaps with existing job {assignment.job.title} "
                        f"({assignment.scheduled_start.strftime('%H:%M')} - "
                        f"{assignment.scheduled_end.strftime('%H:%M')})"
                    )
        
        return None
    
    def validate_travel_feasibility(
        self,
        job: Job,
        technician: Technician,
        proposed_start: datetime,
        existing_assignments: List[Assignment]
    ) -> Optional[ConstraintViolation]:
        """
        HC7: Sufficient time for travel between consecutive jobs.
        
        Args:
            job: Job to assign
            technician: Technician
            proposed_start: Proposed start time
            existing_assignments: Existing assignments
        
        Returns:
            Violation if insufficient travel time, None if valid
        """
        proposed_end = proposed_start + timedelta(minutes=job.duration_minutes)
        
        # Find previous job (latest job ending before proposed start)
        previous_assignment = None
        for assignment in existing_assignments:
            if assignment.scheduled_end <= proposed_start:
                if previous_assignment is None or assignment.scheduled_end > previous_assignment.scheduled_end:
                    previous_assignment = assignment
        
        # Check travel time from previous job
        if previous_assignment:
            travel_time_needed = estimate_travel_time(
                previous_assignment.job.location,
                job.location,
                from_zone=previous_assignment.job.service_zone.name,
                to_zone=job.service_zone.name
            )
            
            available_time = (proposed_start - previous_assignment.scheduled_end).total_seconds() / 60
            
            if available_time < travel_time_needed:
                return ConstraintViolation(
                    RejectionReason.TRAVEL_CONFLICT,
                    f"Insufficient travel time from previous job "
                    f"(need {travel_time_needed} min, have {int(available_time)} min)"
                )
        
        # Find next job (earliest job starting after proposed end)
        next_assignment = None
        for assignment in existing_assignments:
            if assignment.scheduled_start >= proposed_end:
                if next_assignment is None or assignment.scheduled_start < next_assignment.scheduled_start:
                    next_assignment = assignment
        
        # Check travel time to next job
        if next_assignment:
            travel_time_needed = estimate_travel_time(
                job.location,
                next_assignment.job.location,
                from_zone=job.service_zone.name,
                to_zone=next_assignment.job.service_zone.name
            )
            
            available_time = (next_assignment.scheduled_start - proposed_end).total_seconds() / 60
            
            if available_time < travel_time_needed:
                return ConstraintViolation(
                    RejectionReason.TRAVEL_CONFLICT,
                    f"Insufficient travel time to next job "
                    f"(need {travel_time_needed} min, have {int(available_time)} min)"
                )
        
        return None
    
    def validate_sla_deadline(
        self,
        job: Job,
        proposed_start: datetime
    ) -> Optional[ConstraintViolation]:
        """
        HC8: Job must complete before SLA deadline (if configured as hard constraint).
        
        Note: By default, SLA is a soft constraint (penalty in scoring).
        Set config.sla_is_hard_constraint = True to make it hard.
        
        Args:
            job: Job with SLA deadline
            proposed_start: Proposed start time
        
        Returns:
            Violation if past deadline, None if valid
        """
        from app.config import settings
        
        # Only validate as hard constraint if configured
        if not settings.sla_is_hard_constraint:
            return None
        
        proposed_completion = proposed_start + timedelta(minutes=job.duration_minutes)
        
        if proposed_completion > job.sla_deadline:
            return ConstraintViolation(
                RejectionReason.SLA_CONFLICT,
                f"Job would complete after SLA deadline "
                f"(deadline: {job.sla_deadline.strftime('%Y-%m-%d %H:%M')}, "
                f"completion: {proposed_completion.strftime('%Y-%m-%d %H:%M')})"
            )
        
        return None
    
    def is_job_impossible(
        self,
        job: Job,
        all_technicians: List[Technician]
    ) -> tuple[bool, Optional[RejectionReason], str]:
        """
        Determine if a job is impossible with available resources.
        
        A job is "impossible" if NO technician can ever satisfy basic eligibility:
        - No technician has required skills
        - No technician is eligible for the zone
        
        Args:
            job: Job to check
            all_technicians: All available technicians
        
        Returns:
            Tuple of (is_impossible, reason, explanation)
        """
        eligible_technicians = []
        
        required_skill_ids = set(skill.id for skill in job.required_skills)
        
        for tech in all_technicians:
            tech_skill_ids = set(skill.id for skill in tech.skills)
            tech_zone_ids = set(zone.id for zone in tech.service_zones)
            
            # Check skills
            if not required_skill_ids.issubset(tech_skill_ids):
                continue
            
            # Check zone
            if job.service_zone_id not in tech_zone_ids:
                continue
            
            # This technician is eligible
            eligible_technicians.append(tech)
        
        if not eligible_technicians:
            # Determine specific reason
            # First check skills
            any_tech_has_skills = False
            for tech in all_technicians:
                tech_skill_ids = set(skill.id for skill in tech.skills)
                if required_skill_ids.issubset(tech_skill_ids):
                    any_tech_has_skills = True
                    break
            
            if not any_tech_has_skills:
                skill_names = [skill.name for skill in job.required_skills]
                return (
                    True,
                    RejectionReason.MISSING_SKILL,
                    f"No technician has all required skills: {', '.join(skill_names)}"
                )
            
            # Skills exist but no one is in the zone
            return (
                True,
                RejectionReason.NO_ZONE_ELIGIBILITY,
                f"No technician with required skills is authorized for zone: {job.service_zone.name}"
            )
        
        # Job is not impossible (at least one eligible technician exists)
        return (False, None, "")


def classify_feasibility(
    job: Job,
    technician: Technician,
    violations: List[ConstraintViolation]
) -> str:
    """
    Classify job feasibility based on violations.
    
    Returns:
        "feasible", "currently_infeasible", or "impossible"
    """
    if not violations:
        return "feasible"
    
    # Check if violations are "permanent" (impossible) or "temporary" (currently infeasible)
    permanent_reasons = {
        RejectionReason.MISSING_SKILL,
        RejectionReason.NO_ZONE_ELIGIBILITY,
    }
    
    for violation in violations:
        if violation.reason in permanent_reasons:
            return "impossible"  # This technician can never do this job
    
    # All violations are temporary (time-based)
    return "currently_infeasible"
