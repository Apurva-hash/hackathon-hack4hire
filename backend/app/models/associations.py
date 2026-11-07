"""Association tables for many-to-many relationships."""

from sqlalchemy import Table, Column, String, ForeignKey

from app.database import Base


# Technician <-> Skill (many-to-many)
technician_skills = Table(
    'technician_skills',
    Base.metadata,
    Column('technician_id', String(36), ForeignKey('technicians.id'), primary_key=True),
    Column('skill_id', String(36), ForeignKey('skills.id'), primary_key=True)
)


# Technician <-> ServiceZone (many-to-many)
technician_zones = Table(
    'technician_zones',
    Base.metadata,
    Column('technician_id', String(36), ForeignKey('technicians.id'), primary_key=True),
    Column('service_zone_id', String(36), ForeignKey('service_zones.id'), primary_key=True)
)


# Job <-> Skill (many-to-many)
job_skills = Table(
    'job_skills',
    Base.metadata,
    Column('job_id', String(36), ForeignKey('jobs.id'), primary_key=True),
    Column('skill_id', String(36), ForeignKey('skills.id'), primary_key=True)
)
