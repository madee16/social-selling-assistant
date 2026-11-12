@echo off
title Social Selling - Frontend (port 5173)
cd /d "%~dp0frontend"

echo ========================================
echo   Social Selling - Frontend launcher
echo ========================================
echo.

REM Kill any existing Vite process on port 5173 to avoid conflicts
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /R /C:":5173 .*LISTENING"') do (
    echo Stopping old frontend process %%p
    taskkill /PID %%p /F >nul 2>&1
)
timeout /t 1 >nul

echo Starting frontend: npm run dev
echo.
npm run dev

echo.
echo Frontend stopped. Press any key to close.
pause >nul