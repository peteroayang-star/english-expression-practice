@echo off
rem English Practice Tool launcher - starts local proxy server and opens browser
cd /d "%~dp0"

rem try `py` first, then `python`
py -3 --version >nul 2>nul
if %errorlevel%==0 goto run_py
python --version >nul 2>nul
if %errorlevel%==0 goto run_python

echo [ERROR] Python not found. Please install Python 3 first: https://www.python.org/downloads/
pause
exit /b

:run_python
start "English Trainer Server" python -u server.py
goto open

:run_py
start "English Trainer Server" py -3 -u server.py

:open
timeout /t 1 /nobreak >nul
start "" http://localhost:8080
exit /b
