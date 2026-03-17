@echo off
REM High-performance mode (multi-worker) using the repo Python environment.
REM This is intended to be run via Task Scheduler or a dedicated service.

REM Configuration (adjust as needed):
set PORT=9091
set DB_PATH=p:\services\bible\bible_v2.db
set LOAD_IN_MEMORY=true
set WORKERS=5
set UVICORN_RELOAD=false

REM Locate the repo root (one level up from dist) and the venv Python.
set "REPO_ROOT=%~dp0.."
set "PYTHON=%REPO_ROOT%\.venv\Scripts\python.exe"

REM Ensure the python executable exists.
if not exist "%PYTHON%" (
  echo ERROR: Python not found: "%PYTHON%"
  exit /b 1
)

REM Ensure we run from the repo root so Python can import api.py.
cd /d "%REPO_ROOT%"

REM Logging configuration
set LOG_TO_FILE=false
set LOG_DIR="P:\services\bible\logs"

REM Create log directory (if enabled)
if /i "%LOG_TO_FILE%"=="true" (
  if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
  REM Try to create a timestamp using PowerShell; fall back to %DATE%/%TIME% if PowerShell isn't available.
  REM for /f "usebackq delims=" %%A in (`powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss" 2^>^&1`) do set "TIMESTAMP=%%A"
  if "%TIMESTAMP%"=="" (
    set "TS_DATE=%DATE:/=%"
    set "TS_TIME=%TIME::=%"
    set "TS_TIME=%TS_TIME: =0%"  REM pad hour if needed
    set "TIMESTAMP=%TS_DATE%_%TS_TIME%"
  )
  set "LOGFILE=%LOG_DIR%\bible_server_%TIMESTAMP%.log"
  echo Logging to %LOGFILE%
)

REM Run Uvicorn directly. Using --workers for high throughput.
if not DEFINED IS_MINIMIZED set IS_MINIMIZED=1 && start "" /min "%~0" %* && exit
if /i "%LOG_TO_FILE%"=="true" (
  "%PYTHON%" -m uvicorn api:app --host 0.0.0.0 --port %PORT% --workers %WORKERS% --log-level info >> "%LOGFILE%" 2>&1
) else (
  "%PYTHON%" -m uvicorn api:app --host 0.0.0.0 --port %PORT% --workers %WORKERS% --log-level info
)
