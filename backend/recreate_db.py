"""Script to drop and recreate the database schema, then reseed."""
import sys
sys.path.insert(0, '.')

from app.database import engine, Base
from app import models  # registers all models

print("Dropping all tables...")
Base.metadata.drop_all(bind=engine)
print("Creating all tables with current schema...")
Base.metadata.create_all(bind=engine)
print("Schema recreated OK")

from sqlalchemy import inspect
inspector = inspect(engine)
tables = inspector.get_table_names()
print(f"Tables: {sorted(tables)}")

cols = [c['name'] for c in inspector.get_columns('scheduling_runs')]
print(f"scheduling_runs columns: {cols}")

dcols = [c['name'] for c in inspector.get_columns('scheduling_decisions')]
print(f"scheduling_decisions columns: {dcols}")

acols = [c['name'] for c in inspector.get_columns('assignments')]
print(f"assignments columns: {acols}")
