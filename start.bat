@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (echo [ERROR] The application is not installed. Run install.bat first.& pause & exit /b 1)
call .venv\Scripts\activate.bat
python main.py
if errorlevel 1 (echo [ERROR] The application exited with code %errorlevel%.& pause)
