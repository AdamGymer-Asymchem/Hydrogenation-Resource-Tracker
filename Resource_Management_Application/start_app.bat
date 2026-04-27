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

if exist "deployment.env" (
  for /f "usebackq tokens=1,* delims==" %%A in ("deployment.env") do (
    if not "%%A"=="" if not "%%A:~0,1%"=="#" if not "%%B"=="" set "%%A=%%B"
  )
)

if "%PORT%"=="" (
  set "PORT=17001"
)

if "%PORTAL_PASSWORD%"=="" (
  set "PORTAL_PASSWORD=LotsOfBubbles"
)

if "%PORTAL_PASSWORD%"=="" (
  echo [ERROR] PORTAL_PASSWORD is required.
  pause
  exit /b 1
)

echo Starting Hydrogenation Work Tracker on http://0.0.0.0:%PORT% ...
waitress-serve --host 0.0.0.0 --port %PORT% run:app

endlocal
