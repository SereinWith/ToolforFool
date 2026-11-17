#!/bin/bash
set -e
echo "============================================"
echo "  ToolForFool - 启动脚本 (Linux/Mac)"
echo "============================================"
echo

cd "$(dirname "$0")"

# 1. 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未找到 python3，请先安装 Python 3.13（PaddleOCR 不支持 3.14）"
    exit 1
fi

echo "[1/4] 检查 Python 版本..."
python3 --version

# 2. 创建虚拟环境
if [ ! -f "backend/.venv313/bin/python" ]; then
    echo "[2/4] 创建 Python 3.13 虚拟环境..."
    python3 -m venv backend/.venv313
else
    echo "[2/4] 虚拟环境已存在"
fi

# 3. 安装后端依赖
echo "[3/4] 安装后端依赖..."
backend/.venv313/bin/python -m pip install -r backend/requirements.txt

# 4. 构建前端
echo "[4/4] 构建前端..."
if [ ! -d "frontend/node_modules" ]; then
    echo "正在安装前端依赖..."
    cd frontend && npm install && cd ..
fi
cd frontend && npm run build && cd ..

echo
echo "============================================"
echo "  启动完成！访问 http://127.0.0.1:8000"
echo "============================================"
echo

# 启动后端
backend/.venv313/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
