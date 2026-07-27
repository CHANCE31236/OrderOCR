@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul || (echo [错误] 未找到 Python。请安装 Python 3.11 或 3.12。& pause & exit /b 1)
py -3.11 -c "import sys; assert (3,11) <= sys.version_info < (3,14)" >nul 2>nul || (echo [错误] 需要 Python 3.11 到 3.13，推荐 3.11。& pause & exit /b 1)
if not exist .venv py -3.11 -m venv .venv || (echo [错误] 创建虚拟环境失败。& pause & exit /b 1)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt || (echo [错误] 依赖安装失败，请检查网络。& pause & exit /b 1)
echo 安装完成。
pause

