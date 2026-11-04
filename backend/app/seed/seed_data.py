"""Seed data generator for DispatchGrid.

Generates:
- 20+ technicians with varied skills, zones, and shifts
- 100+ service jobs with varied requirements, priorities, and constraints
- Includes edge cases: impossible jobs, conflicting windows, etc.
"""

import random
from datetime import datetime, time, timedelta
from sqlalchemy.orm import Session

from app.models import (
    Skill, ServiceZone, Technician, Job,
    TechnicianStatus, JobPriority, JobStatus,
    AvailabilityBlock
)
from app.seed.travel_matrix import ZONE_DESCRIPTIONS, get_all_zones


# Seed data constants
SKILLS_DATA = [
    ("Plumbing", "General plumbing repairs and installations"),
    ("Electrical", "Electrical repairs and installations"),
    ("HVAC", "Heating, ventilation, and air conditioning"),
    ("Carpentry", "Wood working and structural repairs"),
    ("Appliance Repair", "Home and commercial appliance repair"),
    ("Painting", "Interior and exterior painting"),
    ("Roofing", "Roof repairs and installations"),
    ("Landscaping", "Outdoor maintenance and landscaping"),
    ("Locksmith", "Lock installation and key services"),
    ("Pest Control", "Pest management and control"),
]

FIRST_NAMES = [
    "John", "Jane", "Michael", "Sarah", "David", "Emily", "Robert", "Lisa",
    "James", "Maria", "William", "Jennifer", "Richard", "Linda", "Thomas", "Patricia",
    "Charles", "Susan", "Daniel", "Jessica", "Matthew", "Karen", "Anthony", "Nancy"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Wilson", "Anderson", "Thomas", "Taylor"
]

JOB_TITLES = [
    "Fix leaking faucet",
    "Repair electrical outlet",
    "Service HVAC system",
    "Install new door",
    "Repair dishwasher",
    "Paint interior walls",
    "Fix roof leak",
    "Lawn maintenance",
    "Replace door lock",
    "Pest inspection",
    "Emergency pipe burst",
    "AC not cooling",
    "Broken garbage disposal",
    "Install ceiling fan",
    "Repair drywall damage",
    "Clean gutters",
    "Replace water heater",
    "Fix circuit breaker",
    "Install new flooring",
    "Window repair",
]

LOCATIONS = [
    "123 Main St", "456 Oak Ave", "789 Pine Rd", "321 Elm Dr", "654 Maple Ln",
    "987 Cedar St", "147 Birch Ct", "258 Spruce Way", "369 Ash Blvd", "741 Willow Pl",
    "852 Cherry St", "963 Walnut Ave", "159 Hickory Dr", "357 Poplar Rd", "486 Sycamore Ln",
]


def clear_existing_data(db: Session):
    """Clear all existing data (for re-seeding)."""
    print("Clearing existing data...")
    
    # Delete in correct order to respect foreign keys
    from app.models import Assignment, SchedulingDecision, SchedulingRun
    
    db.query(Assignment).delete()
    db.query(SchedulingDecision).delete()
    db.query(SchedulingRun).delete()
    db.query(AvailabilityBlock).delete()
    db.query(Job).delete()
    db.query(Technician).delete()
    db.query(Skill).delete()
    db.query(ServiceZone).delete()
    
    db.commit()
    print("Existing data cleared.")


def create_skills(db: Session) -> list[Skill]:
    """Create skills."""
    print("Creating skills...")
    
    skills = []
    for name, description in SKILLS_DATA:
        skill = Skill(name=name, description=description)
        skills.append(skill)
        db.add(skill)
    
    db.commit()
    print(f"Created {len(skills)} skills.")
    return skills


def create_service_zones(db: Session) -> list[ServiceZone]:
    """Create service zones."""
    print("Creating service zones...")
    
    zones = []
    for zone_name in get_all_zones():
        zone = ServiceZone(
            name=zone_name,
            description=ZONE_DESCRIPTIONS.get(zone_name, f"{zone_name} service area")
        )
        zones.append(zone)
        db.add(zone)
    
    db.commit()
    print(f"Created {len(zones)} service zones.")
    return zones


