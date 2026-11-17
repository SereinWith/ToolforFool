"""应用配置。"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "ToolForFool"
    debug: bool = False

    # 数据库：第一二档使用 SQLite，单文件便于本地存储与导出
    database_url: str = "sqlite:///./data/app.db"

    # 爬虫默认请求头与间隔（秒）
    crawler_user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
    crawler_delay: float = 1.0
    crawler_timeout: float = 20.0

    # 跨域：生产环境默认允许所有来源（前后端同域部署时无需跨域）；
    # 可通过 CORS_ORIGINS 环境变量设置逗号分隔的来源列表，如 "http://a.com,http://b.com"
    cors_origins: list[str] = ["*"]

    # ===== AI 服务配置（阶段三）=====
    # 支持的 provider: doubao（豆包/火山引擎）、openai（OpenAI 兼容接口）
    ai_provider: str = "doubao"
    ai_api_key: str = ""
    ai_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    ai_model: str = "doubao-lite-4k"
    # 单次请求超时（秒）
    ai_timeout: float = 30.0

    # ===== OCR 配置（阶段三）=====
    # ocr_provider: paddle（本地 PaddleOCR）、cloud（云 API，预留）
    ocr_provider: str = "paddle"
    ocr_api_key: str = ""


settings = Settings()
