@echo off
setlocal EnableDelayedExpansion
title Logistics Verification Hub - Launcher

:: ── ANSI Color Codes ──
for /f %%a in ('echo prompt $E ^| cmd') do set "ESC=%%a"
set "RED=%ESC%[91m"
set "GREEN=%ESC%[92m"
set "YELLOW=%ESC%[93m"
set "CYAN=%ESC%[96m"
set "BOLD=%ESC%[1m"
set "NC=%ESC%[0m"

echo %CYAN%============================================================%NC%
echo %BOLD%%CYAN%             LOGISTICS VERIFICATION HUB - LAUNCHER%NC%
echo %CYAN%============================================================%NC%
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
    echo %RED%[ERROR] Virtual environment not found at %VENV_DIR%%NC%
    echo         Run: python -m venv .venv ^&^& .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)
echo %GREEN%[OK]   Virtual environment found%NC%

:: ── 1. Start Redis ──
echo.
echo %CYAN%[1/3] Starting Redis Server...%NC%
set REDIS_RUNNING=0

where redis-server >nul 2>nul
if !errorlevel! equ 0 (
    start "Redis Server" /min cmd /c "redis-server --port %REDIS_PORT%"
    timeout /t 2 /nobreak >nul
    echo %GREEN%[OK]   Redis started on port %REDIS_PORT%%NC%
    set REDIS_RUNNING=1
)

if !REDIS_RUNNING! equ 0 (
    echo %YELLOW%[WARN] redis-server not found in PATH.%NC%
    echo %YELLOW%       You can start Redis via Docker:%NC%
    echo %YELLOW%         docker run -d --name redis -p 6379:6379 redis%NC%
    echo %YELLOW%       Continuing without Redis ^(Celery will run in eager/sync mode^)...%NC%
    echo.
)

:: ── 2. Start Celery Worker ──
echo %CYAN%[2/3] Starting Celery Worker...%NC%
if !REDIS_RUNNING! equ 0 (
    echo %YELLOW%[SKIP] Celery worker skipped ^(no Redis^).%NC%
    echo %YELLOW%       Tasks will execute synchronously in-process.%NC%
) else (
    start "Celery Worker" /min cmd /c "%VENV_CELERY% -A app.celery_app worker --loglevel=info -P threads"
    timeout /t 2 /nobreak >nul
    echo %GREEN%[OK]   Celery worker started.%NC%
)

:: ── 3. Start FastAPI App ──
echo.
echo %CYAN%[3/3] Starting FastAPI App...%NC%
echo.
echo %CYAN%============================================================%NC%
echo   %GREEN%All services launched!%NC%
echo   App:    %BOLD%http://%APP_HOST%:%APP_PORT%%NC%
echo   Press %RED%Ctrl+C%NC% in this window to stop the app.
echo %CYAN%============================================================%NC%
echo.

%VENV_PYTHON% -m uvicorn app.main:app --host %APP_HOST% --port %APP_PORT%

:: ── Cleanup on exit ──
echo.
echo %CYAN%[INFO] App stopped. Cleaning up background services...%NC%
taskkill /FI "WINDOWTITLE eq Redis Server*" /F >nul 2>nul
taskkill /FI "WINDOWTITLE eq Celery Worker*" /F >nul 2>nul
echo %GREEN%[OK]   All services stopped.%NC%
pause
