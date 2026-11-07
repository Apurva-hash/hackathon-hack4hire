"""
Objective function and scoring for scheduling optimization.

Calculates the cost/score for assignments and complete schedules.
Lower scores are better.
"""

from datetime import datetime, timedelta
from typing import List, Dict
from app.models import Job, Technician, Assignment, JobPriority
from app.utils.travel import estimate_travel_time
from app.config import settings


class ScheduleScorer:
    """Calculates objective scores for scheduling decisions."""
    
    def __init__(self):
        """Initialize scorer with weights from configuration."""
        self.weight_sla = settings.weight_sla_penalty
        self.weight_travel = settings.weight_travel_time
        self.weight_unassigned_priority = settings.weight_unassigned_priority
        self.weight_overtime = settings.weight_overtime
        self.weight_churn = settings.weight_churn
        self.weight_workload_imbalance = settings.weight_workload_imbalance
    
    def calculate_insertion_cost(
        self,
        job: Job,
        technician: Technician,
        proposed_start: datetime,
        existing_assignments: List[Assignment]
    ) -> float:
        """
        Calculate the cost of inserting a job at a specific position.
        
        Args:
            job: Job to insert
            technician: Technician to assign to
            proposed_start: Proposed start time
            existing_assignments: Current assignments for technician
        
        Returns:
            Total insertion cost (lower is better)
        """
        cost = 0.0
        proposed_end = proposed_start + timedelta(minutes=job.duration_minutes)
        
        # SLA Penalty
        if proposed_end > job.sla_deadline:
            lateness_minutes = (proposed_end - job.sla_deadline).total_seconds() / 60
            cost += self.weight_sla * lateness_minutes
        
        # Travel Time Cost
        travel_cost = self._calculate_travel_cost(
            job,
            proposed_start,
            proposed_end,
            existing_assignments
        )
        cost += self.weight_travel * travel_cost
        
        # Overtime Cost
        shift_end = datetime.combine(proposed_start.date(), technician.shift_end)
        if proposed_end > shift_end:
            overtime_minutes = (proposed_end - shift_end).total_seconds() / 60
            cost += self.weight_overtime * overtime_minutes
        
        return cost
    
    def _calculate_travel_cost(
        self,
        job: Job,
        proposed_start: datetime,
        proposed_end: datetime,
        existing_assignments: List[Assignment]
    ) -> float:
        """Calculate additional travel time caused by insertion."""
        total_travel = 0.0
        
        # Find previous job
        previous_assignment = None
        for assignment in existing_assignments:
            if assignment.scheduled_end <= proposed_start:
                if previous_assignment is None or assignment.scheduled_end > previous_assignment.scheduled_end:
                    previous_assignment = assignment
        
        # Travel from previous job
        if previous_assignment:
            travel_time = estimate_travel_time(
                previous_assignment.job.location,
                job.location,
                from_zone=previous_assignment.job.service_zone.name,
                to_zone=job.service_zone.name
            )
            total_travel += travel_time
        
        # Find next job
        next_assignment = None
        for assignment in existing_assignments:
            if assignment.scheduled_start >= proposed_end:
                if next_assignment is None or assignment.scheduled_start < next_assignment.scheduled_start:
                    next_assignment = assignment
        
        # Travel to next job
        if next_assignment:
            travel_time = estimate_travel_time(
                job.location,
                next_assignment.job.location,
                from_zone=job.service_zone.name,
                to_zone=next_assignment.job.service_zone.name
            )
            total_travel += travel_time
            
            # If we had a previous-to-next connection, subtract it (we're inserting in between)
            if previous_assignment:
                old_travel = estimate_travel_time(
                    previous_assignment.job.location,
                    next_assignment.job.location,
                    from_zone=previous_assignment.job.service_zone.name,
                    to_zone=next_assignment.job.service_zone.name
                )
                total_travel -= old_travel
        
        return total_travel
    
    def calculate_schedule_metrics(
        self,
        assignments: List[Assignment],
        all_jobs: List[Job],
        all_technicians: List[Technician]
    ) -> Dict[str, float]:
        """
        Calculate comprehensive metrics for a complete schedule.
        
        Args:
            assignments: List of all assignments
            all_jobs: List of all jobs (to find unassigned)
            all_technicians: List of all technicians (for metrics)
        
        Returns:
            Dictionary of metric names and values
        """
        # Find unassigned jobs
        assigned_job_ids = {a.job_id for a in assignments}
        unassigned_jobs = [j for j in all_jobs if j.id not in assigned_job_ids]
        
        metrics = {
            'total_travel_minutes': 0.0,
            'total_travel_time': 0.0,  # Alias
            'total_idle_time': 0.0,
            'sla_violations': 0,
            'late_minutes': 0.0,
            'unassigned_high_priority': 0,
            'overtime_minutes': 0.0,
            'total_cost': 0.0,
            'total_score': 0.0,  # Will calculate as negative cost
            'assigned_jobs': len(assignments),
            'unassigned_jobs': len(unassigned_jobs),
            'job_coverage': (len(assignments) / len(all_jobs) * 100) if all_jobs else 0,
            'priority_fulfillment_rate': 0.0,
            'technician_utilization': 0.0,
        }
        
        # Group assignments by technician
        tech_assignments: Dict[str, List[Assignment]] = {}
        for assignment in assignments:
            if assignment.technician_id not in tech_assignments:
                tech_assignments[assignment.technician_id] = []
            tech_assignments[assignment.technician_id].append(assignment)
        
        # Calculate metrics per technician
        for tech_id, tech_jobs in tech_assignments.items():
            # Sort by start time
            tech_jobs.sort(key=lambda a: a.scheduled_start)
            
            # Calculate travel time
            for i in range(len(tech_jobs) - 1):
                current = tech_jobs[i]
                next_job = tech_jobs[i + 1]
                
                travel_time = estimate_travel_time(
                    current.job.location,
                    next_job.job.location,
                    from_zone=current.job.service_zone.name,
                    to_zone=next_job.job.service_zone.name
                )
                metrics['total_travel_minutes'] += travel_time
            
            # Check SLA violations and overtime
            technician = tech_jobs[0].technician
            for assignment in tech_jobs:
                job = assignment.job
                
                # SLA check
                if assignment.scheduled_end > job.sla_deadline:
                    metrics['sla_violations'] += 1
                    late_mins = (assignment.scheduled_end - job.sla_deadline).total_seconds() / 60
                    metrics['late_minutes'] += late_mins
                
                # Overtime check
                shift_end = datetime.combine(assignment.scheduled_start.date(), technician.shift_end)
                if assignment.scheduled_end > shift_end:
                    overtime = (assignment.scheduled_end - shift_end).total_seconds() / 60
                    metrics['overtime_minutes'] += overtime
        
        # Count unassigned high-priority jobs
        priority_count = 0
        priority_assigned = 0
        for job in all_jobs:
            if job.priority in [JobPriority.CRITICAL, JobPriority.HIGH]:
                priority_count += 1
                if job.id in assigned_job_ids:
                    priority_assigned += 1
            if job.priority in [JobPriority.CRITICAL, JobPriority.HIGH] and job.id not in assigned_job_ids:
                metrics['unassigned_high_priority'] += 1
        
        metrics['priority_fulfillment_rate'] = (priority_assigned / priority_count * 100) if priority_count > 0 else 100.0
        
        # Calculate total weighted cost
        metrics['total_cost'] = (
            self.weight_sla * metrics['late_minutes'] +
            self.weight_travel * metrics['total_travel_minutes'] +
            self.weight_unassigned_priority * metrics['unassigned_high_priority'] +
            self.weight_overtime * metrics['overtime_minutes']
        )
        
        # Score is negative cost (higher is better)
        metrics['total_score'] = 10000 - metrics['total_cost']  # Base score minus penalties
        metrics['total_travel_time'] = metrics['total_travel_minutes']
        
        return metrics
    
    def calculate_regret(
        self,
        job: Job,
        best_cost: float,
        second_best_cost: float
    ) -> float:
        """
        Calculate regret value for regret-based insertion.
        
        Regret = difference between best and second-best insertion cost.
        High regret = job is difficult to place, should be prioritized.
        
        Args:
            job: Job being considered
            best_cost: Cost of best insertion position
            second_best_cost: Cost of second-best position
        
        Returns:
            Regret value
        """
        if second_best_cost == float('inf'):
            return float('inf')  # Only one feasible position
        
        return second_best_cost - best_cost
