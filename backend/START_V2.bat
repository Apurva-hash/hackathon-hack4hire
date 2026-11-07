@echo off
echo DispatchGrid v2 — Setup and Run
echo =================================

cd /d "%~dp0"

echo.
echo [1/3] Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Could not activate venv.
    pause
    exit /b 1
)

echo [2/3] Seeding test database...
python -m app.seed.v2_seed

echo.
echo [3/3] Starting DispatchGrid API server...
echo.
echo   =========================================
echo   Swagger UI:  http://localhost:8000/docs
echo   Health:      http://localhost:8000/api/health
echo   =========================================
echo.
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
