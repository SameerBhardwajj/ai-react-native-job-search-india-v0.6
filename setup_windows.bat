@echo off
setlocal EnableExtensions
cd /d %~dp0
if not exist .venv\Scripts\python.exe (
  py -3 -m venv .venv
  if errorlevel 1 (echo Python 3 was not found. Install Python 3.11+ and rerun this file.& exit /b 1)
  .venv\Scripts\python.exe -m pip install --upgrade pip
  .venv\Scripts\python.exe -m pip install -r requirements.txt
)
.venv\Scripts\python.exe -m rnjob init
schtasks /Create /TN "RNJobSearch - 10AM" /TR "\"%CD%\scheduled_refresh.bat\"" /SC DAILY /ST 10:00 /F
schtasks /Create /TN "RNJobSearch - 2PM" /TR "\"%CD%\scheduled_refresh.bat\"" /SC DAILY /ST 14:00 /F
schtasks /Create /TN "RNJobSearch - 8PM" /TR "\"%CD%\scheduled_refresh.bat\"" /SC DAILY /ST 20:00 /F
if errorlevel 1 echo WARNING: Windows Task Scheduler registration failed. Inspect Task Scheduler.
echo.
echo Setup complete. Scheduled refreshes: 10:00 AM, 2:00 PM, 8:00 PM (Windows local time).
echo Start the dashboard with start_dashboard.bat
pause
endlocal