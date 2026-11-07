"""Simple file structure verification for Phases 1-6"""
import os
from pathlib import Path

print("\n" + "="*60)
print("PHASES 1-6 FILE STRUCTURE VERIFICATION")
print("="*60)

root = Path(__file__).parent

# Core files to check
files_to_check = [
    # Phase 2
    ("Phase 2", "requirements.txt", "requirements.txt"),
    ("Phase 2", "main.py", "app/main.py"),
    ("Phase 2", "config.py", "app/config.py"),
    ("Phase 2", "database.py", "app/database.py"),
    
    # Phase 3 - Models
    ("Phase 3", "job model", "app/models/job.py"),
    ("Phase 3", "technician model", "app/models/technician.py"),
    ("Phase 3", "assignment model", "app/models/assignment.py"),
    
    # Phase 3 - APIs
    ("Phase 3", "jobs API", "app/api/jobs.py"),
    ("Phase 3", "technicians API", "app/api/technicians.py"),
    
    # Phase 4
    ("Phase 4", "travel_matrix", "app/seed/travel_matrix.py"),
    ("Phase 4", "time_utils", "app/utils/time_utils.py"),
    ("Phase 4", "seed_data", "app/seed/seed_data.py"),
    
    # Phase 5
    ("Phase 5", "constraints", "app/scheduler/constraints.py"),
    ("Phase 5", "scoring", "app/scheduler/scoring.py"),
    ("Phase 5", "greedy_insertion", "app/scheduler/greedy_insertion.py"),
    
    # Phase 6
    ("Phase 6", "alns_optimizer", "app/scheduler/alns_optimizer.py"),
    ("Phase 6", "engine", "app/scheduler/engine.py"),
    ("Phase 6", "scheduling router", "app/routers/scheduling.py"),
    
    # Tests & Docs
    ("Tests", "test_scheduling", "test_scheduling.py"),
    ("Tests", "verify scripts", "quick_verify.py"),
    ("Docs", "API docs", "API_SCHEDULING.md"),
]

phase_counts = {}
total_files = 0
found_files = 0

for phase, name, path in files_to_check:
    full_path = root / path
    if phase not in phase_counts:
        phase_counts[phase] = {"total": 0, "found": 0}
    
    phase_counts[phase]["total"] += 1
    total_files += 1
    
    if full_path.exists():
        phase_counts[phase]["found"] += 1
        found_files += 1
        print(f"✅ [{phase}] {name}")
    else:
        print(f"❌ [{phase}] {name} - MISSING: {path}")

# Summary by phase
print("\n" + "="*60)
print("SUMMARY BY PHASE")
print("="*60)

all_passed = True
for phase in ["Phase 2", "Phase 3", "Phase 4", "Phase 5", "Phase 6", "Tests", "Docs"]:
    if phase in phase_counts:
        counts = phase_counts[phase]
        percentage = (counts["found"] / counts["total"] * 100) if counts["total"] > 0 else 0
        status = "✅" if counts["found"] == counts["total"] else "⚠️"
        print(f"{status} {phase}: {counts['found']}/{counts['total']} files ({percentage:.0f}%)")
        if counts["found"] < counts["total"]:
            all_passed = False

print("\n" + "="*60)
print(f"OVERALL: {found_files}/{total_files} files present ({found_files/total_files*100:.0f}%)")
print("="*60)

if all_passed:
    print("\n✅ ALL FILES PRESENT - Phases 1-6 Complete!")
    print("\nReady for Phase 7: Disruption Handling")
else:
    print("\n⚠️  Some files missing but core phases may still be functional")

print("\nNext: Install dependencies and test functionality")
print("  Command: pip install -r requirements.txt")
print("="*60 + "\n")
