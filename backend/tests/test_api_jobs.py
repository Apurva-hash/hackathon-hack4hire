"""Tests for Job API endpoints."""

import pytest
from datetime import datetime, timedelta

from app.models import JobPriority, JobStatus


class TestJobAPI:
    """Test job CRUD operations."""
    
    def test_create_job_success(self, client, db):
        """Test successful job creation."""
        # First create a service zone and skill
        zone_response = client.post("/api/service-zones/", json={
            "name": "North Zone",
            "description": "Northern service area"
        })
        zone_id = zone_response.json()["id"]
        
        skill_response = client.post("/api/skills/", json={
            "name": "Plumbing",
            "description": "Plumbing repairs"
        })
        skill_id = skill_response.json()["id"]
        
        # Create job
        job_data = {
            "title": "Fix Leaking Pipe",
            "description": "Customer reports leaking under sink",
            "location": "123 Main St",
            "service_zone_id": zone_id,
            "duration_minutes": 60,
            "time_window_start": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "time_window_end": (datetime.utcnow() + timedelta(hours=8)).isoformat(),
            "sla_deadline": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
            "priority": "high",
            "required_skill_ids": [skill_id]
        }
        
        response = client.post("/api/jobs/", json=job_data)
        assert response.status_code == 201
        
        data = response.json()
        assert data["title"] == job_data["title"]
        assert data["status"] == "pending"
        assert data["priority"] == "high"
        assert len(data["required_skills"]) == 1
    
    def test_create_job_invalid_time_window(self, client, db):
        """Test job creation with invalid time window."""
        # Create service zone
        zone_response = client.post("/api/service-zones/", json={
            "name": "Test Zone"
        })
        zone_id = zone_response.json()["id"]
        
        job_data = {
            "title": "Test Job",
            "location": "123 Main St",
            "service_zone_id": zone_id,
            "duration_minutes": 60,
            "time_window_start": datetime.utcnow().isoformat(),
            "time_window_end": (datetime.utcnow() - timedelta(hours=1)).isoformat(),  # Invalid: end before start
            "sla_deadline": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
            "priority": "medium",
            "required_skill_ids": []
        }
        
        response = client.post("/api/jobs/", json=job_data)
        assert response.status_code == 422  # Validation error
    
    def test_list_jobs(self, client, db):
        """Test listing jobs."""
        response = client.get("/api/jobs/")
        assert response.status_code == 200
        
        data = response.json()
        assert "total" in data
        assert "jobs" in data
    
    def test_get_job(self, client, db):
        """Test getting a single job."""
        # Create a job first
        zone_response = client.post("/api/service-zones/", json={"name": "Zone A"})
        zone_id = zone_response.json()["id"]
        
        job_data = {
            "title": "Test Job",
            "location": "123 Main St",
            "service_zone_id": zone_id,
            "duration_minutes": 30,
            "time_window_start": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "time_window_end": (datetime.utcnow() + timedelta(hours=8)).isoformat(),
            "sla_deadline": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
            "priority": "medium",
            "required_skill_ids": []
        }
        
        create_response = client.post("/api/jobs/", json=job_data)
        job_id = create_response.json()["id"]
        
        # Get the job
        response = client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        assert response.json()["id"] == job_id
    
    def test_update_job(self, client, db):
        """Test updating a job."""
        # Create a job first
        zone_response = client.post("/api/service-zones/", json={"name": "Zone B"})
        zone_id = zone_response.json()["id"]
        
        job_data = {
            "title": "Original Title",
            "location": "123 Main St",
            "service_zone_id": zone_id,
            "duration_minutes": 30,
            "time_window_start": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "time_window_end": (datetime.utcnow() + timedelta(hours=8)).isoformat(),
            "sla_deadline": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
            "priority": "medium",
            "required_skill_ids": []
        }
        
        create_response = client.post("/api/jobs/", json=job_data)
        job_id = create_response.json()["id"]
        
        # Update the job
        update_data = {"title": "Updated Title", "duration_minutes": 45}
        response = client.patch(f"/api/jobs/{job_id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["duration_minutes"] == 45
    
    def test_cancel_job(self, client, db):
        """Test cancelling a job."""
        # Create a job first
        zone_response = client.post("/api/service-zones/", json={"name": "Zone C"})
        zone_id = zone_response.json()["id"]
        
        job_data = {
            "title": "Job to Cancel",
            "location": "123 Main St",
            "service_zone_id": zone_id,
            "duration_minutes": 30,
            "time_window_start": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "time_window_end": (datetime.utcnow() + timedelta(hours=8)).isoformat(),
            "sla_deadline": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
            "priority": "medium",
            "required_skill_ids": []
        }
        
        create_response = client.post("/api/jobs/", json=job_data)
        job_id = create_response.json()["id"]
        
        # Cancel the job
        response = client.post(f"/api/jobs/{job_id}/cancel")
        
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"
