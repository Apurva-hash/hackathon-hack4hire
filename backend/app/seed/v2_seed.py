"""V2 seed data — creates admin, customer, technician users, categories, SLA tiers, and matching config.

Run with:
    cd backend
    venv\\Scripts\\activate
    python -m app.seed.v2_seed
"""

from __future__ import annotations

import sys
import os

# Reconfigure stdout and stderr for UTF-8 with fallback to avoid charmap UnicodeEncodeErrors on Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure the backend directory is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.database import SessionLocal, engine, Base
from app import models  # registers all models
from app.models import (
    User, Customer, TechnicianProfile, ServiceCategory,
    SLATier, MatchingConfig, Notification,
    UserRole,
)
from app.models.base import generate_uuid
from app.services.auth_service import hash_password

# Create all tables
Base.metadata.create_all(bind=engine)


TEST_CREDENTIALS = """
╔══════════════════════════════════════════════════════════════════╗
║                  DispatchGrid v2 — Test Credentials              ║
╠══════════════════════════════════════════════════════════════════╣
║  ADMIN                                                           ║
║    email:    admin@dispatchgrid.dev                              ║
║    password: Admin@1234                                          ║
╠══════════════════════════════════════════════════════════════════╣
║  CUSTOMERS                                                       ║
║    alice@example.com   / Customer@1234                           ║
║    bob@example.com     / Customer@1234                           ║
║    carol@example.com   / Customer@1234                           ║
╠══════════════════════════════════════════════════════════════════╣
║  TECHNICIANS (all pre-approved, ready to go online)              ║
║    raj.tech@example.com      / Tech@1234  (AC, cert=4)          ║
║    priya.tech@example.com    / Tech@1234  (Plumbing, cert=3)    ║
║    amit.tech@example.com     / Tech@1234  (Electrical, cert=5)  ║
║    sunita.tech@example.com   / Tech@1234  (Washing, cert=2)     ║
║    deepak.tech@example.com   / Tech@1234  (Multi, cert=3)       ║
╚══════════════════════════════════════════════════════════════════╝
"""


