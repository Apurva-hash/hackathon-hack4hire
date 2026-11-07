"""Tests for seed data generation."""

import pytest
from app.models import Job, Technician, Skill, ServiceZone, JobPriority


def test_seed_data_generation(db):
    """Test that seed data generates correctly."""
    from app.seed.seed_data import generate_seed_data
    
    # Generate seed data
    generate_seed_data(db)
    
    # Check technicians
    technicians = db.query(Technician).all()
    assert len(technicians) >= 20, "Should have at least 20 technicians"
    
    # Check jobs
    jobs = db.query(Job).all()
    assert len(jobs) >= 100, "Should have at least 100 jobs"
    
    # Check skills
    skills = db.query(Skill).all()
    assert len(skills) >= 5, "Should have at least 5 skills"
    
    # Check service zones
    zones = db.query(ServiceZone).all()
    assert len(zones) >= 3, "Should have at least 3 service zones"


def test_technicians_have_skills(db):
    """Test that technicians have skills assigned."""
    from app.seed.seed_data import generate_seed_data
    
    generate_seed_data(db)
    
    technicians = db.query(Technician).all()
    
    # At least some technicians should have skills
    techs_with_skills = [t for t in technicians if len(t.skills) > 0]
    assert len(techs_with_skills) > 0, "Technicians should have skills"
    
    # Check that skills are valid
    for tech in techs_with_skills:
        assert len(tech.skills) <= 4, "Technician should have at most 4 skills"
        for skill in tech.skills:
            assert skill.name is not None


def test_technicians_have_zones(db):
    """Test that technicians have service zones assigned."""
    from app.seed.seed_data import generate_seed_data
    
    generate_seed_data(db)
    
    technicians = db.query(Technician).all()
    
    # At least some technicians should have zones
    techs_with_zones = [t for t in technicians if len(t.service_zones) > 0]
    assert len(techs_with_zones) > 0, "Technicians should have service zones"


def test_jobs_have_valid_data(db):
    """Test that jobs have valid required data."""
    from app.seed.seed_data import generate_seed_data
    
    generate_seed_data(db)
    
    jobs = db.query(Job).all()
    
    for job in jobs:
        # Basic fields
        assert job.title is not None
        assert job.location is not None
        assert job.duration_minutes > 0
        
        # Time validation
        assert job.time_window_end > job.time_window_start
        assert job.sla_deadline >= job.time_window_start
        
        # Has service zone
        assert job.service_zone_id is not None
        assert job.service_zone is not None


def test_jobs_priority_distribution(db):
    """Test that jobs have varied priorities."""
    from app.seed.seed_data import generate_seed_data
    
    generate_seed_data(db)
    
    jobs = db.query(Job).all()
    
    # Check we have multiple priorities
    priorities = set(job.priority for job in jobs)
    assert len(priorities) >= 3, "Should have at least 3 different priority levels"
    
    # Check distribution makes sense
    critical_count = sum(1 for j in jobs if j.priority == JobPriority.CRITICAL)
    high_count = sum(1 for j in jobs if j.priority == JobPriority.HIGH)
    medium_count = sum(1 for j in jobs if j.priority == JobPriority.MEDIUM)
    low_count = sum(1 for j in jobs if j.priority == JobPriority.LOW)
    
    # Medium should be most common
    assert medium_count > critical_count
    assert medium_count > low_count
