"""应用配置管理"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # 应用基础配置
    app_name: str = "NicePT Helper"
    debug: bool = True
    secret_key: str = "change-this-to-a-random-secret-key"
    access_token_expire_minutes: int = 1440  # 24小时

    # 数据库配置
    database_url: str = "sqlite+aiosqlite:///./nicept.db"

    # NicePT 站点配置
    site_url: str = ""  # 例如 https://nicept.net
    site_passkey: str = ""

    # 请求配置（防风控）
    request_timeout: int = 30
    request_delay: float = 2.0  # 请求间隔秒数
    max_retries: int = 3
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )

    # 日志配置
    log_dir: str = "logs"
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
