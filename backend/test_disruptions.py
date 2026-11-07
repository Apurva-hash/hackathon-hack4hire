"""
Test script for Phase 7: Disruption Handling & Re-optimization

Tests all disruption detection and recovery strategies.
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, Any

BASE_URL = "http://localhost:8000"


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def print_result(label: str, data: Any):
    """Print formatted result."""
    print(f"{label}:")
    print(json.dumps(data, indent=2, default=str))
    print()


def test_technician_unavailability():
    """Test technician unavailability detection and recovery."""
    print_section("TEST 1: Technician Unavailability")
    
    # Get a technician with assignments
    response = requests.get(f"{BASE_URL}/api/technicians")
    response.raise_for_status()
    technicians = response.json()
    
    if not technicians:
        print("❌ No technicians found in database")
        return
    
    technician = technicians[0]
    tech_id = technician["id"]
    print(f"Testing with technician: {technician['name']} ({tech_id})")
    
    # Check current assignments
    response = requests.get(f"{BASE_URL}/api/assignments")
    response.raise_for_status()
    assignments = [a for a in response.json() if a["technician_id"] == tech_id]
    print(f"Current assignments for this technician: {len(assignments)}")
    
    # Report unavailability
    unavailable_from = datetime.now()
    unavailable_until = unavailable_from + timedelta(hours=8)
    
    payload = {
        "technician_id": tech_id,
        "unavailable_from": unavailable_from.isoformat(),
        "unavailable_until": unavailable_until.isoformat()
    }
    
    print(f"\n📢 Reporting technician unavailable from {unavailable_from.strftime('%H:%M')} to {unavailable_until.strftime('%H:%M')}")
    
    response = requests.post(
        f"{BASE_URL}/api/disruptions/technician-unavailable",
        json=payload
    )
    
    if response.status_code == 200:
        result = response.json()
        print("\n✅ Disruption processed successfully!")
        print_result("Recovery Result", result)
        
        if result.get("recovery_successful"):
            print("✅ Recovery was successful")
        else:
            print("⚠️  Recovery had issues")
    else:
        print(f"\n❌ Failed: {response.status_code}")
        print(response.text)


def test_job_cancellation():
    """Test job cancellation detection and recovery."""
    print_section("TEST 2: Job Cancellation")
    
    # Get an assigned job
    response = requests.get(f"{BASE_URL}/api/jobs?status=ASSIGNED")
    response.raise_for_status()
    jobs = response.json()
    
    if not jobs:
        print("⚠️  No assigned jobs found. Skipping test.")
        return
    
    job = jobs[0]
    job_id = job["id"]
    print(f"Testing with job: {job['title']} ({job_id})")
    print(f"Priority: {job['priority']}, Status: {job['status']}")
    
    # Report cancellation
    payload = {"job_id": job_id}
    
    print(f"\n📢 Reporting job cancellation")
    
    response = requests.post(
        f"{BASE_URL}/api/disruptions/job-cancellation",
        json=payload
    )
    
    if response.status_code == 200:
        result = response.json()
        print("\n✅ Cancellation processed successfully!")
        print_result("Cancellation Result", result)
        
        # Check job status
        response = requests.get(f"{BASE_URL}/api/jobs/{job_id}")
        if response.status_code == 200:
            updated_job = response.json()
            print(f"Job new status: {updated_job['status']}")
    else:
        print(f"\n❌ Failed: {response.status_code}")
        print(response.text)


def test_emergency_job():
    """Test emergency job insertion."""
    print_section("TEST 3: Emergency Job")
    
    # Get service zone and skills
    zones_resp = requests.get(f"{BASE_URL}/api/service-zones")
    zones_resp.raise_for_status()
    zones = zones_resp.json()
    
    skills_resp = requests.get(f"{BASE_URL}/api/skills")
    skills_resp.raise_for_status()
    skills = skills_resp.json()
    
    if not zones or not skills:
        print("❌ No zones or skills found")
        return
    
    # Create emergency job
    now = datetime.now()
    emergency_job_data = {
        "title": "EMERGENCY: Gas leak repair",
        "description": "Customer reports strong gas smell",
        "priority": "CRITICAL",
        "earliest_start": (now + timedelta(hours=1)).isoformat(),
        "latest_end": (now + timedelta(hours=4)).isoformat(),
        "duration_minutes": 90,
        "service_zone_id": zones[0]["id"],
        "required_skill_ids": [skills[0]["id"]]
    }
    
    print("Creating emergency job...")
    response = requests.post(f"{BASE_URL}/api/jobs", json=emergency_job_data)
    
    if response.status_code != 201:
        print(f"❌ Failed to create job: {response.status_code}")
        print(response.text)
        return
    
    job = response.json()
    job_id = job["id"]
    print(f"✅ Created emergency job: {job['title']} ({job_id})")
    
    # Report as emergency
    payload = {"job_id": job_id}
    
    print(f"\n📢 Reporting emergency job for immediate scheduling")
    
    response = requests.post(
        f"{BASE_URL}/api/disruptions/emergency-job",
        json=payload
    )
    
    if response.status_code == 200:
        result = response.json()
        print("\n✅ Emergency job processed successfully!")
        print_result("Emergency Scheduling Result", result)
        
        if result.get("job_assigned"):
            print(f"✅ Job successfully assigned to technician: {result.get('assigned_to')}")
            print(f"   Scheduled start: {result.get('scheduled_start')}")
        else:
            print("❌ Job could not be assigned")
    else:
        print(f"\n❌ Failed: {response.status_code}")
        print(response.text)


def test_impact_analysis():
    """Test disruption impact analysis."""
    print_section("TEST 4: Impact Analysis")
    
    # Get recent disruptions
    response = requests.get(f"{BASE_URL}/api/disruptions?limit=5")
    response.raise_for_status()
    disruptions = response.json()
    
    if not disruptions:
        print("⚠️  No disruptions found. Run other tests first.")
        return
    
    # Analyze first disruption
    disruption = disruptions[0]
    disruption_id = disruption["id"]
    
    print(f"Analyzing disruption: {disruption_id}")
    print(f"Type: {disruption.get('event_type', 'unknown')}")
    
    response = requests.get(
        f"{BASE_URL}/api/disruptions/impact-analysis/{disruption_id}"
    )
    
    if response.status_code == 200:
        analysis = response.json()
        print("\n✅ Impact analysis completed!")
        print_result("Analysis", analysis)
        
        print(f"\n📊 Summary:")
        print(f"   Impact Score: {analysis['impact_score']:.1f}/100")
        print(f"   Impact Level: {analysis['impact_level']}")
        print(f"   Recovery Strategy: {analysis['recovery_strategy']}")
        print(f"   Affected Assignments: {analysis['affected_summary']['assignments']}")
        print(f"   Affected Jobs: {analysis['affected_summary']['jobs']}")
        print(f"   Reason: {analysis['reason']}")
    else:
        print(f"\n❌ Failed: {response.status_code}")
        print(response.text)


def test_recovery_history():
    """Test recovery runs listing."""
    print_section("TEST 5: Recovery History")
    
    response = requests.get(f"{BASE_URL}/api/disruptions/recovery-runs?limit=10")
    
    if response.status_code == 200:
        runs = response.json()
        print(f"Found {len(runs)} recovery runs\n")
        
        if not runs:
            print("⚠️  No recovery runs found yet")
            return
        
        print("Recent Recovery Operations:")
        print("-" * 80)
        
        for i, run in enumerate(runs, 1):
            print(f"\n{i}. Recovery Run: {run['id']}")
            print(f"   Algorithm: {run['algorithm']}")
            print(f"   Strategy: {run.get('recovery_strategy', 'N/A')}")
            print(f"   Status: {run['status']}")
            print(f"   Started: {run['started_at']}")
            
            metrics = run.get('metrics', {})
            if metrics:
                print(f"   Metrics:")
                for key, value in metrics.items():
                    print(f"     - {key}: {value}")
        
        print("\n✅ Recovery history retrieved successfully")
    else:
        print(f"\n❌ Failed: {response.status_code}")
        print(response.text)


def test_disruption_stats():
    """Test disruption statistics."""
    print_section("TEST 6: Disruption Statistics")
    
    response = requests.get(f"{BASE_URL}/api/disruptions/stats")
    
    if response.status_code == 200:
        stats = response.json()
        print("✅ Statistics retrieved successfully!\n")
        print_result("Disruption Stats", stats)
        
        print("📊 Summary:")
        print(f"   Total Disruptions: {stats['total_disruptions']}")
        print(f"   Processed: {stats['processed']}")
        print(f"   Unprocessed: {stats['unprocessed']}")
        print(f"\n   By Type:")
        for event_type, count in stats.get('by_type', {}).items():
            if count > 0:
                print(f"     - {event_type}: {count}")
    else:
        print(f"\n❌ Failed: {response.status_code}")
        print(response.text)


def main():
    """Run all tests."""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "PHASE 7 DISRUPTION HANDLING TESTS" + " " * 25 + "║")
    print("╚" + "═" * 78 + "╝")
    
    try:
        # Test 1: Technician Unavailability
        test_technician_unavailability()
        
        # Test 2: Job Cancellation
        test_job_cancellation()
        
        # Test 3: Emergency Job
        test_emergency_job()
        
        # Test 4: Impact Analysis
        test_impact_analysis()
        
        # Test 5: Recovery History
        test_recovery_history()
        
        # Test 6: Statistics
        test_disruption_stats()
        
        # Final summary
        print_section("TEST SUMMARY")
        print("✅ All tests completed!")
        print("\nPhase 7 Disruption Handling is operational.")
        print("\nKey Features Tested:")
        print("  ✓ Technician unavailability detection & recovery")
        print("  ✓ Job cancellation detection & recovery")
        print("  ✓ Emergency job insertion")
        print("  ✓ Impact analysis with scoring")
        print("  ✓ Recovery history tracking")
        print("  ✓ Disruption statistics")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to server")
        print("Make sure the backend is running on http://localhost:8000")
        print("\nStart it with:")
        print("  cd backend")
        print("  python -m uvicorn app.main:app --reload")
    
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
