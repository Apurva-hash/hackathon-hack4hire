"""Tests for Technician API endpoints."""

import pytest
from datetime import time, datetime, timedelta


class TestTechnicianAPI:
    """Test technician CRUD operations."""
    
    def test_create_technician_success(self, client, db):
        """Test successful technician creation."""
        # Create skill and zone first
        skill_response = client.post("/api/skills/", json={
            "name": "HVAC"
        })
        skill_id = skill_response.json()["id"]
        
        zone_response = client.post("/api/service-zones/", json={
            "name": "Downtown"
        })
        zone_id = zone_response.json()["id"]
        
        # Create technician
        tech_data = {
            "name": "John Smith",
            "shift_start": "08:00:00",
            "shift_end": "17:00:00",
            "current_location": "Downtown",
            "skill_ids": [skill_id],
            "service_zone_ids": [zone_id],
            "status": "available"
        }
        
        response = client.post("/api/technicians/", json=tech_data)
        assert response.status_code == 201
        
        data = response.json()
        assert data["name"] == "John Smith"
        assert data["status"] == "available"
        assert len(data["skills"]) == 1
        assert len(data["service_zones"]) == 1
    
    def test_create_technician_invalid_shift(self, client, db):
        """Test technician creation with invalid shift times."""
        tech_data = {
            "name": "Jane Doe",
            "shift_start": "17:00:00",
            "shift_end": "08:00:00",  # Invalid: end before start
            "skill_ids": [],
            "service_zone_ids": []
        }
        
        response = client.post("/api/technicians/", json=tech_data)
        assert response.status_code == 400
    
    def test_list_technicians(self, client, db):
        """Test listing technicians."""
        response = client.get("/api/technicians/")
        assert response.status_code == 200
        
        data = response.json()
        assert "total" in data
        assert "technicians" in data
    
    def test_get_technician(self, client, db):
        """Test getting a single technician."""
        # Create technician first
        tech_data = {
            "name": "Test Technician",
            "shift_start": "08:00:00",
            "shift_end": "17:00:00",
            "skill_ids": [],
            "service_zone_ids": []
        }
        
        create_response = client.post("/api/technicians/", json=tech_data)
        tech_id = create_response.json()["id"]
        
        # Get the technician
        response = client.get(f"/api/technicians/{tech_id}")
        assert response.status_code == 200
        assert response.json()["id"] == tech_id
    
    def test_update_technician(self, client, db):
        """Test updating a technician."""
        # Create technician first
        tech_data = {
            "name": "Original Name",
            "shift_start": "08:00:00",
            "shift_end": "17:00:00",
            "skill_ids": [],
            "service_zone_ids": []
        }
        
        create_response = client.post("/api/technicians/", json=tech_data)
        tech_id = create_response.json()["id"]
        
        # Update the technician
        update_data = {
            "name": "Updated Name",
            "status": "unavailable"
        }
        response = client.patch(f"/api/technicians/{tech_id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["status"] == "unavailable"
    
    def test_add_availability_block(self, client, db):
        """Test adding an unavailable period."""
        # Create technician first
        tech_data = {
            "name": "Busy Tech",
            "shift_start": "08:00:00",
            "shift_end": "17:00:00",
            "skill_ids": [],
            "service_zone_ids": []
        }
        
        create_response = client.post("/api/technicians/", json=tech_data)
        tech_id = create_response.json()["id"]
        
        # Add availability block
        block_data = {
            "start_time": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "end_time": (datetime.utcnow() + timedelta(hours=3)).isoformat(),
            "reason": "Training session"
        }
        
        response = client.post(f"/api/technicians/{tech_id}/availability", json=block_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["technician_id"] == tech_id
        assert data["reason"] == "Training session"
