@echo off
echo Installing Python dependencies...
venv\Scripts\pip.exe install -r requirements.txt
if %ERRORLEVEL% EQU 0 (
    echo Dependencies installed successfully!
    venv\Scripts\python.exe quick_verify.py
) else (
    echo Failed to install dependencies
)
pause
