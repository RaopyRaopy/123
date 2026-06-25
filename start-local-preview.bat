@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Python virtual environment was not found at .venv\Scripts\python.exe
  echo Please create the environment and install requirements first.
  pause
  exit /b 1
)

echo Starting Smart Travel local preview...
echo URL: http://127.0.0.1:8000/
echo.
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

echo.
echo Server stopped.
pause
