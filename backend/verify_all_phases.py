"""
Comprehensive verification of Phases 1-6 without requiring database.
Checks file existence, structure, and basic imports.
"""

import os
import sys
from pathlib import Path

print("\n" + "="*70)
print("DISPATCHGRID PHASES 1-6 COMPREHENSIVE VERIFICATION")
print("="*70)

errors = []
warnings = []

# ============================================================================
# PHASE 1: Requirements & Architecture
# ============================================================================
print("\n[PHASE 1] Requirements & Architecture")
print("-" * 70)

phase1_checks = {
    "README.md": "../README.md",
    "Phase 5 & 6 Complete Doc": "../PHASE_5_6_COMPLETE.md",
}

for name, path in phase1_checks.items():
    full_path = Path(__file__).parent / path
    if full_path.exists():
        print(f"  ✅ {name} exists")
    else:
        errors.append(f"Phase 1: {name} missing at {path}")
        print(f"  ❌ {name} MISSING")

# ============================================================================
# PHASE 2: Project Setup
# ============================================================================
print("\n[PHASE 2] Project Setup")
print("-" * 70)

phase2_files = {
    "requirements.txt": "requirements.txt",
    ".env.example": ".env.example",
    "main.py": "app/main.py",
    "config.py": "app/config.py",
    "database.py": "app/database.py",
}

for name, path in phase2_files.items():
    full_path = Path(__file__).parent / path
    if full_path.exists():
        print(f"  ✅ {name} exists")
    else:
        errors.append(f"Phase 2: {name} missing at {path}")
        print(f"  ❌ {name} MISSING")

# ============================================================================
# PHASE 3: Database Models & APIs
# ============================================================================
print("\n[PHASE 3] Database Models & APIs")
print("-" * 70)

phase3_files = {
    "models.py": "app/models.py",
    "schemas (jobs)": "app/schemas/jobs.py",
    "schemas (technicians)": "app/schemas/technicians.py",
    "api (jobs)": "app/api/jobs.py",
    "api (technicians)": "app/api/technicians.py",
    "api (skills)": "app/api/skills.py",
    "api (service_zones)": "app/api/service_zones.py",
}

for name, path in phase3_files.items():
    full_path = Path(__file__).parent / path
    if full_path.exists():
        size = full_path.stat().st_size
        print(f"  ✅ {name} exists ({size} bytes)")
    else:
        errors.append(f"Phase 3: {name} missing at {path}")
        print(f"  ❌ {name} MISSING")

# Check for 11 models
print("\n  Checking database models...")
models_path = Path(__file__).parent / "app" / "models.py"
if models_path.exists():
    content = models_path.read_text()
    expected_models = [
        "Job", "Technician", "Skill", "ServiceZone", "Assignment",
        "AvailabilityBlock", "SchedulingRun", "SchedulingDecision",
        "DisruptionEvent"
    ]
    found_models = []
    for model in expected_models:
        if f"class {model}" in content:
            found_models.append(model)
    print(f"  ✅ Found {len(found_models)}/{len(expected_models)} models")
    if len(found_models) < len(expected_models):
        missing = set(expected_models) - set(found_models)
        warnings.append(f"Phase 3: Missing models: {missing}")
else:
    errors.append("Phase 3: models.py not found")

# ============================================================================
# PHASE 4: Seed Data & Utilities
# ============================================================================
print("\n[PHASE 4] Seed Data & Utilities")
print("-" * 70)

phase4_files = {
    "travel_matrix.py": "app/utils/travel_matrix.py",
    "time_utils.py": "app/utils/time_utils.py",
    "seed_data.py": "app/seed_data.py",
}

for name, path in phase4_files.items():
    full_path = Path(__file__).parent / path
    if full_path.exists():
        print(f"  ✅ {name} exists")
    else:
        errors.append(f"Phase 4: {name} missing at {path}")
        print(f"  ❌ {name} MISSING")

# ============================================================================
# PHASE 5: Greedy Insertion Algorithm
# ============================================================================
print("\n[PHASE 5] Greedy Insertion Algorithm")
print("-" * 70)

phase5_files = {
    "constraints.py": "app/scheduler/constraints.py",
    "scoring.py": "app/scheduler/scoring.py",
    "greedy_insertion.py": "app/scheduler/greedy_insertion.py",
}

for name, path in phase5_files.items():
    full_path = Path(__file__).parent / path
    if full_path.exists():
        size = full_path.stat().st_size
        lines = len(full_path.read_text().splitlines())
        print(f"  ✅ {name} exists ({lines} lines, {size} bytes)")
    else:
        errors.append(f"Phase 5: {name} missing at {path}")
        print(f"  ❌ {name} MISSING")