def create_technicians(db: Session, skills: list[Skill], zones: list[ServiceZone]) -> list[Technician]:
    """Create 20+ technicians with varied skills and zones."""
    print("Creating technicians...")
    
    technicians = []
    random.seed(42)  # For reproducibility
    
    for i in range(25):  # Create 25 technicians
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        name = f"{first_name} {last_name}"
        
        # Varied shift times
        shift_patterns = [
            (time(8, 0), time(17, 0)),   # Standard 9-5
            (time(7, 0), time(16, 0)),   # Early shift
            (time(9, 0), time(18, 0)),   # Late shift
            (time(6, 0), time(15, 0)),   # Very early
            (time(10, 0), time(19, 0)),  # Afternoon shift
        ]
        shift_start, shift_end = random.choice(shift_patterns)
        
        # Assign 1-4 skills per technician
        num_skills = random.randint(1, 4)
        tech_skills = random.sample(skills, num_skills)
        
        # Assign 1-3 service zones
        num_zones = random.randint(1, 3)
        tech_zones = random.sample(zones, num_zones)
        
        # Most technicians available, some unavailable
        status = TechnicianStatus.AVAILABLE if random.random() > 0.1 else TechnicianStatus.UNAVAILABLE
        
        # Random starting location
        current_location = random.choice(tech_zones).name if tech_zones else None
        
        technician = Technician(
            name=name,
            shift_start=shift_start,
            shift_end=shift_end,
            status=status,
            current_location=current_location,
        )
        
        technician.skills = tech_skills
        technician.service_zones = tech_zones
        
        technicians.append(technician)
        db.add(technician)
    
    db.commit()
    print(f"Created {len(technicians)} technicians.")
    return technicians


def create_availability_blocks(db: Session, technicians: list[Technician]):
    """Create some unavailable periods for technicians."""
    print("Creating availability blocks...")
    
    base_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = base_date + timedelta(days=1)
    
    blocks = []
    random.seed(42)
    
    # Add unavailable periods for some technicians
    for tech in random.sample(technicians, k=5):  # 5 technicians with unavailable periods
        # Morning meeting
        block = AvailabilityBlock(
            technician_id=tech.id,
            start_time=tomorrow + timedelta(hours=8),
            end_time=tomorrow + timedelta(hours=10),
            reason="Team meeting"
        )
        blocks.append(block)
        db.add(block)
        
    for tech in random.sample(technicians, k=3):  # 3 with afternoon training
        block = AvailabilityBlock(
            technician_id=tech.id,
            start_time=tomorrow + timedelta(hours=14),
            end_time=tomorrow + timedelta(hours=16),
            reason="Training session"
        )
        blocks.append(block)
        db.add(block)
    
    db.commit()
    print(f"Created {len(blocks)} availability blocks.")


