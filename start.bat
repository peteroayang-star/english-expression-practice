@echo off
rem English Practice Tool launcher - run local proxy server in this window
cd /d "%~dp0"

set "PY="
py -3 --version >nul 2>nul && set "PY=py -3"
if not defined PY python --version >nul 2>nul && set "PY=python"
if not defined PY (
  echo [ERROR] Python not found. Please install Python 3 first: https://www.python.org/downloads/
  pause
  exit /b
)

title English Trainer Server
start "" http://localhost:8080
timeout /t 1 /nobreak >nul
%PY% -u server.py

echo.
echo Server stopped. Press any key to close.
pause >nul