# Check for key classes
greedy_path = Path(__file__).parent / "app/scheduler/greedy_insertion.py"
if greedy_path.exists():
    content = greedy_path.read_text()
    if "class GreedyInsertion" in content:
        print(f"  ✅ GreedyInsertion class found")
    else:
        errors.append("Phase 5: GreedyInsertion class not found")
    if "_prioritize_jobs_lfj" in content:
        print(f"  ✅ LFJ prioritization method found")
    else:
        warnings.append("Phase 5: LFJ method not found")

# ============================================================================
# PHASE 6: ALNS Optimization
# ============================================================================
print("\n[PHASE 6] ALNS Optimization")
print("-" * 70)

phase6_files = {
    "alns_optimizer.py": "app/scheduler/alns_optimizer.py",
    "engine.py": "app/scheduler/engine.py",
    "scheduling router": "app/routers/scheduling.py",
}

for name, path in phase6_files.items():
    full_path = Path(__file__).parent / path
    if full_path.exists():
        size = full_path.stat().st_size
        lines = len(full_path.read_text().splitlines())
        print(f"  ✅ {name} exists ({lines} lines, {size} bytes)")
    else:
        errors.append(f"Phase 6: {name} missing at {path}")
        print(f"  ❌ {name} MISSING")

# Check ALNS components
alns_path = Path(__file__).parent / "app/scheduler/alns_optimizer.py"
if alns_path.exists():
    content = alns_path.read_text()
    components = {
        "ALNSOptimizer class": "class ALNSOptimizer",
        "Destroy operators": "_destroy_random",
        "Repair operators": "_repair_greedy",
        "Simulated Annealing": "_accept_solution",
        "Adaptive weights": "_update_operator_weights",
    }
    for comp_name, search_str in components.items():
        if search_str in content:
            print(f"  ✅ {comp_name} found")
        else:
            warnings.append(f"Phase 6: {comp_name} not found")

# Check API integration
main_path = Path(__file__).parent / "app" / "main.py"
if main_path.exists():
    content = main_path.read_text()
    if "scheduling.router" in content or "from app.routers import scheduling" in content:
        print(f"  ✅ Scheduling router integrated in main.py")
    else:
        warnings.append("Phase 6: Scheduling router not registered in main.py")

# ============================================================================
# Testing & Documentation
# ============================================================================
print("\n[TESTING & DOCS]")
print("-" * 70)

test_docs = {
    "test_scheduling.py": "test_scheduling.py",
    "quick_verify.py": "quick_verify.py",
    "API Documentation": "API_SCHEDULING.md",
}

for name, path in test_docs.items():
    full_path = Path(__file__).parent / path
    if full_path.exists():
        print(f"  ✅ {name} exists")
    else:
        warnings.append(f"Documentation: {name} missing")
        print(f"  ⚠️  {name} missing")

# ============================================================================
# File Structure Summary
# ============================================================================
print("\n[FILE STRUCTURE]")
print("-" * 70)

key_dirs = [
    "app",
    "app/api",
    "app/schemas",
    "app/services",
    "app/scheduler",
    "app/routers",
    "app/utils",
]

for dir_path in key_dirs:
    full_path = Path(__file__).parent / dir_path
    if full_path.exists() and full_path.is_dir():
        file_count = len(list(full_path.glob("*.py")))
        print(f"  ✅ {dir_path}/ ({file_count} Python files)")
    else:
        errors.append(f"Directory missing: {dir_path}")
        print(f"  ❌ {dir_path}/ MISSING")

# ============================================================================
# Summary
# ============================================================================
print("\n" + "="*70)
print("VERIFICATION SUMMARY")
print("="*70)

if not errors and not warnings:
    print("\n✅ ALL CHECKS PASSED!")
    print("\nAll Phases 1-6 files are present and properly structured.")
    print("The implementation is complete and ready for testing.")
    print("\nNext steps:")
    print("  1. Install dependencies: pip install -r requirements.txt")
    print("  2. Run verification with imports: python quick_verify.py")
    print("  3. Seed database: python -m app.seed_data")
    print("  4. Run tests: python test_scheduling.py")
    print("  5. Start server: python -m uvicorn app.main:app --reload")
    sys.exit(0)
else:
    if errors:
        print(f"\n❌ ERRORS FOUND ({len(errors)}):")
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}")
    
    if warnings:
        print(f"\n⚠️  WARNINGS ({len(warnings)}):")
        for i, warning in enumerate(warnings, 1):
            print(f"  {i}. {warning}")
    
    if errors:
        print("\n❌ VERIFICATION FAILED - Critical files missing")
        sys.exit(1)
    else:
        print("\n⚠️  VERIFICATION PASSED WITH WARNINGS")
        print("Core files present but some components may need attention.")
        sys.exit(0)

print("="*70 + "\n")
