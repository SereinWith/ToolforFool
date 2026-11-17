"""路由聚合。"""
from app.routers.ai import router as ai_router
from app.routers.convert import router as convert_router
from app.routers.search import router as search_router
from app.routers.sources import router as sources_router
from app.routers.timeline import router as timeline_router

__all__ = ["sources_router", "search_router", "ai_router", "timeline_router", "convert_router"]
