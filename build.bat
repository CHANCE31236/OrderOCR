@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (echo [ERROR] The application is not installed. Run install.bat first.& pause & exit /b 1)
call .venv\Scripts\activate.bat
python -m pip install -r requirements-dev.txt || (echo [ERROR] Development dependency installation failed.& pause & exit /b 1)
python -m pytest || (echo [ERROR] Tests failed. The build was stopped.& pause & exit /b 1)
python -m PyInstaller --noconfirm --clean --onefile --windowed --name "OrderOCR" --icon assets\app.ico --add-data "config;config" --add-data "assets;assets" --collect-all rapidocr_onnxruntime --hidden-import keyring.backends.Windows main.py || (echo [ERROR] Packaging failed.& pause & exit /b 1)
if not exist dist\config mkdir dist\config
xcopy /E /I /Y config dist\config >nul
xcopy /E /I /Y assets dist\assets >nul
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\create_shortcut.ps1 -TargetPath "%~dp0dist\OrderOCR.exe" -ShortcutPath "%USERPROFILE%\Desktop\OrderOCR.lnk" -WorkingDirectory "%~dp0dist"
if errorlevel 1 (echo [ERROR] Failed to create the desktop shortcut.& pause & exit /b 1)
echo Packaging completed.
pause
