@echo off
echo Running DB migration - adding email and phone columns...
cd /d "%~dp0"
python add_columns.py
if %errorlevel% equ 0 (
    echo Migration complete! You can now start the server.
) else (
    echo Migration failed. Try running: python add_columns.py
)
pause

