@echo off
title ReadyZone
cd /d "%~dp0"
where python >nul 2>nul || (echo Python is not installed. Get it from https://www.python.org/downloads/ and tick "Add Python to PATH". & pause & exit /b 1)
if not exist venv (
  echo Setting up ReadyZone for the first time...
  python -m venv venv || (pause & exit /b 1)
)
call venv\Scripts\activate.bat
pip install -q -r requirements.txt || (pause & exit /b 1)
echo Starting ReadyZone at http://127.0.0.1:5000  (press Ctrl+C to stop)
start "" http://127.0.0.1:5000
python app.py
pause
