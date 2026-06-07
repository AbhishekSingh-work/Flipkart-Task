@echo off
title Logistics Verification Hub - Launcher
color 0A

echo ============================================================
echo             LOGISTICS VERIFICATION HUB - LAUNCHER
echo ============================================================
echo.

:: ── Configuration ──
set VENV_DIR=.venv
set REDIS_PORT=6379
set APP_HOST=127.0.0.1
set APP_PORT=8000

:: ── Activate venv path ──
set VENV_PYTHON=%VENV_DIR%\Scripts\python.exe
set VENV_CELERY=%VENV_DIR%\Scripts\celery.exe

:: ── Check venv exists ──
if not exist "%VENV_PYTHON%" (
    echo [ERROR] Virtual environment not found at %VENV_DIR%
    echo         Run: python -m venv .venv ^&^& .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

:: ── 1. Start Redis ──
echo [1/3] Starting Redis Server...
where redis-server >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARN] redis-server not found in PATH.
    echo        Install Redis for Windows or use WSL.
    echo        Continuing without Redis (Celery will run in eager/sync mode)...
    echo.
    set REDIS_PID=NONE
) else (
    start "Redis Server" /min cmd /c "redis-server --port %REDIS_PORT%"
    timeout /t 2 /nobreak >nul
    echo [OK]   Redis started on port %REDIS_PORT%
    set REDIS_PID=STARTED
)

:: ── 2. Start Celery Worker ──
echo [2/3] Starting Celery Worker...
if "%REDIS_PID%"=="NONE" (
    echo [SKIP] Celery worker skipped (no Redis).
    echo        Tasks will execute synchronously in-process.
) else (
    start "Celery Worker" /min cmd /c "%VENV_CELERY% -A app.celery_app worker --loglevel=info -P threads"
    timeout /t 2 /nobreak >nul
    echo [OK]   Celery worker started.
)

:: ── 3. Start FastAPI App ──
echo [3/3] Starting FastAPI App...
echo.
echo ============================================================
echo   All services launched! App at http://%APP_HOST%:%APP_PORT%
echo   Press Ctrl+C in this window to stop the app.
echo   Close the Redis / Celery windows to stop those services.
echo ============================================================
echo.

%VENV_PYTHON% -m uvicorn app.main:app --host %APP_HOST% --port %APP_PORT%

:: ── Cleanup on exit ──
echo.
echo [INFO] App stopped. Cleaning up background services...
taskkill /FI "WINDOWTITLE eq Redis Server*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Celery Worker*" /F >nul 2>&1
echo [OK]   All services stopped.
pause
