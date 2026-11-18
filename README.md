# ToolForFool

面向古籍研究需求的轻量化文献阅读辅助工具。支持网页抓取入库、关键词检索、AI 语义搜索、OCR 文字识别、繁简转换、人物时间线等功能。

## ✨ 功能特性

- **抓取入库**：输入古籍 URL，自动抓取标题、概述、正文并存储（支持古诗文网、识典古籍等站点）
- **关键词检索**：多关键词检索已入库文献，导出 JSON / CSV / TXT
- **AI 语义搜索**：基于大模型扩展近义词/别称，扩大检索范围（未配置 API Key 时使用内置同义词典）
- **OCR 文字识别**：上传古籍图片识别文字，自动选择视觉大模型 / 百度云 OCR / 本地 PaddleOCR
- **自动繁转简**：录入古籍时自动转为简体存储（可通过 `AUTO_SIMPLIFY=false` 关闭）
- **繁简转换**：繁体 ↔ 简体互转，集成于 OCR 结果、文献详情、搜索选段及独立工具页
- **人物时间线**：自动从文献中提取人物与事件，按人物归档展示

## 🛠 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.12+ / FastAPI / SQLAlchemy 2.0 / SQLite |
| 前端 | Vue 3 + TypeScript + Vite + Element Plus + Pinia + Vue Router |
| OCR | 视觉大模型 / 百度云 OCR / PaddleOCR（自动优先级） |
| 繁简转换 | opencc-python-reimplemented |
| AI | 豆包 / OpenAI 兼容接口 |

## 🚀 本地部署

### 前置要求

- Python 3.9 - 3.13（使用 OCR 功能必须 ≤ 3.13，PaddlePaddle 暂不支持 3.14）
- Node.js 18+

### 一键启动

**Windows：**
```bash
start.bat
```

**Linux / macOS：**
```bash
chmod +x start.sh
./start.sh
```

启动后访问 http://127.0.0.1:8000

### 手动部署

```bash
# 1. 创建虚拟环境
cd backend
python -m venv .venv
.venv\Scripts\activate    # Windows
# source .venv/bin/activate  # Linux/Mac

# 2. 安装核心依赖
pip install -r requirements.txt

# 3. （可选）安装 OCR 依赖
pip install -r requirements-ocr.txt

# 4. 配置环境变量
cp .env.example .env   # 按需修改

# 5. 构建前端
cd ../frontend
npm install
npm run build

# 6. 启动后端（单服务，托管前端静态文件）
cd ../backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## ☁️ Render 部署

### 方式一：使用 render.yaml（推荐）

1. 将本仓库推送到 GitHub
2. 登录 [Render](https://render.com)，点击 **New → Web Service**
3. 选择你的 GitHub 仓库
4. Render 会自动识别 `render.yaml`，点击 **Apply**
5. 等待构建完成后访问分配的域名

### 方式二：手动配置

| 配置项 | 值 |
|--------|-----|
| Runtime | Python 3 |
| Build Command | `cd frontend && npm install && npm run build && cd .. && pip install -r backend/requirements.txt && pip install -r backend/requirements-ocr.txt || true` |
| Start Command | `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Python Version | 3.12.6 |

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEBUG` | `false` | 调试模式 |
| `DATABASE_URL` | `sqlite:///./data/app.db` | 数据库连接（Render 上 SQLite 为临时存储） |
| `CORS_ORIGINS` | `*` | 跨域来源，逗号分隔 |
| `AI_PROVIDER` | `doubao` | AI 服务商：`doubao` 或 `openai` |
| `AI_API_KEY` | （空） | AI API 密钥 |
| `AI_BASE_URL` | 豆包接口地址 | AI 接口地址 |
| `AI_MODEL` | `doubao-lite-4k` | 模型名称 |
| `OCR_PROVIDER` | `paddle` | OCR 服务商：`paddle` 或 `cloud` |

> **注意**：Render 免费实例会休眠，且 SQLite 数据在重启后会丢失。如需持久化数据，建议接入 PostgreSQL。

## 📁 项目结构

```
ToolForFool/
├── backend/
│   ├── app/
│   │   ├── crawler/      # 站点爬虫适配器
│   │   ├── models/       # SQLAlchemy 数据模型
│   │   ├── routers/      # API 路由
│   │   ├── schemas/      # Pydantic 数据模型
│   │   ├── services/     # 业务服务（AI/OCR/检索/转换/时间线）
│   │   ├── config.py     # 配置
│   │   ├── database.py   # 数据库连接
│   │   └── main.py       # 应用入口
│   ├── requirements.txt      # 核心依赖
│   ├── requirements-ocr.txt  # OCR 可选依赖
│   └── .env.example          # 环境变量模板
├── frontend/
│   ├── src/
│   │   ├── api/         # API 请求封装
│   │   ├── views/       # 页面组件
│   │   ├── router/      # 路由
│   │   └── App.vue      # 根组件
│   └── package.json
├── render.yaml          # Render 部署配置
├── Dockerfile           # Docker 构建
├── start.bat / start.sh # 一键启动脚本
└── README.md
```

## 📤 上传到 GitHub

```bash
git init
git add .
git commit -m "feat: init ToolForFool"
git branch -M main
git remote add origin https://github.com/你的用户名/ToolForFool.git
git push -u origin main
```

## 📄 License

MIT
