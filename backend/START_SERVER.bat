@echo off
echo ========================================
echo DispatchGrid Backend Server
echo ========================================
echo.
echo Starting FastAPI server on http://localhost:8000
echo.
echo API Documentation will be available at:
echo   - Swagger UI: http://localhost:8000/docs
echo   - ReDoc:      http://localhost:8000/redoc
echo.
echo Press CTRL+C to stop the server
echo.
echo ========================================
echo.

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
