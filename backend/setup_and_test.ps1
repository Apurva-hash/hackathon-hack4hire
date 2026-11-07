# Setup and Test Script for Phase 5 & 6
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "DispatchGrid Phase 5 & 6 Setup & Test" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Check if venv exists
if (-not (Test-Path "venv")) {
    Write-Host "`nCreating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

# Activate venv
Write-Host "`nActivating virtual environment..." -ForegroundColor Yellow
. .\venv\Scripts\Activate.ps1

# Install dependencies
Write-Host "`nInstalling dependencies..." -ForegroundColor Yellow
pip install -q -r requirements.txt

# Check database
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Checking Database Status..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

python -c @"
from app.database import SessionLocal
from app.models import Job, Technician
db = SessionLocal()
try:
    jobs = db.query(Job).count()
    techs = db.query(Technician).count()
    print(f'Jobs in database: {jobs}')
    print(f'Technicians in database: {techs}')
    if jobs == 0 or techs == 0:
        print('\nWARNING: Database appears empty. Run seed_data.py first!')
finally:
    db.close()
"@

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Ready to test!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "`nNext steps:"
Write-Host "  1. If database is empty, run: python -m app.seed_data"
Write-Host "  2. Run tests: python test_scheduling.py"
Write-Host "  3. Start API: python -m uvicorn app.main:app --reload"
Write-Host ""
