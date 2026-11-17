"""FastAPI 应用入口。"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db
from app.routers import ai_router, convert_router, search_router, sources_router, timeline_router

# 前端构建产物目录（用于单服务部署）
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """统一 HTTP 异常响应格式。"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """兜底异常处理：避免未捕获异常直接暴露堆栈。"""
    return JSONResponse(
        status_code=500,
        content={"detail": f"服务器内部错误: {exc}" if settings.debug else "服务器内部错误，请稍后重试"},
    )


app.include_router(sources_router, prefix="/api")
app.include_router(search_router, prefix="/api")
app.include_router(ai_router, prefix="/api")
app.include_router(timeline_router, prefix="/api")
app.include_router(convert_router, prefix="/api")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "app": settings.app_name}


# ===== 单服务部署：托管前端静态文件 =====
if FRONTEND_DIST.exists():
    # 挂载静态资源（js/css/images）
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str) -> FileResponse:
        """SPA 路由回退：非 /api 路径统一返回 index.html，交给前端路由处理。"""
        # API 路径不应到达此处（路由已在前注册），此处兜底
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        # 优先返回实际存在的静态文件（如 favicon.ico）
        file_path = FRONTEND_DIST / full_path
        if full_path and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIST / "index.html")
else:
    @app.get("/", include_in_schema=False)
    async def frontend_not_built() -> JSONResponse:
        return JSONResponse(
            status_code=200,
            content={
                "message": "前端未构建。请在 frontend 目录执行 npm run build，"
                "或将 FRONTEND_DIST 指向已构建的 dist 目录。"
            },
        )
