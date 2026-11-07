"""
Quick script to get actual job IDs from the database.
"""

from app.database import SessionLocal
from app.models import Job

db = SessionLocal()

print("\n" + "="*70)
print("ACTUAL JOB IDs IN DATABASE")
print("="*70 + "\n")

jobs = db.query(Job).limit(10).all()

print(f"Showing first 10 jobs out of {db.query(Job).count()} total:\n")

for i, job in enumerate(jobs, 1):
    print(f"{i}. ID: {job.id}")
    print(f"   Title: {job.title}")
    print(f"   Status: {job.status.value}")
    print(f"   Priority: {job.priority.value}")
    print()

db.close()

print("="*70)
print("To test GET /api/jobs/{id}, use one of these UUIDs above")
print("Example: http://localhost:8000/api/jobs/" + jobs[0].id if jobs else "")
print("="*70 + "\n")
