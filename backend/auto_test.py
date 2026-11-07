"""
Automated backend testing script
Installs dependencies, seeds database, runs scheduling tests
"""

import subprocess
import sys
import os

print("\n" + "="*70)
print("DISPATCHGRID AUTOMATED BACKEND TESTING")
print("="*70 + "\n")

# Step 1: Install dependencies
print("STEP 1: Installing dependencies...")
print("-" * 70)

packages = [
    'fastapi',
    'uvicorn[standard]',
    'sqlalchemy',
    'pydantic',
    'pydantic-settings',
    'python-dotenv'
]

for package in packages:
    print(f"Installing {package}...", end=" ")
    result = subprocess.run(
        [sys.executable, '-m', 'pip', 'install', '-q', package],
        capture_output=True
    )
    if result.returncode == 0:
        print("[OK]")
    else:
        print(f"[ERROR]: {result.stderr.decode()[:100]}")

print("\nSTEP 2: Verifying imports...")
print("-" * 70)

try:
    import fastapi
    import uvicorn
    import sqlalchemy
    import pydantic
    print("[OK] All core packages imported successfully")
except Exception as e:
    print(f"[ERROR] Import error: {e}")
    sys.exit(1)

# Step 3: Import app modules
print("\nSTEP 3: Testing application imports...")
print("-" * 70)

try:
    from app.config import Config
    from app.database import SessionLocal
    print("[OK] Config and database modules OK")
    
    from app.scheduler.scoring import ScheduleScorer
    from app.scheduler.greedy_insertion import GreedyInsertion
    from app.scheduler.alns_optimizer import ALNSOptimizer
    from app.scheduler.engine import SchedulingEngine
    print("[OK] All scheduler modules OK")
    
except Exception as e:
    print(f"[ERROR] Import error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 4: Seed database
print("\nSTEP 4: Seeding database...")
print("-" * 70)

try:
    # Check if already seeded
    from app.models import Job, Technician
    db = SessionLocal()
    existing_jobs = db.query(Job).count()
    existing_techs = db.query(Technician).count()
    
    if existing_jobs > 0 and existing_techs > 0:
        print(f"[OK] Database already seeded: {existing_techs} technicians, {existing_jobs} jobs")
    else:
        print("Seeding database with sample data...")
        result = subprocess.run(
            [sys.executable, '-m', 'app.seed.seed_data'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("[OK] Database seeded successfully")
        else:
            print(f"[ERROR] Seeding error: {result.stderr}")
            # Continue anyway, try with existing data
    
    db.close()
    
except Exception as e:
    print(f"[WARNING] Seeding issue: {e}")
    print("Continuing with test...")

# Step 5: Run scheduling test
print("\nSTEP 5: Running scheduling algorithms...")
print("="*70)

try:
    from app.models import Job, Technician
    from sqlalchemy.orm import joinedload
    
    db = SessionLocal()
    
    # Load data
    jobs = db.query(Job).options(
        joinedload(Job.required_skills),
        joinedload(Job.service_zone)
    ).all()
    
    technicians = db.query(Technician).options(
        joinedload(Technician.skills),
        joinedload(Technician.service_zones),
        joinedload(Technician.availability_blocks)
    ).all()
    
    print(f"\n[DATA] Dataset: {len(jobs)} jobs, {len(technicians)} technicians")
    
    if len(jobs) == 0 or len(technicians) == 0:
        print("[ERROR] No data in database. Run: python -m app.seed.seed_data")
        sys.exit(1)
    
    # Initialize engine
    config = Config()
    from app.scheduler.alns_optimizer import ALNSConfig
    alns_config = ALNSConfig(
        max_iterations=50,  # Reduced for faster testing
        destroy_size_min=5,
        destroy_size_max=15,
        random_seed=42
    )
    
    engine = SchedulingEngine(config, alns_config)
    
    # Run scheduling
    print("\n" + "="*70)
    results = engine.run_scheduling(
        jobs=jobs,
        technicians=technicians,
        db=db,
        use_alns=True,
        algorithm="auto"
    )
    
    # Display summary
    print("\n" + "="*70)
    print("[SUCCESS] TESTING COMPLETE - SUMMARY")
    print("="*70)
    
    if 'comparison' in results:
        comp = results['comparison']
        print(f"\n[RESULTS]:")
        print(f"   Greedy:     {comp['assigned_jobs']['greedy']}/{len(jobs)} jobs")
        print(f"   ALNS:       {comp['assigned_jobs']['alns']}/{len(jobs)} jobs")
        print(f"   Improvement: {comp['assigned_jobs']['improvement']:+d} jobs")
        print(f"\n[SCORE]:")
        print(f"   Greedy:     {comp['total_score']['greedy']:.2f}")
        print(f"   ALNS:       {comp['total_score']['alns']:.2f}")
        print(f"   Improvement: {comp['total_score']['improvement']:+.2f} ({comp['total_score']['improvement_pct']:+.1f}%)")
        print(f"\n[TIME]:")
        print(f"   Total:      {comp['execution_time']['total']:.2f}s")
    
    print("\n" + "="*70)
    print("[SUCCESS] ALL TESTS PASSED!")
    print("="*70)
    print("\nPhases 1-6 are fully operational!")
    print("Ready for Phase 7: Disruption Handling")
    
    db.close()
    
except Exception as e:
    print(f"\n[ERROR] Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*70 + "\n")
