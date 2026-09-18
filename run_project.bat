@echo off
setlocal enabledelayedexpansion
title WorkforceAI Platform Launcher

echo ======================================================================
echo    AI-Powered Dynamic Workforce ^& Resource Allocation System
echo    Machine Learning (Random Forest) + Optimization (Google OR-Tools)
echo ======================================================================
echo.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

:: Add Node.js and Python to PATH if needed
set "PATH=C:\Users\HP\AppData\Local\Programs\nodejs;C:\Program Files\nodejs;%SCRIPT_DIR%venv\Scripts;%PATH%"
set "PYTHONPATH=%SCRIPT_DIR%"

:: Check Python
if not exist "venv\Scripts\python.exe" (
    echo [INFO] Virtual environment not found. Creating venv...
    python -m venv venv
    call .\venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    python ml\train_model.py
    python backend\seed.py
)

:: Check ML model
if not exist "ml\models\workforce_rf_model.joblib" (
    echo [INFO] Training AI Random Forest model...
    .\venv\Scripts\python.exe ml\train_model.py
)

:: Check Database
if not exist "database\workforce.db" (
    echo [INFO] Seeding initial demo database...
    .\venv\Scripts\python.exe backend\seed.py
)

echo.
echo ======================================================================
echo Starting Backend and Frontend Servers...
echo ======================================================================
echo.

:: Start Backend in a separate window
start "WorkforceAI Backend (FastAPI)" cmd /k "cd /d %SCRIPT_DIR% && set PYTHONPATH=%SCRIPT_DIR% && .\venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload"

:: Start Frontend in a separate window
start "WorkforceAI Frontend (Vite React)" cmd /k "cd /d %SCRIPT_DIR%\frontend && set PATH=C:\Users\HP\AppData\Local\Programs\nodejs;C:\Program Files\nodejs;%PATH% && npm run dev"

echo.
echo ======================================================================
echo    PLATFORM SERVICES ACTIVE:
echo ======================================================================
echo    * Frontend UI:         http://localhost:5173
echo    * Backend REST API:    http://localhost:8000
echo    * Swagger API Docs:    http://localhost:8000/docs
echo    * System Health:       http://localhost:8000/api/health
echo ======================================================================
echo    DEMO LOGIN CREDENTIALS:
echo ======================================================================
echo    * Admin Account:    admin@demo.com    / admin123
echo    * Manager Account:  manager@demo.com  / manager123
echo    * Employee Account: employee@demo.com / employee123
echo ======================================================================
echo.
echo Press any key to exit this launcher window (servers will remain running).
pause >nul
