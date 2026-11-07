"""
Comprehensive API test script for DispatchGrid backend.
Tests all major endpoints end-to-end.
"""
import sys
import json
import time
sys.path.insert(0, '.')

import urllib.request
import urllib.error

BASE = "http://localhost:8000"

def req(method, path, body=None):
    url = BASE + path
    data = json.dumps(body).encode() if body else None
    
    # Retry once on WinError socket errors
    for attempt in range(2):
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        req.add_header("Connection", "close")
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            try:
                return e.code, json.loads(e.read())
            except Exception:
                return e.code, {"error": str(e)}
        except Exception as e:
            if attempt == 0:
                time.sleep(0.5)
                continue
            print(f"  CONNECTION ERROR: {e}")
            return 0, {"error": str(e)}

def test(name, status, body, check_fn=None):
    ok = status < 400
    if check_fn:
        try:
            ok = ok and check_fn(body)
        except Exception as e:
            ok = False
            print(f"  Check failed: {e}")
    icon = "PASS" if ok else "FAIL"
    print(f"  [{icon}] {name} (HTTP {status})")
    if not ok:
        print(f"         Response: {json.dumps(body)[:200]}")
    return ok

results = []
print("\n" + "="*60)
print("DispatchGrid Backend - API Tests")
print("="*60)

# ── Health ────────────────────────────────────────────
print("\n[Health]")
s, b = req("GET", "/api/health")
results.append(test("GET /api/health", s, b, lambda b: b["status"] == "healthy"))

s, b = req("GET", "/")
results.append(test("GET / (root)", s, b, lambda b: "name" in b))

# ── Skills ────────────────────────────────────────────
print("\n[Skills]")
s, b = req("GET", "/api/skills")
results.append(test("GET /api/skills (list)", s, b, lambda b: len(b) >= 10))
skills = b
skill_id = skills[0]["id"] if skills else None

s, b = req("GET", f"/api/skills/{skill_id}")
results.append(test(f"GET /api/skills/{{id}}", s, b, lambda b: "name" in b))

# ── Service Zones ─────────────────────────────────────
print("\n[Service Zones]")
s, b = req("GET", "/api/service-zones")
results.append(test("GET /api/service-zones (list)", s, b, lambda b: len(b) >= 5))
zones = b
zone_id = zones[0]["id"] if zones else None

# ── Technicians ───────────────────────────────────────
print("\n[Technicians]")
s, b = req("GET", "/api/technicians")
results.append(test("GET /api/technicians (list)", s, b, lambda b: b["total"] >= 25))
techs = b.get("technicians", [])
tech_id = techs[0]["id"] if techs else None

s, b = req("GET", f"/api/technicians/{tech_id}")
results.append(test("GET /api/technicians/{id}", s, b, lambda b: "name" in b))

# ── Jobs ─────────────────────────────────────────────
print("\n[Jobs]")
s, b = req("GET", "/api/jobs")
results.append(test("GET /api/jobs (list)", s, b, lambda b: b["total"] >= 100))
jobs_list = b.get("jobs", [])
job_id = jobs_list[0]["id"] if jobs_list else None

s, b = req("GET", "/api/jobs?status=pending")
results.append(test("GET /api/jobs?status=pending", s, b, lambda b: "total" in b))

s, b = req("GET", f"/api/jobs/{job_id}")
results.append(test("GET /api/jobs/{id}", s, b, lambda b: "title" in b))

# Create a new job
s2, zone2 = req("GET", "/api/service-zones")
s3, skill2 = req("GET", "/api/skills")
new_job = {
    "title": "Test Electrical Repair",
    "description": "API test job",
    "location": "456 Test St, North Zone",
    "service_zone_id": zones[0]["id"],
    "duration_minutes": 60,
    "time_window_start": "2026-10-31T08:00:00",
    "time_window_end": "2026-10-31T17:00:00",
    "sla_deadline": "2026-10-31T18:00:00",
    "priority": "high",
    "required_skill_ids": [skills[0]["id"]]
}
s, b = req("POST", "/api/jobs/", new_job)
results.append(test("POST /api/jobs (create)", s, b, lambda b: "id" in b))
created_job_id = b.get("id")

# ── Assignments ────────────────────────────────────────
print("\n[Assignments]")
s, b = req("GET", "/api/assignments")
results.append(test("GET /api/assignments (list)", s, b, lambda b: isinstance(b, list)))

