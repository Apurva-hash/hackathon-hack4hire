"""
Test script for Phase 5 & 6 scheduling algorithms.
Tests Greedy Insertion and ALNS optimization with seed data.
"""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from sqlalchemy.orm import Session, joinedload
from app.database import SessionLocal
from app.models import Job, Technician
from app.scheduler.engine import SchedulingEngine, ALNSConfig
from app.config import Config


def test_greedy_only():
    """Test Greedy Insertion algorithm only."""
    print("\n" + "="*80)
    print("TEST 1: GREEDY INSERTION ONLY")
    print("="*80)
    
    db = SessionLocal()
    try:
        # Load jobs and technicians
        jobs = db.query(Job).options(
            joinedload(Job.required_skills),
            joinedload(Job.service_zone)
        ).all()
        
        technicians = db.query(Technician).options(
            joinedload(Technician.skills),
            joinedload(Technician.service_zones),
            joinedload(Technician.availability_blocks)
        ).all()
        
        print(f"\nLoaded {len(jobs)} jobs and {len(technicians)} technicians from database")
        
        # Initialize engine
        config = Config()
        engine = SchedulingEngine(config)
        
        # Run greedy only
        results = engine.run_scheduling(
            jobs=jobs,
            technicians=technicians,
            db=db,
            use_alns=False,
            algorithm="greedy"
        )
        
        print("\n✅ Greedy test completed successfully")
        return results
        
    finally:
        db.close()


def test_alns_only():
    """Test ALNS algorithm (with greedy as initial solution)."""
    print("\n" + "="*80)
    print("TEST 2: ALNS OPTIMIZATION (from Greedy initial)")
    print("="*80)
    
    db = SessionLocal()
    try:
        # Load jobs and technicians
        jobs = db.query(Job).options(
            joinedload(Job.required_skills),
            joinedload(Job.service_zone)
        ).all()
        
        technicians = db.query(Technician).options(
            joinedload(Technician.skills),
            joinedload(Technician.service_zones),
            joinedload(Technician.availability_blocks)
        ).all()
        
        print(f"\nLoaded {len(jobs)} jobs and {len(technicians)} technicians from database")
        
        # Initialize engine with ALNS config
        config = Config()
        alns_config = ALNSConfig(
            max_iterations=50,  # Reduced for testing
            destroy_size_min=3,
            destroy_size_max=10,
            initial_temperature=100.0,
            cooling_rate=0.95,
            random_seed=42
        )
        engine = SchedulingEngine(config, alns_config)
        
        # Run ALNS (will automatically run greedy first for initial solution)
        results = engine.run_scheduling(
            jobs=jobs,
            technicians=technicians,
            db=db,
            use_alns=True,
            algorithm="alns"
        )
        
        print("\n✅ ALNS test completed successfully")
        return results
        
    finally:
        db.close()


def test_full_comparison():
    """Test full workflow: Greedy + ALNS with comparison."""
    print("\n" + "="*80)
    print("TEST 3: FULL WORKFLOW (Greedy → ALNS → Comparison)")
    print("="*80)
    
    db = SessionLocal()
    try:
        # Load jobs and technicians
        jobs = db.query(Job).options(
            joinedload(Job.required_skills),
            joinedload(Job.service_zone)
        ).all()
        
        technicians = db.query(Technician).options(
            joinedload(Technician.skills),
            joinedload(Technician.service_zones),
            joinedload(Technician.availability_blocks)
        ).all()
        
        print(f"\nLoaded {len(jobs)} jobs and {len(technicians)} technicians from database")
        
        # Initialize engine
        config = Config()
        alns_config = ALNSConfig(
            max_iterations=100,
            destroy_size_min=5,
            destroy_size_max=20,
            initial_temperature=100.0,
            cooling_rate=0.95,
            random_seed=42
        )
        engine = SchedulingEngine(config, alns_config)
        
        # Run both algorithms with comparison
        results = engine.run_scheduling(
            jobs=jobs,
            technicians=technicians,
            db=db,
            use_alns=True,
            algorithm="auto"
        )
        
        print("\n✅ Full comparison test completed successfully")
        
        # Print summary
        if 'comparison' in results:
            print("\n" + "="*80)
            print("FINAL SUMMARY")
            print("="*80)
            comp = results['comparison']
            print(f"\nGreedy assigned:     {comp['assigned_jobs']['greedy']} jobs")
            print(f"ALNS assigned:       {comp['assigned_jobs']['alns']} jobs")
            print(f"Improvement:         {comp['assigned_jobs']['improvement']:+d} jobs")
            print(f"\nGreedy score:        {comp['total_score']['greedy']:.2f}")
            print(f"ALNS score:          {comp['total_score']['alns']:.2f}")
            print(f"Improvement:         {comp['total_score']['improvement']:+.2f} ({comp['total_score']['improvement_pct']:+.1f}%)")
            print(f"\nTotal execution:     {comp['execution_time']['total']:.2f}s")
            print("="*80)
        
        return results
        
    finally:
        db.close()


def test_small_subset():
    """Test with small subset of jobs for quick verification."""
    print("\n" + "="*80)
    print("TEST 4: SMALL SUBSET (Quick Verification)")
    print("="*80)
    
    db = SessionLocal()
    try:
        # Load only first 20 jobs
        jobs = db.query(Job).options(
            joinedload(Job.required_skills),
            joinedload(Job.service_zone)
        ).limit(20).all()
        
        technicians = db.query(Technician).options(
            joinedload(Technician.skills),
            joinedload(Technician.service_zones),
            joinedload(Technician.availability_blocks)
        ).all()
        
        print(f"\nLoaded {len(jobs)} jobs and {len(technicians)} technicians")
        
        # Initialize engine
        config = Config()
        alns_config = ALNSConfig(
            max_iterations=20,
            destroy_size_min=2,
            destroy_size_max=5,
            initial_temperature=50.0,
            cooling_rate=0.95,
            random_seed=42
        )
        engine = SchedulingEngine(config, alns_config)
        
        # Run both algorithms
        results = engine.run_scheduling(
            jobs=jobs,
            technicians=technicians,
            db=db,
            use_alns=True,
            algorithm="auto"
        )
        
        print("\n✅ Small subset test completed successfully")
        return results
        
    finally:
        db.close()


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("DISPATCHGRID SCHEDULING ALGORITHM TEST SUITE")
    print("Testing Phase 5 (Greedy) and Phase 6 (ALNS)")
    print("="*80)
    
    try:
        # Test 1: Greedy only
        test_greedy_only()
        
        # Test 2: ALNS only
        test_alns_only()
        
        # Test 3: Full comparison
        test_full_comparison()
        
        # Test 4: Small subset (quick)
        test_small_subset()
        
        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED SUCCESSFULLY")
        print("="*80)
        print("\nPhase 5 & 6 implementation is complete and working!")
        print("You can now:")
        print("  1. Start the API server: python -m uvicorn app.main:app --reload")
        print("  2. Test via API: POST http://localhost:8000/api/scheduling/run")
        print("  3. View Swagger docs: http://localhost:8000/docs")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