def create_jobs(db: Session, skills: list[Skill], zones: list[ServiceZone]) -> list[Job]:
    """Create 100+ jobs with varied requirements and edge cases."""
    print("Creating jobs...")
    
    jobs = []
    random.seed(42)
    
    base_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = base_date + timedelta(days=1)
    
    # Priority distribution
    priority_weights = {
        JobPriority.CRITICAL: 10,
        JobPriority.HIGH: 25,
        JobPriority.MEDIUM: 45,
        JobPriority.LOW: 20,
    }
    
    for i in range(110):  # Create 110 jobs
        # Random job details
        title = random.choice(JOB_TITLES)
        location = f"{random.choice(LOCATIONS)}, {random.choice(zones).name}"
        zone = random.choice(zones)
        
        # Duration: 30 min to 4 hours
        duration_minutes = random.choice([30, 45, 60, 90, 120, 180, 240])
        
        # Priority
        priority = random.choices(
            list(priority_weights.keys()),
            weights=list(priority_weights.values())
        )[0]
        
        # Time windows - varied patterns
        if i < 60:  # Normal time windows
            window_start = tomorrow + timedelta(hours=random.randint(8, 14))
            window_end = window_start + timedelta(hours=random.randint(4, 8))
        elif i < 80:  # Tight time windows (conflicts likely)
            window_start = tomorrow + timedelta(hours=random.randint(9, 11))
            window_end = window_start + timedelta(hours=2)
        elif i < 90:  # Late day jobs
            window_start = tomorrow + timedelta(hours=random.randint(14, 16))
            window_end = window_start + timedelta(hours=3)
        else:  # Very tight windows (difficult to schedule)
            window_start = tomorrow + timedelta(hours=random.randint(8, 15))
            window_end = window_start + timedelta(minutes=90)
        
        # SLA deadline
        if priority == JobPriority.CRITICAL:
            sla_deadline = window_start + timedelta(hours=4)
        elif priority == JobPriority.HIGH:
            sla_deadline = window_end + timedelta(hours=2)
        else:
            sla_deadline = window_end + timedelta(hours=random.randint(4, 12))
        
        # Required skills - varied
        if i < 70:  # Single skill
            required_skills = [random.choice(skills)]
        elif i < 95:  # 2 skills
            required_skills = random.sample(skills, 2)
        else:  # 3 skills (harder to assign)
            required_skills = random.sample(skills, 3)
        
        # Create impossible jobs (edge cases)
        if i >= 105:  # Last 5 jobs are impossible
            # Require a skill that no one or very few have
            rare_skills = random.sample(skills, 3)
            required_skills = rare_skills
            title = f"[EDGE CASE] {title}"
        
        job = Job(
            title=title,
            description=f"Service request: {title}",
            location=location,
            service_zone_id=zone.id,
            duration_minutes=duration_minutes,
            time_window_start=window_start,
            time_window_end=window_end,
            sla_deadline=sla_deadline,
            priority=priority,
            status=JobStatus.PENDING,
        )
        
        job.required_skills = required_skills
        
        jobs.append(job)
        db.add(job)
    
    db.commit()
    print(f"Created {len(jobs)} jobs.")
    return jobs


def generate_seed_data(db: Session):
    """Generate complete seed dataset."""
    print("\n" + "="*60)
    print("DISPATCHGRID SEED DATA GENERATOR")
    print("="*60 + "\n")
    
    # Clear existing data
    clear_existing_data(db)
    
    # Create base data
    skills = create_skills(db)
    zones = create_service_zones(db)
    
    # Create technicians
    technicians = create_technicians(db, skills, zones)
    
    # Create availability blocks
    create_availability_blocks(db, technicians)
    
    # Create jobs
    jobs = create_jobs(db, skills, zones)
    
    # Summary
    print("\n" + "="*60)
    print("SEED DATA GENERATION COMPLETE")
    print("="*60)
    print(f"\nCreated:")
    print(f"  - {len(skills)} skills")
    print(f"  - {len(zones)} service zones")
    print(f"  - {len(technicians)} technicians")
    print(f"  - {len(jobs)} jobs")
    print(f"\nJob breakdown:")
    print(f"  - Critical: {sum(1 for j in jobs if j.priority == JobPriority.CRITICAL)}")
    print(f"  - High: {sum(1 for j in jobs if j.priority == JobPriority.HIGH)}")
    print(f"  - Medium: {sum(1 for j in jobs if j.priority == JobPriority.MEDIUM)}")
    print(f"  - Low: {sum(1 for j in jobs if j.priority == JobPriority.LOW)}")
    print(f"\nTechnician skills distribution:")
    skill_counts = {}
    for tech in technicians:
        for skill in tech.skills:
            skill_counts[skill.name] = skill_counts.get(skill.name, 0) + 1
    for skill_name, count in sorted(skill_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {skill_name}: {count} technicians")
    
    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    from app.database import SessionLocal
    
    db = SessionLocal()
    try:
        generate_seed_data(db)
    finally:
        db.close()
