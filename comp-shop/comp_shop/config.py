"""应用配置管理"""

import os
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """全局配置，从环境变量和.env文件读取"""

    # 数据库
    database_url: str = "sqlite:///./comp_shop.db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Claude API
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-20250514"

    # 代理配置
    proxy_url: str = ""
    proxy_username: str = ""
    proxy_password: str = ""

    # 飞书
    feishu_webhook_url: str = ""
    feishu_app_id: str = ""
    feishu_app_secret: str = ""

    # 爬虫参数
    scrape_delay_min: float = 2.0
    scrape_delay_max: float = 5.0
    scrape_max_retries: int = 3
    scrape_timeout: int = 30000

    # 存储路径
    image_storage_path: str = "./data/images"

    # API服务
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # 日志
    log_level: str = "INFO"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }

    @property
    def image_dir(self) -> Path:
        path = Path(self.image_storage_path)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def proxy_config(self) -> dict | None:
        if not self.proxy_url:
            return None
        proxy = {"server": self.proxy_url}
        if self.proxy_username:
            proxy["username"] = self.proxy_username
            proxy["password"] = self.proxy_password
        return proxy


settings = Settings()
