@echo off
setlocal
cd /d %~dp0
if not exist .venv\Scripts\python.exe call setup_windows.bat
if not exist .venv\Scripts\python.exe exit /b 1
start "RN Job Dashboard" http://127.0.0.1:8000
.venv\Scripts\python.exe -m uvicorn rnjob.web:app --host 127.0.0.1 --port 8000
endlocal