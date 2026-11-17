@echo off
chcp 65001 >nul
echo ============================================
echo   ToolForFool - 启动脚本 (Windows)
echo ============================================
echo.

REM 切换到项目根目录
cd /d "%~dp0"

REM 1. 检查 Python
where python >nul 2>nul
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.13（PaddleOCR 不支持 3.14）
    pause
    exit /b 1
)

echo [1/4] 检查 Python 版本...
python --version

REM 2. 创建并激活虚拟环境（如果不存在）
if not exist "backend\.venv313\Scripts\python.exe" (
    echo [2/4] 创建 Python 3.13 虚拟环境...
    echo 提示：如系统无 Python 3.13，请先安装 uv：pip install uv，然后 uv python install 3.13
    python -m venv backend\.venv313
) else (
    echo [2/4] 虚拟环境已存在
)

REM 3. 安装后端依赖
echo [3/4] 安装后端依赖...
backend\.venv313\Scripts\python.exe -m pip install -r backend\requirements.txt
if errorlevel 1 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)

REM 4. 构建前端
echo [4/4] 构建前端...
if not exist "frontend\node_modules" (
    echo 正在安装前端依赖...
    cd frontend
    call npm install
    cd ..
)
cd frontend
call npm run build
cd ..

echo.
echo ============================================
echo   启动完成！访问 http://127.0.0.1:8000
echo ============================================
echo.

REM 启动后端（单服务，托管前端静态文件）
backend\.venv313\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
