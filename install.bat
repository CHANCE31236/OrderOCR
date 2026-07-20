@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul || (echo [ERROR] Python was not found. Install Python 3.11, 3.12, or 3.13.& pause & exit /b 1)
py -3.11 -c "import sys; assert (3,11) <= sys.version_info < (3,14)" >nul 2>nul || (echo [ERROR] Python 3.11 to 3.13 is required. Python 3.11 is recommended.& pause & exit /b 1)
if not exist .venv py -3.11 -m venv .venv || (echo [ERROR] Failed to create the virtual environment.& pause & exit /b 1)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt || (echo [ERROR] Dependency installation failed. Check your network connection.& pause & exit /b 1)
echo Installation completed.
pause
