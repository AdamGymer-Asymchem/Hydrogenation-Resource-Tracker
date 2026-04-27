@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
  echo [ERROR] Virtual environment not found at .venv\Scripts\activate.bat
  echo Run: python -m venv .venv
  pause
  exit /b 1
)

call ".venv\Scripts\activate.bat"

if "%PORTAL_PASSWORD%"=="" (
  set /p PORTAL_PASSWORD=Enter PORTAL_PASSWORD: 
)

if "%PORTAL_PASSWORD%"=="" (
  echo [ERROR] PORTAL_PASSWORD is required.
  pause
  exit /b 1
)

echo Starting Hydrogenation Work Tracker on http://0.0.0.0:8080 ...
waitress-serve --host 0.0.0.0 --port 8080 run:app

endlocal
