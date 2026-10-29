@echo off
cd /d %~dp0
if not exist .venv\Scripts\python.exe exit /b 1
.venv\Scripts\python.exe -m rnjob.scheduler >> scheduler.log 2>&1
exit /b %ERRORLEVEL%