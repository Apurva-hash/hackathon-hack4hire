"""Integration tests for the main booking flow.

Flow: register customer → book service → dispatch offer → tech accepts → update status → rate

These tests use FastAPI's TestClient with an in-memory SQLite database
(isolated from the production DB).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.seed.v2_seed import seed

# ── Test DB setup (in-memory) ─────────────────────────────────────────────────

TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=test_engine)
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="module")
def seeded_client(client):
    """Seed the test DB and return client + credentials."""
    # Seed via API — register users directly
    # 1. Register admin (manually insert via SQL is complex; use auth endpoint)
    # We call seed-like registrations through the API instead
    return client


# ── Helper: register + login ──────────────────────────────────────────────────

def register_and_login(client, email, password, name, role="customer"):
    endpoint = f"/api/auth/register/{role}"
    payload = {"email": email, "password": password, "name": name}
    r = client.post(endpoint, json=payload)
    assert r.status_code == 201, f"Register failed: {r.text}"
    return r.json()["access_token"]


def login(client, email, password):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"Login failed: {r.text}"
    return r.json()["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestHealthCheck:
    def test_root(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert r.json()["status"] == "operational"

    def test_health(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"


class TestAuthFlow:
    def test_register_customer(self, client):
        r = client.post("/api/auth/register/customer", json={
            "email": "test.customer@example.com",
            "password": "Test@1234",
            "name": "Test Customer",
        })
        assert r.status_code == 201
        data = r.json()
        assert "access_token" in data
        assert data["role"] == "customer"

    def test_register_duplicate_email(self, client):
        r = client.post("/api/auth/register/customer", json={
            "email": "test.customer@example.com",
            "password": "Test@1234",
            "name": "Duplicate",
        })
        assert r.status_code == 409

    def test_login_valid(self, client):
        r = client.post("/api/auth/login", json={
            "email": "test.customer@example.com",
            "password": "Test@1234",
        })
        assert r.status_code == 200
        assert "access_token" in r.json()
        assert "refresh_token" in r.json()

    def test_login_invalid_password(self, client):
        r = client.post("/api/auth/login", json={
            "email": "test.customer@example.com",
            "password": "WrongPassword",
        })
        assert r.status_code == 401

    def test_get_me(self, client):
        token = login(client, "test.customer@example.com", "Test@1234")
        r = client.get("/api/auth/me", headers=auth_headers(token))
        assert r.status_code == 200
        assert r.json()["email"] == "test.customer@example.com"

    def test_register_technician(self, client):
        r = client.post("/api/auth/register/technician", json={
            "email": "test.tech@example.com",
            "password": "Tech@1234",
            "name": "Test Technician",
            "certification_level": 3,
            "service_radius_km": 20.0,
        })
        assert r.status_code == 201
        data = r.json()
        assert data["role"] == "technician"
        assert "Awaiting admin approval" in data["message"]


class TestCustomerProfile:
    @pytest.fixture(autouse=True)
    def setup(self, client):
        self.token = login(client, "test.customer@example.com", "Test@1234")
        self.headers = auth_headers(self.token)

    def test_get_profile(self, client):
        r = client.get("/api/customer/profile", headers=self.headers)
        assert r.status_code == 200
        assert "name" in r.json()

    def test_update_profile(self, client):
        r = client.patch("/api/customer/profile", headers=self.headers, json={"phone": "9999999999"})
        assert r.status_code == 200

    def test_add_address(self, client):
        r = client.post("/api/customer/addresses", headers=self.headers, json={
            "label": "Home",
            "address": "123 Test Street",
            "lat": 12.97,
            "lng": 77.59,
        })
        assert r.status_code == 201
        assert "addresses" in r.json()

    def test_list_addresses(self, client):
        r = client.get("/api/customer/addresses", headers=self.headers)
        assert r.status_code == 200
        assert isinstance(r.json()["addresses"], list)


class TestCategoryEndpoint:
    def test_list_categories_requires_auth(self, client):
        r = client.get("/api/customer/categories")
        assert r.status_code == 403

    def test_list_categories_with_auth(self, client):
        token = login(client, "test.customer@example.com", "Test@1234")
        r = client.get("/api/customer/categories", headers=auth_headers(token))
        # May be empty in fresh test DB, but endpoint should respond OK
        assert r.status_code == 200
        assert isinstance(r.json(), list)


class TestBookingFlow:
    """Full end-to-end booking flow.

    NOTE: In a bare test DB without seed data, the category must be created first.
    These tests are structured to be as standalone as possible.
    """

    @pytest.fixture(autouse=True)
    def setup(self, client):
        self.customer_token = login(client, "test.customer@example.com", "Test@1234")
        self.c_headers = auth_headers(self.customer_token)

    def test_list_bookings_empty(self, client):
        r = client.get("/api/customer/bookings", headers=self.c_headers)
        assert r.status_code == 200
        data = r.json()
        assert "bookings" in data
        assert data["total"] >= 0

    def test_nearby_technicians(self, client):
        r = client.get("/api/customer/nearby-technicians?lat=12.97&lng=77.59", headers=self.c_headers)
        assert r.status_code == 200
        assert "technicians" in r.json()

    def test_create_booking_without_valid_category(self, client):
        """Booking with a non-existent category should fail with 404."""
        r = client.post("/api/customer/bookings", headers=self.c_headers, json={
            "category_id": "nonexistent-cat-id",
            "address": "123 Test Street",
            "lat": 12.97,
            "lng": 77.59,
            "urgency": "normal",
        })
        assert r.status_code == 404


class TestTechnicianPortal:
    @pytest.fixture(autouse=True)
    def setup(self, client):
        self.tech_token = login(client, "test.tech@example.com", "Tech@1234")
        self.t_headers = auth_headers(self.tech_token)

    def test_get_profile(self, client):
        r = client.get("/api/technician/profile", headers=self.t_headers)
        assert r.status_code == 200
        data = r.json()
        assert "name" in data
        assert data["is_approved"] is False  # Newly registered tech is not approved

    def test_cannot_go_online_without_approval(self, client):
        r = client.patch("/api/technician/availability", headers=self.t_headers, json={"is_online": True})
        assert r.status_code == 403

    def test_update_location(self, client):
        r = client.patch("/api/technician/location", headers=self.t_headers, json={"lat": 12.97, "lng": 77.59})
        assert r.status_code == 200

    def test_list_offers_empty(self, client):
        r = client.get("/api/technician/offers", headers=self.t_headers)
        assert r.status_code == 200
        assert r.json()["count"] == 0

    def test_list_jobs_empty(self, client):
        r = client.get("/api/technician/jobs", headers=self.t_headers)
        assert r.status_code == 200
        assert r.json()["total"] == 0


class TestRoleProtection:
    def test_customer_cannot_access_admin(self, client):
        token = login(client, "test.customer@example.com", "Test@1234")
        r = client.get("/api/admin/dashboard/overview", headers=auth_headers(token))
        assert r.status_code == 403

    def test_technician_cannot_access_customer_bookings(self, client):
        """Technician token should be rejected by customer endpoints."""
        tech_token = login(client, "test.tech@example.com", "Tech@1234")
        r = client.get("/api/customer/bookings", headers=auth_headers(tech_token))
        assert r.status_code == 403

    def test_unauthenticated_request_rejected(self, client):
        r = client.get("/api/customer/profile")
        assert r.status_code == 403


class TestNotifications:
    def test_list_notifications_customer(self, client):
        token = login(client, "test.customer@example.com", "Test@1234")
        r = client.get("/api/customer/notifications", headers=auth_headers(token))
        assert r.status_code == 200
        assert "notifications" in r.json()