def seed():
    db = SessionLocal()
    try:
        print("[seed] Checking and seeding V2 data...")

        # ── SLA Tiers ─────────────────────────────────────────────────────────
        existing_tiers_count = db.query(SLATier).count()
        if existing_tiers_count == 0:
            sla_tiers = [
                SLATier(id=generate_uuid(), name="Critical", priority_level=1, response_time_minutes=15, resolution_time_minutes=60, is_default=False),
                SLATier(id=generate_uuid(), name="High", priority_level=2, response_time_minutes=30, resolution_time_minutes=120, is_default=False),
                SLATier(id=generate_uuid(), name="Normal", priority_level=3, response_time_minutes=60, resolution_time_minutes=240, is_default=True),
                SLATier(id=generate_uuid(), name="Low", priority_level=4, response_time_minutes=120, resolution_time_minutes=480, is_default=False),
            ]
            for t in sla_tiers:
                db.add(t)
            db.flush()
            print(f"  [OK] {len(sla_tiers)} SLA tiers")
        # ── MatchingConfig singleton ───────────────────────────────────────────
        existing_cfg = db.query(MatchingConfig).first()
        if not existing_cfg:
            cfg = MatchingConfig(
                id=1,
                weight_distance=0.35,
                weight_rating=0.25,
                weight_workload=0.20,
                weight_skill_level=0.15,
                weight_acceptance_rate=0.05,
                offer_timeout_seconds=120,
                max_offer_attempts=5,
                high_risk_min_certification=3,
                high_risk_wider_radius_km=30.0,
                high_risk_offer_timeout_seconds=60,
            )
            db.add(cfg)
            db.flush()
            print("  [OK] MatchingConfig singleton")

        # ── Service Categories ─────────────────────────────────────────────────
        # IMPORTANT: These IDs are fixed/deterministic so that they always match
        # the DEFAULT_SERVICE_CATEGORIES hardcoded in the frontend BookService.tsx.
        # Render's ephemeral SQLite DB is recreated on every deploy, so seed must
        # produce the SAME UUIDs every time — never use generate_uuid() here.
        categories_data = [
            {"id": "b2929618-c561-4442-a767-ba2cb74b02c2", "name": "AC Service", "description": "Air conditioner installation, repair, and maintenance", "icon": "❄️", "price_per_minute": 3.0, "required_certification_level": 2},
            {"id": "39952130-5456-4b08-8ddd-08ee102b4578", "name": "Plumbing", "description": "Pipe repair, leak fixing, drainage, and water heaters", "icon": "🔧", "price_per_minute": 2.5, "required_certification_level": 1},
            {"id": "2544bf08-cd85-4756-8c4e-6386d6cd33a7", "name": "Electrical", "description": "Wiring, switchboard, MCB, fan, and light fittings", "icon": "⚡", "price_per_minute": 3.5, "required_certification_level": 3},
            {"id": "24fd4b95-07ed-443e-a1ca-e64a6fd9b7f2", "name": "Washing Machine", "description": "Washing machine repair and servicing", "icon": "🫧", "price_per_minute": 2.0, "required_certification_level": 1},
            {"id": "5ae2629c-e467-477c-9608-c6c330e72d35", "name": "Refrigerator", "description": "Refrigerator cooling, compressor, and general repair", "icon": "🧊", "price_per_minute": 2.5, "required_certification_level": 2},
            {"id": "c5ad066c-fc2a-4720-85c8-8fb603d7b5ce", "name": "Painting", "description": "Interior and exterior wall painting", "icon": "🎨", "price_per_minute": 1.5, "required_certification_level": 1},
            {"id": "e9510ae6-718f-48ab-b7c5-68c145052307", "name": "Carpentry", "description": "Furniture assembly, repair, and woodwork", "icon": "🪑", "price_per_minute": 2.0, "required_certification_level": 1},
        ]
        categories_added = 0
        for cd in categories_data:
            fixed_id = cd["id"]
            existing_by_id = db.query(ServiceCategory).filter(ServiceCategory.id == fixed_id).first()
            if existing_by_id:
                # Already present with correct ID — ensure it is active
                if not existing_by_id.is_active:
                    existing_by_id.is_active = True
                continue
            existing_by_name = db.query(ServiceCategory).filter(ServiceCategory.name == cd["name"]).first()
            if existing_by_name:
                # Present with wrong (random) ID from a previous seed run — update ID in place
                existing_by_name.id = fixed_id
                existing_by_name.is_active = True
            else:
                cat = ServiceCategory(
                    id=fixed_id,
                    name=cd["name"],
                    description=cd["description"],
                    icon=cd["icon"],
                    price_per_minute=cd["price_per_minute"],
                    required_certification_level=cd["required_certification_level"],
                    is_active=True,
                )
                db.add(cat)
                categories_added += 1
        db.flush()
        if categories_added > 0:
            print(f"  [OK] {categories_added} service categories added")

        # ── Admin user ────────────────────────────────────────────────────────
        existing_admin = db.query(User).filter(User.email == "admin@dispatchgrid.dev").first()
        if not existing_admin:
            admin_user = User(
                id=generate_uuid(),
                email="admin@dispatchgrid.dev",
                hashed_password=hash_password("Admin@1234"),
                role=UserRole.ADMIN,
                is_active=True,
            )
            db.add(admin_user)
            db.flush()
            print("  [OK] Admin user")

        # ── Customer users ────────────────────────────────────────────────────
        customers_data = [
            {"email": "alice@example.com", "name": "Alice Sharma", "phone": "9876543210",
             "lat": 12.9716, "lng": 77.5946},  # Bangalore center
            {"email": "bob@example.com", "name": "Bob Patel", "phone": "9876543211",
             "lat": 12.9352, "lng": 77.6245},
            {"email": "carol@example.com", "name": "Carol Nair", "phone": "9876543212",
             "lat": 12.9784, "lng": 77.6408},
        ]
        cust_count = 0
        for cd in customers_data:
            existing_cust = db.query(User).filter(User.email == cd["email"]).first()
            if not existing_cust:
                lat, lng = cd.pop("lat"), cd.pop("lng")
                u = User(
                    id=generate_uuid(),
                    email=cd["email"],
                    hashed_password=hash_password("Customer@1234"),
                    role=UserRole.CUSTOMER,
                    is_active=True,
                )
                db.add(u)
                db.flush()
                c = Customer(
                    id=generate_uuid(),
                    user_id=u.id,
                    name=cd["name"],
                    phone=cd["phone"],
                    saved_addresses=[{"label": "Home", "address": "Test Address", "lat": lat, "lng": lng}],
                    total_bookings=0,
                    avg_rating=0.0,
                )
                db.add(c)
                cust_count += 1
        db.flush()
        if cust_count > 0:
            print(f"  [OK] {cust_count} customer accounts")

        # ── Technician users ──────────────────────────────────────────────────
        techs_data = [
            {
                "email": "raj.tech@example.com", "name": "Raj Kumar",
                "phone": "9000000001", "certification_level": 4,
                "lat": 12.9716, "lng": 77.5946, "service_radius_km": 20.0,
                "bio": "AC specialist with 8 years experience",
                "avg_rating": 4.7, "total_jobs_completed": 120,
            },
            {
                "email": "priya.tech@example.com", "name": "Priya Singh",
                "phone": "9000000002", "certification_level": 3,
                "lat": 12.9352, "lng": 77.6245, "service_radius_km": 15.0,
                "bio": "Expert plumber, handles commercial & residential",
                "avg_rating": 4.5, "total_jobs_completed": 85,
            },
            {
                "email": "amit.tech@example.com", "name": "Amit Verma",
                "phone": "9000000003", "certification_level": 5,
                "lat": 12.9784, "lng": 77.6408, "service_radius_km": 25.0,
                "bio": "Master electrician, licensed for HV work",
                "avg_rating": 4.9, "total_jobs_completed": 200,
            },
            {
                "email": "sunita.tech@example.com", "name": "Sunita Devi",
                "phone": "9000000004", "certification_level": 2,
                "lat": 12.9500, "lng": 77.5700, "service_radius_km": 12.0,
                "bio": "Washing machine and appliance repair",
                "avg_rating": 4.3, "total_jobs_completed": 60,
            },
            {
                "email": "deepak.tech@example.com", "name": "Deepak Rao",
                "phone": "9000000005", "certification_level": 3,
                "lat": 12.9900, "lng": 77.6100, "service_radius_km": 18.0,
                "bio": "Multi-skilled: AC, refrigerator, electrical",
                "avg_rating": 4.6, "total_jobs_completed": 150,
            },
        ]
        tech_count = 0
        for td in techs_data:
            existing_tech = db.query(User).filter(User.email == td["email"]).first()
            if not existing_tech:
                u = User(
                    id=generate_uuid(),
                    email=td["email"],
                    hashed_password=hash_password("Tech@1234"),
                    role=UserRole.TECHNICIAN,
                    is_active=True,
                )
                db.add(u)
                db.flush()
                profile = TechnicianProfile(
                    id=generate_uuid(),
                    user_id=u.id,
                    name=td["name"],
                    phone=td["phone"],
                    bio=td["bio"],
                    certification_level=td["certification_level"],
                    lat=td["lat"],
                    lng=td["lng"],
                    service_radius_km=td["service_radius_km"],
                    max_concurrent_jobs=3,
                    is_online=True,       # Start online for testing
                    is_approved=True,     # Pre-approved
                    is_suspended=False,
                    avg_rating=td["avg_rating"],
                    total_jobs_completed=td["total_jobs_completed"],
                    total_jobs_rejected=0,
                    acceptance_rate=1.0,
                    total_earnings=round(td["total_jobs_completed"] * 45.0, 2),
                )
                db.add(profile)
                tech_count += 1
        db.flush()
        if tech_count > 0:
            print(f"  [OK] {tech_count} technician accounts (online + approved)")

        db.commit()
        print("\n[seed] [OK] V2 seed completed successfully!")
        print(TEST_CREDENTIALS)

    except Exception as exc:
        db.rollback()
        print(f"[seed] [ERROR] {exc}")
        raise
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()

