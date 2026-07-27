@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (echo [错误] 尚未安装，请先运行 install.bat。& pause & exit /b 1)
call .venv\Scripts\activate.bat
python -m pip install -r requirements-dev.txt || (echo [错误] 开发依赖安装失败。& pause & exit /b 1)
python -m pytest || (echo [错误] 测试未通过，已停止打包。& pause & exit /b 1)
python -m PyInstaller --noconfirm --clean --onefile --windowed --name "订单纸单识别器" --icon assets\app.ico --add-data "config;config" --add-data "assets;assets" --collect-all rapidocr_onnxruntime --hidden-import keyring.backends.Windows main.py || (echo [错误] 打包失败。& pause & exit /b 1)
if not exist dist\config mkdir dist\config
xcopy /E /I /Y config dist\config >nul
xcopy /E /I /Y assets dist\assets >nul
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\create_shortcut.ps1 -TargetPath "%~dp0dist\订单纸单识别器.exe" -ShortcutPath "%USERPROFILE%\Desktop\订单纸单识别器.lnk" -WorkingDirectory "%~dp0dist"
if errorlevel 1 (echo [错误] 桌面快捷方式创建失败。& pause & exit /b 1)
echo 打包完成。
pause
