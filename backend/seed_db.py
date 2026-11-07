#!/usr/bin/env python
"""
Seed database with initial data.

Usage:
    python seed_db.py
"""

import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from app.seed.seed_data import generate_seed_data


def main():
    """Run seed data generation."""
    print("Starting database seeding...")
    
    db = SessionLocal()
    try:
        generate_seed_data(db)
        print("\n✅ Database seeded successfully!")
        print("\nYou can now:")
        print("  - Start the API: python -m uvicorn app.main:app --reload")
        print("  - Run tests: pytest")
        print("  - Generate schedule: POST /api/schedules/generate")
    except Exception as e:
        print(f"\n❌ Error seeding database: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