s, b = req("GET", f"/api/assignments/technician/{tech_id}")
results.append(test("GET /api/assignments/technician/{id}", s, b, lambda b: isinstance(b, list)))

# ── Dashboard ─────────────────────────────────────────
print("\n[Dashboard]")
s, b = req("GET", "/api/dashboard/overview")
results.append(test("GET /api/dashboard/overview", s, b, lambda b: "total_jobs" in b))

s, b = req("GET", "/api/dashboard/technicians")
results.append(test("GET /api/dashboard/technicians", s, b, lambda b: isinstance(b, list)))

s, b = req("GET", "/api/dashboard/performance")
results.append(test("GET /api/dashboard/performance", s, b, lambda b: "total_scheduling_runs" in b))

s, b = req("GET", "/api/dashboard/jobs/unassigned")
results.append(test("GET /api/dashboard/jobs/unassigned", s, b, lambda b: isinstance(b, list)))

s, b = req("GET", "/api/dashboard/alerts")
results.append(test("GET /api/dashboard/alerts", s, b, lambda b: isinstance(b, list)))

s, b = req("GET", "/api/dashboard/schedule")
results.append(test("GET /api/dashboard/schedule", s, b, lambda b: isinstance(b, list)))

# ── Disruptions ───────────────────────────────────────
print("\n[Disruptions]")
s, b = req("GET", "/api/disruptions")
results.append(test("GET /api/disruptions (list)", s, b, lambda b: isinstance(b, list)))

# Report a disruption
disruption_payload = {
    "event_type": "urgent_job",
    "affected_entity_type": "job",
    "affected_entity_id": job_id,
    "description": "API test disruption"
}
s, b = req("POST", "/api/disruptions/", disruption_payload)
results.append(test("POST /api/disruptions (report)", s, b, lambda b: "id" in b))
disruption_id = b.get("id") if s < 400 else None

if disruption_id:
    s, b = req("GET", f"/api/disruptions/{disruption_id}")
    results.append(test("GET /api/disruptions/{id}", s, b, lambda b: "event_type" in b))

s, b = req("GET", "/api/disruptions/stats")
results.append(test("GET /api/disruptions/stats", s, b))

# ── Scheduling Runs ────────────────────────────────────
print("\n[Scheduling - Greedy only (fast test)]")
sched_payload = {
    "algorithm": "greedy",
    "use_alns": False,
    "max_iterations": 10
}
print("  Running greedy scheduling (this may take ~5s)...")
t0 = time.time()
s, b = req("POST", "/api/scheduling/run", sched_payload)
elapsed = time.time() - t0
results.append(test(
    f"POST /api/scheduling/run (greedy, {elapsed:.1f}s)", s, b,
    lambda b: b.get("status") == "completed" and "run_id" in b
))

if s < 400:
    run_id = b.get("run_id")
    assigned = b.get("assigned_count", 0)
    total = b.get("jobs_count", 0)
    score = b.get("metrics", {}).get("total_score", 0)
    print(f"         Assigned: {assigned}/{total} jobs, Score: {score:.1f}")

    s2, b2 = req("GET", "/api/scheduling/runs")
    results.append(test("GET /api/scheduling/runs", s2, b2, lambda b: len(b) >= 1))

    s3, b3 = req("GET", f"/api/scheduling/runs/{run_id}")
    results.append(test("GET /api/scheduling/runs/{id}", s3, b3, lambda b: "timestamp" in b))

    # Assignments should now be populated
    s4, b4 = req("GET", "/api/assignments")
    results.append(test("GET /api/assignments (post-scheduling)", s4, b4, lambda b: len(b) >= 1))

    # Dashboard should show results
    s5, b5 = req("GET", "/api/dashboard/overview")
    results.append(test("GET /api/dashboard/overview (post-scheduling)", s5, b5,
        lambda b: b.get("total_assignments", 0) >= 1))

# ── Summary ───────────────────────────────────────────
passed = sum(1 for r in results if r)
total_tests = len(results)
print("\n" + "="*60)
print(f"RESULTS: {passed}/{total_tests} tests passed")
if passed == total_tests:
    print("ALL TESTS PASSED!")
else:
    print(f"{total_tests - passed} test(s) FAILED")
print("="*60)
