"""Tests for database models."""

import pytest
from datetime import datetime, timedelta, time

from app.models import (
    Job, Technician, Skill, ServiceZone, Assignment,
    JobPriority, JobStatus, TechnicianStatus, AssignmentStatus
)


class TestJobModel:
    """Test Job model."""
    
    def test_create_job(self, db):
        """Test creating a job."""
        zone = ServiceZone(name="Test Zone")
        db.add(zone)
        db.commit()
        
        job = Job(
            title="Test Job",
            location="123 Main St",
            service_zone_id=zone.id,
            duration_minutes=60,
            time_window_start=datetime.utcnow(),
            time_window_end=datetime.utcnow() + timedelta(hours=8),
            sla_deadline=datetime.utcnow() + timedelta(hours=24),
            priority=JobPriority.HIGH,
            status=JobStatus.PENDING
        )
        
        db.add(job)
        db.commit()
        
        assert job.id is not None
        assert job.title == "Test Job"
        assert job.status == JobStatus.PENDING
    
    def test_job_with_skills(self, db):
        """Test job with required skills."""
        zone = ServiceZone(name="Zone A")
        skill1 = Skill(name="Plumbing")
        skill2 = Skill(name="Electrical")
        
        db.add_all([zone, skill1, skill2])
        db.commit()
        
        job = Job(
            title="Complex Job",
            location="456 Oak St",
            service_zone_id=zone.id,
            duration_minutes=120,
            time_window_start=datetime.utcnow(),
            time_window_end=datetime.utcnow() + timedelta(hours=8),
            sla_deadline=datetime.utcnow() + timedelta(hours=24),
            priority=JobPriority.CRITICAL
        )
        
        job.required_skills = [skill1, skill2]
        db.add(job)
        db.commit()
        
        assert len(job.required_skills) == 2
        assert skill1 in job.required_skills
        assert skill2 in job.required_skills


class TestTechnicianModel:
    """Test Technician model."""
    
    def test_create_technician(self, db):
        """Test creating a technician."""
        tech = Technician(
            name="John Doe",
            shift_start=time(8, 0),
            shift_end=time(17, 0),
            status=TechnicianStatus.AVAILABLE
        )
        
        db.add(tech)
        db.commit()
        
        assert tech.id is not None
        assert tech.name == "John Doe"
        assert tech.status == TechnicianStatus.AVAILABLE
    
    def test_technician_with_skills_and_zones(self, db):
        """Test technician with skills and service zones."""
        skill1 = Skill(name="HVAC")
        skill2 = Skill(name="Plumbing")
        zone1 = ServiceZone(name="North")
        zone2 = ServiceZone(name="South")
        
        db.add_all([skill1, skill2, zone1, zone2])
        db.commit()
        
        tech = Technician(
            name="Jane Smith",
            shift_start=time(8, 0),
            shift_end=time(17, 0)
        )
        
        tech.skills = [skill1, skill2]
        tech.service_zones = [zone1, zone2]
        
        db.add(tech)
        db.commit()
        
        assert len(tech.skills) == 2
        assert len(tech.service_zones) == 2
        assert skill1 in tech.skills
        assert zone1 in tech.service_zones


class TestAssignmentModel:
    """Test Assignment model."""
    
    def test_create_assignment(self, db):
        """Test creating an assignment."""
        # Setup
        zone = ServiceZone(name="Zone X")
        tech = Technician(
            name="Tech A",
            shift_start=time(8, 0),
            shift_end=time(17, 0)
        )
        job = Job(
            title="Job A",
            location="789 Pine St",
            service_zone_id=zone.id,
            duration_minutes=90,
            time_window_start=datetime.utcnow(),
            time_window_end=datetime.utcnow() + timedelta(hours=8),
            sla_deadline=datetime.utcnow() + timedelta(hours=24),
            priority=JobPriority.MEDIUM
        )
        
        from app.models import SchedulingRun, TriggerType, RunStatus
        run = SchedulingRun(
            trigger_type=TriggerType.INITIAL,
            status=RunStatus.RUNNING
        )
        
        db.add_all([zone, tech, job, run])
        db.commit()
        
        # Create assignment
        start_time = datetime.utcnow() + timedelta(hours=1)
        end_time = start_time + timedelta(minutes=job.duration_minutes)
        
        assignment = Assignment(
            job_id=job.id,
            technician_id=tech.id,
            scheduled_start=start_time,
            scheduled_end=end_time,
            travel_before_minutes=15,
            status=AssignmentStatus.PENDING,
            run_id=run.id
        )
        
        db.add(assignment)
        db.commit()
        
        assert assignment.id is not None
        assert assignment.job_id == job.id
        assert assignment.technician_id == tech.id
        assert assignment.travel_before_minutes == 15
