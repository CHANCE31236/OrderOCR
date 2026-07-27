@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (echo [错误] 尚未安装，请先运行 install.bat。& pause & exit /b 1)
call .venv\Scripts\activate.bat
python main.py
if errorlevel 1 (echo [错误] 程序异常退出，错误码 %errorlevel%。& pause)

