"""
Test script to verify job creation API works correctly.
"""

import requests
import json
from datetime import datetime, timedelta

print("\n" + "="*70)
print("TESTING JOB CREATION API")
print("="*70 + "\n")

# API endpoint
base_url = "http://localhost:8000"
jobs_url = f"{base_url}/api/jobs"

# Test 1: Create a new job
print("TEST 1: Creating a new job...")
print("-" * 70)

tomorrow = datetime.now() + timedelta(days=1)
job_data = {
    "title": "Test Emergency Plumbing Repair",
    "description": "Testing job creation via API - leak in main pipe",
    "location": "456 Test Avenue, Downtown",
    "service_zone_id": 1,
    "duration_minutes": 120,
    "time_window_start": tomorrow.replace(hour=8, minute=0).isoformat(),
    "time_window_end": tomorrow.replace(hour=17, minute=0).isoformat(),
    "sla_deadline": tomorrow.replace(hour=18, minute=0).isoformat(),
    "priority": "HIGH",
    "required_skill_ids": [1, 2]  # Plumbing and General Repair
}

print(f"Sending POST request to: {jobs_url}")
print(f"Job data: {json.dumps(job_data, indent=2)}")
print()

try:
    response = requests.post(jobs_url, json=job_data, timeout=10)
    
    print(f"Response Status Code: {response.status_code}")
    print()
    
    if response.status_code == 201:
        print("[SUCCESS] Job created successfully!")
        created_job = response.json()
        print(f"\nCreated Job Details:")
        print(f"  ID: {created_job.get('id')}")
        print(f"  Title: {created_job.get('title')}")
        print(f"  Status: {created_job.get('status')}")
        print(f"  Priority: {created_job.get('priority')}")
        print(f"  Duration: {created_job.get('duration_minutes')} minutes")
        print(f"  Location: {created_job.get('location')}")
        print(f"  Service Zone ID: {created_job.get('service_zone_id')}")
        print(f"  Required Skills: {len(created_job.get('required_skills', []))} skills")
        
        job_id = created_job.get('id')
        
        # Test 2: Retrieve the created job
        print(f"\n{'-'*70}")
        print("TEST 2: Retrieving the created job...")
        print("-" * 70)
        
        get_response = requests.get(f"{jobs_url}/{job_id}", timeout=10)
        if get_response.status_code == 200:
            print("[SUCCESS] Job retrieved successfully!")
            retrieved_job = get_response.json()
            print(f"  Retrieved ID: {retrieved_job.get('id')}")
            print(f"  Title: {retrieved_job.get('title')}")
        else:
            print(f"[ERROR] Failed to retrieve job: {get_response.status_code}")
            print(get_response.text)
        
        # Test 3: List all jobs
        print(f"\n{'-'*70}")
        print("TEST 3: Listing all jobs...")
        print("-" * 70)
        
        list_response = requests.get(jobs_url, timeout=10)
        if list_response.status_code == 200:
            jobs_list = list_response.json()
            total = jobs_list.get('total', 0)
            jobs = jobs_list.get('jobs', [])
            print(f"[SUCCESS] Retrieved jobs list!")
            print(f"  Total jobs in database: {total}")
            print(f"  Jobs in response: {len(jobs)}")
            
            # Find our created job
            our_job = next((j for j in jobs if j.get('id') == job_id), None)
            if our_job:
                print(f"  [VERIFIED] Our created job is in the list!")
            else:
                print(f"  [WARNING] Our job not found in list (might be paginated)")
        else:
            print(f"[ERROR] Failed to list jobs: {list_response.status_code}")
        
    else:
        print(f"[ERROR] Failed to create job!")
        print(f"Response: {response.text}")

except requests.exceptions.ConnectionError:
    print("[ERROR] Could not connect to server!")
    print("Make sure the server is running on http://localhost:8000")
except requests.exceptions.Timeout:
    print("[ERROR] Request timed out!")
except Exception as e:
    print(f"[ERROR] Unexpected error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
print("TESTING COMPLETE")
print("="*70 + "\n")
