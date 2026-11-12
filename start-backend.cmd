@echo off
title Social Selling - Backend (port 8000)
cd /d "%~dp0backend"

echo ========================================
echo   Social Selling - Backend launcher
echo ========================================
echo.

REM Kill any existing backend on port 8000 to avoid conflicts
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /R /C:":8000 .*LISTENING"') do (
    echo Stopping old backend process %%p
    taskkill /PID %%p /F >nul 2>&1
)
timeout /t 1 >nul

echo Starting backend: python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
echo.
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

echo.
echo Backend stopped. Press any key to close.
pause >nul